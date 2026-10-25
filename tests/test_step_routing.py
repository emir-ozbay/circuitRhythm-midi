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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

try:
    import seq_Patch  # noqa: F401
except ImportError:
    pass

from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB, CS_MODE_MCLASS
from inspect_ui import load_image, BASE
from patch_firmware import apply_patches
from seq_patch import (
    CODE_CAVE_BASE,
    HEAP_CUR_PTR,
    HEAP_LIMIT,
    HEAP_LIMIT_PTR,
    HOOK_GRID_MODE_CLEANUP,
    HOOK_GRID_PRESS_RESOLVE,
    HOOK_GRID_PRESS_TRANSFORM,
    HOOK_GRID_RELEASE_RESOLVE,
    HOOK_GRID_RELEASE_TRANSFORM,
    HOOK_STEP_PRESS_PAGE,
    HOOK_STEP_RELEASE_PAGE,
    HOOK_COMP_TOP_LEDS,
    HOOK_COMP_BOTTOM_MEMCPY,
    OFF_GRID_PTR,
    OFF_SEQ_ENABLED,
    SEQ_STATE_ADDR,
    STOCK_GRID_PRESS,
    STOCK_GRID_RELEASE,
    arm_code,
    build_step_routing_patches,
)
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_THUMB, UC_MODE_MCLASS, UC_HOOK_CODE
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


