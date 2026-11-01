"""Current UI/sample hooks; shared64-project coverage is in test_shared_project.py.

Historical bank-isolation tests are fully archived under analysis/historical-bank-isolation.
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

    def test_current_hook_integrity_and_removed_project_hooks_are_stock(self):
        md = Cs(CS_ARCH_ARM, CS_MODE_THUMB | CS_MODE_MCLASS)
        for site, label in ((HOOK_PAGE_BTN_MODE0, 'c_page_btn_mode0'),
                            (HOOK_BUTTON_MODE, 'c_button_mode_hook')):
            insns = list(md.disasm(self.patched_image[site-BASE:site-BASE+4], site))
            self.assertEqual(len(insns), 1)
            self.assertEqual(insns[0].mnemonic, 'bl')
            self.assertEqual(insns[0].op_str, f"#{self.labels[label]:#x}")
        for site in (HOOK_PROJ_ENTER_PAGE, HOOK_PROJ_PAGE_LOCK, HOOK_CHECK_PACKS):
            self.assertEqual(self.patched_image[site-BASE:site-BASE+4], self.stock_image[site-BASE:site-BASE+4])
        gate = list(md.disasm(self.patched_image[HOOK_SAMPLE_TRIGGER_GATE-BASE:HOOK_SAMPLE_TRIGGER_GATE-BASE+4], HOOK_SAMPLE_TRIGGER_GATE))
        self.assertEqual(gate[0].mnemonic, 'b.w')
        self.assertEqual(gate[0].op_str, f"#{self.labels['c_sample_trigger_gate']:#x}")


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
