"""Unicorn emulation and Capstone disassembly tests for `src/thumb_asm.py` and `src/seq_Patch.py`.

Verifies:
1. Capstone disassembly of `thumb_asm` helpers (`bl`, `b_w`, `push`, `pop`, `ldr`, `str`, `ldrb`, `strb`, `movw`, `movt`) and `c_seq_state()`.
2. First-call reservation in normal heap state (`limit == 0x2004F760`, `current <= 0x2004F660`):
   - `[0x20002B54]` lowers to `0x2004F660`.
   - All 256 bytes at `0x2004F660..0x2004F75F` are zeroed from pre-filled garbage.
   - `+0x00` (`magic`) is set to `0x31514553` ("SEQ1").
   - `+0x04` (`seq_enabled`) is `0`, `+0x05` (`last_normal_proj`) is `0`, `+0x06` (`last_seq_proj`) is `32`, `+0x08` (`grid_ptr`) is `0`.
   - Returns `r0 = 0x2004F660`.
3. Second-call state preservation when `[0x20002B54] == 0x2004F660` and `magic == 0x31514553`:
   - Existing values (`seq_enabled`, `last_normal_proj`, `last_seq_proj`, `grid_ptr`, etc.) remain completely untouched.
   - Returns `r0 = 0x2004F660`.
4. Exact boundary condition (`current == 0x2004F660` succeeds; `current == 0x2004F661` aborts).
5. Heap full (`current > 0x2004F660`) and unexpected heap limit (`limit != 0x2004F760`):
   - Returns `r0 = 0` and does not modify `[0x20002B54]`, `[0x20002B58]`, or `[0x2004F660..0x2004F760)`.
6. Integration with `scripts/patch_firmware.py` at `CODE_CAVE_BASE = 0x0806A570` on stock 5706 image.
"""
from __future__ import annotations

from pathlib import Path
import struct
import sys
import unittest

from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB, CS_MODE_MCLASS
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_THUMB, UC_MODE_MCLASS
from unicorn.arm_const import (
    UC_ARM_REG_R0,
    UC_ARM_REG_R1,
    UC_ARM_REG_R2,
    UC_ARM_REG_R3,
    UC_ARM_REG_R4,
    UC_ARM_REG_R5,
    UC_ARM_REG_R6,
    UC_ARM_REG_R7,
    UC_ARM_REG_SP,
    UC_ARM_REG_LR,
)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import thumb_asm as T  # noqa: E402
from seq_Patch import (  # noqa: E402
    CODE_CAVE_BASE,
    HEAP_LIMIT_PTR,
    HEAP_CUR_PTR,
    HEAP_LIMIT,
    SEQ_STATE_ADDR,
    SEQ_STATE_SIZE,
    SEQ_STATE_MAGIC,
    OFF_MAGIC,
    OFF_SEQ_ENABLED,
    OFF_LAST_NORMAL_PROJ,
    OFF_LAST_SEQ_PROJ,
    OFF_GRID_PTR,
    DEFAULT_SEQ_PROJ,
    arm_code,
    c_seq_state,
    check_layout,
)
from patch_firmware import (  # noqa: E402
    APP_BASE,
    PatchHunk,
    apply_patches,
    unpack_syx,
)


class TestThumbAsmEncodings(unittest.TestCase):
    """Cross-checks `src/thumb_asm.py` instruction encodings against Capstone."""

    def setUp(self):
        self.md = Cs(CS_ARCH_ARM, CS_MODE_THUMB | CS_MODE_MCLASS)

    def test_required_helpers_disassemble_cleanly(self):
        base = CODE_CAVE_BASE
        a = T.Asm(base)
        E = a.emit

        a.label("entry")
        E(T.push, [4, 5], lr=True)
        E(T.movw, 0, 0xF660)
        E(T.movt, 0, 0x2004)
        E(T.ldr, 1, 0, 0)
        E(T.ldr, 2, 0, 0x264)      # wide LDR.W
        E(T.str, 1, 0, 8)
        E(T.str, 2, 0, 0x264)      # wide STR.W
        E(T.ldrb, 3, 0, 4)
        E(T.ldrb, 3, 0, 0x36)      # wide LDRB.W
        E(T.strb, 3, 0, 6)
        E(T.strb, 3, 0, 0x36)      # wide STRB.W
        E(T.bl, "subroutine")
        E(T.b_w, "exit_label")

        a.label("subroutine")
        E(T.bx_lr)

        a.label("exit_label")
        E(T.pop, [4, 5], pc=True)

        code, labels = a.assemble()
        insns = list(self.md.disasm(code, base))

        # Ensure every single byte was decoded as valid Thumb/Thumb-2 instructions
        decoded_len = sum(i.size for i in insns)
        self.assertEqual(decoded_len, len(code))

        mnemonics = [i.mnemonic for i in insns]
        self.assertEqual(
            mnemonics,
            [
                "push",
                "movw",
                "movt",
                "ldr",
                "ldr.w",
                "str",
                "str.w",
                "ldrb",
                "ldrb.w",
                "strb",
                "strb.w",
                "bl",
                "b.w",
                "bx",
                "pop",
            ],
        )
        self.assertEqual(labels["entry"], base)
        self.assertIn("subroutine", labels)
        self.assertIn("exit_label", labels)

    def test_c_seq_state_disassembles_cleanly(self):
        code, labels = arm_code(CODE_CAVE_BASE)
        self.assertEqual(labels["c_seq_state"], CODE_CAVE_BASE)
        self.assertEqual(code, c_seq_state(CODE_CAVE_BASE))

        insns = list(self.md.disasm(code, CODE_CAVE_BASE))
        decoded_len = sum(i.size for i in insns)
        self.assertEqual(decoded_len, len(code))
        self.assertEqual(insns[-1].mnemonic, "bx")
        self.assertEqual(insns[-1].op_str, "lr")