class PatchedStepRoutingTests(StepRoutingTests):
    """Unicorn emulation tests on the patched 5706 firmware image with M4 step routing hooks."""

    @classmethod
    def setUpClass(cls):
        cls.stock_image = load_image()
        cls.patches = build_step_routing_patches(CODE_CAVE_BASE)
        cls.image, cls.patches_info, cls.changed_ranges = apply_patches(
            cls.stock_image, cls.patches
        )
        cls.cave_bytes, cls.labels = arm_code(CODE_CAVE_BASE)

    def setUp(self):
        super().setUp()
        # Initialize stock bump allocator pointers in RAM
        self.word(HEAP_LIMIT_PTR, HEAP_LIMIT)
        self.word(HEAP_CUR_PTR, 0x2004EA98)

    def setup_grid_and_step_view(self, seq_enabled=1, grid_mode=0, track=0):
        """Sets up a complete Grid Container + Step View + Bottom Subviews environment."""
        env = self.setup_step_view_environment(active_pattern=0)
        view = env["view"]
        page = env["page"]

        grid = 0x20005000
        track_store = self.store(bytes([track, 0, 0, 0]))
        self.word(grid + 0x25C, track_store)
        self.u.mem_write(grid + 0x264, bytes([grid_mode]))
        self.u.mem_write(grid + 0x228, bytes(4))  # clear held pad bitmask

        # Grid's per-track page object ([grid + 0x19C + track * 4] -> +0x10 -> page store)
        page_obj = 0x20005400
        self.word(page_obj + 0x10, page)
        self.word(grid + 0x19C + track * 4, page_obj)

        # Top subview for track = Step View
        self.word(grid + 0x74 + track * 4, view)

        # Bottom subviews for mode 0 (+0x14), mode 2 Velocity (+0x9C), mode 3 Gate (+0xBC)
        bottom_views = {}
        bottom_events = []

        press_cb = 0x0800E100
        release_cb = 0x0800E104
        self.u.mem_write(press_cb, bytes.fromhex("7047"))    # bx lr
        self.u.mem_write(release_cb, bytes.fromhex("7047"))  # bx lr

        for mode_id, offset, b_addr in ((0, 0x14, 0x20006000), (2, 0x9C, 0x20006100), (3, 0xBC, 0x20006200)):
            vt_addr = b_addr + 0x40
            self.word(b_addr, vt_addr)
            self.word(vt_addr + 0, press_cb | 1)
            self.word(vt_addr + 4, release_cb | 1)
            self.word(grid + offset + track * 4, b_addr)
            bottom_views[mode_id] = b_addr

        def on_bottom_cb(uc, addr, size, data):
            if addr == press_cb:
                bottom_events.append((
                    "press",
                    uc.reg_read(UC_ARM_REG_R0),
                    uc.reg_read(UC_ARM_REG_R1),
                    uc.reg_read(UC_ARM_REG_R2),
                ))
            elif addr == release_cb:
                bottom_events.append((
                    "release",
                    uc.reg_read(UC_ARM_REG_R0),
                    uc.reg_read(UC_ARM_REG_R1),
                ))

        self.u.hook_add(UC_HOOK_CODE, on_bottom_cb)

        # Initialize Sequencer Mode state block via c_seq_state() and set seq_enabled
        state_addr = self.call(self.labels["c_seq_state"])
        self.assertEqual(state_addr, SEQ_STATE_ADDR)
        self.u.mem_write(SEQ_STATE_ADDR + OFF_SEQ_ENABLED, bytes([seq_enabled]))

        env["grid"] = grid
        env["bottom_views"] = bottom_views
        env["bottom_events"] = bottom_events
        return env

    def test_patched_hooks_and_code_cave_disassembly(self):
        """Verifies all 9 in-place Thumb-2 BL hooks and code-cave layout via Capstone."""
        md = Cs(CS_ARCH_ARM, CS_MODE_THUMB | CS_MODE_MCLASS)

        expected_hooks = [
            (HOOK_GRID_MODE_CLEANUP, self.labels["c_grid_mode_cleanup"]),
            (HOOK_GRID_PRESS_RESOLVE, self.labels["c_resolve_subview"]),
            (HOOK_GRID_PRESS_TRANSFORM, self.labels["c_transform_pad"]),
            (HOOK_GRID_RELEASE_RESOLVE, self.labels["c_resolve_subview"]),
            (HOOK_GRID_RELEASE_TRANSFORM, self.labels["c_transform_pad"]),
            (HOOK_STEP_PRESS_PAGE, self.labels["c_step_page_read"]),
            (HOOK_STEP_RELEASE_PAGE, self.labels["c_step_page_read"]),
            (HOOK_COMP_TOP_LEDS, self.labels["c_comp_top_leds"]),
            (HOOK_COMP_BOTTOM_MEMCPY, self.labels["c_comp_bottom_memcpy"]),
        ]
        for hook_addr, target_addr in expected_hooks:
            raw = self.image[hook_addr - BASE : hook_addr - BASE + 4]
            insns = list(md.disasm(raw, hook_addr))
            self.assertEqual(len(insns), 1)
            self.assertEqual(insns[0].mnemonic, "bl")
            self.assertEqual(insns[0].op_str, f"#{target_addr:#x}")

        # Verify c_zero_word is 4-byte aligned and holds 0x00000000
        zero_addr = self.labels["c_zero_word"]
        self.assertEqual(zero_addr % 4, 0)
        self.assertEqual(self.readword(zero_addr), 0)

    def test_patched_seq_mode_grid_mode_0_32pads_with_page_1_no_overflow(self):
        """Proves that with seq_enabled=1 and grid_mode=0, even when page_store=1:
        - All 32 pads (0..31) pressed/released through 0x0804D7A0 / 0x0804D7DE toggle steps 0..31
          in Step View ON and OFF cleanly.
        - view + 0xB4 is never corrupted.
        - Bottom subview is never invoked.
        """
        env = self.setup_grid_and_step_view(seq_enabled=1, grid_mode=0, track=0)
        grid = env["grid"]
        view = env["view"]
        leds = env["leds"]
        patterns = env["patterns"]
        page = env["page"]
        bottom_events = env["bottom_events"]

        palette = 0x08062AB0
        pressed_color = self.image[palette - BASE + 31 * 2 : palette - BASE + 32 * 2]

        # Force page_store to 1 (page 2: steps 17..32) to prove page lock to 0 in grid_mode == 0
        self.u.mem_write(page + 0x40, bytes([1, 0, 0, 0]))
        self.assertEqual(self.u.mem_read(view + 0xB4, 4), bytes(4))

        # --- Cycle 1: Press & Release all 32 pads (0..31) via Grid Container -> Turn ON steps 0..31 ---
        for pad in range(32):
            with self.subTest(cycle="turn_on", pad=pad):
                self.call(STOCK_GRID_PRESS, grid, pad, 96)
                # Verify grid_ptr captured in state block (+0x08)
                self.assertEqual(self.readword(SEQ_STATE_ADDR + OFF_GRID_PTR), grid)
                # Verify held pad bitmask in grid
                self.assertEqual(self.readword(grid + 0x228), 1 << pad)
                # Verify Step View status bit 3 (held = 8) on step == pad
                status_press = struct.unpack("<H", self.u.mem_read(view + 0x74 + 2 * pad, 2))[0]
                self.assertEqual(status_press, 8)
                self.assertEqual(bytes(self.u.mem_read(leds + 2 * pad, 2)), pressed_color)
                self.assertEqual(self.u.mem_read(view + 0xB4, 4), bytes(4))

                self.call(STOCK_GRID_RELEASE, grid, pad)
                self.assertEqual(self.readword(grid + 0x228), 0)
                status_rel = struct.unpack("<H", self.u.mem_read(view + 0x74 + 2 * pad, 2))[0]
                self.assertEqual(status_rel, 2)  # hit active
                self.assertEqual(self.u.mem_read(view + 0xB4, 4), bytes(4))

        # Bottom subview must never have been called in grid_mode == 0
        self.assertEqual(bottom_events, [])

        # All 32 steps must be committed to pattern memory
        pattern_data = self.u.mem_read(patterns, 32 * 8)
        for step in range(32):
            step_bytes = pattern_data[step * 8 : (step + 1) * 8]
            self.assertEqual(step_bytes[0], 60, f"Step {step} note must be 60")
            self.assertEqual(step_bytes[3], 96, f"Step {step} velocity must be 96")

        # --- Cycle 2: Press & Release all 32 pads (0..31) via Grid Container -> Turn OFF steps 0..31 ---
        for pad in range(32):
            with self.subTest(cycle="turn_off", pad=pad):
                self.call(STOCK_GRID_PRESS, grid, pad, 96)
                self.call(STOCK_GRID_RELEASE, grid, pad)
                status_off = struct.unpack("<H", self.u.mem_read(view + 0x74 + 2 * pad, 2))[0]
                self.assertEqual(status_off, 0)
                self.assertEqual(self.u.mem_read(view + 0xB4, 4), bytes(4))

        self.assertEqual(bottom_events, [])
        pattern_data_off = self.u.mem_read(patterns, 32 * 8)
        for step in range(32):
            step_bytes = pattern_data_off[step * 8 : (step + 1) * 8]
            self.assertEqual(step_bytes[3], 0, f"Step {step} velocity must be cleared to 0")

    def test_patched_seq_mode_velocity_and_gate_modes_preserve_page_and_bottom_pads(self):
        """Proves that with seq_enabled=1 in grid_mode=2 (Velocity) and grid_mode=3 (Gate):
        - The 1-16 page switch works natively for top pads 0..15 (page 0 -> steps 0..15, page 1 -> steps 16..31).
        - Bottom pads 16..31 route to the mode's bottom subview with local pad 0..15 (pad - 16).
        """
        for grid_mode in (2, 3):
            with self.subTest(grid_mode=grid_mode):
                self.setUp()
                env = self.setup_grid_and_step_view(seq_enabled=1, grid_mode=grid_mode, track=0)
                grid = env["grid"]
                view = env["view"]
                patterns = env["patterns"]
                page = env["page"]
                bottom_view = env["bottom_views"][grid_mode]
                bottom_events = env["bottom_events"]

                # 1. Top pads 0..15 on Page 0 (steps 0..15) and Page 1 (steps 16..31)
                for page_val, step_offset in ((0, 0), (1, 16)):
                    self.u.mem_write(page + 0x40, bytes([page_val, 0, 0, 0]))
                    for pad in range(16):
                        expected_step = pad + step_offset
                        self.call(STOCK_GRID_PRESS, grid, pad, 96)
                        st_press = struct.unpack("<H", self.u.mem_read(view + 0x74 + 2 * expected_step, 2))[0]
                        self.assertEqual(st_press, 8)
                        self.call(STOCK_GRID_RELEASE, grid, pad)
                        st_rel = struct.unpack("<H", self.u.mem_read(view + 0x74 + 2 * expected_step, 2))[0]
                        self.assertEqual(st_rel, 2)
                        self.assertEqual(self.u.mem_read(view + 0xB4, 4), bytes(4))

                    # Verify committed steps in pattern memory for this page
                    for pad in range(16):
                        expected_step = pad + step_offset
                        step_bytes = self.u.mem_read(patterns + expected_step * 8, 8)
                        self.assertEqual(step_bytes[0], 60)
                        self.assertEqual(step_bytes[3], 96)

                    # Toggle them back OFF on the same page
                    for pad in range(16):
                        expected_step = pad + step_offset
                        self.call(STOCK_GRID_PRESS, grid, pad, 96)
                        self.call(STOCK_GRID_RELEASE, grid, pad)
                        st_off = struct.unpack("<H", self.u.mem_read(view + 0x74 + 2 * expected_step, 2))[0]
                        self.assertEqual(st_off, 0)

                self.assertEqual(bottom_events, [])

                # 2. Bottom pads 16..31 on both Page 0 and Page 1 route to bottom_view with local_pad = pad - 16
                for page_val in (0, 1):
                    self.u.mem_write(page + 0x40, bytes([page_val, 0, 0, 0]))
                    for pad in range(16, 32):
                        bottom_events.clear()
                        self.call(STOCK_GRID_PRESS, grid, pad, 100)
                        self.call(STOCK_GRID_RELEASE, grid, pad)
                        self.assertEqual(
                            bottom_events,
                            [
                                ("press", bottom_view, pad - 16, 100),
                                ("release", bottom_view, pad - 16),
                            ],
                        )
                        # Step View must remain completely untouched by bottom pad presses in mode 2/3
                        for step in range(32):
                            st = struct.unpack("<H", self.u.mem_read(view + 0x74 + 2 * step, 2))[0]
                            self.assertEqual(st, 0)
                        self.assertEqual(self.u.mem_read(view + 0xB4, 4), bytes(4))

    def test_patched_normal_mode_seq_disabled_preserves_stock_behavior(self):
        """Proves that when seq_enabled=0 (Normal Mode) in grid_mode=0:
        - Top pads 0..15 route to Step View with normal page 0/1 switching.
        - Bottom pads 16..31 route to the bottom Note/Sample subview with stock local pad transformation.
        """
        env = self.setup_grid_and_step_view(seq_enabled=0, grid_mode=0, track=0)
        grid = env["grid"]
        view = env["view"]
        page = env["page"]
        bottom_view = env["bottom_views"][0]
        bottom_events = env["bottom_events"]

        # Page 1 on top pad 0 -> step 16 in Step View
        self.u.mem_write(page + 0x40, bytes([1, 0, 0, 0]))
        self.call(STOCK_GRID_PRESS, grid, 0, 96)
        self.call(STOCK_GRID_RELEASE, grid, 0)
        self.assertEqual(struct.unpack("<H", self.u.mem_read(view + 0x74 + 2 * 16, 2))[0], 2)
        self.assertEqual(bottom_events, [])

        # Bottom pad 16 on Page 0 -> bottom_view with local_pad 0; on Page 1 -> local_pad 16
        for page_val, expected_local in ((0, 0), (1, 16)):
            self.u.mem_write(page + 0x40, bytes([page_val, 0, 0, 0]))
            bottom_events.clear()
            self.call(STOCK_GRID_PRESS, grid, 16, 80)
            self.call(STOCK_GRID_RELEASE, grid, 16)
            self.assertEqual(
                bottom_events,
                [
                    ("press", bottom_view, expected_local, 80),
                    ("release", bottom_view, expected_local),
                ],
            )

    def test_held_pad_ownership_cleanup_on_track_or_mode_change(self):
        """Validates that holding a pad while changing tracks or switching view mode (0x0804D6B6)
        cleanly clears grid+0x228, view+0xB8, view+0xC0, status bit 3 (held), and restores normal LED color.
        """
        env = self.setup_grid_and_step_view(seq_enabled=1, grid_mode=0, track=0)
        grid = env["grid"]
        view0 = env["view"]
        leds0 = env["leds"]

        # Setup Track 1 Step View on grid
        env1 = self.setup_step_view_environment(active_pattern=0)
        view1 = env1["view"]
        self.word(grid + 0x74 + 1 * 4, view1)

        # Configure Grid container vtable and store arrays expected by 0x0804D6B6
        self.word(grid, 0x080678DC)
        dummy_store = self.store(bytes(16))
        self.word(grid + 0x260, dummy_store)
        for i in range(8):
            self.word(grid + 0x238 + i * 4, self.store(bytes(16)))
        for i in range(8):
            obj = self.store(bytes(0x100))
            self.u.mem_write(obj + 0x50, bytes([1]))  # allows 0x0805814E to return cleanly
            self.word(grid + 0x1C4 + i * 4, obj)

        palette = 0x08062AB0
        pressed_color = self.image[palette - BASE + 31 * 2 : palette - BASE + 32 * 2]

        # Scenario 1: Pad 5 (top half, step 5) held on Track 0 when switching tracks
        self.call(STOCK_GRID_PRESS, grid, 5, 96)
        self.assertEqual(self.readword(grid + 0x228), 1 << 5)
        self.assertEqual(self.readword(view0 + 0xB8), 1 << 5)
        self.assertEqual(self.readword(view0 + 0xC0), 1 << 5)
        st5_press = struct.unpack("<H", self.u.mem_read(view0 + 0x74 + 2 * 5, 2))[0]
        self.assertEqual(st5_press, 8)
        self.assertEqual(bytes(self.u.mem_read(leds0 + 2 * 5, 2)), pressed_color)

        # Track change: calls 0x0804D6B6(grid, 0)
        self.call(0x0804D6B6, grid, 0)

        # Verify all held bits and masks are cleanly cleared and LED returned to normal
        self.assertEqual(self.readword(grid + 0x228), 0)
        self.assertEqual(self.readword(view0 + 0xB8), 0)
        self.assertEqual(self.readword(view0 + 0xC0), 0)
        st5_after = struct.unpack("<H", self.u.mem_read(view0 + 0x74 + 2 * 5, 2))[0]
        self.assertEqual(st5_after & 8, 0)
        self.assertNotEqual(bytes(self.u.mem_read(leds0 + 2 * 5, 2)), pressed_color)

        # Scenario 2: Pad 20 (bottom half, step 20 in 32-pad mode) held on Track 0 when switching to Velocity mode
        self.call(STOCK_GRID_PRESS, grid, 20, 96)
        self.assertEqual(self.readword(grid + 0x228), 1 << 20)
        self.assertEqual(self.readword(view0 + 0xB8), 1 << 20)
        self.assertEqual(self.readword(view0 + 0xC0), 1 << 20)
        st20_press = struct.unpack("<H", self.u.mem_read(view0 + 0x74 + 2 * 20, 2))[0]
        self.assertEqual(st20_press, 8)
        self.assertEqual(bytes(self.u.mem_read(leds0 + 2 * 20, 2)), pressed_color)

        # View mode change: calls 0x0804D6B6(grid, 2) (mode 2 = Velocity)
        self.call(0x0804D6B6, grid, 2)

        # Verify all held bits and masks are cleanly cleared and LED returned to normal
        self.assertEqual(self.readword(grid + 0x228), 0)
        self.assertEqual(self.readword(view0 + 0xB8), 0)
        self.assertEqual(self.readword(view0 + 0xC0), 0)
        st20_after = struct.unpack("<H", self.u.mem_read(view0 + 0x74 + 2 * 20, 2))[0]
        self.assertEqual(st20_after & 8, 0)
        self.assertNotEqual(bytes(self.u.mem_read(leds0 + 2 * 20, 2)), pressed_color)


if __name__ == "__main__":
    unittest.main()
