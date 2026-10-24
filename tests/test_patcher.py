"""Unit and integration tests for scripts/patch_firmware.py.

Covers:
- Hash verification and corruption rejection.
- Overwrite protection against stock and input files.
- Application bounds enforcement (vector table & bootloader protection, app end limit).
- Range collision and overlap rejection.
- Original bytes mismatch rejection.
- Round-trip lossless SysEx codec verification on unmodified stock.
- End-to-end M2 candidate patch application and manifest generation.
- Unicorn emulation comparing stock vs. patched color handler behavior.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest

from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB, CS_MODE_MCLASS
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_THUMB, UC_MODE_MCLASS
from unicorn.arm_const import (
    UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3,
    UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_PC,
)

import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from patch_firmware import (
    STOCK_SYX_SHA256,
    STOCK_IMAGE_SHA256,
    STOCK_IMAGE_SIZE,
    STOCK_CRC32_MPEG2,
    APP_BASE,
    APP_END,
    APP_WRITABLE_START,
    APP_WRITABLE_END,
    M2_CANDIDATE_PATCH,
    PatchHunk,
    InputHashMismatchError,
    DestinationSafetyError,
    AddressBoundsError,
    RangeOverlapError,
    OriginalBytesMismatchError,
    SysExFormatError,
    validate_input_syx,
    validate_destination_paths,
    validate_patch_ranges,
    apply_patches,
    pack_syx,
    unpack_syx,
    patch_firmware,
    crc32_mpeg2,
)


class TestPatcherSecurityAndBounds(unittest.TestCase):
    def setUp(self):
        self.stock_path = ROOT / "stock" / "circuitrhythm-firmware-5706.syx"
        self.assertTrue(self.stock_path.exists(), "Stock firmware file must exist")
        self.stock_bytes = self.stock_path.read_bytes()

    def test_stock_hash_verification_success(self):
        """Verifies that the canonical stock SysEx passes hash validation."""
        validate_input_syx(self.stock_bytes)
        self.assertEqual(hashlib.sha256(self.stock_bytes).hexdigest(), STOCK_SYX_SHA256)

    def test_corrupted_input_hash_rejected(self):
        """Verifies that tampering with even a single byte rejects the input file."""
        corrupt = bytearray(self.stock_bytes)
        corrupt[100] ^= 0xFF
        with self.assertRaises(InputHashMismatchError):
            validate_input_syx(bytes(corrupt))

    def test_destination_safety_rejects_overwrite_input(self):
        """Verifies that output path matching input path is strictly rejected."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_in = Path(tmp) / "input.syx"
            tmp_in.write_bytes(b"dummy")
            with self.assertRaises(DestinationSafetyError):
                validate_destination_paths(tmp_in, tmp_in, self.stock_path)

    def test_destination_safety_rejects_overwrite_stock(self):
        """Verifies that output path pointing to stock firmware is strictly rejected."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_in = Path(tmp) / "input.syx"
            tmp_in.write_bytes(b"dummy")
            with self.assertRaises(DestinationSafetyError):
                validate_destination_paths(tmp_in, self.stock_path, self.stock_path)

    def test_bounds_rejects_vector_table_and_bootloader(self):
        """Verifies that addresses in the vector table [0x08010000, 0x08010200) or bootloader (<0x08010000) are rejected."""
        prohibited_addresses = [
            0x08000000,  # Bootloader base
            0x08008000,  # Bootloader mid
            0x0800FFFE,  # Just below app base
            0x08010000,  # Application SP (vector 0)
            0x08010004,  # Reset vector
            0x08010008,  # NMI vector
            0x08010100,  # Interrupt vectors
            0x080101C8,  # Identity header area
            0x080101FE,  # Edge of protected vector table area
        ]
        for addr in prohibited_addresses:
            patch = PatchHunk(address=addr, expected=b"\x00\x00", replacement=b"\x01\x01", name="prohibited")
            with self.subTest(addr=hex(addr)):
                with self.assertRaises(AddressBoundsError):
                    validate_patch_ranges([patch])

    def test_bounds_rejects_past_application_end(self):
        """Verifies that patch addresses at or beyond APP_END (0x0806A570) are rejected."""
        prohibited_ranges = [
            (APP_END, 2),        # Exact end
            (APP_END + 0x10, 2), # Far beyond end
            (APP_END - 2, 4),    # Crosses boundary (0x0806A56E..0x0806A572)
        ]
        for addr, length in prohibited_ranges:
            patch = PatchHunk(
                address=addr,
                expected=b"\x00" * length,
                replacement=b"\x01" * length,
                name="overflow",
            )
            with self.subTest(addr=hex(addr), len=length):
                with self.assertRaises(AddressBoundsError):
                    validate_patch_ranges([patch])

    def test_bounds_accepts_valid_application_addresses(self):
        """Verifies that addresses within [0x08010200, 0x0806A570) pass boundary checks."""
        valid_patches = [
            PatchHunk(address=APP_WRITABLE_START, expected=b"\x00\x00", replacement=b"\x01\x01", name="start"),
            PatchHunk(address=0x0805CF68, expected=b"\x1F\x22", replacement=b"\x1E\x22", name="m2_candidate"),
            PatchHunk(address=APP_WRITABLE_END - 2, expected=b"\x00\x00", replacement=b"\x01\x01", name="end"),
        ]
        # Should not raise
        validate_patch_ranges(valid_patches)

    def test_rejects_overlapping_ranges(self):
        """Verifies that overlapping or colliding patch ranges are rejected."""
        # Overlapping case 1: Partial overlap
        p1 = PatchHunk(address=0x08050000, expected=b"\x00\x00\x00\x00", replacement=b"\x01\x01\x01\x01", name="p1")
        p2 = PatchHunk(address=0x08050002, expected=b"\x00\x00\x00\x00", replacement=b"\x02\x02\x02\x02", name="p2")
        with self.assertRaises(RangeOverlapError):
            validate_patch_ranges([p1, p2])

        # Overlapping case 2: Exact same address
        p3 = PatchHunk(address=0x08050000, expected=b"\x00\x00", replacement=b"\x03\x03", name="p3")
        with self.assertRaises(RangeOverlapError):
            validate_patch_ranges([p1, p3])

        # Overlapping case 3: Out of order in list
        with self.assertRaises(RangeOverlapError):
            validate_patch_ranges([p2, p1])

    def test_rejects_original_bytes_mismatch(self):
        """Verifies that if target address bytes differ from expected, patch is aborted without mutation."""
        parsed = unpack_syx(self.stock_bytes)
        image = parsed["image"]
        wrong_patch = PatchHunk(
            address=0x0805CF68,
            expected=bytes([0xAA, 0xBB]),  # Actual is [0x1F, 0x22]
            replacement=bytes([0x1E, 0x22]),
            name="wrong_expected",
        )
        with self.assertRaises(OriginalBytesMismatchError):
            apply_patches(image, [wrong_patch])


class TestSysExCodecAndRoundTrip(unittest.TestCase):
    def setUp(self):
        self.stock_path = ROOT / "stock" / "circuitrhythm-firmware-5706.syx"
        self.stock_bytes = self.stock_path.read_bytes()

    def test_stock_syx_lossless_roundtrip(self):
        """Verifies that unpack_syx followed by pack_syx without edits produces identical stock bytes."""
        parsed = unpack_syx(self.stock_bytes)
        self.assertEqual(parsed["device"], 0x63)
        self.assertEqual(parsed["size"], STOCK_IMAGE_SIZE)
        self.assertEqual(parsed["crc"], STOCK_CRC32_MPEG2)
        self.assertEqual(hashlib.sha256(parsed["image"]).hexdigest(), STOCK_IMAGE_SHA256)

        rebuilt = pack_syx(parsed["image"], parsed["init"], parsed["header_prefix"])
        self.assertEqual(len(rebuilt), len(self.stock_bytes))
        self.assertEqual(rebuilt, self.stock_bytes)
        self.assertEqual(hashlib.sha256(rebuilt).hexdigest(), STOCK_SYX_SHA256)

    def test_crc32_mpeg2_matches_stock(self):
        """Verifies that the standalone crc32_mpeg2 function calculates the exact stock CRC."""
        parsed = unpack_syx(self.stock_bytes)
        computed = crc32_mpeg2(parsed["image"])
        self.assertEqual(computed, STOCK_CRC32_MPEG2)
        self.assertEqual(f"{computed:08X}", "9EEE802C")


class TestM2CandidatePatching(unittest.TestCase):
    def setUp(self):
        self.stock_path = ROOT / "stock" / "circuitrhythm-firmware-5706.syx"

    def test_m2_patch_produces_exact_single_byte_diff(self):
        """Tests that applying M2_CANDIDATE_PATCH mutates exactly 1 byte and produces valid SysEx and manifest."""
        with tempfile.TemporaryDirectory() as tmp:
            out_syx = Path(tmp) / "patched.syx"
            out_manifest = Path(tmp) / "patched.manifest.json"

            manifest = patch_firmware(
                input_path=self.stock_path,
                output_path=out_syx,
                patches=[M2_CANDIDATE_PATCH],
                manifest_path=out_manifest,
                stock_path=self.stock_path,
            )

            # File existence
            self.assertTrue(out_syx.exists())
            self.assertTrue(out_manifest.exists())

            # Manifest structure & verification
            self.assertEqual(manifest["total_bytes_changed"], 1)
            self.assertEqual(manifest["patches_count"], 1)
            self.assertTrue(manifest["safety_checks"]["vector_table_preserved"])
            self.assertTrue(manifest["safety_checks"]["bootloader_untouched"])
            self.assertTrue(manifest["safety_checks"]["identity_preserved"])

            # Verify changed range in manifest
            expected_range = [{
                "start_address": "0x0805cf68",
                "end_address": "0x0805cf69",
                "offset": "0x4cf68",
                "byte_count": 1,
                "old_bytes": "1f",
                "new_bytes": "1e",
            }]
            self.assertEqual(manifest["changed_ranges"], expected_range)

            # Unpack patched SysEx and directly verify image bytes
            patched_syx_bytes = out_syx.read_bytes()
            unpacked_patched = unpack_syx(patched_syx_bytes)
            patched_image = unpacked_patched["image"]

            orig_image = unpack_syx(self.stock_path.read_bytes())["image"]

            # Exactly 1 byte differs in the entire 370032 byte image
            diffs = [(i, orig_image[i], patched_image[i]) for i in range(len(orig_image)) if orig_image[i] != patched_image[i]]
            self.assertEqual(len(diffs), 1)

            diff_offset, old_byte, new_byte = diffs[0]
            self.assertEqual(diff_offset, 0x0805CF68 - APP_BASE)
            self.assertEqual(diff_offset, 0x4CF68)
            self.assertEqual(old_byte, 0x1F)
            self.assertEqual(new_byte, 0x1E)

            # First 0x200 bytes (Vector Table + identity) are 100% identical
            self.assertEqual(patched_image[:0x200], orig_image[:0x200])

            # Output SysEx CRC is verified
            self.assertTrue(unpacked_patched["crc_ok"])
            self.assertNotEqual(unpacked_patched["crc"], STOCK_CRC32_MPEG2)
            self.assertEqual(f"{unpacked_patched['crc']:08X}", "2DBD7611")


class TestSyntheticRamExecutionOfPatchedCode(unittest.TestCase):
    """Executes the patched vs stock color handler in Unicorn synthetic RAM."""

    @classmethod
    def setUpClass(cls):
        stock_path = ROOT / "stock" / "circuitrhythm-firmware-5706.syx"
        cls.stock_image = unpack_syx(stock_path.read_bytes())["image"]

        # Apply M2 candidate patch
        patched, _, _ = apply_patches(cls.stock_image, [M2_CANDIDATE_PATCH])
        cls.patched_image = patched

        cls.md = Cs(CS_ARCH_ARM, CS_MODE_THUMB | CS_MODE_MCLASS)

    def _create_emulator(self, image: bytes) -> tuple[Uc, int, int, int]:
        u = Uc(UC_ARCH_ARM, UC_MODE_THUMB | UC_MODE_MCLASS)
        u.mem_map(0x08000000, 0x80000)
        u.mem_write(APP_BASE, image)
        u.mem_map(0x20000000, 0x50000)

        view = 0x20002000
        cell = 0x20003000
        leds = 0x20003100

        u.mem_write(view + 4, struct.pack("<I", cell))
        u.mem_write(cell, struct.pack("<I", leds))
        return u, view, cell, leds

    def _call(self, u: Uc, addr: int, *args):
        STOP = 0x0800F000
        regs = [UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3]
        for reg, value in zip(regs, args):
            u.reg_write(reg, value)
        u.reg_write(UC_ARM_REG_SP, 0x2004F000)
        u.reg_write(UC_ARM_REG_LR, STOP | 1)
        u.emu_start(addr | 1, STOP, count=1000)

    def test_disassembly_at_patch_site(self):
        """Verifies disassembly of the instruction at 0x0805CF68 before and after patch."""
        off = 0x0805CF68 - APP_BASE
        stock_ins = list(self.md.disasm(self.stock_image[off : off + 2], 0x0805CF68))
        patched_ins = list(self.md.disasm(self.patched_image[off : off + 2], 0x0805CF68))

        self.assertEqual(len(stock_ins), 1)
        self.assertEqual(len(patched_ins), 1)

        self.assertEqual(stock_ins[0].mnemonic, "movs")
        self.assertEqual(stock_ins[0].op_str, "r2, #0x1f")  # 31 decimal

        self.assertEqual(patched_ins[0].mnemonic, "movs")
        self.assertEqual(patched_ins[0].op_str, "r2, #0x1e")  # 30 decimal

    def test_color_branch_execution_stock_vs_patched(self):
        """Executes 0x0805CF24 on synthetic step view with held bit set (bit 3).

        Verifies that stock branch writes palette 31 color (0x0055),
        while patched branch writes palette 30 color (0x001E).
        """
        palette_addr = 0x08062AB0
        palette_31_color = self.stock_image[palette_addr - APP_BASE + 31 * 2 : palette_addr - APP_BASE + 32 * 2]
        palette_30_color = self.stock_image[palette_addr - APP_BASE + 30 * 2 : palette_addr - APP_BASE + 31 * 2]

        self.assertEqual(palette_31_color, bytes([0x55, 0x00]))  # 0x0055 in little-endian
        self.assertEqual(palette_30_color, bytes([0x1E, 0x00]))  # 0x001E in little-endian

        for step in (0, 15, 16, 31):
            with self.subTest(step=step):
                # 1. Run Stock
                u_stock, view_s, _, leds_s = self._create_emulator(self.stock_image)
                u_stock.mem_write(leds_s, bytes([0xA5]) * 64)
                u_stock.mem_write(view_s + 0x74 + step * 2, struct.pack("<H", 8))  # bit 3 held
                self._call(u_stock, 0x0805CF24, view_s, step)

                written_stock_color = bytes(u_stock.mem_read(leds_s + step * 2, 2))
                self.assertEqual(written_stock_color, palette_31_color)

                # 2. Run Patched
                u_patched, view_p, _, leds_p = self._create_emulator(self.patched_image)
                u_patched.mem_write(leds_p, bytes([0xA5]) * 64)
                u_patched.mem_write(view_p + 0x74 + step * 2, struct.pack("<H", 8))  # bit 3 held
                self._call(u_patched, 0x0805CF24, view_p, step)

                written_patched_color = bytes(u_patched.mem_read(leds_p + step * 2, 2))
                self.assertEqual(written_patched_color, palette_30_color)

                # Ensure only the target step LED was modified, and all other 31 LEDs stayed 0xA5
                unaffected_stock = [b for i, b in enumerate(u_stock.mem_read(leds_s, 64)) if i not in (step * 2, step * 2 + 1)]
                unaffected_patched = [b for i, b in enumerate(u_patched.mem_read(leds_p, 64)) if i not in (step * 2, step * 2 + 1)]
                self.assertEqual(unaffected_stock, [0xA5] * 62)
                self.assertEqual(unaffected_patched, [0xA5] * 62)


if __name__ == "__main__":
    unittest.main()