class TestSeqStateEmulation(unittest.TestCase):
    """Unicorn ARM Cortex-M emulation tests for `c_seq_state()`."""

    STOP_ADDR = 0x0800F000

    def setUp(self):
        check_layout()
        self.code = c_seq_state(CODE_CAVE_BASE)

    def _make_uc(self, heap_limit: int = HEAP_LIMIT, heap_cur: int = 0x2004EA98) -> Uc:
        u = Uc(UC_ARCH_ARM, UC_MODE_THUMB | UC_MODE_MCLASS)
        u.mem_map(0x08000000, 0x80000)
        u.mem_map(0x20000000, 0x50000)

        # Write c_seq_state machine code at CODE_CAVE_BASE (0x0806A570)
        u.mem_write(CODE_CAVE_BASE, self.code)

        # Populate heap allocator pointers
        u.mem_write(HEAP_LIMIT_PTR, struct.pack("<I", heap_limit))
        u.mem_write(HEAP_CUR_PTR, struct.pack("<I", heap_cur))

        # Pre-fill state block and surrounding canary regions with non-zero bytes
        u.mem_write(SEQ_STATE_ADDR - 16, b"\xCC" * 16)
        u.mem_write(SEQ_STATE_ADDR, b"\xAA" * SEQ_STATE_SIZE)
        u.mem_write(SEQ_STATE_ADDR + SEQ_STATE_SIZE, b"\xDD" * 16)

        return u

    def _call_seq_state(self, u: Uc) -> int:
        u.reg_write(UC_ARM_REG_R0, 0xDEADBEEF)
        u.reg_write(UC_ARM_REG_R1, 0x11111111)
        u.reg_write(UC_ARM_REG_R2, 0x22222222)
        u.reg_write(UC_ARM_REG_R3, 0x33333333)
        u.reg_write(UC_ARM_REG_R4, 0x44444444)
        u.reg_write(UC_ARM_REG_R5, 0x55555555)
        u.reg_write(UC_ARM_REG_R6, 0x66666666)
        u.reg_write(UC_ARM_REG_R7, 0x77777777)
        u.reg_write(UC_ARM_REG_SP, 0x2004FDE0)
        u.reg_write(UC_ARM_REG_LR, self.STOP_ADDR | 1)

        u.emu_start(CODE_CAVE_BASE | 1, self.STOP_ADDR, count=10000)
        return u.reg_read(UC_ARM_REG_R0)

    def test_normal_heap_initializes_and_second_call_preserves_state(self):
        """Verifies first call reserves and initializes block, and second call preserves state."""
        u = self._make_uc(heap_limit=HEAP_LIMIT, heap_cur=0x2004EA98)

        # 1st call: should lower limit, zero 256 bytes, set last_seq_proj=32 and magic="SEQ1"
        r0 = self._call_seq_state(u)
        self.assertEqual(r0, SEQ_STATE_ADDR)

        # Verify heap limit lowered to 0x2004F660 and heap_cur unchanged
        new_limit = struct.unpack("<I", u.mem_read(HEAP_LIMIT_PTR, 4))[0]
        cur_val = struct.unpack("<I", u.mem_read(HEAP_CUR_PTR, 4))[0]
        self.assertEqual(new_limit, SEQ_STATE_ADDR)
        self.assertEqual(cur_val, 0x2004EA98)

        # Verify state block contents
        block = bytes(u.mem_read(SEQ_STATE_ADDR, SEQ_STATE_SIZE))
        magic = struct.unpack_from("<I", block, OFF_MAGIC)[0]
        self.assertEqual(magic, SEQ_STATE_MAGIC)
        self.assertEqual(block[0:4], b"SEQ1")
        self.assertEqual(block[OFF_SEQ_ENABLED], 0)
        self.assertEqual(block[OFF_LAST_NORMAL_PROJ], 0)
        self.assertEqual(block[OFF_LAST_SEQ_PROJ], DEFAULT_SEQ_PROJ)
        self.assertEqual(block[OFF_LAST_SEQ_PROJ], 32)
        self.assertEqual(struct.unpack_from("<I", block, OFF_GRID_PTR)[0], 0)

        # All other bytes in the 256-byte block must be zero
        expected_block = bytearray(SEQ_STATE_SIZE)
        struct.pack_into("<I", expected_block, OFF_MAGIC, SEQ_STATE_MAGIC)
        expected_block[OFF_LAST_SEQ_PROJ] = DEFAULT_SEQ_PROJ
        self.assertEqual(block, bytes(expected_block))

        # Surrounding canaries must be untouched
        self.assertEqual(bytes(u.mem_read(SEQ_STATE_ADDR - 16, 16)), b"\xCC" * 16)
        self.assertEqual(bytes(u.mem_read(SEQ_STATE_ADDR + SEQ_STATE_SIZE, 16)), b"\xDD" * 16)

        # Callee-saved registers r4..r7 and SP must be preserved
        self.assertEqual(u.reg_read(UC_ARM_REG_R4), 0x44444444)
        self.assertEqual(u.reg_read(UC_ARM_REG_R5), 0x55555555)
        self.assertEqual(u.reg_read(UC_ARM_REG_R6), 0x66666666)
        self.assertEqual(u.reg_read(UC_ARM_REG_R7), 0x77777777)
        self.assertEqual(u.reg_read(UC_ARM_REG_SP), 0x2004FDE0)

        # Mutate state fields to simulate runtime changes
        u.mem_write(SEQ_STATE_ADDR + OFF_SEQ_ENABLED, bytes([1]))
        u.mem_write(SEQ_STATE_ADDR + OFF_LAST_NORMAL_PROJ, bytes([12]))
        u.mem_write(SEQ_STATE_ADDR + OFF_LAST_SEQ_PROJ, bytes([47]))
        u.mem_write(SEQ_STATE_ADDR + OFF_GRID_PTR, struct.pack("<I", 0x20048B9C))
        snapshot_before_second_call = bytes(u.mem_read(SEQ_STATE_ADDR, SEQ_STATE_SIZE))

        # 2nd call: must return SEQ_STATE_ADDR and preserve all runtime fields
        r0_second = self._call_seq_state(u)
        self.assertEqual(r0_second, SEQ_STATE_ADDR)
        self.assertEqual(bytes(u.mem_read(SEQ_STATE_ADDR, SEQ_STATE_SIZE)), snapshot_before_second_call)
        self.assertEqual(u.mem_read(SEQ_STATE_ADDR + OFF_SEQ_ENABLED, 1)[0], 1)
        self.assertEqual(u.mem_read(SEQ_STATE_ADDR + OFF_LAST_NORMAL_PROJ, 1)[0], 12)
        self.assertEqual(u.mem_read(SEQ_STATE_ADDR + OFF_LAST_SEQ_PROJ, 1)[0], 47)
        self.assertEqual(
            struct.unpack("<I", u.mem_read(SEQ_STATE_ADDR + OFF_GRID_PTR, 4))[0],
            0x20048B9C,
        )

    def test_exact_boundary_current_equals_seq_state_addr_succeeds(self):
        """Verifies `current == 0x2004F660` (`<= 0x2004F660`) succeeds."""
        u = self._make_uc(heap_limit=HEAP_LIMIT, heap_cur=SEQ_STATE_ADDR)
        r0 = self._call_seq_state(u)
        self.assertEqual(r0, SEQ_STATE_ADDR)
        self.assertEqual(struct.unpack("<I", u.mem_read(HEAP_LIMIT_PTR, 4))[0], SEQ_STATE_ADDR)
        self.assertEqual(struct.unpack("<I", u.mem_read(SEQ_STATE_ADDR, 4))[0], SEQ_STATE_MAGIC)

    def test_heap_full_returns_zero_and_touches_nothing(self):
        """Verifies that when `current > 0x2004F660`, `c_seq_state()` returns 0 without writing."""
        for full_cur in (SEQ_STATE_ADDR + 1, SEQ_STATE_ADDR + 4, 0x2004F700, HEAP_LIMIT):
            with self.subTest(heap_cur=hex(full_cur)):
                u = self._make_uc(heap_limit=HEAP_LIMIT, heap_cur=full_cur)
                r0 = self._call_seq_state(u)
                self.assertEqual(r0, 0)

                # Limit, current, and state memory must remain untouched
                self.assertEqual(struct.unpack("<I", u.mem_read(HEAP_LIMIT_PTR, 4))[0], HEAP_LIMIT)
                self.assertEqual(struct.unpack("<I", u.mem_read(HEAP_CUR_PTR, 4))[0], full_cur)
                self.assertEqual(bytes(u.mem_read(SEQ_STATE_ADDR, SEQ_STATE_SIZE)), b"\xAA" * SEQ_STATE_SIZE)

    def test_unexpected_heap_limit_returns_zero_and_touches_nothing(self):
        """Verifies that if `[0x20002B54]` is neither `0x2004F760` nor `0x2004F660`, returns 0."""
        for bad_limit in (0x00000000, 0x20040000, 0x2004F560, 0x2004F800, 0xFFFFFFFF):
            with self.subTest(heap_limit=hex(bad_limit)):
                u = self._make_uc(heap_limit=bad_limit, heap_cur=0x2004EA98)
                r0 = self._call_seq_state(u)
                self.assertEqual(r0, 0)

                # Limit, current, and state memory must remain untouched
                self.assertEqual(struct.unpack("<I", u.mem_read(HEAP_LIMIT_PTR, 4))[0], bad_limit)
                self.assertEqual(struct.unpack("<I", u.mem_read(HEAP_CUR_PTR, 4))[0], 0x2004EA98)
                self.assertEqual(bytes(u.mem_read(SEQ_STATE_ADDR, SEQ_STATE_SIZE)), b"\xAA" * SEQ_STATE_SIZE)

    def test_already_reserved_limit_with_missing_magic_reinitializes_block(self):
        """Verifies that if limit is already `0x2004F660` but magic is invalid, block is initialized."""
        u = self._make_uc(heap_limit=SEQ_STATE_ADDR, heap_cur=0x2004EA98)
        r0 = self._call_seq_state(u)
        self.assertEqual(r0, SEQ_STATE_ADDR)
        self.assertEqual(struct.unpack("<I", u.mem_read(SEQ_STATE_ADDR, 4))[0], SEQ_STATE_MAGIC)
        self.assertEqual(u.mem_read(SEQ_STATE_ADDR + OFF_LAST_SEQ_PROJ, 1)[0], DEFAULT_SEQ_PROJ)

    def test_code_cave_patch_integration_with_stock_allocator(self):
        """Applies `c_seq_state` to stock 5706 image at `0x0806A570` and tests alongside stock allocator `0x08025A98`."""
        stock_path = ROOT / "stock" / "circuitrhythm-firmware-5706.syx"
        stock_image = unpack_syx(stock_path.read_bytes())["image"]

        cave_hunk = PatchHunk(
            address=CODE_CAVE_BASE,
            expected=b"\xFF" * len(self.code),
            replacement=self.code,
            name="c_seq_state_code_cave",
        )
        patched_image, _, _ = apply_patches(stock_image, [cave_hunk])

        u = Uc(UC_ARCH_ARM, UC_MODE_THUMB | UC_MODE_MCLASS)
        u.mem_map(0x08000000, 0x80000)
        u.mem_map(0x20000000, 0x50000)
        u.mem_write(APP_BASE, patched_image)

        # Set heap limit to stock 0x2004F760 and current to 32 bytes below SEQ_STATE_ADDR
        u.mem_write(HEAP_LIMIT_PTR, struct.pack("<I", HEAP_LIMIT))
        u.mem_write(HEAP_CUR_PTR, struct.pack("<I", SEQ_STATE_ADDR - 32))

        # Call c_seq_state() in code cave -> lowers limit to 0x2004F660
        r0 = self._call_seq_state(u)
        self.assertEqual(r0, SEQ_STATE_ADDR)

        # Call stock bump allocator 0x08025A98(32): fits exactly up to 0x2004F660
        u.reg_write(UC_ARM_REG_R0, 32)
        u.reg_write(UC_ARM_REG_SP, 0x2004FDE0)
        u.reg_write(UC_ARM_REG_LR, self.STOP_ADDR | 1)
        u.emu_start(0x08025A98 | 1, self.STOP_ADDR, count=1000)
        alloc_ok = u.reg_read(UC_ARM_REG_R0)
        self.assertEqual(alloc_ok, SEQ_STATE_ADDR - 32)
        self.assertEqual(struct.unpack("<I", u.mem_read(HEAP_CUR_PTR, 4))[0], SEQ_STATE_ADDR)

        # Verify state block at 0x2004F660 is still intact
        self.assertEqual(struct.unpack("<I", u.mem_read(SEQ_STATE_ADDR, 4))[0], SEQ_STATE_MAGIC)
        self.assertEqual(u.mem_read(SEQ_STATE_ADDR + OFF_LAST_SEQ_PROJ, 1)[0], DEFAULT_SEQ_PROJ)


if __name__ == "__main__":
    unittest.main()
