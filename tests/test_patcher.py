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
    FLASH_END,
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

    def _create_full_environment(self, image: bytes) -> tuple[Uc, dict]:
        """Creates a fully configured synthetic step view environment with pattern memory,

        edit stores, and observer chains for comprehensive stock vs patched comparison.
        """
        u = Uc(UC_ARCH_ARM, UC_MODE_THUMB | UC_MODE_MCLASS)
        u.mem_map(0x08000000, 0x80000)
        u.mem_write(APP_BASE, image)
        # Stub timer start (0x08046dde) and stop (0x08046e2a) with bx lr (0x7047)
        u.mem_write(0x08046dde, bytes.fromhex("7047"))
        u.mem_write(0x08046e2a, bytes.fromhex("7047"))
        u.mem_map(0x20000000, 0x50000)

        view = 0x20002000
        led_cell = 0x20003000
        leds = 0x20003100
        listener = 0x20001000
        listeners = 0x20001100
        view_listeners = 0x20001200
        patterns = 0x20010000

        # Non-empty 8-pattern test fixture (8 * 0xA28 = 20,800 bytes)
        pattern_data = (bytes([60, 6, 1, 96, 7, 255, 0, 0]) * 32 + bytes([0x5A]) * (0xA28 - 256)) * 8
        u.mem_write(patterns, pattern_data)

        next_store = 0x20008000

        def store(data, active=0):
            nonlocal next_store
            obj = next_store
            next_store += 0x200
            u.mem_write(obj, struct.pack("<5I", len(data) // 4, active, 0, obj + 0x40, obj + 0xC0))
            u.mem_write(obj + 0x40, data)
            u.mem_write(obj + 0xC0, data)
            return obj

        st1 = store(bytes([96]) * 32 + bytes([7]) * 32 + bytes([1]) * 32 + bytes([255]) * 32)
        st2 = store(bytes([60]) * 32 + bytes([6]) * 32 + bytes(32))
        selection = store(bytes([7, 0, 0, 0]))
        note = store(bytes([60, 0, 0, 0]))
        held = store(bytes([255, 0, 0, 0]) * 2)
        pressed = store(bytes(8))
        page = store(bytes(4))
        zero_mod = store(bytes(4))

        u.mem_write(listener, struct.pack("<I", 0x080696A0))
        for off, val in ((4, patterns), (0x1C, st1), (0x20, st2), (0x28, selection)):
            u.mem_write(listener + off, struct.pack("<I", val))

        u.mem_write(listeners, struct.pack("<I", listener))
        u.mem_write(listeners + 4, struct.pack("<I", 0xFFFFFFFF))
        u.mem_write(listeners + 8, struct.pack("<I", view + 8))
        u.mem_write(listeners + 12, struct.pack("<I", 0xFFFFFFFF))

        u.mem_write(view_listeners, struct.pack("<I", view + 8))
        u.mem_write(view_listeners + 4, struct.pack("<I", 0xFFFFFFFF))

        for s, count, l_list in (
            (st1, 2, listeners),
            (st2, 1, listeners),
            (pressed, 1, view_listeners),
            (held, 1, view_listeners),
        ):
            u.mem_write(s + 1, bytes([count]))
            u.mem_write(s + 0x14, struct.pack("<I", l_list))

        u.mem_write(led_cell, struct.pack("<I", leds))
        for off, val in (
            (0, 0x080682CC), (4, led_cell), (8, 0x080682F8),
            (0xC, st1), (0x10, st2), (0x18, held), (0x20, pressed),
            (0x34, zero_mod), (0x3C, zero_mod), (0x40, zero_mod), (0x44, zero_mod),
            (0x5C, note), (0x60, page), (0x64, held), (0x70, zero_mod)
        ):
            u.mem_write(view + off, struct.pack("<I", val))

        u.mem_write(leds, bytes([0xA5]) * 64)
        return u, {
            "view": view,
            "leds": leds,
            "patterns": patterns,
            "st1": st1,
            "st2": st2,
            "selection": selection,
            "note": note,
            "page": page,
            "pattern_data": pattern_data,
        }

    def _call(self, u: Uc, addr: int, *args):
        STOP = 0x0800F000
        regs = [UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3]
        for reg, value in zip(regs, args):
            u.reg_write(reg, value)
        u.reg_write(UC_ARM_REG_SP, 0x2004F000)
        u.reg_write(UC_ARM_REG_LR, STOP | 1)
        u.emu_start(addr | 1, STOP, count=20000)

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

    def test_pad_press_synthetic_ram_full_state_comparison(self):
        """Executes full pad press (0x0805CB04) and release (0x0805CCF0) dispatch in synthetic RAM.

        Proves that:
        1. Only the pressed step's 16-bit LED record changes from palette 31 (0x0055) to 30 (0x001E).
        2. All remaining 31 LED records remain completely untouched and byte-identical between stock and patched.
        3. All 8 patterns of pattern memory (8 * 0xA28 = 20,800 bytes) remain byte-for-byte untouched and identical.
        4. All edit buffers (st1, st2, selection, note) remain byte-for-byte identical.
        5. Upon pad release, commit and active step LED updates are byte-for-byte identical.
        """
        palette_31_color = bytes([0x55, 0x00])  # Palette index 31 word 0x0055 (little-endian)
        palette_30_color = bytes([0x1E, 0x00])  # Palette index 30 word 0x001E (little-endian)

        for step in range(32):
            with self.subTest(step=step):
                u_stock, env_s = self._create_full_environment(self.stock_image)
                u_patched, env_p = self._create_full_environment(self.patched_image)

                page_idx = step // 16
                pad = step % 16

                # Set page in both emulators
                u_stock.mem_write(env_s["page"] + 0x40, bytes([page_idx, 0, 0, 0]))
                u_patched.mem_write(env_p["page"] + 0x40, bytes([page_idx, 0, 0, 0]))

                # 1. Action: Pad Press (0x0805CB04)
                self._call(u_stock, 0x0805CB04, env_s["view"], pad, 96)
                self._call(u_patched, 0x0805CB04, env_p["view"], pad, 96)

                led_s = bytes(u_stock.mem_read(env_s["leds"], 64))
                led_p = bytes(u_patched.mem_read(env_p["leds"], 64))

                # Assertion 1: Only the pressed step's LED word differs (palette 31 vs palette 30)
                step_led_s = led_s[step * 2 : step * 2 + 2]
                step_led_p = led_p[step * 2 : step * 2 + 2]
                self.assertEqual(step_led_s, palette_31_color, f"Step {step}: stock must be palette 31")
                self.assertEqual(step_led_p, palette_30_color, f"Step {step}: patched must be palette 30")
                self.assertNotEqual(step_led_s, step_led_p)

                # Assertion 2: The remaining 31 LED entries are completely untouched and identical
                for other in range(32):
                    if other != step:
                        self.assertEqual(
                            led_s[other * 2 : other * 2 + 2],
                            bytes([0xA5, 0xA5]),
                            f"Step {step}: stock other step {other} modified",
                        )
                        self.assertEqual(
                            led_p[other * 2 : other * 2 + 2],
                            bytes([0xA5, 0xA5]),
                            f"Step {step}: patched other step {other} modified",
                        )
                # Verify that across all 64 bytes of LED records, diff is strictly at byte step * 2
                # (Since high byte of both palette 31 [0x0055] and palette 30 [0x001E] is 0x00)
                led_diff_indices = [i for i in range(64) if led_s[i] != led_p[i]]
                self.assertEqual(led_diff_indices, [step * 2])

                # Assertion 3: Pattern memory (all 8 patterns = 20,800 bytes) is untouched and byte-identical
                pattern_bytes_s = bytes(u_stock.mem_read(env_s["patterns"], 8 * 0xA28))
                pattern_bytes_p = bytes(u_patched.mem_read(env_p["patterns"], 8 * 0xA28))
                self.assertEqual(pattern_bytes_s, env_s["pattern_data"])
                self.assertEqual(pattern_bytes_p, env_p["pattern_data"])
                self.assertEqual(pattern_bytes_s, pattern_bytes_p)

                # Assertion 4: Edit buffers are byte-for-byte identical
                self.assertEqual(
                    bytes(u_stock.mem_read(env_s["st1"], 0x100)),
                    bytes(u_patched.mem_read(env_p["st1"], 0x100)),
                )
                self.assertEqual(
                    bytes(u_stock.mem_read(env_s["st2"], 0x100)),
                    bytes(u_patched.mem_read(env_p["st2"], 0x100)),
                )
                self.assertEqual(
                    bytes(u_stock.mem_read(env_s["selection"], 0x20)),
                    bytes(u_patched.mem_read(env_p["selection"], 0x20)),
                )

                # Assertion 5: Step status word (view + 0x74 + 2 * step) has bit 3 set (value 8) in both
                status_s = struct.unpack("<H", u_stock.mem_read(env_s["view"] + 0x74 + 2 * step, 2))[0]
                status_p = struct.unpack("<H", u_patched.mem_read(env_p["view"] + 0x74 + 2 * step, 2))[0]
                self.assertEqual(status_s, 8)
                self.assertEqual(status_p, 8)

                # 2. Action: Pad Release (0x0805CCF0) - toggles ON and commits
                self._call(u_stock, 0x0805CCF0, env_s["view"], pad)
                self._call(u_patched, 0x0805CCF0, env_p["view"], pad)

                # Post-release Assertion: Commit to pattern memory is byte-for-byte identical
                rel_pattern_s = bytes(u_stock.mem_read(env_s["patterns"], 8 * 0xA28))
                rel_pattern_p = bytes(u_patched.mem_read(env_p["patterns"], 8 * 0xA28))
                self.assertEqual(rel_pattern_s, rel_pattern_p)

                # Post-release Assertion: Active step LED is byte-for-byte identical
                rel_led_s = bytes(u_stock.mem_read(env_s["leds"], 64))
                rel_led_p = bytes(u_patched.mem_read(env_p["leds"], 64))
                self.assertEqual(rel_led_s, rel_led_p)
                self.assertNotEqual(rel_led_s[step * 2 : step * 2 + 2], bytes([0xA5, 0xA5]))

                # Post-release Assertion: Edit buffers remain byte-for-byte identical
                self.assertEqual(
                    bytes(u_stock.mem_read(env_s["st1"], 0x100)),
                    bytes(u_patched.mem_read(env_p["st1"], 0x100)),
                )
                self.assertEqual(
                    bytes(u_stock.mem_read(env_s["st2"], 0x100)),
                    bytes(u_patched.mem_read(env_p["st2"], 0x100)),
                )



class TestCodeCaveSupport(unittest.TestCase):
    """Tests for code cave extension support in [0x0806A570, 0x08080000)."""

    def setUp(self):
        self.stock_path = ROOT / "stock" / "circuitrhythm-firmware-5706.syx"
        self.stock_bytes = self.stock_path.read_bytes()
        self.stock_image = unpack_syx(self.stock_bytes)["image"]

    def test_boundary_crossing_patch_strictly_rejected(self):
        """Verifies that a patch crossing the stock image boundary (e.g., at 0x0806A56E) is rejected."""
        # 0x0806A56E with len 4 spans 0x0806A56E..0x0806A572 (crosses stock APP_END 0x0806A570)
        cross_patch = PatchHunk(
            address=0x0806A56E,
            expected=b"\xFF" * 4,
            replacement=b"\x01\x02\x03\x04",
            name="cross_stock_boundary_even",
        )
        with self.assertRaises(AddressBoundsError):
            validate_patch_ranges([cross_patch])

        # 0x0806A56F with len 2 spans 0x0806A56F..0x0806A571
        cross_patch_odd = PatchHunk(
            address=APP_END - 1,
            expected=b"\xFF" * 2,
            replacement=b"\xAA\xBB",
            name="cross_stock_boundary_odd",
        )
        with self.assertRaises(AddressBoundsError):
            validate_patch_ranges([cross_patch_odd])

    def test_code_cave_bounds_and_expected_bytes_validation(self):
        """Verifies that valid code cave ranges pass, but non-0xFF expected or flash overflow are rejected."""
        # Valid code cave patch right at APP_END (0x0806A570)
        valid_cave = PatchHunk(
            address=APP_END,
            expected=b"\xFF" * 16,
            replacement=b"\x42" * 16,
            name="valid_cave_16",
        )
        validate_patch_ranges([valid_cave])

        # Extension patch must expect unprogrammed 0xFF bytes
        invalid_expected = PatchHunk(
            address=APP_END,
            expected=b"\x00" * 16,
            replacement=b"\x42" * 16,
            name="invalid_expected_zeroes",
        )
        with self.assertRaises(AddressBoundsError):
            validate_patch_ranges([invalid_expected])

        # Patch exceeding FLASH_END (0x08080000)
        at_flash_end = PatchHunk(
            address=FLASH_END,
            expected=b"\xFF" * 4,
            replacement=b"\x01" * 4,
            name="at_flash_end",
        )
        with self.assertRaises(AddressBoundsError):
            validate_patch_ranges([at_flash_end])

        cross_flash_end = PatchHunk(
            address=FLASH_END - 2,
            expected=b"\xFF" * 4,
            replacement=b"\x01" * 4,
            name="cross_flash_end",
        )
        with self.assertRaises(AddressBoundsError):
            validate_patch_ranges([cross_flash_end])

    def test_code_cave_apply_and_alignment(self):
        """Verifies that code cave patches extend the image and are 4-byte word aligned."""
        # 16-byte extension patch (already 4-byte aligned)
        cave_data = bytes(range(16))
        cave_patch = PatchHunk(
            address=APP_END,
            expected=b"\xFF" * 16,
            replacement=cave_data,
            name="cave_16_bytes",
        )
        patched, patches_applied, changed_ranges = apply_patches(self.stock_image, [cave_patch])

        self.assertEqual(len(patched), STOCK_IMAGE_SIZE + 16)
        self.assertEqual(len(patched) % 4, 0)
        self.assertEqual(patched[:STOCK_IMAGE_SIZE], self.stock_image)
        self.assertEqual(patched[STOCK_IMAGE_SIZE : STOCK_IMAGE_SIZE + 16], cave_data)
        self.assertEqual(len(patches_applied), 1)
        self.assertEqual(len(changed_ranges), 1)
        self.assertEqual(changed_ranges[0]["start_address"], f"{APP_END:#010x}")
        self.assertEqual(changed_ranges[0]["end_address"], f"{APP_END + 16:#010x}")
        self.assertEqual(changed_ranges[0]["byte_count"], 16)

        # 5-byte extension patch: must be padded to 8 bytes (multiple of 4) with 0xFF
        cave_data_5 = bytes([0x11, 0x22, 0x33, 0x44, 0x55])
        cave_patch_5 = PatchHunk(
            address=APP_END,
            expected=b"\xFF" * 5,
            replacement=cave_data_5,
            name="cave_5_bytes",
        )
        patched_5, _, _ = apply_patches(self.stock_image, [cave_patch_5])
        self.assertEqual(len(patched_5), STOCK_IMAGE_SIZE + 8)
        self.assertEqual(len(patched_5) % 4, 0)
        self.assertEqual(patched_5[STOCK_IMAGE_SIZE : STOCK_IMAGE_SIZE + 5], cave_data_5)
        self.assertEqual(patched_5[STOCK_IMAGE_SIZE + 5 : STOCK_IMAGE_SIZE + 8], b"\xFF\xFF\xFF")

    def test_code_cave_pack_unpack_and_crc(self):
        """Verifies that extended images pack into SysEx, calculate correct CRC, and unpack with allow_extended=True."""
        cave_data = bytes([0xAA, 0xBB, 0xCC, 0xDD] * 4)  # 16 bytes
        cave_patch = PatchHunk(
            address=APP_END,
            expected=b"\xFF" * 16,
            replacement=cave_data,
            name="cave_16",
        )
        patched, _, _ = apply_patches(self.stock_image, [cave_patch])

        parsed_stock = unpack_syx(self.stock_bytes)
        packed_syx = pack_syx(patched, parsed_stock["init"], parsed_stock["header_prefix"])

        # Default unpack_syx (allow_extended=False) must reject extended image
        with self.assertRaises(SysExFormatError):
            unpack_syx(packed_syx, allow_extended=False)

        # allow_extended=True accepts and validates size and CRC
        unpacked = unpack_syx(packed_syx, allow_extended=True)
        self.assertEqual(unpacked["size"], STOCK_IMAGE_SIZE + 16)
        self.assertEqual(unpacked["image"], patched)
        self.assertEqual(unpacked["crc"], crc32_mpeg2(patched))
        self.assertTrue(unpacked["crc_ok"])

    def test_pack_syx_rejects_invalid_sizes(self):
        """Verifies pack_syx size and alignment constraints."""
        parsed_stock = unpack_syx(self.stock_bytes)
        init = parsed_stock["init"]
        hdr = parsed_stock["header_prefix"]

        # Size not a multiple of 4
        with self.assertRaises(ValueError):
            pack_syx(b"\xFF" * (STOCK_IMAGE_SIZE + 1), init, hdr)

        # Size smaller than stock image size
        with self.assertRaises(ValueError):
            pack_syx(b"\xFF" * (STOCK_IMAGE_SIZE - 4), init, hdr)

        # Size exceeding flash capacity (0x70000)
        with self.assertRaises(ValueError):
            pack_syx(b"\xFF" * (FLASH_END - APP_BASE + 4), init, hdr)

    def test_code_cave_patch_firmware_end_to_end(self):
        """Verifies end-to-end patch_firmware pipeline with a code cave extension patch."""
        with tempfile.TemporaryDirectory() as tmp:
            out_syx = Path(tmp) / "extended.syx"
            out_manifest = Path(tmp) / "extended.manifest.json"

            cave_data = bytes([0x10, 0x20, 0x30, 0x40] * 4)  # 16 bytes
            cave_patch = PatchHunk(
                address=APP_END,
                expected=b"\xFF" * 16,
                replacement=cave_data,
                name="test_code_cave_16",
            )

            manifest = patch_firmware(
                input_path=self.stock_path,
                output_path=out_syx,
                patches=[cave_patch],
                manifest_path=out_manifest,
                stock_path=self.stock_path,
            )

            self.assertTrue(out_syx.exists())
            self.assertTrue(out_manifest.exists())
            self.assertEqual(manifest["output"]["image_size"], STOCK_IMAGE_SIZE + 16)
            self.assertEqual(manifest["total_bytes_changed"], 16)

            unpacked = unpack_syx(out_syx.read_bytes(), allow_extended=True)
            self.assertEqual(unpacked["size"], STOCK_IMAGE_SIZE + 16)
            self.assertEqual(unpacked["image"][:STOCK_IMAGE_SIZE], self.stock_image)
            self.assertEqual(unpacked["image"][STOCK_IMAGE_SIZE : STOCK_IMAGE_SIZE + 16], cave_data)
            self.assertEqual(unpacked["crc"], crc32_mpeg2(unpacked["image"]))


if __name__ == "__main__":
    unittest.main()
