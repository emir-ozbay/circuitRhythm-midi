"""Safe heap state block and Thumb-2 code-cave generator for 32-Step Sequencer Mode.

Retains upstream MIT License for the `c_rst` safe bump-allocator reservation pattern
from CIRCUIT-REMIX (tools/rhstate.py, Copyright (c) 2026 Ghillermo).

Memory layout at `SEQ_STATE_ADDR = 0x2004F660` (256 bytes, `HEAP_LIMIT - 256`):
  +0x00 (4B): magic            (0x31514553 = "SEQ1")
  +0x04 (1B): seq_enabled      (0 = Normal Mode, 1 = Sequencer Only Mode)
  +0x05 (1B): last_normal_proj (0..31, default 0)
  +0x06 (1B): last_seq_proj    (32..63, default 32)
  +0x08 (4B): grid_ptr         (runtime captured Grid Container pointer)
"""
from __future__ import annotations

from pathlib import Path
import sys

_SRC_DIR = Path(__file__).resolve().parent
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from thumb_asm import (  # noqa: E402
    Asm,
    b,
    b_cond,
    bx_lr,
    cmp_imm,
    cmp_reg,
    ldr_imm,
    movs_imm,
    movt,
    movw,
    str_imm,
    str_reg,
    strb_imm,
    subs_imm8,
)

# Register both module casings in sys.modules for cross-import compatibility
sys.modules.setdefault("seq_Patch", sys.modules[__name__])
sys.modules.setdefault("seq_patch", sys.modules[__name__])

# Code cave boundaries in Circuit Rhythm 5706 application flash
CODE_CAVE_BASE = 0x0806A570
CODE_CAVE_END = 0x08080000

# Stock bump allocator (0x08025A98) pointers and default stock limit
STOCK_ALLOCATOR_ADDR = 0x08025A98
HEAP_LIMIT_PTR = 0x20002B54
HEAP_CUR_PTR = 0x20002B58
HEAP_LIMIT = 0x2004F760
HEAP_LIMIT_STOCK = HEAP_LIMIT

# Safe 256-byte Sequencer Mode state block at top of heap
SEQ_STATE_SIZE = 256
SIZE = SEQ_STATE_SIZE
SEQ_STATE_ADDR = HEAP_LIMIT - SEQ_STATE_SIZE  # 0x2004F660
ST = SEQ_STATE_ADDR
SEQ_STATE_MAGIC = 0x31514553  # "SEQ1" in little-endian ASCII
MAGIC = SEQ_STATE_MAGIC

# Field offsets within SEQ_STATE_ADDR (0x2004F660)
OFF_MAGIC = 0x00
OFF_SEQ_ENABLED = 0x04
OFF_LAST_NORMAL_PROJ = 0x05
OFF_LAST_SEQ_PROJ = 0x06
OFF_GRID_PTR = 0x08

# Default initial values
DEFAULT_SEQ_ENABLED = 0
DEFAULT_NORMAL_PROJ = 0
DEFAULT_SEQ_PROJ = 32

OFF: dict[str, tuple[int, int]] = {
    "magic": (OFF_MAGIC, 4),
    "seq_enabled": (OFF_SEQ_ENABLED, 1),
    "last_normal_proj": (OFF_LAST_NORMAL_PROJ, 1),
    "last_seq_proj": (OFF_LAST_SEQ_PROJ, 1),
    "grid_ptr": (OFF_GRID_PTR, 4),
}


def check_layout() -> None:
    """Verifies that all state block fields are non-overlapping and fit within 256 bytes."""
    used = sorted(OFF.values())
    for (a, n), (b2, _) in zip(used, used[1:]):
        assert a + n <= b2, f"seq_Patch.OFF overlaps at offset {b2:#x}"
    assert used[-1][0] + used[-1][1] <= SEQ_STATE_SIZE, "seq_Patch.OFF exceeds SEQ_STATE_SIZE"


