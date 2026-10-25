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
_SCRIPTS_DIR = _SRC_DIR.parent / "scripts"
for _p in (_SRC_DIR, _SCRIPTS_DIR):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from patch_firmware import PatchHunk  # noqa: E402

from thumb_asm import (  # noqa: E402
    Asm,
    add_sp_imm,
    adds_imm8,
    adds_reg,
    adr,
    ands_reg,
    b,
    b_cond,
    bics_reg,
    bl,
    bx_lr,
    cbnz,
    cbz,
    cmp_imm,
    cmp_reg,
    ldr,
    ldr_imm,
    ldr_reg,
    ldr_sp,
    ldr_w,
    ldrb_imm,
    ldrb_w,
    ldrh_imm,
    lsls_imm,
    mov_reg,
    movs_imm,
    movt,
    movw,
    nop,
    orrs_reg,
    pop,
    push,
    raw,
    str_imm,
    str_mem,
    str_reg,
    str_sp,
    str_w,
    strb_imm,
    strh_imm,
    sub_sp_imm,
    subs_imm8,
    tst_reg,
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

# Stock 5706 function addresses and Grid offsets for M4 step routing
GRID_MODE_OFFSET = 0x264
STOCK_GRID_PRESS = 0x0804D7A0
STOCK_GRID_RELEASE = 0x0804D7DE
STOCK_RESOLVE_SUBVIEW = 0x0804DC86
STOCK_TRANSFORM_PAD = 0x0804DF3E
STOCK_STEP_PRESS = 0x0805CB04
STOCK_STEP_RELEASE = 0x0805CCF0
STOCK_READ_STORE_WORD = 0x0803FC58
STOCK_CALL_VT_SLOT7 = 0x08052108
STOCK_MEMCPY = 0x08022CF0
STOCK_GRID_MODE_UPDATE = 0x0804DAAC
STOCK_STEP_LED_CALC = 0x0805CF24

# In-place 4-byte Thumb-2 BL hook sites and expected stock bytes
HOOK_GRID_MODE_CLEANUP = 0x0804D6E0
EXPECTED_GRID_MODE_CLEANUP = bytes.fromhex("00f0e4f9")  # bl #0x804daac
HOOK_GRID_PRESS_RESOLVE = 0x0804D7B6
EXPECTED_GRID_PRESS_RESOLVE = bytes.fromhex("00f066fa")    # bl #0x804dc86

HOOK_GRID_PRESS_TRANSFORM = 0x0804D7CC
EXPECTED_GRID_PRESS_TRANSFORM = bytes.fromhex("00f0b7fb")  # bl #0x804df3e

HOOK_GRID_RELEASE_RESOLVE = 0x0804D7FC
EXPECTED_GRID_RELEASE_RESOLVE = bytes.fromhex("00f043fa")  # bl #0x804dc86

HOOK_GRID_RELEASE_TRANSFORM = 0x0804D812
EXPECTED_GRID_RELEASE_TRANSFORM = bytes.fromhex("00f094fb")  # bl #0x804df3e

HOOK_STEP_PRESS_PAGE = 0x0805CB14
EXPECTED_STEP_PRESS_PAGE = bytes.fromhex("e3f7a0f8")       # bl #0x803fc58

HOOK_STEP_RELEASE_PAGE = 0x0805CCFA
EXPECTED_STEP_RELEASE_PAGE = bytes.fromhex("e2f7adff")     # bl #0x803fc58

HOOK_COMP_TOP_LEDS = 0x0804DDA4
EXPECTED_COMP_TOP_LEDS = bytes.fromhex("04f0b0f9")         # bl #0x8052108

HOOK_COMP_BOTTOM_MEMCPY = 0x0804DDBE
EXPECTED_COMP_BOTTOM_MEMCPY = bytes.fromhex("d4f797ff")     # bl #0x8022cf0

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


def emit_resolve_subview(a: Asm) -> None:
    """Emits `c_resolve_subview(r0=grid, r1=pad)` into `a`.

    Behavior:
    - Calls `c_seq_state()` while preserving `r0-r3`.
    - If `state != 0`, captures `grid` into `[state + 0x08]` (`grid_ptr`).
    - If `seq_enabled == 1` AND `ldrb [grid, #0x264] == 0` (`grid_mode == 0`):
      calls `0x0804DC86(grid, 0)` so all 32 pads `0..31` resolve to the top subview (`Step View`).
    - Otherwise (`seq_enabled == 0` or `grid_mode != 0`):
      calls original `0x0804DC86(grid, pad)`.
    """
    E = a.emit

    a.label("c_resolve_subview")
    E(push, [0, 1, 2, 3, 4], lr=True)           # save r0=grid, r1=pad, r2, r3, r4, lr
    E(bl, "c_seq_state")                        # r0 = state (or 0)
    E(cbz, "resolve_orig", 0)                   # if state == 0 -> resolve_orig
    E(ldr_sp, 1, 0)                             # r1 = saved r0 (grid)
    E(str_imm, 1, 0, OFF_GRID_PTR)              # [state + 0x08] = grid
    E(ldrb_imm, 2, 0, OFF_SEQ_ENABLED)          # r2 = [state + 0x04] (seq_enabled)
    E(cmp_imm, 2, 1)                            # is seq_enabled == 1?
    E(b_cond, "resolve_orig", "ne")             # if != 1 -> resolve_orig
    E(ldrb_w, 2, 1, GRID_MODE_OFFSET)           # r2 = [grid + 0x264] (grid_mode)
    E(cbnz, "resolve_orig", 2)                  # if grid_mode != 0 -> resolve_orig
    E(movs_imm, 2, 0)                           # r2 = 0
    E(str_sp, 2, 4)                             # overwrite saved r1 (pad) with 0

    a.label("resolve_orig")
    E(pop, [0, 1, 2, 3])                        # restore r0=grid, r1=(0 or pad), r2, r3
    E(bl, STOCK_RESOLVE_SUBVIEW)                # call 0x0804DC86(grid, r1)
    E(pop, [4], pc=True)                        # return subview in r0


def emit_transform_pad(a: Asm) -> None:
    """Emits `c_transform_pad(r0=grid, r1=pad, r2=track, r3=mode)` into `a`.

    Behavior:
    - If `seq_enabled == 1` AND `r3 == 0` (`mode == 0`):
      returns `r0 = pad & 0x1F` directly (`0..31`, without subtracting 16 or adding page offset).
    - Otherwise (`seq_enabled == 0` or `mode != 0`):
      calls original `0x0804DF3E(grid, pad, track, mode)`.
    """
    E = a.emit

    a.label("c_transform_pad")
    E(push, [0, 1, 2, 3, 4], lr=True)           # save r0=grid, r1=pad, r2=track, r3=mode, r4, lr
    E(bl, "c_seq_state")                        # r0 = state (or 0)
    E(cbz, "transform_orig", 0)                 # if state == 0 -> transform_orig
    E(ldrb_imm, 1, 0, OFF_SEQ_ENABLED)          # r1 = [state + 0x04] (seq_enabled)
    E(cmp_imm, 1, 1)                            # is seq_enabled == 1?
    E(b_cond, "transform_orig", "ne")           # if != 1 -> transform_orig
    E(ldr_sp, 3, 12)                            # r3 = saved mode ([sp + 12])
    E(cbnz, "transform_orig", 3)                # if mode != 0 -> transform_orig
    E(pop, [0, 1, 2, 3])                        # restore r0..r3 (r1 = pad)
    E(movs_imm, 0, 0x1F)                        # r0 = 0x1F
    E(ands_reg, 0, 1)                           # r0 = pad & 0x1F
    E(pop, [4], pc=True)                        # return local_pad (0..31) in r0

    a.label("transform_orig")
    E(pop, [0, 1, 2, 3])                        # restore r0=grid, r1=pad, r2=track, r3=mode
    E(bl, STOCK_TRANSFORM_PAD)                  # call 0x0804DF3E(grid, pad, track, mode)
    E(pop, [4], lr=True)                        # restore r4, lr
    E(bx_lr)                                    # return


def emit_step_page_read(a: Asm) -> None:
    """Emits `c_step_page_read(r0=page_store, r1=0)` into `a`.

    Behavior:
    - If `seq_enabled == 1`, `[state + 0x08]` (`grid_ptr`) is non-zero, and
      `ldrb [grid_ptr, #0x264] == 0` (`grid_mode == 0`):
      returns `r0 = &c_zero_word` (address of a constant `0x00000000` word in the code cave),
      so Step Press (`0x0805CB04`) and Step Release (`0x0805CCF0`) read page `0` and never add `+16`.
    - Otherwise (`seq_enabled == 0` or `grid_ptr == 0` or `grid_mode != 0`):
      calls original `0x0803FC58(page_store, 0)`, preserving 100% stock `1-16` page toggle in
      Velocity, Gate, Note, Pattern Settings, Microstep, and Probability modes.
    """
    E = a.emit

    a.label("c_step_page_read")
    E(push, [0, 1, 2, 3, 4], lr=True)           # save r0=page_store, r1=0, r2, r3, r4, lr
    E(bl, "c_seq_state")                        # r0 = state (or 0)
    E(cbz, "page_read_orig", 0)                 # if state == 0 -> page_read_orig
    E(ldrb_imm, 1, 0, OFF_SEQ_ENABLED)          # r1 = [state + 0x04] (seq_enabled)
    E(cmp_imm, 1, 1)                            # is seq_enabled == 1?
    E(b_cond, "page_read_orig", "ne")           # if != 1 -> page_read_orig
    E(ldr_imm, 1, 0, OFF_GRID_PTR)              # r1 = [state + 0x08] (grid_ptr)
    E(cbz, "page_read_orig", 1)                 # if grid_ptr == 0 -> page_read_orig
    E(ldrb_w, 1, 1, GRID_MODE_OFFSET)           # r1 = [grid_ptr + 0x264] (grid_mode)
    E(cbnz, "page_read_orig", 1)                # if grid_mode != 0 -> page_read_orig
    E(pop, [0, 1, 2, 3])                        # restore r1..r3
    E(adr, "c_zero_word", 0)                    # r0 = &c_zero_word (0x00000000 in code cave)
    E(pop, [4], pc=True)                        # return &c_zero_word in r0

    a.label("c_zero_word")
    E(raw, b"\x00\x00\x00\x00")                 # constant 0x00000000 word

    a.label("page_read_orig")
    E(pop, [0, 1, 2, 3])                        # restore r0=page_store, r1=0, r2, r3
    E(bl, STOCK_READ_STORE_WORD)                # call 0x0803FC58(page_store, 0)
    E(pop, [4], lr=True)                        # restore r4, lr
    E(bx_lr)                                    # return


def emit_comp_top_leds(a: Asm) -> None:
    """Emits `c_comp_top_leds(r0=sb)` into `a`.

    Called at `0x0804DDA4` in Stock Compositor (`0x0804DD1C`).
    In stock compositor at this point:
      r0 = sb (top_subview, i.e., Step View)
      r6 = grid
      sb = top_subview
      r8 = bottom_leds
      r4, r5, r7 = other view/page pointers

    Behavior:
    - Calls `c_seq_state()`.
    - If `seq_enabled == 1` AND `ldrb [r6, #0x264] == 0` (`grid_mode == 0`):
      Returns `r0 = ldr r0, [sb, #4]; ldr r0, [r0]` (the start of Step View's 64-byte LED buffer).
      Top 16 pads always display steps 0..15 even if page_store was toggled to page 1.
    - Otherwise (`seq_enabled == 0` or `grid_mode != 0`):
      Restores `r0 = sb` and calls original `0x08052108(sb)`.
    """
    E = a.emit

    a.label("c_comp_top_leds")
    E(push, [4], lr=True)                       # push {r4, lr} (8 bytes, SP aligned)
    E(bl, "c_seq_state")                        # r0 = state (or 0); preserves r4..r11
    E(cbz, "comp_top_orig", 0)                  # if state == 0 -> comp_top_orig
    E(ldrb_imm, 1, 0, OFF_SEQ_ENABLED)          # r1 = [state + 0x04] (seq_enabled)
    E(cmp_imm, 1, 1)                            # is seq_enabled == 1?
    E(b_cond, "comp_top_orig", "ne")            # if != 1 -> comp_top_orig
    E(ldrb_w, 1, 6, GRID_MODE_OFFSET)           # r1 = [grid + 0x264] (grid_mode, r6=grid)
    E(cbnz, "comp_top_orig", 1)                 # if grid_mode != 0 -> comp_top_orig

    # seq_enabled == 1 and grid_mode == 0:
    # Read Step View LED buffer start: ldr r0, [sb, #4]; ldr r0, [r0]
    E(ldr, 0, 9, 4)                             # r0 = [sb + 4] (step_led_cell)
    E(ldr_imm, 0, 0, 0)                         # r0 = [r0] (step_led_buf, steps 0..15)
    E(pop, [4], pc=True)                        # return step_led_buf in r0

    a.label("comp_top_orig")
    E(mov_reg, 0, 9)                            # r0 = sb
    E(bl, STOCK_CALL_VT_SLOT7)                  # call 0x08052108(sb)
    E(pop, [4], pc=True)                        # return


def emit_comp_bottom_memcpy(a: Asm) -> None:
    """Emits `c_comp_bottom_memcpy(r0=grid_out+0x20, r1=r8, r2=0x20)` into `a`.

    Called at `0x0804DDBE` in Stock Compositor (`0x0804DD1C`).
    In stock compositor at this point:
      r0 = grid_out + 0x20 (dest: bottom 16 pads)
      r1 = r8 (src: bottom subview LED buffer)
      r2 = 0x20 (length: 32 bytes)
      r6 = grid
      sb = top_subview (Step View)

    Behavior:
    - Calls `c_seq_state()`.
    - If `seq_enabled == 1` AND `ldrb [r6, #0x264] == 0` (`grid_mode == 0`):
      replaces `r1` with Step View second 16-step buffer (`ldr r1, [sb, #4]; ldr r1, [r1]; adds r1, #0x20`)
      and calls `0x08022CF0(r0, r1, 0x20)` (`memcpy`).
    - Otherwise (`seq_enabled == 0` or `grid_mode != 0`):
      calls original `0x08022CF0(r0, r1, 0x20)` without touching `r1`.
    """
    E = a.emit

    a.label("c_comp_bottom_memcpy")
    E(push, [0, 1, 2, 3, 4], lr=True)           # save r0, r1, r2, r3, r4, lr (24B, 8B aligned)
    E(bl, "c_seq_state")                        # r0 = state (or 0); preserves r4..r11
    E(cbz, "comp_bottom_orig", 0)               # if state == 0 -> comp_bottom_orig
    E(ldrb_imm, 1, 0, OFF_SEQ_ENABLED)          # r1 = [state + 0x04] (seq_enabled)
    E(cmp_imm, 1, 1)                            # is seq_enabled == 1?
    E(b_cond, "comp_bottom_orig", "ne")         # if != 1 -> comp_bottom_orig
    E(ldrb_w, 1, 6, GRID_MODE_OFFSET)           # r1 = [grid + 0x264] (grid_mode, r6=grid)
    E(cbnz, "comp_bottom_orig", 1)              # if grid_mode != 0 -> comp_bottom_orig

    # seq_enabled == 1 and grid_mode == 0:
    # Source is Step View second 16 steps: ldr r1, [sb, #4]; ldr r1, [r1]; adds r1, #0x20
    E(ldr, 1, 9, 4)                             # r1 = [sb + 4] (step_led_cell)
    E(ldr_imm, 1, 1, 0)                         # r1 = [r1] (step_led_buf)
    E(adds_imm8, 1, 0x20)                       # r1 += 0x20 (steps 16..31)
    E(str_sp, 1, 4)                             # update saved r1 in stack [sp + 4]

    a.label("comp_bottom_orig")
    E(pop, [0, 1, 2, 3])                        # restore r0, r1, r2, r3 (sp points to [r4, lr])
    E(bl, STOCK_MEMCPY)                         # call 0x08022CF0(r0, r1, r2)
    E(pop, [4], lr=True)                        # restore r4, lr
    E(bx_lr)                                    # return


def emit_grid_mode_cleanup(a: Asm) -> None:
    """Emits `c_grid_mode_cleanup` into `a`.

    Hooked at `0x0804D6E0` in Grid Container mode/track update `0x0804D6B6`.
    Replaces `bl #0x804daac`.

    Calling context in `0x0804D6B6`:
      r0 = r5 (grid)
      r1 = r0 (selected track)
      r2 = [r6, #4] (old grid_mode)
      r3 = r4 (track info)
      [sp] = new mode / track (5th arg to 0x0804DAAC)
      r4 = 8
      r5 = grid
      r6 = grid + 0x260
      r7 = new mode / track
      r8 = grid + 0x238
      lr = 0x0804D6E5

    Behavior:
    1. Loads 5th arg from [sp] into r12.
    2. Pushes {r4, r5, r6, r7, r8, lr} (24 bytes, 8-byte aligned).
    3. Allocates 8 bytes on stack (sub sp, #8) and stores r12 at [sp] (arg 5).
    4. Calls original 0x0804DAAC(r0, r1, r2, r3, [sp]).
    5. Cleans up stack arg (add sp, #8).
    6. If grid (r5) == 0, jumps to cleanup_done.
    7. Clears [grid + 0x228] = 0 (Grid physical held pad bitmask).
    8. Loops t in 0..7 (r4 = t):
       view = [grid + 0x74 + 4*t]
       If view != 0 and ([view + 0xB8] != 0 or [view + 0xC0] != 0):
         [view + 0xB8] = 0 (pending toggle mask)
         [view + 0xC0] = 0 (held pad mask)
         Loops s in 0..31 (r7 = s):
           status_addr = view + 0x74 + 2*s
           status = [status_addr] (16-bit halfword)
           If bit 3 (held = 0x0008) is set:
             status &= ~0x0008 (bic)
             [status_addr] = status
             Calls 0x0805CF24(view, s) to restore normal step LED palette color.
    9. Restores {r4, r5, r6, r7, r8, pc} cleanly so caller's registers remain intact.
    """
    E = a.emit

    a.label("c_grid_mode_cleanup")
    E(ldr_w, 12, 13, 0)                         # r12 = [sp] (5th arg for 0x0804DAAC)
    E(push, [4, 5, 6, 7, 8], lr=True)           # push.w {r4..r8, lr} (24B, 8B aligned)
    E(sub_sp_imm, 8)                            # reserve 8 bytes on stack (8B aligned)
    E(str_w, 12, 13, 0)                         # [sp] = 5th arg
    E(bl, STOCK_GRID_MODE_UPDATE)               # call 0x0804DAAC(r0, r1, r2, r3, [sp])
    E(add_sp_imm, 8)                            # pop 8B stack arg
    E(cbz, "cleanup_done", 5)                   # if grid (r5) == 0 -> done

    # Clear [grid + 0x228] = 0
    E(movs_imm, 0, 0)
    E(str_w, 0, 5, 0x228)                       # [grid + 0x228] = 0

    # Loop 8 tracks (t = 0..7, r4 = t)
    E(movs_imm, 4, 0)                           # r4 = t = 0

    a.label("cleanup_track_loop")
    E(lsls_imm, 0, 4, 2)                        # r0 = t * 4
    E(adds_imm8, 0, 0x74)                       # r0 = 0x74 + t * 4
    E(ldr_reg, 6, 5, 0)                         # r6 = view = [grid + r0]
    E(cmp_imm, 6, 0)
    E(b_cond, "cleanup_next_track", "eq")       # if view == 0 -> next track

    # Check if [view + 0xB8] != 0 or [view + 0xC0] != 0
    E(ldr, 0, 6, 0xB8)                          # r0 = [view + 0xB8]
    E(ldr, 1, 6, 0xC0)                          # r1 = [view + 0xC0]
    E(orrs_reg, 0, 1)                           # r0 = [view + 0xB8] | [view + 0xC0]
    E(cmp_imm, 0, 0)
    E(b_cond, "cleanup_next_track", "eq")       # if both are 0 -> next track

    # Clear pending toggle mask and held pad mask
    E(movs_imm, 0, 0)
    E(str_mem, 0, 6, 0xB8)                      # [view + 0xB8] = 0
    E(str_mem, 0, 6, 0xC0)                      # [view + 0xC0] = 0

    # Loop 32 steps (s = 0..31, r7 = s)
    E(movs_imm, 7, 0)                           # r7 = s = 0

    a.label("cleanup_step_loop")
    E(lsls_imm, 0, 7, 1)                        # r0 = s * 2
    E(adds_imm8, 0, 0x74)                       # r0 = 0x74 + s * 2
    E(adds_reg, 0, 0, 6)                        # r0 = view + 0x74 + 2*s
    E(ldrh_imm, 1, 0, 0)                        # r1 = [r0] (status halfword)
    E(movs_imm, 2, 8)                           # r2 = 8 (bit 3)
    E(tst_reg, 1, 2)                            # test bit 3
    E(b_cond, "cleanup_skip_step", "eq")        # if bit 3 is not set -> skip

    # Bit 3 is set: clear it and recalculate LED
    E(bics_reg, 1, 2)                           # r1 = r1 & ~8
    E(strh_imm, 1, 0, 0)                        # [r0] = r1 (status halfword updated)
    E(mov_reg, 0, 6)                            # r0 = view
    E(mov_reg, 1, 7)                            # r1 = s
    E(bl, STOCK_STEP_LED_CALC)                  # 0x0805CF24(view, s)

    a.label("cleanup_skip_step")
    E(adds_imm8, 7, 1)                          # s++
    E(cmp_imm, 7, 32)
    E(b_cond, "cleanup_step_loop", "ne")        # loop if s < 32

    a.label("cleanup_next_track")
    E(adds_imm8, 4, 1)                          # t++
    E(cmp_imm, 4, 8)
    E(b_cond, "cleanup_track_loop", "ne")       # loop if t < 8

    a.label("cleanup_done")
    E(pop, [4, 5, 6, 7, 8], lr=True)            # restore r4..r8, lr
    E(bx_lr)                                    # return


def emit_step_routing_cave(a: Asm) -> None:
    """Emits `c_seq_state`, `c_resolve_subview`, `c_transform_pad`, `c_step_page_read`, `c_comp_top_leds`, `c_comp_bottom_memcpy`, and `c_grid_mode_cleanup`."""
    emit_seq_state(a)
    emit_resolve_subview(a)
    emit_transform_pad(a)
    emit_step_page_read(a)
    emit_comp_top_leds(a)
    emit_comp_bottom_memcpy(a)
    emit_grid_mode_cleanup(a)


def arm_code(base: int = CODE_CAVE_BASE) -> tuple[bytes, dict[str, int]]:
    """Assembles the Sequencer Mode code cave at `base` and returns `(code_bytes, labels)`."""
    a = Asm(base)
    emit_step_routing_cave(a)
    return a.assemble()


def c_seq_state(base: int = CODE_CAVE_BASE) -> bytes:
    """Produces the Thumb-2 machine code bytes for the code cave starting with `c_seq_state()` at `base`."""
    code, _ = arm_code(base)
    return code


def build_step_routing_patches(base: int = CODE_CAVE_BASE) -> list[PatchHunk]:
    """Builds the code-cave PatchHunk and the 9 in-place Thumb-2 `BL` hook PatchHunks."""
    cave_bytes, labels = arm_code(base)

    resolve_addr = labels["c_resolve_subview"]
    transform_addr = labels["c_transform_pad"]
    page_read_addr = labels["c_step_page_read"]
    comp_top_addr = labels["c_comp_top_leds"]
    comp_bottom_addr = labels["c_comp_bottom_memcpy"]
    cleanup_addr = labels["c_grid_mode_cleanup"]

    return [
        PatchHunk(
            address=HOOK_GRID_MODE_CLEANUP,
            expected=EXPECTED_GRID_MODE_CLEANUP,
            replacement=bl(HOOK_GRID_MODE_CLEANUP, cleanup_addr),
            name="grid_mode_cleanup_hook",
        ),
        PatchHunk(
            address=HOOK_GRID_PRESS_RESOLVE,
            expected=EXPECTED_GRID_PRESS_RESOLVE,
            replacement=bl(HOOK_GRID_PRESS_RESOLVE, resolve_addr),
            name="grid_press_resolve_subview_hook",
        ),
        PatchHunk(
            address=HOOK_GRID_PRESS_TRANSFORM,
            expected=EXPECTED_GRID_PRESS_TRANSFORM,
            replacement=bl(HOOK_GRID_PRESS_TRANSFORM, transform_addr),
            name="grid_press_transform_pad_hook",
        ),
        PatchHunk(
            address=HOOK_GRID_RELEASE_RESOLVE,
            expected=EXPECTED_GRID_RELEASE_RESOLVE,
            replacement=bl(HOOK_GRID_RELEASE_RESOLVE, resolve_addr),
            name="grid_release_resolve_subview_hook",
        ),
        PatchHunk(
            address=HOOK_GRID_RELEASE_TRANSFORM,
            expected=EXPECTED_GRID_RELEASE_TRANSFORM,
            replacement=bl(HOOK_GRID_RELEASE_TRANSFORM, transform_addr),
            name="grid_release_transform_pad_hook",
        ),
        PatchHunk(
            address=HOOK_STEP_PRESS_PAGE,
            expected=EXPECTED_STEP_PRESS_PAGE,
            replacement=bl(HOOK_STEP_PRESS_PAGE, page_read_addr),
            name="step_press_page_read_hook",
        ),
        PatchHunk(
            address=HOOK_STEP_RELEASE_PAGE,
            expected=EXPECTED_STEP_RELEASE_PAGE,
            replacement=bl(HOOK_STEP_RELEASE_PAGE, page_read_addr),
            name="step_release_page_read_hook",
        ),
        PatchHunk(
            address=HOOK_COMP_TOP_LEDS,
            expected=EXPECTED_COMP_TOP_LEDS,
            replacement=bl(HOOK_COMP_TOP_LEDS, comp_top_addr),
            name="comp_top_leds_hook",
        ),
        PatchHunk(
            address=HOOK_COMP_BOTTOM_MEMCPY,
            expected=EXPECTED_COMP_BOTTOM_MEMCPY,
            replacement=bl(HOOK_COMP_BOTTOM_MEMCPY, comp_bottom_addr),
            name="comp_bottom_memcpy_hook",
        ),
        PatchHunk(
            address=base,
            expected=b"\xFF" * len(cave_bytes),
            replacement=cave_bytes,
            name="seq_step_routing_code_cave",
        ),
    ]


build_seq_patches = build_step_routing_patches

