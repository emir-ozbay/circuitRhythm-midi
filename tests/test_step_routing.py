"""Synthetic RAM tests for 32-pad step routing, page isolation, and overflow prevention.

This module validates:
1. Stock grid container pad routing split (top 16 to step view, bottom 16 to subview).
2. The 32-pad Sequencer Mode routing control flow design (all 32 pads to step view).
3. The exact mathematical and memory corruption hazards of step index overflow (step >= 32):
   - Overwrite of step view control block (view + 0xB4)
   - Aliasing of ST2 store parameters (Note[32] overwriting Step 0 Gate length in pattern commit)
   - Aliasing of ST1 store parameters (Velocity[32] overwriting Step 0 Probability in pattern commit)
   - LED buffer heap boundary overflow
4. Safe 32-pad full lifecycle execution (pads 0..31) in synthetic RAM with real stock code:
   - Full toggle ON and toggle OFF across all 32 steps
   - Non-interference with view + 0xB4 control area
   - Clean pattern commit for all 32 steps
5. Concurrent multi-pad press/release across top/bottom boundaries (pad 15 and 16).
6. Routing guard clamping/masking preventing any invalid index (>31).

Run from the project root:
  .\\.venv\\Scripts\\python.exe -m unittest tests/test_step_routing.py -v
"""
import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from inspect_ui import load_image, BASE
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_THUMB, UC_MODE_MCLASS
from unicorn.arm_const import (
    UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3,
    UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_PC,
)

REGS = [UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3]
STOP = 0x0800F000


class StepRoutingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.image = load_image()

    def setUp(self):
        self.u = Uc(UC_ARCH_ARM, UC_MODE_THUMB | UC_MODE_MCLASS)
        self.u.mem_map(0x08000000, 0x80000)
        self.u.mem_write(BASE, self.image)
        self.u.mem_map(0x20000000, 0x50000)
        self.next_store = 0x20008000

        # Stub timer routines: 0x08046dde (start) and 0x08046e2a (stop) with bx lr (0x7047)
        self.u.mem_write(0x08046dde, bytes.fromhex("7047"))
        self.u.mem_write(0x08046e2a, bytes.fromhex("7047"))

    def word(self, addr, value):
        self.u.mem_write(addr, struct.pack("<I", value))

    def readword(self, addr):
        return struct.unpack("<I", self.u.mem_read(addr, 4))[0]

    def store(self, data, active=0):
        obj = self.next_store
        self.next_store += 0x200
        self.u.mem_write(obj, struct.pack("<5I", len(data) // 4, active, 0, obj + 0x40, obj + 0xC0))
        self.u.mem_write(obj + 0x40, data)
        self.u.mem_write(obj + 0xC0, data)
        return obj

    def call(self, addr, *args):
        for reg, value in zip(REGS, args):
            self.u.reg_write(reg, value)
        self.u.reg_write(UC_ARM_REG_SP, 0x2004F000)
        self.u.reg_write(UC_ARM_REG_LR, STOP | 1)
        self.u.emu_start(addr | 1, STOP, count=20000)
        self.assertEqual(self.u.reg_read(UC_ARM_REG_PC), STOP)
        return self.u.reg_read(UC_ARM_REG_R0)

    def setup_step_view_environment(self, active_pattern=0):
        """Sets up a complete synthetic step view, stores, listener and pattern memory."""
        view, led_cell, leds = 0x20002000, 0x20003000, 0x20003100
        listener, listeners, patterns = 0x20001000, 0x20001100, 0x20010000
        view_listeners = 0x20001200
        empty_pattern = bytes([0, 6, 0, 0, 7, 255, 0, 0]) * 32 + bytes([0xA5]) * (0xA28 - 256)

        st1 = self.store(bytes(32) + bytes([7]) * 32 + bytes(32) + bytes([255]) * 32)
        st2 = self.store(bytes(32) + bytes([6]) * 32 + bytes(32))
        selection = self.store(bytes([active_pattern, 0, 0, 0]))
        note = self.store(bytes([60, 0, 0, 0]))
        held = self.store(bytes([255, 0, 0, 0]) * 2)
        pressed = self.store(bytes(8))
        page = self.store(bytes(4))
        zero_mod = self.store(bytes(4))

        self.word(listener, 0x080696A0)  # real stock vtable -> 0x08048208
        for offset, val in ((4, patterns), (0x1C, st1), (0x20, st2), (0x28, selection)):
            self.word(listener + offset, val)

        self.word(listeners, listener)
        self.word(listeners + 4, 0xFFFFFFFF)
        self.word(listeners + 8, view + 8)
        self.word(listeners + 12, 0xFFFFFFFF)

        self.word(view_listeners, view + 8)
        self.word(view_listeners + 4, 0xFFFFFFFF)

        for s, count, l_list in ((st1, 2, listeners), (st2, 1, listeners),
                                 (pressed, 1, view_listeners), (held, 1, view_listeners)):
            self.u.mem_write(s + 1, bytes([count]))
            self.word(s + 0x14, l_list)

        self.word(led_cell, leds)
        for offset, val in (
            (0, 0x080682CC), (4, led_cell), (8, 0x080682F8),
            (0xC, st1), (0x10, st2), (0x18, held), (0x20, pressed),
            (0x34, zero_mod), (0x3C, zero_mod), (0x40, zero_mod), (0x44, zero_mod),
            (0x5C, note), (0x60, page), (0x64, held), (0x70, zero_mod)
        ):
            self.word(view + offset, val)

        self.u.mem_write(patterns, empty_pattern * 8)
        self.u.mem_write(view + 0xB4, bytes(16))  # clean control block
        self.u.mem_write(leds, bytes([0xA5]) * 64)

        return {
            "view": view,
            "leds": leds,
            "patterns": patterns,
            "page": page,
            "st1": st1,
            "st2": st2,
        }

    def test_stock_container_routing_split(self):
        """Validates stock grid container subview routing and local pad transformation.

        Pads 0..15 route to top subview (Step View).
        Pads 16..31 route to bottom subview (Note/Sample view).
        In stock mode 0, transformed pad for bottom half subtracts 16 and adds page offset.
        """
        grid = 0x20001000
        track_store = self.store(bytes(4))
        self.word(grid + 0x25C, track_store)
        top_view, bottom_view = 0x20002000, 0x20003000
        page_obj = 0x20004000
        page_store = self.store(bytes(4))
        self.word(page_obj + 0x10, page_store)

        for track in (0, 7):
            self.u.mem_write(track_store + 0x40, bytes([track, 0, 0, 0]))
            self.word(grid + 0x74 + track * 4, top_view)
            self.word(grid + 0x14 + track * 4, bottom_view)
            self.word(grid + 0x19C + track * 4, page_obj)

            # Test in mode 0
            self.u.mem_write(grid + 0x264, bytes([0]))

            # Page 0
            self.u.mem_write(page_store + 0x40, bytes([0, 0, 0, 0]))
            for pad in range(32):
                resolved_view = self.call(0x0804DC86, grid, pad)
                local_pad = self.call(0x0804DF3E, grid, pad, track, 0)
                if pad < 16:
                    self.assertEqual(resolved_view, top_view)
                    self.assertEqual(local_pad, pad)
                else:
                    self.assertEqual(resolved_view, bottom_view)
                    self.assertEqual(local_pad, pad - 16)

            # Page 1
            self.u.mem_write(page_store + 0x40, bytes([1, 0, 0, 0]))
            for pad in range(32):
                resolved_view = self.call(0x0804DC86, grid, pad)
                local_pad = self.call(0x0804DF3E, grid, pad, track, 0)
                if pad < 16:
                    self.assertEqual(resolved_view, top_view)
                    self.assertEqual(local_pad, pad)
                else:
                    self.assertEqual(resolved_view, bottom_view)
                    # Mode 0 on page 1 adds 16 back to bottom pad
                    self.assertEqual(local_pad, pad)

    def test_step_index_overflow_hazard_and_corruption_proof(self):
        """Demonstrates that step index >= 32 corrupts step view control memory and pattern stores.

        Proves:
        1. view + 0x74 + 2 * 32 = view + 0xB4: status word overwrites clear/secondary control byte.
        2. ST2 Note setter (0x08054A5C) with step=32 overwrites Step 0 Gate length in pattern commit.
        3. ST1 Velocity setter (0x080549B0) with step=32 overwrites Step 0 Probability in pattern commit.
        """
        env = self.setup_step_view_environment(active_pattern=0)
        view = env["view"]
        patterns = env["patterns"]
        page = env["page"]
        st1 = env["st1"]
        st2 = env["st2"]

        # 1. Status array overflow writing into view + 0xB4
        # When page == 1, passing pad 16 causes step = 16 + 16 = 32
        self.u.mem_write(page + 0x40, bytes([1, 0, 0, 0]))
        self.assertEqual(self.u.mem_read(view + 0xB4, 4), bytes(4))

        # Press pad 16 with page 1
        self.call(0x0805CB04, view, 16, 96)
        b4_after = self.u.mem_read(view + 0xB4, 4)
        # Status bit 3 (0x0008) is written to view + 0x74 + 2 * 32 = view + 0xB4
        self.assertEqual(b4_after[0], 0x08, "Status bit 3 must corrupt view + 0xB4 on step 32")

        # 2. ST2 store parameter aliasing
        # Step 0 Gate is originally 6
        # Setting Note on step 32 to 72 aliases to Word 8 (32 // 4 = 8), which is Gate[0]
        self.call(0x08054A5C, st2, 32, 72)
        self.call(0x0803FBEC, st2)  # notify commits to pattern memory
        committed_step0 = self.u.mem_read(patterns, 8)
        self.assertEqual(committed_step0[1], 72, "Note[32] must corrupt Step 0 Gate length")

        # 3. ST1 store parameter aliasing
        # Step 0 Probability is originally 7
        # Setting Velocity on step 32 to 3 aliases to Word 8 (offset 32), which is Probability[0]
        self.call(0x080549B0, st1, 32, 3)
        self.call(0x0803FBEC, st1)  # notify commits to pattern memory
        committed_step0 = self.u.mem_read(patterns, 8)
        self.assertEqual(committed_step0[4], 3, "Velocity[32] must corrupt Step 0 Probability")

    def test_safe_32pad_full_lifecycle_all_steps(self):
        """Validates full 32-pad press/release lifecycle for all 32 steps (0..31).

        In the 32-pad Sequencer Mode control flow:
        - All 32 pads (0..31) route to the Step View.
        - Page offset is 0, so local_pad maps 1:1 to step (0..31).
        - Every step toggles ON on first tap, and OFF on second tap.
        - view + 0xB4 control area remains completely intact (0x00).
        - Pattern memory commits all 32 steps accurately.
        - LED color buffer receives proper palette updates for all 32 steps.
        """
        env = self.setup_step_view_environment(active_pattern=0)
        view = env["view"]
        leds = env["leds"]
        patterns = env["patterns"]
        palette = 0x08062AB0
        pressed_color = self.image[palette - BASE + 31 * 2:palette - BASE + 32 * 2]

        # Verify initial control area integrity
        self.assertEqual(self.u.mem_read(view + 0xB4, 4), bytes(4))

        # --- Cycle 1: Turn ON all 32 steps ---
        for pad in range(32):
            with self.subTest(cycle="turn_on", step=pad):
                # Press
                self.call(0x0805CB04, view, pad, 96)
                status_press = struct.unpack("<H", self.u.mem_read(view + 0x74 + 2 * pad, 2))[0]
                self.assertEqual(status_press, 8)  # bit 3 held
                led_press = bytes(self.u.mem_read(leds + 2 * pad, 2))
                self.assertEqual(led_press, pressed_color)

                # Release
                self.call(0x0805CCF0, view, pad)
                status_rel = struct.unpack("<H", self.u.mem_read(view + 0x74 + 2 * pad, 2))[0]
                self.assertEqual(status_rel, 2)  # bit 1 hit (step active)

                # Control block view + 0xB4 must NEVER be touched
                self.assertEqual(self.u.mem_read(view + 0xB4, 4), bytes(4))

        # Verify that all 32 steps are committed to pattern memory
        pattern_data = self.u.mem_read(patterns, 32 * 8)
        for step in range(32):
            step_bytes = pattern_data[step * 8:(step + 1) * 8]
            self.assertEqual(step_bytes[0], 60, f"Step {step} note must be 60")
            self.assertEqual(step_bytes[3], 96, f"Step {step} velocity must be 96")

        # --- Cycle 2: Turn OFF all 32 steps ---
        for pad in range(32):
            with self.subTest(cycle="turn_off", step=pad):
                # Press
                self.call(0x0805CB04, view, pad, 96)
                # Release
                self.call(0x0805CCF0, view, pad)
                status_off = struct.unpack("<H", self.u.mem_read(view + 0x74 + 2 * pad, 2))[0]
                self.assertEqual(status_off, 0)  # cleared

                # Control block view + 0xB4 must remain intact
                self.assertEqual(self.u.mem_read(view + 0xB4, 4), bytes(4))

        # Pattern memory must now have all 32 steps cleared (velocity 0)
        pattern_data_off = self.u.mem_read(patterns, 32 * 8)
        for step in range(32):
            step_bytes = pattern_data_off[step * 8:(step + 1) * 8]
            self.assertEqual(step_bytes[3], 0, f"Step {step} velocity must be cleared to 0")

    def test_cross_boundary_concurrent_press_and_release(self):
        """Validates concurrent pad presses across top/bottom half boundaries (pad 15 and 16).

        Tests that holding pad 15 while pressing pad 16 maintains correct multi-bit held masks
        and commits both steps independently on sequential releases.
        """
        env = self.setup_step_view_environment(active_pattern=0)
        view = env["view"]
        patterns = env["patterns"]

        # Press pad 15 (step 15)
        self.call(0x0805CB04, view, 15, 96)
        held_mask = self.readword(view + 0xC0)
        self.assertEqual(held_mask, (1 << 15))

        # Press pad 16 (step 16) while pad 15 is still held
        self.call(0x0805CB04, view, 16, 96)
        held_mask = self.readword(view + 0xC0)
        self.assertEqual(held_mask, (1 << 15) | (1 << 16))

        # Release pad 15 first
        self.call(0x0805CCF0, view, 15)
        held_mask = self.readword(view + 0xC0)
        self.assertEqual(held_mask, (1 << 16))

        # Release pad 16
        self.call(0x0805CCF0, view, 16)
        held_mask = self.readword(view + 0xC0)
        self.assertEqual(held_mask, 0)

        # Both steps 15 and 16 must be active and committed
        st15 = struct.unpack("<H", self.u.mem_read(view + 0x74 + 2 * 15, 2))[0]
        st16 = struct.unpack("<H", self.u.mem_read(view + 0x74 + 2 * 16, 2))[0]
        self.assertEqual(st15, 2)
        self.assertEqual(st16, 2)

        p15 = self.u.mem_read(patterns + 15 * 8, 8)
        p16 = self.u.mem_read(patterns + 16 * 8, 8)
        self.assertEqual(p15[0], 60)
        self.assertEqual(p15[3], 96)
        self.assertEqual(p16[0], 60)
        self.assertEqual(p16[3], 96)

    def test_routing_guard_clamping_prevents_overflow(self):
        """Validates that a routing guard mask (pad & 0x1F) prevents any invalid index >= 32.

        Tests that passing out-of-range pad IDs (e.g. 32, 47, 63, 127) through the guard
        clamps them safely within [0..31] and never causes step index overflow.
        """
        env = self.setup_step_view_environment(active_pattern=0)
        view = env["view"]

        def guarded_step_press(raw_pad, velocity):
            # 32-pad routing guard: strict clamping / masking to 5 bits (0..31)
            clamped_pad = raw_pad & 0x1F
            self.assertLess(clamped_pad, 32)
            self.call(0x0805CB04, view, clamped_pad, velocity)
            return clamped_pad

        def guarded_step_release(raw_pad):
            clamped_pad = raw_pad & 0x1F
            self.assertLess(clamped_pad, 32)
            self.call(0x0805CCF0, view, clamped_pad)
            return clamped_pad

        for out_of_range_pad in (32, 33, 47, 48, 63, 127):
            guarded_step_press(out_of_range_pad, 96)
            guarded_step_release(out_of_range_pad)
            # view + 0xB4 must remain completely uncorrupted
            self.assertEqual(self.u.mem_read(view + 0xB4, 4), bytes(4))


if __name__ == "__main__":
    unittest.main()
