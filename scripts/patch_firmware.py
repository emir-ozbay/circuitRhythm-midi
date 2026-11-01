"""Safe Circuit Rhythm firmware patcher and SysEx packager.

Ensures strict validation against stock 5706 firmware:
- Enforces SHA-256 hash validation on input SysEx and extracted image.
- Prevents overwriting stock firmware or input file.
- Enforces application bounds [0x08010000, 0x08080000) and strictly protects
  the Cortex-M vector table and identity area [0x08010000, 0x08010200).
- Supports in-place patches within [0x08010200, 0x0806A570) and code-cave
  extension patches within [0x0806A570, 0x08080000).
- Verifies original bytes at target addresses before applying changes.
- Detects and rejects overlapping patch ranges.
- Recomputes MPEG-2 CRC-32 and packages valid SysEx frames.
- Generates a detailed diff and manifest JSON report.

Physical device safety: This tool operates purely offline on host files;
no MIDI/USB transmission or device flashing is performed.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import datetime
import hashlib
import json
from pathlib import Path
import struct
import sys
from typing import Optional, Sequence

# Canonical stock 5706 constants
STOCK_SYX_SHA256 = "11d604a6b6bef0d41378da03718658c7fe9c959ac24e7fef6563796b9932afaf"
STOCK_IMAGE_SHA256 = "d5b9ff5dadf2e284f80d69ecb7087486cf0df315a697bed8272af9de0e90df15"
STOCK_IMAGE_SIZE = 0x5A570  # 370032 bytes
STOCK_CRC32_MPEG2 = 0x9EEE802C
APP_BASE = 0x08010000
APP_END = APP_BASE + STOCK_IMAGE_SIZE  # 0x0806A570
FLASH_END = 0x08080000  # 0x08080000 (maximum application flash boundary; 0x70000 = 458,752 bytes)
MAX_IMAGE_SIZE = FLASH_END - APP_BASE  # 0x70000 (458,752 bytes)

# Vector table & identity protection: the first 0x200 bytes (512 bytes)
# contains the ARM Cortex-M vector table (SP, Reset, NMI, HardFault, handlers)
# and Novation identity string ("DR1.1.5143.5706"). Never patch this region.
VECTOR_TABLE_SIZE = 0x200
APP_WRITABLE_START = APP_BASE + VECTOR_TABLE_SIZE  # 0x08010200
APP_WRITABLE_END = APP_END  # 0x0806A570 (stock writable boundary)

# SysEx Protocol Constants
SYX_PREFIX = bytes([0xF0, 0x00, 0x20, 0x29, 0x00])
CMD_INIT = 0x71
CMD_HEADER = 0x7C
CMD_WRITE = 0x72
CMD_FINISH = 0x73
PRODUCT_RHYTHM = 0x63
BLOCK_SIZE = 32
BLOCK_7BIT_SIZE = 37


# Custom Exceptions
class PatcherError(Exception):
    """Base exception for all firmware patcher errors."""
    pass


class InputHashMismatchError(PatcherError):
    """Raised when the input SysEx or image hash does not match expected stock."""
    pass


class DestinationSafetyError(PatcherError):
    """Raised when attempting to overwrite the stock firmware or input file."""
    pass


class AddressBoundsError(PatcherError):
    """Raised when a patch address falls outside allowed application bounds or touches protected areas."""
    pass


class RangeOverlapError(PatcherError):
    """Raised when two or more patch ranges overlap."""
    pass


class OriginalBytesMismatchError(PatcherError):
    """Raised when original bytes in the image do not match expected bytes."""
    pass


class SysExFormatError(PatcherError):
    """Raised when SysEx messages are corrupt, malformed, or fail CRC."""
    pass


@dataclass(frozen=True)
class PatchHunk:
    """Represents a discrete contiguous in-place binary patch."""
    address: int
    expected: bytes
    replacement: bytes
    name: str = ""

    def __post_init__(self):
        if not isinstance(self.address, int):
            raise TypeError("Patch address must be an integer")
        if not isinstance(self.expected, (bytes, bytearray)):
            raise TypeError("Patch expected must be bytes")
        if not isinstance(self.replacement, (bytes, bytearray)):
            raise TypeError("Patch replacement must be bytes")
        if len(self.expected) != len(self.replacement):
            raise ValueError(
                f"Patch '{self.name}': in-place patch requires expected and replacement "
                f"lengths to match ({len(self.expected)} != {len(self.replacement)})"
            )
        if len(self.expected) == 0:
            raise ValueError(f"Patch '{self.name}': patch length cannot be zero")

    @property
    def length(self) -> int:
        return len(self.expected)

    @property
    def end_address(self) -> int:
        return self.address + self.length

    @property
    def offset(self) -> int:
        return self.address - APP_BASE


# Canonical M2 diagnostic candidate: palette 31 -> 30 on step press color handler
M2_CANDIDATE_PATCH = PatchHunk(
    address=0x0805CF68,
    expected=bytes([0x1F, 0x22]),  # movs r2, #31
    replacement=bytes([0x1E, 0x22]),  # movs r2, #30
    name="step_held_led_palette_31_to_30",
)


# MPEG-2 CRC-32 Implementation
def _build_crc_table() -> list[int]:
    table = []
    for i in range(256):
        c = i << 24
        for _ in range(8):
            c = ((c << 1) ^ 0x04C11DB7) if (c & 0x80000000) else (c << 1)
        table.append(c & 0xFFFFFFFF)
    return table


_CRC_TABLE = _build_crc_table()


def crc32_mpeg2(data: bytes) -> int:
    """Computes CRC-32/MPEG-2 (poly=0x04C11DB7, init=0xFFFFFFFF, refin=False, refout=False, xorout=0)."""
    crc = 0xFFFFFFFF
    for b in data:
        crc = ((crc << 8) & 0xFFFFFFFF) ^ _CRC_TABLE[(crc >> 24) ^ b]
    return crc


# 7-bit SysEx Packing / Unpacking
def unpack7(payload: bytes) -> bytes:
    """Decodes 37 bytes of 7-bit MIDI SysEx payload into 32 bytes of binary data."""
    if len(payload) != BLOCK_7BIT_SIZE or any(b > 127 for b in payload):
        raise SysExFormatError("Invalid 7-bit SysEx payload length or non-7-bit byte")
    if payload[-1] & 7:
        raise SysExFormatError("Non-zero padding bits in 7-bit block")
    bits = "".join(f"{b:07b}" for b in payload)
    bits = bits[: len(bits) // 8 * 8]
    return int(bits, 2).to_bytes(len(bits) // 8, "big")


def pack7(block: bytes) -> bytes:
    """Encodes 32 bytes of binary data into 37 bytes of 7-bit MIDI SysEx payload."""
    if len(block) != BLOCK_SIZE:
        raise ValueError(f"Block size must be exactly {BLOCK_SIZE} bytes")
    bits = "".join(f"{b:08b}" for b in block)
    bits += "0" * (-len(bits) % 7)
    return bytes(int(bits[i : i + 7], 2) for i in range(0, len(bits), 7))


def split_syx(syx: bytes) -> list[bytes]:
    """Splits raw SysEx byte stream into individual F0..F7 messages."""
    msgs: list[bytes] = []
    i = 0
    while i < len(syx):
        if syx[i:i+5] != SYX_PREFIX:
            raise SysExFormatError(f"Unexpected bytes between frames at {i:#x}")
        try:
            start = i
            end = syx.index(0xF7, start)
        except ValueError:
            break
        msg = syx[start : end + 1]
        if not msg.startswith(SYX_PREFIX):
            raise SysExFormatError(f"Message at offset {start} does not start with Novation prefix")
        if len(msg) < 7 or any(b > 127 for b in msg[1:-1]):
            raise SysExFormatError(f"Invalid frame at offset {start:#x}")
        msgs.append(msg)
        i = end + 1
    if not msgs or i != len(syx):
        raise SysExFormatError(f"Malformed SysEx stream: parsed {len(msgs)} messages, {len(syx) - i} trailing bytes")
    return msgs


def nibbles_to_int(b: bytes) -> int:
    v = 0
    for n in b:
        if n > 15:
            raise SysExFormatError("Invalid nibble value > 15")
        v = (v << 4) | n
    return v


def int_to_nibbles(v: int, count: int = 8) -> bytes:
    return bytes((v >> (4 * (count - 1 - i))) & 0xF for i in range(count))


def unpack_syx(syx: bytes, allow_extended: bool = False) -> dict:
    """Parses and validates a Novation Circuit Rhythm firmware .syx file.

    Args:
        syx: Raw SysEx byte stream.
        allow_extended: If False (default), image size must equal STOCK_IMAGE_SIZE.
            If True, accepts extended images in [STOCK_IMAGE_SIZE, FLASH_END - APP_BASE]
            that are 4-byte aligned.
    """
    msgs = split_syx(syx)
    if len(msgs) < 4:
        raise SysExFormatError("Firmware SysEx must have at least INIT, HEADER, WRITE, and FINISH messages")
    if msgs[0][5] != CMD_INIT or msgs[1][5] != CMD_HEADER or msgs[-1][5] != CMD_FINISH:
        raise SysExFormatError("Invalid message sequence: expected INIT, HEADER, WRITE..., FINISH")
    if any(m[5] != CMD_WRITE for m in msgs[2:-1]):
        raise SysExFormatError("Unexpected command inside payload stream")

    init_payload = msgs[0][6:-1]
    header_payload = msgs[1][6:-1]

    if len(init_payload) != 8 or init_payload[0] != 1 or init_payload[1] != PRODUCT_RHYTHM:
        raise SysExFormatError("Unexpected INIT payload or device ID (expected Rhythm 0x63)")
    if len(header_payload) != 23 or header_payload[0] != 0:
        raise SysExFormatError("Unexpected HEADER payload length or target")

    size = nibbles_to_int(header_payload[7:15])
    crc = nibbles_to_int(header_payload[15:23])

    max_image_size = FLASH_END - APP_BASE
    if not allow_extended:
        if size != STOCK_IMAGE_SIZE:
            raise SysExFormatError(f"Unexpected image size in header: {size:#x} (expected stock {STOCK_IMAGE_SIZE:#x})")
    else:
        if size < STOCK_IMAGE_SIZE or size > max_image_size or (size % 4 != 0):
            raise SysExFormatError(
                f"Invalid extended image size in header: {size:#x} "
                f"(expected between {STOCK_IMAGE_SIZE:#x} and {max_image_size:#x}, 4-byte aligned)"
            )

    blocks = []
    # Block 0 is packed in the final FINISH message
    blocks.append(unpack7(msgs[-1][6:-1]))
    # Blocks 1..N-1 are packed in WRITE messages
    for m in msgs[2:-1]:
        blocks.append(unpack7(m[6:-1]))

    data = b"".join(blocks)
    if len(data) != (size + 31) // 32 * 32:
        raise SysExFormatError("Payload block count does not match header size")
    if data[size:] != b"\xFF" * (len(data) - size):
        raise SysExFormatError("Non-FF bytes beyond declared image size")
    if len(data) < size:
        raise SysExFormatError(f"Truncated SysEx payload: decoded {len(data)} bytes, header specifies {size}")

    image = data[:size]
    computed_crc = crc32_mpeg2(image)
    if computed_crc != crc:
        raise SysExFormatError(f"SysEx CRC mismatch: header {crc:#010x} != computed {computed_crc:#010x}")

    return {
        "device": init_payload[1],
        "init": init_payload,
        "header_prefix": header_payload[:7],
        "size": size,
        "crc": crc,
        "image": image,
        "crc_ok": True,
    }


def pack_syx(image: bytes, init: bytes, header_prefix: bytes) -> bytes:
    """Builds a valid Novation Circuit Rhythm firmware .syx from image bytes.

    Accepts image sizes between STOCK_IMAGE_SIZE and FLASH_END - APP_BASE (multiple of 4).
    Writes updated image size and MPEG-2 CRC-32 into the HEADER message.
    """
    max_image_size = FLASH_END - APP_BASE
    if len(init) != 8 or init[:2] != bytes([1, PRODUCT_RHYTHM]) or any(b > 127 for b in init):
        raise SysExFormatError("Invalid Rhythm INIT metadata")
    if len(header_prefix) != 7 or header_prefix[0] != 0 or any(b > 127 for b in header_prefix):
        raise SysExFormatError("Invalid application HEADER metadata")
    if (
        not image
        or len(image) < STOCK_IMAGE_SIZE
        or len(image) > max_image_size
        or (len(image) % 4 != 0)
    ):
        raise ValueError(
            f"Image size must be between {STOCK_IMAGE_SIZE:#x} and {max_image_size:#x} bytes "
            f"and a multiple of 4 bytes (got {len(image) if image else 0} bytes)"
        )
    crc = crc32_mpeg2(image)
    out: list[bytes] = []

    # INIT message
    out.append(SYX_PREFIX + bytes([CMD_INIT]) + init + b"\xF7")

    # HEADER message
    header_body = header_prefix + int_to_nibbles(len(image)) + int_to_nibbles(crc)
    out.append(SYX_PREFIX + bytes([CMD_HEADER]) + header_body + b"\xF7")

    # Pad image to 32-byte blocks
    padded = image + b"\xFF" * (-len(image) % BLOCK_SIZE)
    blocks = [padded[i : i + BLOCK_SIZE] for i in range(0, len(padded), BLOCK_SIZE)]

    # WRITE messages: blocks 1..N-1
    for blk in blocks[1:]:
        out.append(SYX_PREFIX + bytes([CMD_WRITE]) + pack7(blk) + b"\xF7")

    # FINISH message: block 0 (contains Cortex-M vector table)
    out.append(SYX_PREFIX + bytes([CMD_FINISH]) + pack7(blocks[0]) + b"\xF7")

    syx_result = b"".join(out)

    # Round-trip sanity check to ensure output is 100% decodable and CRC matches
    verification = unpack_syx(syx_result, allow_extended=True)
    if verification["image"] != image or verification["crc"] != crc:
        raise SysExFormatError("Sanity verification of newly packed SysEx failed")

    return syx_result


# Validation and Safety Checks
def validate_input_syx(raw_syx: bytes) -> None:
    """Asserts that the input SysEx matches the pinned stock SHA-256 hash."""
    h = hashlib.sha256(raw_syx).hexdigest()
    if h != STOCK_SYX_SHA256:
        raise InputHashMismatchError(
            f"Input SysEx SHA-256 mismatch!\n  Expected: {STOCK_SYX_SHA256}\n  Got:      {h}"
        )


def validate_destination_paths(
    input_path: Path,
    output_path: Path,
    stock_path: Optional[Path] = None,
) -> None:
    """Prevents overwriting the input file or the canonical stock firmware file."""
    in_res = input_path.resolve()
    out_res = output_path.resolve()

    if in_res == out_res or (in_res.exists() and out_res.exists() and in_res.samefile(out_res)):
        raise DestinationSafetyError(
            f"Output path cannot be identical to input path: {out_res}"
        )

    if stock_path is not None:
        stock_res = stock_path.resolve()
        if out_res == stock_res or (out_res.exists() and stock_res.exists() and out_res.samefile(stock_res)):
            raise DestinationSafetyError(
                f"Output path cannot overwrite canonical stock firmware: {stock_res}"
            )

    # Additional heuristic: check if output path points into stock/ directory with stock filename
    if out_res.name == "circuitrhythm-firmware-5706.syx" and "stock" in out_res.parts:
        raise DestinationSafetyError(
            f"Output path appears to target stock firmware repository file: {out_res}"
        )


def validate_patch_ranges(patches: Sequence[PatchHunk]) -> None:
    """Asserts that each patch is within allowed writable app bounds and detects overlaps."""
    if not patches:
        return

    # Check each patch bounds
    for p in patches:
        if p.address < APP_WRITABLE_START:
            raise AddressBoundsError(
                f"Patch '{p.name}' at {p.address:#010x} is below writable application boundary "
                f"({APP_WRITABLE_START:#010x}). Modifying vector table or bootloader is forbidden!"
            )
        if p.end_address > FLASH_END:
            raise AddressBoundsError(
                f"Patch '{p.name}' range [{p.address:#010x}, {p.end_address:#010x}) exceeds "
                f"flash end boundary ({FLASH_END:#010x})!"
            )
        if p.address < APP_END:
            if p.end_address > APP_END:
                raise AddressBoundsError(
                    f"Patch '{p.name}' range [{p.address:#010x}, {p.end_address:#010x}) crosses "
                    f"stock application boundary ({APP_END:#010x})!"
                )
        else:
            # p.address >= APP_END: extension patch (code cave)
            if p.address % 4:
                raise AddressBoundsError("Code cave start must be word aligned")
            if any(b != 0xFF for b in p.expected):
                raise AddressBoundsError(
                    f"Extension patch '{p.name}' at {p.address:#010x} must expect unprogrammed 0xFF bytes!"
                )

    # Check for overlaps between ranges
    sorted_patches = sorted(patches, key=lambda x: x.address)
    for i in range(len(sorted_patches) - 1):
        curr_p = sorted_patches[i]
        next_p = sorted_patches[i + 1]
        if curr_p.end_address > next_p.address:
            raise RangeOverlapError(
                f"Patch range collision detected between '{curr_p.name}' "
                f"[{curr_p.address:#010x}, {curr_p.end_address:#010x}) and '{next_p.name}' "
                f"[{next_p.address:#010x}, {next_p.end_address:#010x})!"
            )


# Patch Application and Manifest Generation
def apply_patches(
    image: bytes,
    patches: Sequence[PatchHunk],
) -> tuple[bytes, list[dict], list[dict]]:
    """Applies patches to image bytearray after validating original bytes.

    Supports in-place patches within [0x08010200, 0x0806A570) and code-cave
    extension patches within [0x0806A570, 0x08080000).

    Returns:
        (patched_image, patches_applied, changed_ranges)
    """
    if len(image) != STOCK_IMAGE_SIZE:
        raise ValueError(f"Image length must be {STOCK_IMAGE_SIZE} bytes")

    validate_patch_ranges(patches)

    patched = bytearray(image)

    # If extension patches exist beyond APP_END, extend patched with 0xFF
    max_end = max((p.end_address for p in patches), default=APP_END)
    if max_end > APP_END:
        extend_len = (max_end - APP_BASE) - len(patched)
        if extend_len > 0:
            patched.extend(b"\xFF" * extend_len)

    patches_applied: list[dict] = []

    for p in patches:
        off = p.offset
        actual = bytes(patched[off : off + p.length])
        if actual != p.expected:
            raise OriginalBytesMismatchError(
                f"Patch '{p.name}' at address {p.address:#010x} (offset {off:#x}) failed byte check:\n"
                f"  Expected: {p.expected.hex(' ')}\n"
                f"  Actual:   {actual.hex(' ')}"
            )

        patched[off : off + p.length] = p.replacement

        patches_applied.append({
            "name": p.name,
            "address": f"{p.address:#010x}",
            "offset": f"{off:#x}",
            "length": p.length,
            "expected_hex": p.expected.hex(),
            "replacement_hex": p.replacement.hex(),
        })

    # Word-align image length to 4 bytes with 0xFF padding
    align_pad = (-len(patched)) % 4
    if align_pad > 0:
        patched.extend(b"\xFF" * align_pad)

    # Compute actual changed byte ranges (at byte granularity)
    compare_orig = image + b"\xFF" * (len(patched) - len(image))
    diff_indices = [i for i, (o, n) in enumerate(zip(compare_orig, patched)) if o != n]
    changed_ranges: list[dict] = []
    if diff_indices:
        range_start = diff_indices[0]
        prev = diff_indices[0]
        for idx in diff_indices[1:]:
            if idx == prev + 1:
                prev = idx
            else:
                changed_ranges.append({
                    "start_address": f"{APP_BASE + range_start:#010x}",
                    "end_address": f"{APP_BASE + prev + 1:#010x}",
                    "offset": f"{range_start:#x}",
                    "byte_count": prev - range_start + 1,
                    "old_bytes": compare_orig[range_start : prev + 1].hex(),
                    "new_bytes": patched[range_start : prev + 1].hex(),
                })
                range_start = idx
                prev = idx
        changed_ranges.append({
            "start_address": f"{APP_BASE + range_start:#010x}",
            "end_address": f"{APP_BASE + prev + 1:#010x}",
            "offset": f"{range_start:#x}",
            "byte_count": prev - range_start + 1,
            "old_bytes": compare_orig[range_start : prev + 1].hex(),
            "new_bytes": patched[range_start : prev + 1].hex(),
        })

    # Vector table and identity preservation check
    if patched[:VECTOR_TABLE_SIZE] != image[:VECTOR_TABLE_SIZE]:
        raise PatcherError("Critical error: vector table / identity region was modified!")

    return bytes(patched), patches_applied, changed_ranges


def patch_firmware(
    input_path: Path,
    output_path: Path,
    patches: Sequence[PatchHunk],
    manifest_path: Optional[Path] = None,
    stock_path: Optional[Path] = None,
) -> dict:
    """High-level function: reads stock SysEx, asserts hashes/bounds/bytes,
    patches image, repacks SysEx, writes output and manifest.
    """
    input_path = input_path.resolve()
    output_path = output_path.resolve()

    # Safety checks on destination
    validate_destination_paths(input_path, output_path, stock_path)
    manifest_path = (manifest_path or output_path.with_suffix(".manifest.json")).resolve()
    validate_destination_paths(input_path, manifest_path, stock_path)
    if manifest_path == output_path or (
        manifest_path.exists() and output_path.exists() and manifest_path.samefile(output_path)
    ):
        raise DestinationSafetyError("Manifest cannot overwrite output SysEx")

    # Read and validate input SysEx
    raw_syx = input_path.read_bytes()
    validate_input_syx(raw_syx)

    # Decode SysEx
    parsed = unpack_syx(raw_syx)
    orig_image = parsed["image"]

    orig_image_sha256 = hashlib.sha256(orig_image).hexdigest()
    if orig_image_sha256 != STOCK_IMAGE_SHA256:
        raise InputHashMismatchError(
            f"Extracted image SHA-256 mismatch!\n  Expected: {STOCK_IMAGE_SHA256}\n  Got:      {orig_image_sha256}"
        )

    # Apply patches
    patched_image, patches_info, changed_ranges = apply_patches(orig_image, patches)

    patched_image_sha256 = hashlib.sha256(patched_image).hexdigest()
    patched_crc = crc32_mpeg2(patched_image)

    # Build new SysEx
    new_syx = pack_syx(patched_image, parsed["init"], parsed["header_prefix"])
    new_syx_sha256 = hashlib.sha256(new_syx).hexdigest()

    # Write output SysEx file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(new_syx)

    # Calculate total changed bytes
    total_changed = sum(r["byte_count"] for r in changed_ranges)

    # Construct manifest
    manifest = {
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "input": {
            "path": str(input_path),
            "size": len(raw_syx),
            "sha256": STOCK_SYX_SHA256,
            "image_size": len(orig_image),
            "image_sha256": orig_image_sha256,
            "image_crc32_mpeg2": f"{parsed['crc']:#010x}",
        },
        "output": {
            "path": str(output_path),
            "size": len(new_syx),
            "sha256": new_syx_sha256,
            "image_size": len(patched_image),
            "image_sha256": patched_image_sha256,
            "image_crc32_mpeg2": f"{patched_crc:#010x}",
        },
        "safety_checks": {
            "vector_table_preserved": True,
            "bootloader_untouched": True,
            "identity_preserved": True,
            "destination_distinct_from_input": True,
            "destination_distinct_from_stock": True,
        },
        "patches_count": len(patches_info),
        "total_bytes_changed": total_changed,
        "patches": patches_info,
        "changed_ranges": changed_ranges,
    }

    if manifest_path is None:
        manifest_path = output_path.with_suffix(".manifest.json")
    else:
        manifest_path = manifest_path.resolve()

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    return manifest


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Safe Circuit Rhythm 5706 firmware patcher and SysEx builder."
    )
    root = Path(__file__).resolve().parents[1]
    default_stock = root / "stock" / "circuitrhythm-firmware-5706.syx"
    default_output = root / "build" / "circuitrhythm-5706-m2-candidate.syx"
    phase1_output = root / "build" / "circuitrhythm-5706-phase1-sequencer.syx"

    parser.add_argument(
        "--input",
        type=Path,
        default=default_stock,
        help="Path to stock Circuit Rhythm 5706 .syx file",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Path for generated patched .syx file (default depends on target mode)",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=None,
        help="Path for manifest diff JSON output (default: <output>.manifest.json)",
    )
    parser.add_argument(
        "--candidate-m2",
        action="store_true",
        help="Apply canonical M2 diagnostic patch (step held LED color: palette 31 -> 30)",
    )
    parser.add_argument(
        "--build-phase1",
        action="store_true",
        help="Build Phase 1 consolidated 32-step sequencer firmware image",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Verify input file without generating patched output",
    )

    args = parser.parse_args(argv)

    if args.verify_only:
        print(f"Verifying input SysEx: {args.input}")
        raw = args.input.read_bytes()
        validate_input_syx(raw)
        parsed = unpack_syx(raw)
        print("  SysEx SHA-256:       OK (Stock 5706)")
        print(f"  Extracted image:     {len(parsed['image'])} bytes")
        print(f"  Image CRC-32/MPEG-2: {parsed['crc']:#010x} (OK)")
        print("Verification successful.")
        return 0

    patches: list[PatchHunk] = []
    output_path = args.output
    if args.build_phase1:
        src_path = root / "src"
        if str(src_path) not in sys.path:
            sys.path.insert(0, str(src_path))
        try:
            from seq_patch import build_phase1_patches
        except ImportError:
            from seq_Patch import build_phase1_patches
        patches = build_phase1_patches()
        if output_path is None:
            output_path = phase1_output
    elif args.candidate_m2:
        patches.append(M2_CANDIDATE_PATCH)
        if output_path is None:
            output_path = default_output
    else:
        print("No patch specified. Use --candidate-m2 or --build-phase1.", file=sys.stderr)
        return 1

    print("Executing safe firmware patching...")
    print(f"  Input:    {args.input}")
    print(f"  Output:   {output_path}")
    print(f"  Patches:  {len(patches)}")

    try:
        manifest = patch_firmware(
            input_path=args.input,
            output_path=output_path,
            patches=patches,
            manifest_path=args.manifest,
            stock_path=default_stock,
        )
        print("\nPatching completed successfully!")
        print(f"  Output SysEx SHA-256: {manifest['output']['sha256']}")
        print(f"  Output Image SHA-256: {manifest['output']['image_sha256']}")
        print(f"  Output Image CRC-32:  {manifest['output']['image_crc32_mpeg2']}")
        print(f"  Total bytes changed:  {manifest['total_bytes_changed']}")
        print(f"  Manifest written to:  {args.manifest or output_path.with_suffix('.manifest.json')}")
        return 0
    except PatcherError as err:
        print(f"\nPATCHER ERROR: {err}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
