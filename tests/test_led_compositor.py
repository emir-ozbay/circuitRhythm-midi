"""Stock code and 32-step LED compositor in synthetic RAM.

Verifies:
1. Stock Step View LED getter (0x0805D3BC) and Grid Compositor (0x0804DD1C) split behavior.
2. Step View 32-step logical LED buffer mapping (steps 1-16 to top 16 pads, steps 17-32 to bottom 16 pads).
3. Playhead (playback cursor, status bit 0) continuous flow across all 32 steps (1 to 32) without gaps.
4. Other modes (Note, Velocity, etc.) preserve their original bottom pad layout.
5. Compositor memory safety and boundary integrity (no buffer overflows).

Run from project root:
    .venv/Scripts/python.exe -m unittest tests/test_led_compositor.py -v
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


class LedCompositorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.image = load_image()

    def setUp(self):
        self.u = Uc(UC_ARCH_ARM, UC_MODE_THUMB | UC_MODE_MCLASS)
        self.u.mem_map(0x08000000, 0x80000)
        self.u.mem_write(BASE, self.image)
        self.u.mem_map(0x20000000, 0x50000)
        self.next_store = 0x20008000

        # Memory layout addresses
        self.grid = 0x20001000
        self.grid_led_cell = 0x20001080
        self.grid_led_buf = 0x20001400
        self.u.mem_write(self.grid_led_buf, bytes(0x60))
        self.word(self.grid_led_cell, self.grid_led_buf)
        self.word(self.grid + 4, self.grid_led_cell)

        # Selected track store
        self.selected_track = self.store(bytes([0, 0, 0, 0]))
        self.word(self.grid + 0x25C, self.selected_track)
        self.u.mem_write(self.grid + 0x264, bytes([0]))  # Mode 0

        # Store at grid + 0x22C
        self.store_22c = self.store(bytes([0, 0, 0, 0]))
        self.word(self.grid + 0x22C, self.store_22c)

        # Track stores array at grid + 0x258 (referenced by 0x080588AC)
        self.track_array = 0x20002800
        self.track_prop_store = self.store(bytes([0] * 16))
        for t in range(8):
            self.word(self.track_array + t * 4, self.track_prop_store)
        self.word(self.grid + 0x258, self.track_array)

        # Page object & store
        self.page_obj = 0x20002000
        self.page_vt = 0x20002100
        self.page_led_cell = 0x20002080
        self.page_led_buf = 0x20002400
        self.u.mem_write(self.page_led_buf, bytes([0x55] * 16))
        self.word(self.page_led_cell, self.page_led_buf)
        self.word(self.page_obj + 0, self.page_vt)
        self.word(self.page_obj + 4, self.page_led_cell)

        # Stub LED getter for subviews: ldr r0, [r0, #4]; ldr r0, [r0]; bx lr
        self.stub_led = 0x0800E100
        self.u.mem_write(self.stub_led, bytes.fromhex("4068 0068 7047"))
        self.word(self.page_vt + 0x1C, self.stub_led | 1)

        self.page_store = self.store(bytes([0, 0, 0, 0]))
        self.word(self.page_obj + 0x10, self.page_store)
        self.word(self.grid + 0x19C, self.page_obj)

        # Step View setup
        self.step_view = 0x20003000
        self.step_led_cell = 0x20003500  # Outside view status words!
        self.step_led_buf = 0x20003600
        self.u.mem_write(self.step_led_buf, bytes(64))
        self.word(self.step_led_cell, self.step_led_buf)

        self.held = self.store(bytes([255, 0, 0, 0]) * 2)
        self.st1 = self.store(bytes(32) + bytes([7]) * 32 + bytes(32) + bytes([255]) * 32)
        self.st2 = self.store(bytes(32) + bytes([6]) * 32 + bytes(32))
        self.note = self.store(bytes([60, 0, 0, 0]))

        for offset, value in ((0, 0x080682CC), (4, self.step_led_cell), (8, 0x080682F8),
                              (0xC, self.st1), (0x10, self.st2), (0x18, self.held),
                              (0x5C, self.note), (0x60, self.page_store), (0x64, self.held)):
            self.word(self.step_view + offset, value)
        self.word(self.grid + 0x74, self.step_view)

        # Note View (bottom view for mode 0)
        self.note_view = 0x20004000
        self.note_vt = 0x20004100
        self.note_led_cell = 0x20004500
        self.note_led_buf = 0x20004600
        self.note_bytes = bytes([0x40 + (i % 32) for i in range(64)])
        self.u.mem_write(self.note_led_buf, self.note_bytes)
        self.word(self.note_led_cell, self.note_led_buf)
        self.word(self.note_view + 0, self.note_vt)
        self.word(self.note_view + 4, self.note_led_cell)
        self.word(self.note_vt + 0x1C, self.stub_led | 1)
        self.word(self.grid + 0x14, self.note_view)

        # Velocity View (bottom view for mode 2)
        self.vel_view = 0x20005000
        self.vel_vt = 0x20005100
        self.vel_led_cell = 0x20005500
        self.vel_led_buf = 0x20005600
        self.vel_bytes = bytes([0x80 + (i % 32) for i in range(64)])
        self.u.mem_write(self.vel_led_buf, self.vel_bytes)
        self.word(self.vel_led_cell, self.vel_led_buf)
        self.word(self.vel_view + 0, self.vel_vt)
        self.word(self.vel_view + 4, self.vel_led_cell)
        self.word(self.vel_vt + 0x1C, self.stub_led | 1)
        self.word(self.grid + 0x9C, self.vel_view)

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
        self.u.emu_start(addr | 1, STOP, count=50000)
        self.assertEqual(self.u.reg_read(UC_ARM_REG_PC), STOP)
        return self.u.reg_read(UC_ARM_REG_R0)

    def composite_grid(self, sequencer_only_mode=False):
        """Executes grid composition.

        In stock mode: calls real stock compositor 0x0804DD1C.
        In Sequencer Only mode:
            - Top 16 pads get Step View steps 0..15 (bytes 0..31 of full LED buffer).
            - Bottom 16 pads get Step View steps 16..31 (bytes 32..63 of full LED buffer).
            - Side buttons/controls preserved via stock compositor flow.
        """
        mode = self.u.mem_read(self.grid + 0x264, 1)[0]
        if not sequencer_only_mode or mode != 0:
            # Stock mode or non-step subview mode: run stock compositor
            return self.call(0x0804DD1C, self.grid)

        # 32-step Sequencer Only mode:
        # Run stock compositor with page=0 to populate top half and side controls
        self.u.mem_write(self.page_store + 0x40, bytes([0, 0, 0, 0]))
        self.call(0x0804DD1C, self.grid)

        # Compositor stitch: copy Step View's second 16-step buffer (steps 16..31)
        # to the bottom 16 pads (grid_output + 0x20, length 0x20 bytes).
        full_step_buf = self.readword(self.step_led_cell)
        grid_out = self.readword(self.grid_led_cell)

        # Real ARM memcpy (0x08022CF0): dest = grid_out + 0x20, src = full_step_buf + 0x20, len = 0x20
        self.call(0x08022CF0, grid_out + 0x20, full_step_buf + 0x20, 0x20)
        return grid_out

    def test_stock_step_view_led_getter_and_compositor_split(self):
        """Verifies stock Step View LED getter (0x0805D3BC) and Compositor (0x0804DD1C)."""
        # Populate Step View with distinct bytes across 64 bytes (32 steps * 2 bytes)
        step_pattern = bytes([0x10 + i for i in range(64)])
        self.u.mem_write(self.step_led_buf, step_pattern)

        # Page 0: LED getter returns buffer + 0
        self.u.mem_write(self.page_store + 0x40, bytes([0, 0, 0, 0]))
        ptr0 = self.call(0x0805D3BC, self.step_view)
        self.assertEqual(ptr0, self.step_led_buf)

        # Page 1: LED getter returns buffer + 0x20
        self.u.mem_write(self.page_store + 0x40, bytes([1, 0, 0, 0]))
        ptr1 = self.call(0x0805D3BC, self.step_view)
        self.assertEqual(ptr1, self.step_led_buf + 0x20)

        # Test stock compositor with Page 0
        self.u.mem_write(self.page_store + 0x40, bytes([0, 0, 0, 0]))
        self.call(0x0804DD1C, self.grid)
        out0 = self.u.mem_read(self.grid_led_buf, 64)
        # Top 16 pads: Step View Page 0 (steps 0..15)
        self.assertEqual(out0[:32], step_pattern[:32])
        # Bottom 16 pads: Note View Page 0
        self.assertEqual(out0[32:64], self.note_bytes[:32])

        # Test stock compositor with Page 1
        self.u.mem_write(self.page_store + 0x40, bytes([1, 0, 0, 0]))
        self.call(0x0804DD1C, self.grid)
        out1 = self.u.mem_read(self.grid_led_buf, 64)
        # Top 16 pads: Step View Page 1 (steps 16..31)
        self.assertEqual(out1[:32], step_pattern[32:64])
        # Bottom 16 pads: Note View Page 1
        self.assertEqual(out1[32:64], self.note_bytes[32:64])

    def test_step_view_32step_logical_led_buffer_mapping(self):
        """Verifies 32-step logical buffer mapping to 32 grid pads (1..16 top, 17..32 bottom)."""
        # Compute colors for all 32 steps using real color engine 0x0805CF24
        # Even steps are hit (status=2), odd steps are empty (status=0)
        for s in range(32):
            status = 2 if (s % 2 == 0) else 0
            self.u.mem_write(self.step_view + 0x74 + s * 2, struct.pack("<H", status))
            self.call(0x0805CF24, self.step_view, s)

        # Read the 64-byte Step View LED buffer
        step_buf_data = self.u.mem_read(self.step_led_buf, 64)

        # Run 32-step Compositor
        self.composite_grid(sequencer_only_mode=True)
        grid_data = self.u.mem_read(self.grid_led_buf, 64)

        # Top 16 pads (0..15) must match steps 0..15
        self.assertEqual(grid_data[:32], step_buf_data[:32])

        # Bottom 16 pads (16..31) must match steps 16..31
        self.assertEqual(grid_data[32:64], step_buf_data[32:64])

        # Verify individual step colors
        for s in range(32):
            pad_color = struct.unpack_from("<H", grid_data, s * 2)[0]
            expected_color = 0x0018 if (s % 2 == 0) else 0x0019  # Hit vs empty
            self.assertEqual(pad_color, expected_color, f"Pad {s} mismatch")

    def test_playhead_continuous_flow_across_32_steps(self):
        """Verifies playhead (status bit 0) seamlessly flows across all 32 pads (0..31)."""
        # Base pattern: 4-on-the-floor beat (steps 0, 4, 8, 12, 16, 20, 24, 28 have hit=1)
        for s in range(32):
            status = 2 if (s % 4 == 0) else 0
            self.u.mem_write(self.step_view + 0x74 + s * 2, struct.pack("<H", status))
            self.call(0x0805CF24, self.step_view, s)

        # Iterate playhead across all 32 steps (0 to 31)
        for cursor in range(32):
            with self.subTest(cursor=cursor):
                prev_cursor = (cursor - 1) % 32

                # 1. Clear playhead on previous step
                prev_status = 2 if (prev_cursor % 4 == 0) else 0
                self.u.mem_write(self.step_view + 0x74 + prev_cursor * 2, struct.pack("<H", prev_status))
                self.call(0x0805CF24, self.step_view, prev_cursor)

                # 2. Set playhead (bit 0 = 1) on current step
                curr_status = (2 if (cursor % 4 == 0) else 0) | 1
                self.u.mem_write(self.step_view + 0x74 + cursor * 2, struct.pack("<H", curr_status))
                self.call(0x0805CF24, self.step_view, cursor)

                # 3. Composite 32-step grid
                self.composite_grid(sequencer_only_mode=True)
                grid_data = self.u.mem_read(self.grid_led_buf, 64)

                # 4. Verify all 32 pads
                for pad in range(32):
                    color = struct.unpack_from("<H", grid_data, pad * 2)[0]
                    is_hit = (pad % 4 == 0)
                    if pad == cursor:
                        # Current step must have playhead color
                        expected = 0x001A if is_hit else 0x001B
                        self.assertEqual(color, expected,
                                         f"Playhead pad {pad} expected {hex(expected)}, got {hex(color)}")
                    else:
                        # Non-cursor steps must NOT have playhead color
                        expected = 0x0018 if is_hit else 0x0019
                        self.assertEqual(color, expected,
                                         f"Step {pad} expected non-playhead {hex(expected)}, got {hex(color)}")

                # 5. Verify row isolation
                if cursor < 16:
                    # Cursor is on top row (0..15); bottom row (16..31) must have NO playhead
                    for pad in range(16, 32):
                        c = struct.unpack_from("<H", grid_data, pad * 2)[0]
                        self.assertNotIn(c, (0x001A, 0x001B), f"Bottom pad {pad} improperly lit by top playhead")
                else:
                    # Cursor is on bottom row (16..31); top row (0..15) must have NO playhead
                    for pad in range(0, 16):
                        c = struct.unpack_from("<H", grid_data, pad * 2)[0]
                        self.assertNotIn(c, (0x001A, 0x001B), f"Top pad {pad} improperly lit by bottom playhead")

    def test_other_modes_preserve_original_bottom_pad_layout(self):
        """Verifies that switching to Note or Velocity mode preserves bottom pad layout."""
        # 1. First setup 32-step sequencer mode and verify both rows show steps
        for s in range(32):
            status = 2 if (s < 16) else 0  # Steps 0..15 hit, steps 16..31 empty
            self.u.mem_write(self.step_view + 0x74 + s * 2, struct.pack("<H", status))
            self.call(0x0805CF24, self.step_view, s)

        self.composite_grid(sequencer_only_mode=True)
        grid_data = self.u.mem_read(self.grid_led_buf, 64)
        # Bottom row shows Step View steps 16..31 (all empty = 0x0019)
        for pad in range(16, 32):
            self.assertEqual(struct.unpack_from("<H", grid_data, pad * 2)[0], 0x0019)

        # 2. Switch to Mode 2 (Velocity mode)
        self.u.mem_write(self.grid + 0x264, bytes([2]))
        self.composite_grid(sequencer_only_mode=False)
        vel_grid = self.u.mem_read(self.grid_led_buf, 64)

        # Top row still shows Step View steps 0..15 (all hit = 0x0018)
        for pad in range(0, 16):
            self.assertEqual(struct.unpack_from("<H", vel_grid, pad * 2)[0], 0x0018)

        # Bottom row MUST show Velocity view LEDs, NOT Step View steps 16..31!
        self.assertEqual(vel_grid[32:64], self.vel_bytes[:32])

        # 3. Switch back to Mode 0 with sequencer_only_mode=False (Note mode)
        self.u.mem_write(self.grid + 0x264, bytes([0]))
        self.composite_grid(sequencer_only_mode=False)
        note_grid = self.u.mem_read(self.grid_led_buf, 64)

        # Top row shows Step View
        for pad in range(0, 16):
            self.assertEqual(struct.unpack_from("<H", note_grid, pad * 2)[0], 0x0018)

        # Bottom row MUST show Note view LEDs
        self.assertEqual(note_grid[32:64], self.note_bytes[:32])

    def test_compositor_memory_safety_and_no_overflow(self):
        """Verifies buffer boundaries, view+0xB4 integrity, and no adjacent heap corruption."""
        # Fill grid buffer beyond 64 bytes with canary pattern (bytes 64..95)
        canary = bytes([0xCE] * 32)
        self.u.mem_write(self.grid_led_buf + 64, canary)

        # Step View + 0xB4 must be 0
        self.word(self.step_view + 0xB4, 0)

        # Execute 32-step composition multiple times
        for _ in range(5):
            self.composite_grid(sequencer_only_mode=True)

        # Canary at grid_led_buf + 64 must be intact (first 0x14 bytes are side buttons)
        # Stock compositor writes up to offset 0x54 for side buttons.
        # Bytes 0x54..0x60 are untouched canary.
        canary_after = self.u.mem_read(self.grid_led_buf + 0x54, 12)
        self.assertEqual(canary_after, bytes([0xCE] * 12))

        # Critical: Step View 0xB4 control byte must remain 0
        self.assertEqual(self.readword(self.step_view + 0xB4), 0)


if __name__ == "__main__":
    unittest.main()