def emit_seq_state(a: Asm) -> None:
    """Emits the `c_seq_state` Thumb-2 function into the given assembler instance.

    Contract (mirrors `c_rst` in CIRCUIT-REMIX/tools/rhstate.py):
    - Input: none
    - Output: `r0 = 0x2004F660` (`SEQ_STATE_ADDR`) on success, or `r0 = 0` on failure.
    - Clobbers: `r1`, `r2`, `r3` (preserves `r4..r11`, `sp`, `lr`).
    - Behavior:
      1. If `[0x20002B54] == 0x2004F660` and `[0x2004F660] == 0x31514553`:
         returns `r0 = 0x2004F660` immediately without modifying state.
      2. If `[0x20002B54] == 0x2004F760` and `[0x20002B58] <= 0x2004F660`:
         lowers `[0x20002B54]` to `0x2004F660`, zeroes all 256 bytes of
         `[0x2004F660..0x2004F760)`, writes `32` (`last_seq_proj`) to `+0x06`,
         writes `0x31514553` (`magic`) to `+0x00`, and returns `r0 = 0x2004F660`.
      3. Otherwise (unexpected heap limit or heap current > `0x2004F660`):
         writes nothing and returns `r0 = 0`.
    """
    check_layout()
    E = a.emit

    def imm32(rd: int, v: int) -> None:
        E(movw, rd, v & 0xFFFF)
        E(movt, rd, (v >> 16) & 0xFFFF)

    a.label("c_seq_state")
    imm32(0, SEQ_STATE_ADDR)                # r0 = 0x2004F660
    imm32(3, HEAP_LIMIT_PTR)                # r3 = 0x20002B54
    E(ldr_imm, 1, 3, 0)                     # r1 = [0x20002B54] (current heap limit)
    E(cmp_reg, 1, 0)                        # is limit already 0x2004F660?
    E(b_cond, "seq_res", "ne")
    E(ldr_imm, 1, 0, 0)                     # r1 = [0x2004F660] (magic word)
    imm32(2, SEQ_STATE_MAGIC)               # r2 = 0x31514553 ("SEQ1")
    E(cmp_reg, 1, 2)                        # is magic valid?
    E(b_cond, "seq_ok", "eq")
    E(b, "seq_init")

    a.label("seq_res")
    imm32(2, HEAP_LIMIT)                    # r2 = 0x2004F760 (expected stock limit)
    E(cmp_reg, 1, 2)
    E(b_cond, "seq_off", "ne")              # unexpected limit -> stay off (r0 = 0)
    E(ldr_imm, 1, 3, 4)                     # r1 = [0x20002B58] (current heap pointer)
    E(cmp_reg, 1, 0)
    E(b_cond, "seq_off", "hi")              # current > 0x2004F660 -> stay off (r0 = 0)
    E(str_imm, 0, 3, 0)                     # [0x20002B54] = 0x2004F660 (reserve block)

    a.label("seq_init")
    E(movs_imm, 1, 0)                       # r1 = 0
    E(movw, 2, SEQ_STATE_SIZE)              # r2 = 256
    a.label("seq_clr")                      # zeroes +252 down to +0 (all 256 bytes)
    E(subs_imm8, 2, 4)
    E(str_reg, 1, 0, 2)                     # str r1, [r0, r2]
    E(cmp_imm, 2, 0)
    E(b_cond, "seq_clr", "ne")
    E(movs_imm, 1, DEFAULT_SEQ_PROJ)        # r1 = 32 (default last_seq_proj)
    E(strb_imm, 1, 0, OFF_LAST_SEQ_PROJ)    # [r0 + 0x06] = 32
    imm32(2, SEQ_STATE_MAGIC)               # r2 = 0x31514553 ("SEQ1")
    E(str_imm, 2, 0, OFF_MAGIC)             # [r0 + 0x00] = 0x31514553

    a.label("seq_ok")
    E(bx_lr)

    a.label("seq_off")
    E(movs_imm, 0, 0)
    E(bx_lr)


def arm_code(base: int = CODE_CAVE_BASE) -> tuple[bytes, dict[str, int]]:
    """Assembles `c_seq_state` at `base` and returns `(code_bytes, labels)`."""
    a = Asm(base)
    emit_seq_state(a)
    return a.assemble()


def c_seq_state(base: int = CODE_CAVE_BASE) -> bytes:
    """Produces the Thumb-2 machine code bytes for `c_seq_state()` at `base`."""
    code, _ = arm_code(base)
    return code
