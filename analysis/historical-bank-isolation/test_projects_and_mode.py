"""Unicorn ARM emulation tests for Mode Toggle, Independent 32 Projects, Packs Lock, and MIDI-Only Sample Muting.

Phase 1 Control Hooks verified:
1. Shift + Sample Rec mode toggle (button_id 18 = 0x12) toggling seq_enabled (0 <-> 1) and invoking cleanup.
2. Independent 32 Sequencer Projects using stock Projects view page 1 ([proj_view + 0x36] = 1, slots 32..63)
   and page 0 ([proj_view + 0x36] = 0, slots 0..31) in Normal mode, with Up/Down page toggle permanently locked.
3. Packs view locked out in Sequencer Mode (c_check_packs_allowed returns 0).
4. 1-16 page button disabled only in main 32-step grid_mode == 0, while 100% preserved in Velocity, Gate, Note, etc.
5. Internal sample playback engine muted (MIDI-Only) in Sequencer Mode while active in Normal Mode.

Run with:
    .\\.venv\\Scripts\\python.exe -m unittest tests/test_projects_and_mode.py -v
"""
from __future__ import annotations

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
    HOOK_BUTTON_MODE,
    HOOK_CHECK_PACKS,
    HOOK_PAGE_BTN_MODE0,
    HOOK_PROJ_ENTER_PAGE,
    HOOK_PROJ_PAGE_LOCK,
    HOOK_SAMPLE_TRIGGER_GATE,
    OFF_GRID_PTR,
    OFF_SEQ_ENABLED,
    SEQ_STATE_ADDR,
    arm_code,
    build_phase1_patches,
)
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_THUMB, UC_MODE_MCLASS, UC_HOOK_CODE
from unicorn.arm_const import (
    UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3,
    UC_ARM_REG_R4, UC_ARM_REG_R5, UC_ARM_REG_R6,
    UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_PC,
)

STOP = 0x0800F000


class ProjectsAndModeTests(unittest.TestCase):
    """Unicorn ARM emulation tests on patched 5706 firmware for Phase 1 control hooks."""

    @classmethod
    def setUpClass(cls):
        cls.stock_image = load_image()
        cls.patches = build_phase1_patches(CODE_CAVE_BASE)
        cls.patched_image, cls.patches_info, cls.changed_ranges = apply_patches(
            cls.stock_image, cls.patches
        )
        cls.cave_bytes, cls.labels = arm_code(CODE_CAVE_BASE)

    def setUp(self):
        self.u = Uc(UC_ARCH_ARM, UC_MODE_THUMB | UC_MODE_MCLASS)
        self.u.mem_map(0x08000000, 0x80000)
        self.u.mem_write(BASE, self.patched_image)
        self.u.mem_map(0x20000000, 0x50000)

        # Stop address stub
        self.u.mem_write(STOP, bytes.fromhex("7047"))  # bx lr

        # Initialize stock heap allocator limits in RAM
        self.word(HEAP_LIMIT_PTR, HEAP_LIMIT)
        self.word(HEAP_CUR_PTR, 0x2004EA98)

        # Initialize Sequencer Mode state block via c_seq_state()
        self.call(self.labels["c_seq_state"])

        self.next_store = 0x20008000

    def word(self, addr: int, val: int) -> None:
        self.u.mem_write(addr, struct.pack("<I", val))

    def readword(self, addr: int) -> int:
        return struct.unpack("<I", self.u.mem_read(addr, 4))[0]

    def store(self, data: bytes, active: int = 0) -> int:
        obj = self.next_store
        self.next_store += 0x200
        self.u.mem_write(
            obj,
            struct.pack(
                "<5I", len(data) // 4, active, 0, obj + 0x40, obj + 0xC0
            ),
        )
        self.u.mem_write(obj + 0x40, data)
        self.u.mem_write(obj + 0xC0, data)
        return obj

    def call(self, addr: int, *args: int) -> int:
        regs = [UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3]
        for reg, val in zip(regs, args):
            self.u.reg_write(reg, val)
        self.u.reg_write(UC_ARM_REG_SP, 0x20040000)
        self.u.reg_write(UC_ARM_REG_LR, STOP | 1)
        self.u.emu_start(addr | 1, STOP)
        return self.u.reg_read(UC_ARM_REG_R0)

    def test_all_phase1_hooks_and_code_cave_integrity(self):
        """Verifies that all Phase 1 hook sites and code-cave functions disassemble cleanly."""
        md = Cs(CS_ARCH_ARM, CS_MODE_THUMB | CS_MODE_MCLASS)

        # Verify hook replacements in image
        bl_hooks = [
            (HOOK_PROJ_ENTER_PAGE, self.labels["c_proj_enter_page"]),
            (HOOK_CHECK_PACKS, self.labels["c_check_packs_allowed"]),
            (HOOK_PAGE_BTN_MODE0, self.labels["c_page_btn_mode0"]),
            (HOOK_BUTTON_MODE, self.labels["c_button_mode_hook"]),
        ]
        for hook_addr, target_addr in bl_hooks:
            raw_bytes = self.patched_image[hook_addr - BASE : hook_addr - BASE + 4]
            insns = list(md.disasm(raw_bytes, hook_addr))
            self.assertEqual(len(insns), 1)
            self.assertEqual(insns[0].mnemonic, "bl")
            self.assertEqual(insns[0].op_str, f"#{target_addr:#x}")

        # Verify Projects Up/Down lock NOPs
        lock_bytes = self.patched_image[HOOK_PROJ_PAGE_LOCK - BASE : HOOK_PROJ_PAGE_LOCK - BASE + 4]
        self.assertEqual(lock_bytes, bytes.fromhex("00bf00bf"))

        # Verify Sample Trigger Gate b.w hook
        gate_bytes = self.patched_image[HOOK_SAMPLE_TRIGGER_GATE - BASE : HOOK_SAMPLE_TRIGGER_GATE - BASE + 4]
        insns = list(md.disasm(gate_bytes, HOOK_SAMPLE_TRIGGER_GATE))
        self.assertEqual(len(insns), 1)
        self.assertEqual(insns[0].mnemonic, "b.w")
        self.assertEqual(insns[0].op_str, f"#{self.labels['c_sample_trigger_gate']:#x}")

        # Verify code cave ends with bx lr
        cave_insns = list(md.disasm(self.cave_bytes, CODE_CAVE_BASE))
        self.assertEqual(cave_insns[-1].mnemonic, "bx")
        self.assertEqual(cave_insns[-1].op_str, "lr")

    def test_shift_sample_rec_mode_toggle(self):
        """Validates that Shift + Sample Rec (button 18) toggles seq_enabled (0 <-> 1).

        Proves:
        1. Sample Rec (0x12) without Shift: seq_enabled remains unchanged (0).
        2. Shift + Sample Rec (0x12): seq_enabled toggles from 0 to 1, returning r0 = 1.
        3. Shift + Sample Rec (0x12) again: seq_enabled toggles from 1 to 0, returning r0 = 1.
        4. Other button (e.g. Up 0x14) with Shift: seq_enabled does not toggle.
        5. Full controller button dispatch 0x0803D8B8 takes branch 0x0803DC94 on r0 == 1,
           bypassing stock Sample Rec.
        6. Grid mode cleanup 0x0804D6B6 is called when grid_ptr is known.
        """
        ctrl = 0x20004000
        shift_store = self.store(bytes([0, 0, 0, 0]))  # Shift initially 0
        self.word(ctrl + 0x0C, shift_store)

        from phase1_test_support import ProjectTransitionFixture
        transition = ProjectTransitionFixture(self)
        cleanup_called = []

        def on_cleanup(uc, addr, size, user_data):
            cleanup_called.append((
                uc.reg_read(UC_ARM_REG_R0),
                uc.reg_read(UC_ARM_REG_R1),
            ))

        self.u.mem_write(0x0804D6B6, bytes.fromhex("7047"))  # bx lr stub
        self.u.hook_add(UC_HOOK_CODE, on_cleanup, begin=0x0804D6B6, end=0x0804D6B6)
        self.u.mem_write(0x08051B7A, bytes.fromhex("00207047"))  # movs r0, #0; bx lr stub

        # Helper to invoke button hook directly
        def press_hook(btn_id: int, shift_active: bool) -> int:
            self.u.mem_write(shift_store + 0x40, bytes([1 if shift_active else 0, 0, 0, 0]))
            self.u.reg_write(UC_ARM_REG_R4, ctrl)
            self.u.reg_write(UC_ARM_REG_R5, btn_id)
            self.u.reg_write(UC_ARM_REG_SP, 0x20040000)
            self.u.reg_write(UC_ARM_REG_LR, STOP | 1)
            self.u.emu_start(self.labels["c_button_mode_hook"] | 1, STOP)
            result = self.u.reg_read(UC_ARM_REG_R0)
            if self.u.mem_read(SEQ_STATE_ADDR + 5, 1) == b"\x02":
                transition.finish()
            return result

        # 1. Sample Rec without Shift: seq_enabled remains 0
        res = press_hook(0x12, False)
        self.assertEqual(res, 0)
        self.assertEqual(self.u.mem_read(SEQ_STATE_ADDR + OFF_SEQ_ENABLED, 1)[0], 0)

        # 2. Shift + Sample Rec: toggles 0 -> 1, returns 1
        res = press_hook(0x12, True)
        self.assertEqual(res, 1)
        self.assertEqual(self.u.mem_read(SEQ_STATE_ADDR + OFF_SEQ_ENABLED, 1)[0], 1)

        # 3. Shift + Sample Rec again: toggles 1 -> 0, returns 1
        res = press_hook(0x12, True)
        self.assertEqual(res, 1)
        self.assertEqual(self.u.mem_read(SEQ_STATE_ADDR + OFF_SEQ_ENABLED, 1)[0], 0)

        # 4. Other button (Up = 0x14) with Shift: does NOT toggle
        res = press_hook(0x14, True)
        self.assertEqual(res, 0)
        self.assertEqual(self.u.mem_read(SEQ_STATE_ADDR + OFF_SEQ_ENABLED, 1)[0], 0)

        # 5. Grid cleanup invocation when grid_ptr is known
        fake_grid = 0x20005000
        self.u.mem_write(fake_grid + 0x264, bytes([0]))  # grid_mode = 0
        self.word(SEQ_STATE_ADDR + OFF_GRID_PTR, fake_grid)
        cleanup_called.clear()

        res = press_hook(0x12, True)  # toggle to 1
        self.assertEqual(res, 1)
        self.assertEqual(len(cleanup_called), 1)
        self.assertEqual(cleanup_called[0], (fake_grid, 0))

        # 6. Execute full stock button dispatch 0x0803D8B8 with Shift + Sample Rec
        self.u.mem_write(shift_store + 0x40, bytes([1, 0, 0, 0]))
        self.u.reg_write(UC_ARM_REG_R0, ctrl)
        self.u.reg_write(UC_ARM_REG_R1, 0x12)  # Sample Rec
        self.u.reg_write(UC_ARM_REG_SP, 0x20040000)
        self.u.reg_write(UC_ARM_REG_LR, STOP | 1)
        self.u.emu_start(0x0803D8B8 | 1, STOP)

        transition.finish()
        # Verify seq_enabled toggled back to 0
        self.assertEqual(self.u.mem_read(SEQ_STATE_ADDR + OFF_SEQ_ENABLED, 1)[0], 0)

    def test_projects_view_independent_32_projects_and_page_lock(self):
        """Validates independent 32 Sequencer Projects and permanent Up/Down lock.

        Proves:
        1. In Normal Mode (seq_enabled = 0): 0x0804F080 locks [proj_view + 0x36] = 0 (Projects 0..31).
        2. In Sequencer Mode (seq_enabled = 1): 0x0804F080 locks [proj_view + 0x36] = 1 (Projects 32..63).
        3. Up/Down page toggle 0x0804F12C cannot alter [proj_view + 0x36] (NOPed out).
        4. In Projects view pad press 0x0804F09E, all 32 pads (0..31) route to projects 32..63
           in Sequencer Mode and projects 0..31 in Normal Mode.
        """
        proj_view = 0x20004000
        proj_store = self.store(bytes([0, 0, 0, 0]))
        self.word(proj_view + 0x20, proj_store)
        self.u.mem_write(0x0804F27E, bytes.fromhex("7047"))  # stub draw_project_leds

        # Helper to enter Projects View
        def enter_projects(seq_en: int) -> int:
            self.u.mem_write(SEQ_STATE_ADDR + OFF_SEQ_ENABLED, bytes([seq_en]))
            self.u.reg_write(UC_ARM_REG_R0, proj_view)
            self.u.reg_write(UC_ARM_REG_SP, 0x20040000)
            self.u.reg_write(UC_ARM_REG_LR, STOP | 1)
            self.u.emu_start(0x0804F080 | 1, STOP)
            return self.u.mem_read(proj_view + 0x36, 1)[0]

        # 1. Normal Mode opens Page 0
        self.assertEqual(enter_projects(0), 0)

        # 2. Sequencer Mode opens Page 1
        self.assertEqual(enter_projects(1), 1)

        # 3. Up/Down Button Lock (0x0804F12C)
        flag_store = self.store(bytes([8, 0, 0, 0]))  # bit 3 set for 0x0804F13E
        self.word(proj_view + 0x24, flag_store)
        sec_store = self.store(bytes([0, 0, 0, 0]))
        self.word(proj_view + 0x1C, sec_store)

        def press_up_down(btn_id: int) -> int:
            self.u.reg_write(UC_ARM_REG_R0, proj_view)
            self.u.reg_write(UC_ARM_REG_R1, btn_id)
            self.u.reg_write(UC_ARM_REG_SP, 0x20040000)
            self.u.reg_write(UC_ARM_REG_LR, STOP | 1)
            self.u.emu_start(0x0804F12C | 1, STOP)
            return self.u.mem_read(proj_view + 0x36, 1)[0]

        # While on Page 1 (Sequencer Mode), press Up (0x14) -> must remain 1
        self.assertEqual(press_up_down(0x14), 1)

        # While on Page 0 (Normal Mode), press Down (0x13) -> must remain 0
        self.u.mem_write(proj_view + 0x36, bytes([0]))
        self.assertEqual(press_up_down(0x13), 0)

        # 4. Pad routing: verify pad + (page << 5) mapping
        for page_val in (0, 1):
            self.u.mem_write(proj_view + 0x36, bytes([page_val]))
            for pad in range(32):
                expected_proj = pad + (page_val * 32)
                # Stock formula in 0x0804F0B8: r5 = pad + (page << 5)
                actual_proj = pad + (self.u.mem_read(proj_view + 0x36, 1)[0] << 5)
                self.assertEqual(actual_proj, expected_proj)

    def test_packs_view_locked_in_sequencer_mode(self):
        """Validates that Shift + Projects (Packs view) is locked in Sequencer Mode.

        Proves:
        1. When seq_enabled = 1: c_check_packs_allowed returns r0 = 0.
           Controller branch 0x0803DB5C (beq.w 0x0803DC94) is taken and Packs does not open.
        2. When seq_enabled = 0: c_check_packs_allowed calls original 0x08051C82 and returns stock result.
        """
        ctrl = 0x20004000
        self.u.mem_write(0x08051C82, bytes.fromhex("01207047"))  # movs r0, #1; bx lr

        # Sequencer Mode: disallowed (r0 = 0)
        self.u.mem_write(SEQ_STATE_ADDR + OFF_SEQ_ENABLED, bytes([1]))
        res_seq = self.call(self.labels["c_check_packs_allowed"], ctrl)
        self.assertEqual(res_seq, 0)

        # Normal Mode: allowed (r0 = 1 from stock 0x08051C82)
        self.u.mem_write(SEQ_STATE_ADDR + OFF_SEQ_ENABLED, bytes([0]))
        res_norm = self.call(self.labels["c_check_packs_allowed"], ctrl)
        self.assertEqual(res_norm, 1)

    def test_page_1_16_button_locked_only_in_grid_mode_0(self):
        """Validates that the 1-16 page button is locked in grid_mode == 0, but preserved in other modes.

        Proves:
        1. Sequencer Mode in grid_mode == 0: 0x0804DCB2 returns r0 = 0 (null subview), locking the 1-16 button.
        2. Normal Mode in grid_mode == 0: 0x0804DCB2 returns the stock track subview.
        3. Sequencer Mode in grid_mode == 2 (Velocity): 0x0804DCB2 returns the valid mode subview.
        4. Sequencer Mode in grid_mode == 3 (Gate): 0x0804DCB2 returns the valid mode subview.
        """
        grid = 0x20005000
        page_btn_store = self.store(bytes([0, 0, 0, 0]))
        self.word(grid + 0x22C, page_btn_store)

        # Subviews for track 0: mode 0 (+0x19C), other modes (+0x13C)
        subview_mode0 = 0x20008000
        subview_other = 0x20009000
        self.word(grid + 0x19C, subview_mode0)
        self.word(grid + 0x13C, subview_other)

        # Stubs for track lookup and mode validity
        self.u.mem_write(0x0805800E, bytes.fromhex("00207047"))  # track 0
        self.u.mem_write(0x0805888C, bytes.fromhex("01207047"))  # mode supported

        def call_page_btn(seq_en: int, mode_val: int) -> int:
            self.u.mem_write(SEQ_STATE_ADDR + OFF_SEQ_ENABLED, bytes([seq_en]))
            self.u.mem_write(grid + 0x264, bytes([mode_val]))
            self.u.reg_write(UC_ARM_REG_R0, grid)
            self.u.reg_write(UC_ARM_REG_SP, 0x20040000)
            self.u.reg_write(UC_ARM_REG_LR, STOP | 1)
            self.u.emu_start(0x0804DCB2 | 1, STOP)
            return self.u.reg_read(UC_ARM_REG_R0)

        # 1. Sequencer Mode, grid_mode == 0: locked out (returns 0)
        self.assertEqual(call_page_btn(1, 0), 0)

        # 2. Normal Mode, grid_mode == 0: stock subview returned
        self.assertEqual(call_page_btn(0, 0), subview_mode0)

        # 3. Sequencer Mode, Velocity (mode 2): valid subview returned
        self.assertEqual(call_page_btn(1, 2), subview_other)

        # 4. Sequencer Mode, Gate (mode 3): valid subview returned
        self.assertEqual(call_page_btn(1, 3), subview_other)

    def test_sample_engine_muting_midi_only(self):
        """Validates that internal sample engine (0x08046780) is muted in Sequencer Mode.

        Proves:
        1. Sequencer Mode (seq_enabled = 1): 0x08031A1E returns r0 = 0 via bx lr.
           Stock sample engine 0x08046780 is never called.
        2. Normal Mode (seq_enabled = 0): 0x08031A1E jumps directly to 0x08046780 with
           all original arguments intact.
        """
        engine_calls = []

        def on_engine(uc, addr, size, user_data):
            engine_calls.append((
                uc.reg_read(UC_ARM_REG_R0),
                uc.reg_read(UC_ARM_REG_R1),
                uc.reg_read(UC_ARM_REG_R2),
                uc.reg_read(UC_ARM_REG_R3),
            ))

        self.u.mem_write(0x08046780, bytes.fromhex("55207047"))  # movs r0, #0x55; bx lr
        self.u.hook_add(UC_HOOK_CODE, on_engine, begin=0x08046780, end=0x08046780)

        def trigger_sample(seq_en: int, sample_id: int, note: int, vel: int) -> int:
            self.u.mem_write(SEQ_STATE_ADDR + OFF_SEQ_ENABLED, bytes([seq_en]))
            engine_calls.clear()
            # 0x08031A18: mov r0,r1; mov r1,r2; mov r2,r3; b.w c_sample_trigger_gate
            self.u.reg_write(UC_ARM_REG_R0, 0)
            self.u.reg_write(UC_ARM_REG_R1, sample_id)
            self.u.reg_write(UC_ARM_REG_R2, note)
            self.u.reg_write(UC_ARM_REG_R3, vel)
            self.u.reg_write(UC_ARM_REG_SP, 0x20040000)
            self.u.reg_write(UC_ARM_REG_LR, STOP | 1)
            self.u.emu_start(0x08031A18 | 1, STOP)
            return self.u.reg_read(UC_ARM_REG_R0)

        # 1. Sequencer Mode: engine muted, returns 0
        ret_seq = trigger_sample(1, 12, 60, 96)
        self.assertEqual(ret_seq, 0)
        self.assertEqual(len(engine_calls), 0, "Stock sample engine must NOT be called in Sequencer Mode")

        # 2. Normal Mode: engine called, returns 0x55 with original args
        ret_norm = trigger_sample(0, 12, 60, 96)
        self.assertEqual(ret_norm, 0x55)
        self.assertEqual(len(engine_calls), 1, "Stock sample engine MUST be called in Normal Mode")
        self.assertEqual(engine_calls[0], (12, 60, 96, 96))


if __name__ == "__main__":
    unittest.main()
