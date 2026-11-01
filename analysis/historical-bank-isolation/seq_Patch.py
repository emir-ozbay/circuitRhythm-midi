"""Safe heap state block and Thumb-2 code-cave generator for 32-Step Sequencer Mode.

Retains upstream MIT License for the `c_rst` safe bump-allocator reservation pattern
from CIRCUIT-REMIX (tools/rhstate.py, Copyright (c) 2026 Ghillermo).

Memory layout at `SEQ_STATE_ADDR = 0x2004F660` (256 bytes, `HEAP_LIMIT - 256`):
  +0x00 (4B): magic            (0x31514553 = "SEQ1")
  +0x04 (1B): seq_enabled      (0 = Normal Mode, 1 = Sequencer Only Mode)
  +0x05 (1B): trans_state      (0 = idle, 1 = load requested, 2 = load in flight)
  +0x06 (1B): trans_target_mode(0 = Normal, 1 = Sequencer)
  +0x07 (1B): trans_target_slot(0..63)
  +0x08 (4B): grid_ptr         (runtime captured Grid Container pointer)
  +0x0C (4B): proj_view_ptr    (runtime captured Projects View pointer)
  +0x10 (4B): proj_ctrl_ptr    (runtime captured Project Controller P pointer)
  +0x14 (4B): ctrl_ptr         (runtime captured Main Controller pointer)
  +0x18 (1B): last_normal_proj (0..31, default 0)
  +0x19 (1B): last_seq_proj    (32..63, default 32)
  +0x1A (1B): project_dirty    (0 = clean, 1 = dirty)
  +0x1B (1B): trans_prev_slot  (0..63)
  +0x1C (4B): save_owner       (one-shot save snapshot owner)
  +0x20 (1B): save_slot
  +0x21 (1B): save_edited
  +0x24 (32B): recorders       (eight captured recorder pointers)
  +0x44 (4B): close_callback  (captured Save callback waiting for Close)
  +0x48 (12B): close_status   (owned copy; lives through deferred Close)
  +0x54 (4B): load_close_callback
  +0x58 (12B): load_close_status
  +0x64 (1B): project_tainted (failed Load may have overwritten live bytes)
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
    b_cond_w,
    b_w,
    bics_reg,
    bl,
    bx_lr,
    cbnz,
    cbz,
    cmp_imm,
    cmp_reg,
    eors_reg,
    ldr,
    ldr_imm,
    ldr_reg,
    ldr_sp,
    ldr_w,
    ldrb_imm,
    ldrb_w,
    ldrh_imm,
    lsls_imm,
    lsrs_imm,
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
    strb_reg,
    strb_w,
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
OFF_TRANS_STATE = 0x05
OFF_TRANS_TARGET_MODE = 0x06
OFF_TRANS_TARGET_SLOT = 0x07
OFF_GRID_PTR = 0x08
OFF_PROJ_VIEW_PTR = 0x0C
OFF_PROJ_CTRL_PTR = 0x10
OFF_CTRL_PTR = 0x14
OFF_LAST_NORMAL_PROJ = 0x18
OFF_LAST_SEQ_PROJ = 0x19
OFF_PROJECT_DIRTY = 0x1A
OFF_TRANS_PREV_SLOT = 0x1B
OFF_SAVE_OWNER = 0x1C
OFF_SAVE_SLOT = 0x20
OFF_SAVE_EDITED = 0x21
OFF_RECORDERS = 0x24  # eight boot-lifetime recorder pointers, captured by track
OFF_CLOSE_CALLBACK = 0x44
OFF_CLOSE_STATUS = 0x48
OFF_LOAD_CLOSE_CALLBACK = 0x54
OFF_LOAD_CLOSE_STATUS = 0x58
OFF_PROJECT_TAINTED = 0x64

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
STOCK_WRITE_STORE_WORD = 0x0803FD26
STOCK_NOTIFY_STORE = 0x0803FBEC
STOCK_CALL_VT_SLOT7 = 0x08052108
STOCK_MEMCPY = 0x08022CF0
STOCK_GRID_MODE_UPDATE = 0x0804DAAC
STOCK_STEP_LED_CALC = 0x0805CF24
STOCK_CHECK_PACKS = 0x08051C82
STOCK_GET_ACTIVE_TRACK = 0x0805800E
STOCK_CTRL_BUTTON_PRE = 0x08051B7A
STOCK_GRID_CONTAINER_UPDATE = 0x0804D6B6
STOCK_SAMPLE_TRIGGER_ENGINE = 0x08046780
STOCK_SAMPLE_DSP_TRIGGER = 0x08040874
STOCK_SAMPLE_PREVIEW_CONT = 0x080407F0
STOCK_SAMPLE_FORCE_OFF = 0x080467D2
STOCK_ACTION_DISPATCH = 0x08047038
STOCK_DRAW_PROJECT_LEDS = 0x0804F27E
STOCK_LOAD_SUCCESS = 0x08037E3C
STOCK_LOAD_ERROR_CLEANUP = 0x08037DD0
STOCK_NEW_PROJ_CALLBACK = 0x08037C84
STOCK_CLEAR_CALLBACK = 0x08038074
STOCK_TIMER_SCHEDULE = 0x08046DDE

# In-place 4-byte Thumb-2 BL hook sites and expected stock bytes
HOOK_GRID_PRESS_GATE = 0x0804D7A0
EXPECTED_GRID_PRESS_GATE = bytes.fromhex("f8b50446")        # push {r3-r7, lr}; mov r4, r0
STOCK_GRID_PRESS_CONT = 0x0804D7A4

HOOK_GRID_MODE_CLEANUP = 0x0804D6E0
EXPECTED_GRID_MODE_CLEANUP = bytes.fromhex("00f0e4f9")  # bl #0x804daac
HOOK_GRID_TRACK_CLEANUP = 0x0804D680
EXPECTED_GRID_TRACK_CLEANUP = bytes.fromhex("00f014fa")  # bl #0x804daac
EXPECTED_ALLOCATOR_ENTRY = bytes.fromhex("084a0146")  # ldr r2, [pc,#32]; mov r1,r0
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

HOOK_PROJ_ENTER_PAGE = 0x0804F08C
EXPECTED_PROJ_ENTER_PAGE = bytes.fromhex("f0f7e4fd")       # bl #0x803fc58

HOOK_PROJ_PAGE_LOCK = 0x0804F152
EXPECTED_PROJ_PAGE_LOCK = bytes.fromhex("84f83600")        # strb.w r0, [r4, #0x36]
REPLACEMENT_PROJ_PAGE_LOCK = bytes.fromhex("00bf00bf")     # nop; nop

HOOK_CHECK_PACKS = 0x0803DB56
EXPECTED_CHECK_PACKS = bytes.fromhex("14f094f8")           # bl #0x8051c82

HOOK_PAGE_BTN_MODE0 = 0x0804DCF8
EXPECTED_PAGE_BTN_MODE0 = bytes.fromhex("0af089f9")        # bl #0x805800e

HOOK_BUTTON_MODE = 0x0803D8C2
EXPECTED_BUTTON_MODE = bytes.fromhex("14f05af9")            # bl #0x8051b7a

HOOK_SAMPLE_TRIGGER_GATE = 0x08031A1E
EXPECTED_SAMPLE_TRIGGER_GATE = bytes.fromhex("14f0afbe")    # b.w #0x8046780

HOOK_METRONOME_TRIGGER_GATE = 0x080333E6
EXPECTED_METRONOME_TRIGGER_GATE = bytes.fromhex("13f0cbb9")   # b.w #0x8046780

HOOK_SAMPLE_DSP_GATE = 0x0804679E
EXPECTED_SAMPLE_DSP_GATE = bytes.fromhex("faf769f8")         # bl #0x8040874

HOOK_SAMPLE_PREVIEW_GATE = 0x080467CA
EXPECTED_SAMPLE_PREVIEW_GATE = bytes.fromhex("faf711b8")     # b.w #0x80407f0

HOOK_PROJ_LED_BANK = 0x0804F288
EXPECTED_PROJ_LED_BANK = bytes.fromhex("f0f7e6fc")           # bl #0x803fc58

HOOK_PROJ_PAD_GATE = 0x0804F0A8
EXPECTED_PROJ_PAD_GATE = bytes.fromhex("f0f7d6fd")           # bl #0x803fc58

HOOK_PROJ_DISPATCH_GUARD = 0x080385F6
EXPECTED_PROJ_DISPATCH_GUARD = bytes.fromhex("07f02ffb")     # bl #0x803fc58

HOOK_SAVE_BTN_GATE = 0x0804ED82
EXPECTED_SAVE_BTN_GATE = bytes.fromhex("f0f769ff")           # bl #0x803fc58

HOOK_PROJ_LOAD_COMPLETE = 0x08037EC2
EXPECTED_PROJ_LOAD_COMPLETE = bytes.fromhex("07f093fe")      # bl #0x803fbec

HOOK_PROJ_SAVE_COMPLETE = 0x08038176
EXPECTED_PROJ_SAVE_COMPLETE = bytes.fromhex("07f039fd")      # bl #0x803fbec

HOOK_PROJ_LOAD_CB = 0x080381C8
EXPECTED_PROJ_LOAD_CB = bytes.fromhex("0c380968")            # subs r0,#0xc; ldr r1,[r1]

HOOK_PROJ_TIMER_OR_DIRECT = 0x0803806A
EXPECTED_PROJ_TIMER_OR_DIRECT = bytes.fromhex("0ef0b8fe")    # bl #0x8046dde

OFF: dict[str, tuple[int, int]] = {
    "magic": (OFF_MAGIC, 4),
    "seq_enabled": (OFF_SEQ_ENABLED, 1),
    "trans_state": (OFF_TRANS_STATE, 1),
    "trans_target_mode": (OFF_TRANS_TARGET_MODE, 1),
    "trans_target_slot": (OFF_TRANS_TARGET_SLOT, 1),
    "grid_ptr": (OFF_GRID_PTR, 4),
    "proj_view_ptr": (OFF_PROJ_VIEW_PTR, 4),
    "proj_ctrl_ptr": (OFF_PROJ_CTRL_PTR, 4),
    "ctrl_ptr": (OFF_CTRL_PTR, 4),
    "last_normal_proj": (OFF_LAST_NORMAL_PROJ, 1),
    "last_seq_proj": (OFF_LAST_SEQ_PROJ, 1),
    "project_dirty": (OFF_PROJECT_DIRTY, 1),
    "trans_prev_slot": (OFF_TRANS_PREV_SLOT, 1),
    "save_owner": (OFF_SAVE_OWNER, 4),
    "save_slot": (OFF_SAVE_SLOT, 1),
    "save_edited": (OFF_SAVE_EDITED, 1),
    "recorders": (OFF_RECORDERS, 32),
    "close_callback": (OFF_CLOSE_CALLBACK, 4),
    "close_status": (OFF_CLOSE_STATUS, 12),
    "load_close_callback": (OFF_LOAD_CLOSE_CALLBACK, 4),
    "load_close_status": (OFF_LOAD_CLOSE_STATUS, 12),
    "project_tainted": (OFF_PROJECT_TAINTED, 1),
}


def check_layout() -> None:
    """Verifies that all state block fields are non-overlapping and fit within 256 bytes."""
    used = sorted(OFF.values())
    for (a, n), (b2, _) in zip(used, used[1:]):
        assert a + n <= b2, f"seq_Patch.OFF overlaps at offset {b2:#x}"
    assert used[-1][0] + used[-1][1] <= SEQ_STATE_SIZE, "seq_Patch.OFF exceeds SEQ_STATE_SIZE"


def emit_seq_state(a: Asm) -> None:
    """Emits the `c_seq_state` Thumb-2 function into the given assembler instance."""
    check_layout()
    E = a.emit

    def imm32(rd: int, v: int) -> None:
        E(movw, rd, v & 0xFFFF)
        E(movt, rd, (v >> 16) & 0xFFFF)

    a.label("c_seq_state")
    E(push, [4], lr=True)
    E(raw, bytes.fromhex("eff31084 72b6"))  # mrs r4,primask; cpsid i
    imm32(0, SEQ_STATE_ADDR)                # r0 = 0x2004F660
    imm32(3, HEAP_LIMIT_PTR)                # r3 = 0x20002B54
    # Validate current on EVERY path, including a damaged reserved block.
    E(ldr_imm, 1, 3, 4)
    E(cmp_reg, 1, 0)
    E(b_cond, "seq_off", "hi")
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
    E(movs_imm, 1, DEFAULT_NORMAL_PROJ)     # r1 = 0 (default last_normal_proj)
    E(strb_imm, 1, 0, OFF_LAST_NORMAL_PROJ) # [r0 + 0x18] = 0
    E(movs_imm, 1, DEFAULT_SEQ_PROJ)        # r1 = 32 (default last_seq_proj)
    E(strb_imm, 1, 0, OFF_LAST_SEQ_PROJ)    # [r0 + 0x19] = 32
    imm32(2, SEQ_STATE_MAGIC)               # r2 = 0x31514553 ("SEQ1")
    E(str_imm, 2, 0, OFF_MAGIC)             # [r0 + 0x00] = 0x31514553

    a.label("seq_ok")
    E(raw, bytes.fromhex("84f31088"))       # msr primask,r4 (restore, never blindly enable)
    E(pop, [4], lr=True)
    E(bx_lr)

    a.label("seq_off")
    E(movs_imm, 0, 0)
    E(b, "seq_ok")


def emit_allocator_guard(a: Asm) -> None:
    """Serialize the stock bump allocator with lazy state reservation.
    If allocation exceeds heap_limit, returns -1 (0xFFFFFFFF) safely without BKPT #1.
    """
    E = a.emit
    a.label("c_allocator_guard")
    E(push, [4, 5], lr=True)
    E(sub_sp_imm, 4)                        # depth % 8 == 0
    E(mov_reg, 5, 0)                        # r5 = size requested
    E(raw, bytes.fromhex("eff31084 72b6"))  # mrs r4,primask; cpsid i
    E(bl, "c_seq_state")                    # ensure reservation
    a.imm32(2, HEAP_LIMIT_PTR)              # r2 = 0x20002B54
    E(ldr_imm, 3, 2, 4)                     # r3 = [0x20002B58] (heap_cur)
    E(mov_reg, 1, 5)                        # r1 = size requested
    E(raw, bytes.fromhex("11f0030f"))       # tst.w r1, #3
    E(b_cond, "alloc_aligned", "eq")
    E(lsrs_imm, 1, 1, 2)
    E(lsls_imm, 1, 1, 2)
    E(adds_imm8, 1, 4)
    E(b_cond, "alloc_oom", "hs")            # alignment overflow
    a.label("alloc_aligned")
    E(adds_reg, 1, 1, 3)                    # r1 = new heap_cur candidate
    E(b_cond, "alloc_oom", "hs")            # address overflow
    E(ldr_imm, 0, 2, 0)                     # r0 = heap_limit
    E(cmp_reg, 0, 1)                        # compare limit with candidate
    E(b_cond, "alloc_oom", "lo")            # if limit < candidate -> OOM
    E(str_imm, 1, 2, 4)                     # [0x20002B58] = new heap_cur
    E(mov_reg, 0, 3)                        # return previous heap_cur
    a.label("alloc_exit")
    E(raw, bytes.fromhex("84f31088"))       # msr primask,r4
    E(add_sp_imm, 4)
    E(pop, [4, 5], pc=True)
    a.label("alloc_oom")
    E(movs_imm, 0, 0)
    E(subs_imm8, 0, 1)                      # r0 = -1 (0xFFFFFFFF)
    E(b, "alloc_exit")


def emit_grid_press_gate(a: Asm) -> None:
    """Emits `c_grid_press_gate` into `a` (intercepts 0x0804D7A0)."""
    E = a.emit

    a.label("c_grid_press_gate")
    E(push, [0, 1, 2, 4], lr=True)              # 20B
    E(sub_sp_imm, 4)                            # 24B (depth % 8 == 0)
    E(bl, "c_seq_state")
    E(cbz, "grid_press_allow", 0)
    E(ldrb_imm, 1, 0, OFF_TRANS_STATE)
    E(cbnz, "grid_press_block", 1)
    a.label("grid_press_allow")
    E(ldr_sp, 0, 4)                             # r0 = orig r0
    E(ldr_sp, 1, 8)                             # r1 = orig r1
    E(ldr_sp, 2, 12)                            # r2 = orig r2
    E(ldr_sp, 4, 16)                            # r4 = orig r4
    E(ldr_sp, 3, 20)                            # r3 = orig lr
    E(mov_reg, 14, 3)                           # lr = orig lr
    E(add_sp_imm, 24)                           # free stack frame
    E(push, [3, 4, 5, 6, 7], lr=True)           # replicate stock push
    E(mov_reg, 4, 0)                            # replicate stock mov r4, r0
    E(b_w, STOCK_GRID_PRESS_CONT)               # branch to 0x0804D7A4
    a.label("grid_press_block")
    E(add_sp_imm, 4)
    E(pop, [0, 1, 2, 4], pc=True)


def emit_resolve_subview(a: Asm) -> None:
    """Emits `c_resolve_subview(r0=grid, r1=pad)` into `a`."""
    E = a.emit

    a.label("c_resolve_subview")
    E(push, [0, 1, 2, 3, 4], lr=True)           # save r0=grid, r1=pad, r2, r3, r4, lr
    E(bl, "c_seq_state")                        # r0 = state (or 0)
    E(cbz, "resolve_orig", 0)                   # if state == 0 -> resolve_orig
    E(ldr_sp, 1, 0)                             # r1 = saved r0 (grid)
    E(str_imm, 1, 0, OFF_GRID_PTR)              # [state + 0x08] = grid

    # Mark project dirty on user edit
    E(movs_imm, 2, 1)
    E(strb_w, 2, 0, OFF_SAVE_EDITED)
    E(strb_imm, 2, 0, OFF_PROJECT_DIRTY)

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
    """Emits `c_transform_pad(r0=grid, r1=pad, r2=track, r3=mode)` into `a`."""
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
    """Emits `c_step_page_read(r0=page_store, r1=0)` into `a`."""
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

    a.align(4)
    a.label("c_zero_word")
    E(raw, b"\x00\x00\x00\x00")                 # constant 0x00000000 word

    a.label("page_read_orig")
    E(pop, [0, 1, 2, 3])                        # restore r0=page_store, r1=0, r2, r3
    E(bl, STOCK_READ_STORE_WORD)                # call 0x0803FC58(page_store, 0)
    E(pop, [4], lr=True)                        # restore r4, lr
    E(bx_lr)                                    # return


def emit_comp_top_leds(a: Asm) -> None:
    """Emits `c_comp_top_leds(r0=sb)` into `a`."""
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
    """Emits `c_comp_bottom_memcpy(r0=grid_out+0x20, r1=r8, r2=0x20)` into `a`."""
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
    """Preserve five stock arguments across cleanup at mode AND track hooks."""
    E = a.emit

    a.label("c_grid_mode_cleanup")
    E(push, [0, 1, 2, 3, 4, 5, 6, 7, 8], lr=True)  # 40B
    E(mov_reg, 5, 0)                            # r5 = grid at either call site
    E(cbz, "cleanup_done", 5)                   # if grid (r5) == 0 -> done

    # Loop 8 tracks (t = 0..7, r4 = t)
    E(movs_imm, 4, 0)                           # r4 = t = 0

    a.label("cleanup_track_loop")
    E(lsls_imm, 0, 4, 2)                        # r0 = t * 4
    E(adds_imm8, 0, 0x74)                       # r0 = 0x74 + t * 4
    E(ldr_reg, 6, 5, 0)                         # r6 = view = [grid + r0]
    E(cmp_imm, 6, 0)
    E(b_cond, "cleanup_next_track", "eq")       # if view == 0 -> next track

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
    E(pop, [0, 1, 2, 3])                       # restore stock call arguments
    E(ldr_w, 12, 13, 24)                       # fifth arg above six saved registers
    E(sub_sp_imm, 8)
    E(str_w, 12, 13, 0)
    E(bl, STOCK_GRID_MODE_UPDATE)
    E(add_sp_imm, 8)
    E(movs_imm, 0, 0)
    E(str_w, 0, 5, 0x228)
    E(pop, [4, 5, 6, 7, 8], lr=True)
    E(bx_lr)


def emit_proj_enter_page(a: Asm) -> None:
    """Emits `c_proj_enter_page` into `a`."""
    E = a.emit

    a.label("c_proj_enter_page")
    E(push, [4, 5], lr=True)
    E(sub_sp_imm, 4)
    # r4 is proj_view in 0x0804F080
    E(bl, "c_seq_state")
    E(cbz, "proj_enter_zero", 0)
    E(mov_reg, 5, 0)                            # r5 = state
    E(ldrb_imm, 1, 5, OFF_TRANS_STATE)
    E(cbnz, "proj_enter_skip_p", 1)            # active transition owns its context
    E(str_imm, 4, 5, OFF_PROJ_VIEW_PTR)         # capture proj_view
    # If [proj_view + 0x0C] != 0, capture P
    E(ldr_imm, 1, 4, 0x0C)
    E(cbz, "proj_enter_skip_p", 1)
    E(ldr_imm, 2, 1, 0)
    E(subs_imm8, 2, 4)
    E(str_imm, 2, 5, OFF_PROJ_CTRL_PTR)
    a.label("proj_enter_skip_p")
    E(ldrb_imm, 1, 5, OFF_SEQ_ENABLED)
    E(strb_w, 1, 4, 0x36)                     # [proj_view + 0x36] = seq_enabled
    E(cmp_imm, 1, 1)
    E(b_cond, "proj_enter_seq", "eq")
    a.label("proj_enter_norm")
    E(adr, "c_proj_zero_word", 0)               # 0x00 >> 5 == 0
    E(b, "proj_enter_ret")
    a.label("proj_enter_seq")
    E(adr, "c_proj_seq_word", 0)                # 0x20 >> 5 == 1
    E(b, "proj_enter_ret")
    a.label("proj_enter_zero")
    E(adr, "c_proj_zero_word", 0)
    a.label("proj_enter_ret")
    E(add_sp_imm, 4)
    E(pop, [4, 5], pc=True)

    a.align(4)
    a.label("c_proj_zero_word")
    E(raw, b"\x00\x00\x00\x00")
    a.align(4)
    a.label("c_proj_seq_word")
    E(raw, b"\x20\x00\x00\x00")
    a.align(4)
    a.label("c_byte_two")
    E(raw, b"\x02\x00\x00\x00")


def emit_check_packs_allowed(a: Asm) -> None:
    """Emits `c_check_packs_allowed` into `a`."""
    E = a.emit

    a.label("c_check_packs_allowed")
    E(push, [4], lr=True)
    E(mov_reg, 4, 0)
    E(bl, "c_seq_state")
    E(cbz, "packs_orig", 0)
    E(ldrb_imm, 1, 0, OFF_SEQ_ENABLED)
    E(cmp_imm, 1, 1)
    E(b_cond, "packs_orig", "ne")
    E(movs_imm, 0, 0)
    E(pop, [4], pc=True)

    a.label("packs_orig")
    E(mov_reg, 0, 4)
    E(bl, STOCK_CHECK_PACKS)
    E(pop, [4], pc=True)


def emit_page_btn_mode0(a: Asm) -> None:
    """Emits `c_page_btn_mode0` into `a`."""
    E = a.emit

    a.label("c_page_btn_mode0")
    E(push, [4], lr=True)
    E(bl, "c_seq_state")
    E(cbz, "page_btn_orig", 0)
    E(ldrb_imm, 1, 0, OFF_SEQ_ENABLED)
    E(cmp_imm, 1, 1)
    E(b_cond, "page_btn_orig", "ne")

    # seq_enabled == 1: ignore 1-16 button in grid_mode 0 by returning r0 = 0
    E(movs_imm, 0, 0)
    E(pop, [4], lr=True)
    E(pop, [1, 4, 5], pc=True)

    a.label("page_btn_orig")
    E(pop, [4], lr=True)
    E(mov_reg, 0, 4)
    E(b_w, STOCK_GET_ACTIVE_TRACK)


def emit_silence_active_samples(a: Asm) -> None:
    """Closes playing voices on channels 0x10..0x17 and clears active voice table."""
    E = a.emit
    a.label("c_silence_active_samples")
    E(push, [4, 5], lr=True)
    E(sub_sp_imm, 4)
    a.imm32(4, 0x20000310)                      # sample engine lock object ptr
    E(ldr_imm, 0, 4, 0)
    E(cbz, "silence_voices_clear", 0)
    E(movs_imm, 5, 0x10)                        # ch = 0x10
    a.label("silence_loop")
    E(mov_reg, 0, 5)
    E(bl, STOCK_SAMPLE_FORCE_OFF)               # 0x080467D2(ch)
    E(adds_imm8, 5, 1)
    E(cmp_imm, 5, 0x18)
    E(b_cond, "silence_loop", "ne")
    a.label("silence_voices_clear")
    a.imm32(4, 0x20006D90)                      # active voice table
    E(movs_imm, 1, 0xFF)
    E(movs_imm, 2, 0)
    a.label("clear_voice_table")
    E(strb_reg, 1, 4, 2)                        # strb r1, [r4, r2]
    E(adds_imm8, 2, 1)
    E(cmp_imm, 2, 16)
    E(b_cond, "clear_voice_table", "ne")
    E(add_sp_imm, 4)
    E(pop, [4, 5], pc=True)


def emit_button_mode_hook(a: Asm) -> None:
    """Emits `c_button_mode_hook` into `a`."""
    E = a.emit

    a.label("c_button_mode_hook")
    E(push, [4, 5, 6, 7], lr=True)              # 20B
    E(sub_sp_imm, 4)                            # 24B (depth % 8 == 0)
    E(mov_reg, 0, 4)
    E(adds_imm8, 0, 0xA0)
    E(mov_reg, 1, 5)
    E(bl, STOCK_CTRL_BUTTON_PRE)
    E(cmp_imm, 0, 0)
    E(b_cond_w, "btn_mode_handled", "ne")
    E(cmp_imm, 5, 0x12)                         # Sample Rec
    E(b_cond_w, "btn_mode_orig", "ne")

    # Check Shift held: [ctrl + 0x0C]
    E(ldr_imm, 0, 4, 0x0C)
    E(movs_imm, 1, 0)
    E(bl, STOCK_READ_STORE_WORD)
    E(ldrb_imm, 0, 0, 0)
    E(cmp_imm, 0, 0)
    E(b_cond_w, "btn_mode_orig", "eq")

    # Shift + Sample Rec pressed!
    E(bl, "c_seq_state")
    E(cmp_imm, 0, 0)
    E(b_cond_w, "btn_mode_handled", "eq")
    E(mov_reg, 6, 0)                            # r6 = state
    E(str_imm, 4, 6, OFF_CTRL_PTR)              # capture ctrl

    # Capture grid_view if present in [ctrl + 0x3C]
    E(ldr_imm, 0, 4, 0x3C)
    E(cbz, "btn_skip_grid", 0)
    E(str_imm, 0, 6, OFF_GRID_PTR)
    a.label("btn_skip_grid")

    # Pre-flight guard 1: trans_state == 0
    E(ldrb_imm, 1, 6, OFF_TRANS_STATE)
    E(cmp_imm, 1, 0)
    E(b_cond_w, "btn_mode_handled", "ne")

    # Pre-flight guard 2: project_dirty == 0
    E(ldrb_imm, 1, 6, OFF_PROJECT_DIRTY)
    E(cmp_imm, 1, 0)
    E(b_cond_w, "btn_mode_handled", "ne")               # dirty project -> refuse transition!

    # Obtain proj_view from [ctrl + 0x50] or [state + OFF_PROJ_VIEW_PTR]
    E(ldr_imm, 7, 4, 0x50)                      # r7 = proj_view
    E(cbnz, "btn_have_proj_view", 7)
    E(ldr_imm, 7, 6, OFF_PROJ_VIEW_PTR)
    E(cmp_imm, 7, 0)
    E(b_cond_w, "btn_mode_handled", "eq")               # no project context -> refuse
    a.label("btn_have_proj_view")
    E(str_imm, 7, 6, OFF_PROJ_VIEW_PTR)

    # Check [proj_view + 0x0C] (action node for Load/New)
    E(ldr_imm, 0, 7, 0x0C)
    E(cmp_imm, 0, 0)
    E(b_cond_w, "btn_mode_handled", "eq")

    # Check [proj_view + 0x24] (ready store): bit 3 must be 1, bits 0..1 must be 0
    E(ldr_imm, 0, 7, 0x24)
    E(cmp_imm, 0, 0)
    E(b_cond_w, "btn_mode_handled", "eq")
    E(movs_imm, 1, 0)
    E(bl, STOCK_READ_STORE_WORD)
    E(ldrb_imm, 1, 0, 0)
    E(movs_imm, 2, 8)
    E(tst_reg, 1, 2)
    E(b_cond_w, "btn_mode_handled", "eq")         # bit 3 not set -> not ready
    E(movs_imm, 2, 3)
    E(tst_reg, 1, 2)
    E(b_cond_w, "btn_mode_handled", "ne")         # bits 0..1 set -> busy

    # Check [proj_view + 0x28] (phase store): phase byte must be 0
    E(ldr_imm, 0, 7, 0x28)
    E(cmp_imm, 0, 0)
    E(b_cond_w, "btn_mode_handled", "eq")
    E(movs_imm, 1, 1)
    E(bl, STOCK_READ_STORE_WORD)
    E(ldrb_imm, 1, 0, 0)
    E(cmp_imm, 1, 0)
    E(b_cond_w, "btn_mode_handled", "ne")               # phase != 0 -> busy

    # Missing metadata must fail closed.
    E(ldr_imm, 0, 7, 0x20)
    E(cmp_imm, 0, 0)
    E(b_cond_w, "btn_mode_handled", "eq")
    E(movs_imm, 1, 0x0B)
    E(bl, STOCK_READ_STORE_WORD)
    E(ldrb_imm, 5, 0, 0)                        # r5 = current slot
    E(cmp_imm, 5, 64)
    E(b_cond_w, "btn_mode_handled", "hs")
    E(strb_imm, 5, 6, OFF_TRANS_PREV_SLOT)

    # Save current slot into last_normal or last_seq
    E(ldrb_imm, 1, 6, OFF_SEQ_ENABLED)
    E(cmp_imm, 1, 0)
    E(b_cond, "btn_save_seq_prev", "ne")
    E(cmp_imm, 5, 32)
    E(b_cond, "btn_prep_target", "ge")
    E(strb_imm, 5, 6, OFF_LAST_NORMAL_PROJ)
    E(b, "btn_prep_target")
    a.label("btn_save_seq_prev")
    E(cmp_imm, 5, 32)
    E(b_cond, "btn_prep_target", "lo")
    E(strb_imm, 5, 6, OFF_LAST_SEQ_PROJ)

    a.label("btn_prep_target")
    # target_mode = seq_enabled ^ 1
    E(ldrb_imm, 1, 6, OFF_SEQ_ENABLED)
    E(movs_imm, 2, 1)
    E(eors_reg, 1, 2)                           # r1 = target_mode
    E(strb_imm, 1, 6, OFF_TRANS_TARGET_MODE)
    E(cmp_imm, 1, 1)
    E(b_cond, "btn_target_norm", "ne")
    # Target is Sequencer:
    E(ldrb_imm, 5, 6, OFF_LAST_SEQ_PROJ)
    E(cmp_imm, 5, 64)
    E(b_cond_w, "btn_mode_handled", "hs")
    E(cmp_imm, 5, 32)
    E(b_cond, "btn_target_ok", "ge")
    E(movs_imm, 5, 32)
    E(b, "btn_target_ok")
    a.label("btn_target_norm")
    E(ldrb_imm, 5, 6, OFF_LAST_NORMAL_PROJ)
    E(cmp_imm, 5, 32)
    E(b_cond, "btn_target_ok", "lo")
    E(movs_imm, 5, 0)
    a.label("btn_target_ok")
    E(strb_imm, 5, 6, OFF_TRANS_TARGET_SLOT)

    # Disarm Save if armed: [proj_view + 0x2C]
    E(ldr_imm, 0, 7, 0x2C)
    E(cbz, "btn_skip_disarm", 0)
    E(movs_imm, 1, 0)
    E(bl, STOCK_WRITE_STORE_WORD)               # 0x0803FD26([proj_view + 0x2C], 0)
    E(movs_imm, 1, 0)
    E(strb_imm, 1, 0, 0)                        # byte 0 = 0
    E(ldr_imm, 0, 7, 0x2C)
    E(bl, STOCK_NOTIFY_STORE)                   # 0x0803FBEC
    a.label("btn_skip_disarm")

    # Set trans_state = 1
    E(movs_imm, 1, 1)
    E(strb_imm, 1, 6, OFF_TRANS_STATE)

    # Dispatch Load/New to target slot
    E(ldr_imm, 0, 7, 0x0C)
    E(mov_reg, 1, 5)                            # target_slot
    E(movs_imm, 2, 0)
    E(movs_imm, 3, 0)
    E(bl, STOCK_ACTION_DISPATCH)                # 0x08047038

    # If dispatch returned non-zero (rejected):
    E(cmp_imm, 0, 0)
    E(b_cond, "btn_mode_handled", "eq")
    # Failed! Roll back:
    E(movs_imm, 1, 0)
    E(strb_imm, 1, 6, OFF_TRANS_STATE)
    E(b, "btn_mode_handled")

    a.label("btn_mode_handled")
    E(movs_imm, 0, 1)
    E(add_sp_imm, 4)
    E(pop, [4, 5, 6, 7], pc=True)

    a.label("btn_mode_orig")
    E(movs_imm, 0, 0)
    E(add_sp_imm, 4)
    E(pop, [4, 5, 6, 7], pc=True)


def emit_sample_trigger_gate(a: Asm) -> None:
    """Emits `c_sample_trigger_gate` into `a`."""
    E = a.emit

    a.label("c_sample_trigger_gate")
    E(push, [0, 1, 2, 3, 4], lr=True)
    E(bl, "c_seq_state")
    E(cbz, "sample_trigger_orig", 0)
    E(ldrb_imm, 1, 0, OFF_SEQ_ENABLED)
    E(cmp_imm, 1, 1)
    E(b_cond, "sample_trigger_mute", "eq")
    E(ldrb_imm, 1, 0, OFF_TRANS_STATE)
    E(cbz, "sample_trigger_orig", 1)
    E(ldrb_imm, 2, 0, OFF_TRANS_TARGET_MODE)
    E(cmp_imm, 2, 1)
    E(b_cond, "sample_trigger_mute", "eq")

    a.label("sample_trigger_orig")
    E(pop, [0, 1, 2, 3, 4], lr=True)
    E(b_w, STOCK_SAMPLE_TRIGGER_ENGINE)

    a.label("sample_trigger_mute")
    E(pop, [0, 1, 2, 3, 4], lr=True)
    E(movs_imm, 0, 0)
    E(bx_lr)


def emit_metronome_trigger_gate(a: Asm) -> None:
    """Emits `c_metronome_trigger_gate` into `a`."""
    E = a.emit

    a.label("c_metronome_trigger_gate")
    E(push, [0, 1, 2, 3, 4], lr=True)
    E(bl, "c_seq_state")
    E(cbz, "metro_trigger_orig", 0)
    E(ldrb_imm, 1, 0, OFF_SEQ_ENABLED)
    E(cmp_imm, 1, 1)
    E(b_cond, "metro_trigger_mute", "eq")
    E(ldrb_imm, 1, 0, OFF_TRANS_STATE)
    E(cbz, "metro_trigger_orig", 1)
    E(ldrb_imm, 2, 0, OFF_TRANS_TARGET_MODE)
    E(cmp_imm, 2, 1)
    E(b_cond, "metro_trigger_mute", "eq")

    a.label("metro_trigger_orig")
    E(pop, [0, 1, 2, 3, 4], lr=True)
    E(b_w, STOCK_SAMPLE_TRIGGER_ENGINE)

    a.label("metro_trigger_mute")
    E(pop, [0, 1, 2, 3, 4], lr=True)
    E(movs_imm, 0, 0)
    E(bx_lr)


def emit_sample_dsp_gate(a: Asm) -> None:
    """Emits `c_sample_dsp_gate` into `a`."""
    E = a.emit

    a.label("c_sample_dsp_gate")
    E(push, [0, 1, 2, 3, 4], lr=True)
    E(bl, "c_seq_state")
    E(cbz, "dsp_trigger_orig", 0)
    E(ldrb_imm, 1, 0, OFF_SEQ_ENABLED)
    E(cmp_imm, 1, 1)
    E(b_cond, "dsp_trigger_mute", "eq")
    E(ldrb_imm, 1, 0, OFF_TRANS_STATE)
    E(cbz, "dsp_trigger_orig", 1)
    E(ldrb_imm, 2, 0, OFF_TRANS_TARGET_MODE)
    E(cmp_imm, 2, 1)
    E(b_cond, "dsp_trigger_mute", "eq")

    a.label("dsp_trigger_orig")
    E(pop, [0, 1, 2, 3])
    E(bl, STOCK_SAMPLE_DSP_TRIGGER)          # 0x08040874
    E(pop, [4], pc=True)

    a.label("dsp_trigger_mute")
    E(pop, [0, 1, 2, 3])
    E(movs_imm, 0, 0)
    E(pop, [4], pc=True)


def emit_sample_preview_gate(a: Asm) -> None:
    """Emits `c_sample_preview_gate` into `a`."""
    E = a.emit

    a.label("c_sample_preview_gate")
    E(push, [0, 1, 2, 3, 4], lr=True)
    E(bl, "c_seq_state")
    E(cbz, "preview_trigger_orig", 0)
    E(ldrb_imm, 1, 0, OFF_SEQ_ENABLED)
    E(cmp_imm, 1, 1)
    E(b_cond, "preview_trigger_mute", "eq")
    E(ldrb_imm, 1, 0, OFF_TRANS_STATE)
    E(cbz, "preview_trigger_orig", 1)
    E(ldrb_imm, 2, 0, OFF_TRANS_TARGET_MODE)
    E(cmp_imm, 2, 1)
    E(b_cond, "preview_trigger_mute", "eq")

    a.label("preview_trigger_orig")
    E(pop, [0, 1, 2, 3, 4], lr=True)
    E(b_w, STOCK_SAMPLE_PREVIEW_CONT)        # 0x080407F0

    a.label("preview_trigger_mute")
    E(pop, [0, 1, 2, 3, 4], lr=True)
    E(movs_imm, 0, 0)
    E(bx_lr)


def emit_proj_led_bank(a: Asm) -> None:
    """Emits `c_proj_led_bank` into `a`."""
    E = a.emit

    a.label("c_proj_led_bank")
    E(push, [4, 5], lr=True)                # 12B
    E(sub_sp_imm, 4)                        # 16B (depth % 8 == 0)
    E(mov_reg, 5, 6)                        # r5 = proj_view (caller's r6)
    E(bl, "c_seq_state")
    E(cbz, "proj_led_bank_orig", 0)
    E(str_imm, 5, 0, OFF_PROJ_VIEW_PTR)     # capture proj_view
    E(ldrb_imm, 1, 0, OFF_SEQ_ENABLED)
    E(strb_w, 1, 5, 0x36)                   # enforce [proj_view + 0x36] = seq_enabled
    a.label("proj_led_bank_orig")
    E(ldr_imm, 0, 5, 0x24)
    E(movs_imm, 1, 0)
    E(bl, STOCK_READ_STORE_WORD)            # call 0x0803FC58([proj_view + 0x24], 0)
    E(add_sp_imm, 4)
    E(pop, [4, 5], pc=True)


def emit_proj_pad_gate(a: Asm) -> None:
    """Emits `c_proj_pad_gate` into `a`."""
    E = a.emit

    a.label("c_proj_pad_gate")
    E(push, [4, 5], lr=True)                # 12B
    E(sub_sp_imm, 4)                        # 16B (depth % 8 == 0)
    E(mov_reg, 5, 4)                        # r5 = proj_view (caller's r4)
    E(bl, "c_seq_state")
    E(cbz, "proj_pad_orig", 0)
    E(mov_reg, 4, 0)                        # r4 = state
    # If trans_state != 0, block pad action
    E(ldrb_imm, 1, 4, OFF_TRANS_STATE)
    E(cbnz, "proj_pad_block", 1)
    # Enforce current verified bank on proj_view
    E(ldrb_imm, 1, 4, OFF_SEQ_ENABLED)
    E(strb_w, 1, 5, 0x36)                   # [proj_view + 0x36] = seq_enabled
    # Check if project controller is busy (phase store [proj_view + 0x28])
    E(ldr_imm, 0, 5, 0x28)
    E(cbz, "proj_pad_orig", 0)
    E(movs_imm, 1, 1)
    E(bl, STOCK_READ_STORE_WORD)            # read phase word 1
    E(ldrb_imm, 0, 0, 0)
    E(cbnz, "proj_pad_block", 0)             # if phase != 0 -> block

    a.label("proj_pad_orig")
    E(ldr_imm, 0, 5, 0x24)
    E(movs_imm, 1, 0)
    E(bl, STOCK_READ_STORE_WORD)            # 0x0803FC58([proj_view + 0x24], 0)
    E(add_sp_imm, 4)
    E(pop, [4, 5], pc=True)

    a.label("proj_pad_block")
    E(add_sp_imm, 4)
    E(adr, "pad_gate_zero_word", 0)         # bit 3 is 0 -> caller exits immediately
    E(pop, [4, 5], pc=True)
    a.align(4)
    a.label("pad_gate_zero_word")
    E(raw, b"\x00\x00\x00\x00")


def emit_proj_dispatch_guard(a: Asm) -> None:
    """Emits `c_proj_dispatch_guard` into `a`."""
    E = a.emit

    a.label("c_proj_dispatch_guard")
    E(push, [4, 5, 6, 7], lr=True)          # 20B
    E(sub_sp_imm, 4)                        # 24B (depth % 8 == 0)
    # Caller: r5 = P, r4 = action_node, r6 = arg1
    E(bl, STOCK_READ_STORE_WORD)            # r0 = phase_ptr
    E(mov_reg, 7, 0)                        # r7 = phase_ptr
    E(ldrb_imm, 0, 7, 0)
    E(cmp_imm, 0, 2)
    E(b_cond, "dispatch_guard_busy", "eq")
    E(bl, "c_seq_state")
    E(cbz, "dispatch_guard_pass", 0)
    # r0 = state
    E(ldrb_imm, 1, 0, OFF_TRANS_STATE)
    E(cmp_imm, 1, 2)
    E(b_cond, "dispatch_guard_reject", "eq") # load in flight -> block everything
    E(cmp_imm, 1, 1)
    E(b_cond, "dispatch_guard_check_trans", "eq")

    # trans_state == 0: check bank
    E(ldrb_imm, 2, 0, OFF_SEQ_ENABLED)      # r2 = expected bank (0 or 1)
    # Case A: Load/New ([P + 0x38])
    E(ldr_imm, 3, 5, 0x38)
    E(cmp_reg, 4, 3)
    E(b_cond, "dispatch_guard_load", "eq")
    # Case B: Save/Duplicate ([P + 0x3C])
    E(ldr_imm, 3, 5, 0x3C)
    E(cmp_reg, 4, 3)
    E(b_cond, "dispatch_guard_save", "eq")
    # Case C: Clear ([P + 0x1C])
    E(ldr_imm, 3, 5, 0x1C)
    E(cmp_reg, 4, 3)
    E(b_cond, "dispatch_guard_clear", "eq")
    # Case D: Pack switch ([P + 0x40])
    E(ldr_imm, 3, 5, 0x40)
    E(cmp_reg, 4, 3)
    E(b_cond, "dispatch_guard_pack", "eq")
    E(b, "dispatch_guard_pass")

    a.label("dispatch_guard_load")
    E(mov_reg, 1, 6)
    E(cmp_imm, 1, 0x40)
    E(b_cond, "load_slot_no_sub", "lo")
    E(subs_imm8, 1, 0x40)
    a.label("load_slot_no_sub")
    E(lsrs_imm, 1, 1, 5)                    # r1 = slot >> 5
    E(cmp_reg, 1, 2)
    E(b_cond, "dispatch_guard_reject", "ne")
    E(str_imm, 5, 0, OFF_PROJ_CTRL_PTR)     # capture only an admitted Load/New
    E(b, "dispatch_guard_pass")

    a.label("dispatch_guard_save")
    E(ldrb_w, 1, 0, OFF_PROJECT_TAINTED)
    E(cbnz, "dispatch_guard_reject", 1)
    E(mov_reg, 1, 6)
    E(lsrs_imm, 1, 1, 5)                    # r1 = slot >> 5
    E(cmp_reg, 1, 2)
    E(b_cond, "dispatch_guard_reject", "ne")
    E(b, "dispatch_guard_pass")

    a.label("dispatch_guard_clear")
    E(mov_reg, 6, 2)                        # stock read clobbers r2
    E(ldr_imm, 0, 5, 0x44)
    E(movs_imm, 1, 0x0B)
    E(bl, STOCK_READ_STORE_WORD)
    E(ldrb_imm, 1, 0, 0)
    E(lsrs_imm, 1, 1, 5)                    # r1 = active_slot >> 5
    E(cmp_reg, 1, 6)
    E(b_cond, "dispatch_guard_reject", "ne")
    E(b, "dispatch_guard_pass")

    a.label("dispatch_guard_pack")
    E(cbnz, "dispatch_guard_reject", 2)      # reject pack switch in sequencer mode
    E(b, "dispatch_guard_pass")

    a.label("dispatch_guard_check_trans")
    E(ldr_imm, 3, 5, 0x38)
    E(cmp_reg, 4, 3)
    E(b_cond, "dispatch_guard_reject", "ne")
    E(ldrb_imm, 2, 0, OFF_TRANS_TARGET_SLOT)
    E(mov_reg, 1, 6)
    E(cmp_imm, 1, 0x40)
    E(b_cond, "trans_slot_no_sub", "lo")
    E(subs_imm8, 1, 0x40)
    a.label("trans_slot_no_sub")
    E(cmp_reg, 1, 2)
    E(b_cond, "dispatch_guard_reject", "ne")
    # Transition trans_state: 1 -> 2 (now in flight!)
    E(str_imm, 5, 0, OFF_PROJ_CTRL_PTR)
    E(movs_imm, 1, 2)
    E(strb_imm, 1, 0, OFF_TRANS_STATE)
    E(b, "dispatch_guard_pass")

    a.label("dispatch_guard_busy")
    a.label("dispatch_guard_pass")
    E(mov_reg, 0, 7)                        # return phase_ptr
    E(add_sp_imm, 4)
    E(pop, [4, 5, 6, 7], pc=True)

    a.label("dispatch_guard_reject")
    E(adr, "dispatch_guard_byte_two", 0)    # byte at [r0] is 2 -> stock caller rejects with r0 = 1!
    E(add_sp_imm, 4)
    E(pop, [4, 5, 6, 7], pc=True)
    a.align(4)
    a.label("dispatch_guard_byte_two")
    E(raw, b"\x02\x02\x02\x02")


def emit_save_btn_gate(a: Asm) -> None:
    """Emits `c_save_btn_gate` into `a`."""
    E = a.emit

    a.label("c_save_btn_gate")
    E(push, [0, 1, 4], lr=True)             # 16B (depth % 8 == 0)
    E(bl, "c_seq_state")
    E(cbz, "save_btn_orig", 0)
    E(ldrb_imm, 1, 0, OFF_TRANS_STATE)
    E(cbnz, "save_btn_block", 1)
    # Check active slot in [save_btn + 0x18] word 0x0B
    E(ldr_imm, 2, 4, 0x18)
    E(cbz, "save_btn_orig", 2)
    E(ldrb_imm, 4, 0, OFF_SEQ_ENABLED)      # callee-saved: stock read clobbers r3
    E(mov_reg, 0, 2)
    E(movs_imm, 1, 0x0B)
    E(bl, STOCK_READ_STORE_WORD)
    E(ldrb_imm, 1, 0, 0)
    E(lsrs_imm, 1, 1, 5)                    # r1 = active_slot >> 5
    E(cmp_reg, 1, 4)
    E(b_cond, "save_btn_block", "ne")
    a.label("save_btn_orig")
    E(pop, [0, 1])
    E(bl, STOCK_READ_STORE_WORD)
    E(pop, [4], pc=True)
    a.label("save_btn_block")
    E(pop, [0, 1])
    E(adr, "save_btn_zero_word", 0)         # byte 0 has bit 3 = 0 -> aborts Save
    E(pop, [4], pc=True)
    a.align(4)
    a.label("save_btn_zero_word")
    E(raw, b"\x00\x00\x00\x00")


def emit_proj_load_complete(a: Asm) -> None:
    """Emits `c_proj_load_complete` into `a`."""
    E = a.emit

    a.label("c_proj_load_complete")
    E(push, [4, 5, 6], lr=True)             # 16B (depth % 8 == 0)
    # In 0x08037E3C: r4 = P, r5 = loaded slot, r0 = [P + 0x44]
    E(bl, STOCK_NOTIFY_STORE)               # 0x0803FBEC([P + 0x44])
    E(bl, "c_seq_state")
    E(cbz, "load_complete_exit", 0)
    E(mov_reg, 6, 0)                        # r6 = state
    E(cmp_imm, 5, 64)
    E(b_cond, "load_complete_exit", "hs")
    # A foreign or premature completion must not clear dirty or saved slots.
    E(ldrb_imm, 1, 6, OFF_TRANS_STATE)
    E(cbz, "load_complete_owned", 1)
    E(cmp_imm, 1, 2)
    E(b_cond, "load_complete_exit", "ne")
    E(ldr_imm, 2, 6, OFF_PROJ_CTRL_PTR)
    E(cmp_reg, 4, 2)
    E(b_cond, "load_complete_exit", "ne")
    E(ldrb_imm, 2, 6, OFF_TRANS_TARGET_SLOT)
    E(cmp_reg, 5, 2)
    E(b_cond, "load_complete_exit", "ne")
    a.label("load_complete_owned")
    E(movs_imm, 1, 0)
    E(strb_w, 1, 6, OFF_PROJECT_TAINTED)    # only a completed apply restores trust
    # Clear dirty flag: fresh project loaded/initialized
    E(movs_imm, 1, 0)
    E(strb_imm, 1, 6, OFF_PROJECT_DIRTY)
    E(str_imm, 1, 6, OFF_SAVE_OWNER)         # invalidate old project's save completion
    # Save active slot into last_normal or last_seq
    E(cmp_imm, 5, 32)
    E(b_cond, "load_complete_save_seq", "ge")
    E(strb_imm, 5, 6, OFF_LAST_NORMAL_PROJ)
    E(b, "load_complete_check_trans")
    a.label("load_complete_save_seq")
    E(strb_imm, 5, 6, OFF_LAST_SEQ_PROJ)

    a.label("load_complete_check_trans")
    E(ldrb_imm, 1, 6, OFF_TRANS_STATE)
    E(cmp_imm, 1, 2)
    E(b_cond, "load_complete_exit", "ne")
    E(ldr_imm, 2, 6, OFF_PROJ_CTRL_PTR)
    E(cmp_reg, 4, 2)
    E(b_cond, "load_complete_exit", "ne")
    # Mode transition verification:
    E(ldrb_imm, 2, 6, OFF_TRANS_TARGET_SLOT)
    E(cmp_reg, 5, 2)
    E(b_cond, "load_complete_exit", "ne")
    # Match! Commit target mode:
    E(ldrb_imm, 3, 6, OFF_TRANS_TARGET_MODE)
    E(strb_imm, 3, 6, OFF_SEQ_ENABLED)      # commit seq_enabled!
    E(movs_imm, 1, 0)
    E(strb_imm, 1, 6, OFF_TRANS_STATE)      # trans_state = 0
    # If target_mode == 1, silence samples
    E(cmp_imm, 3, 1)
    E(b_cond, "load_complete_no_silence", "ne")
    E(bl, "c_silence_active_samples")
    a.label("load_complete_no_silence")
    # Clean up grid if known
    E(ldr_imm, 0, 6, OFF_GRID_PTR)
    E(cbz, "load_complete_check_view", 0)
    E(ldrb_w, 1, 0, GRID_MODE_OFFSET)
    E(bl, STOCK_GRID_CONTAINER_UPDATE)      # 0x0804D6B6(grid, grid_mode)
    a.label("load_complete_check_view")
    # Sync and redraw Projects view if known
    E(ldr_imm, 0, 6, OFF_PROJ_VIEW_PTR)
    E(cbz, "load_complete_exit", 0)
    E(ldrb_imm, 1, 6, OFF_SEQ_ENABLED)
    E(strb_w, 1, 0, 0x36)                 # [proj_view + 0x36] = seq_enabled
    E(ldr_imm, 1, 0, 0x24)
    E(cbz, "load_complete_exit", 1)
    E(bl, STOCK_DRAW_PROJECT_LEDS)          # 0x0804F27E(proj_view)
    E(b, "load_complete_exit")

    a.label("load_complete_exit")
    E(pop, [4, 5, 6], pc=True)


def emit_proj_save_complete(a: Asm) -> None:
    """Emits `c_proj_save_complete` into `a`."""
    E = a.emit

    a.label("c_proj_save_complete")
    E(push, [4], lr=True)
    E(bl, STOCK_NOTIFY_STORE)               # 0x0803FBEC([P + 0x44])
    E(bl, "c_seq_state")
    E(cbz, "save_complete_exit", 0)
    # A completion can only acknowledge its own captured snapshot.
    E(ldr_imm, 1, 0, OFF_SAVE_OWNER)
    E(cmp_reg, 1, 5)                        # stock caller r5 = P
    E(b_cond, "save_complete_exit", "ne")
    E(ldrb_w, 1, 0, OFF_SAVE_SLOT)
    E(cmp_reg, 1, 6)
    E(b_cond, "save_complete_exit", "ne")
    E(raw, bytes.fromhex("eff31084 72b6"))  # mrs r4,primask; cpsid i
    E(ldrb_w, 1, 0, OFF_SAVE_EDITED)
    E(cbnz, "save_keep_dirty", 1)
    E(bl, "c_records_pending")             # r0 state preserved; r1 = pending
    E(cbnz, "save_keep_dirty", 1)
    E(movs_imm, 1, 0)
    E(strb_imm, 1, 0, OFF_PROJECT_DIRTY)
    a.label("save_keep_dirty")
    E(movs_imm, 1, 0)
    E(str_imm, 1, 0, OFF_SAVE_OWNER)         # consume completion once
    E(raw, bytes.fromhex("84f31088"))       # restore caller PRIMASK
    # Update last saved slot
    E(cmp_imm, 6, 32)                       # in 0x08038078, r6 = saved slot
    E(b_cond, "save_complete_seq", "ge")
    E(strb_imm, 6, 0, OFF_LAST_NORMAL_PROJ)
    E(b, "save_complete_exit")
    a.label("save_complete_seq")
    E(strb_imm, 6, 0, OFF_LAST_SEQ_PROJ)
    a.label("save_complete_exit")
    E(pop, [4], pc=True)


def emit_proj_load_cb(a: Asm) -> None:
    """Emits `c_proj_load_cb` into `a`."""
    E = a.emit

    a.label("c_proj_load_cb")
    # r0 = P + 0x0C, r1 = &status
    E(subs_imm8, 0, 0x0C)                   # r0 = P
    E(ldr_imm, 1, 1, 0)                     # r1 = status
    E(cmp_imm, 1, 2)
    E(b_cond, "load_cb_success", "eq")
    E(cmp_imm, 1, 3)
    E(b_cond, "load_cb_error", "eq")
    E(bx_lr)                                # in-progress (1) -> ignore

    a.label("load_cb_success")
    E(b_w, STOCK_LOAD_SUCCESS)              # 0x08037E3C(P)

    a.label("load_cb_error")
    E(push, [4, 5, 6], lr=True)
    E(mov_reg, 4, 0)                        # r4 = P
    E(movs_imm, 5, 0)
    E(bl, "c_seq_state")
    E(cbz, "load_cb_error_clean", 0)
    E(ldr_imm, 1, 0, OFF_PROJ_CTRL_PTR)
    E(cmp_reg, 1, 4)
    E(b_cond, "load_cb_error_clean", "ne")
    E(movs_imm, 1, 1)
    E(strb_w, 1, 0, OFF_PROJECT_TAINTED)
    E(strb_w, 1, 0, OFF_SAVE_EDITED)
    E(strb_imm, 1, 0, OFF_PROJECT_DIRTY)
    E(ldr_imm, 5, 4, 0x4C)
    E(ldrb_imm, 1, 0, OFF_TRANS_STATE)
    E(cmp_imm, 1, 2)
    E(b_cond, "load_cb_error_ready", "ne")
    E(movs_imm, 1, 0)
    E(strb_imm, 1, 0, OFF_TRANS_STATE)      # roll back transition
    a.label("load_cb_error_ready")
    E(cbz, "load_cb_error_clean", 5)
    E(mov_reg, 0, 5)
    E(movs_imm, 1, 0)
    E(bl, STOCK_WRITE_STORE_WORD)
    E(ldr_imm, 1, 0, 0)
    E(movs_imm, 2, 3)                     # stock Load busy mask, preserve ready bits
    E(bics_reg, 1, 2)
    E(str_imm, 1, 0, 0)
    E(mov_reg, 0, 5)
    E(bl, STOCK_NOTIFY_STORE)
    a.label("load_cb_error_clean")
    E(mov_reg, 0, 4)
    E(bl, STOCK_LOAD_ERROR_CLEANUP)         # 0x08037DD0(P)
    E(pop, [4, 5, 6], pc=True)


def emit_proj_save_cb(a: Asm) -> None:
    """Invalidate a failed save snapshot before running the stock cleanup."""
    E = a.emit
    a.label("c_proj_save_cb")
    E(subs_imm8, 0, 0x10)                  # stock callback r0 = P + 0x10
    E(ldr_imm, 1, 1, 0)
    E(cmp_imm, 1, 2)
    E(b_cond, "save_cb_success", "eq")
    E(cmp_imm, 1, 3)
    E(b_cond, "save_cb_error", "eq")
    E(bx_lr)
    a.label("save_cb_success")
    E(b_w, 0x08038078)
    a.label("save_cb_error")
    E(push, [4, 5, 6], lr=True)
    E(mov_reg, 4, 0)
    E(movs_imm, 6, 0)
    E(raw, bytes.fromhex("eff31085 72b6"))  # mrs r5,primask; cpsid i
    E(bl, "c_seq_state")
    E(cbz, "save_cb_error_restore", 0)
    E(ldr_imm, 1, 0, OFF_SAVE_OWNER)
    E(cmp_reg, 1, 4)
    E(b_cond, "save_cb_error_restore", "ne")
    E(movs_imm, 1, 0)
    E(str_imm, 1, 0, OFF_SAVE_OWNER)
    E(ldr_imm, 6, 4, 0x4C)                # owned Save's ready/busy store
    a.label("save_cb_error_restore")
    E(raw, bytes.fromhex("85f31088"))
    E(cbz, "save_cb_error_cleanup", 6)
    E(mov_reg, 0, 6)
    E(movs_imm, 1, 0)
    E(bl, STOCK_WRITE_STORE_WORD)
    E(ldr_imm, 1, 0, 0)
    E(movs_imm, 2, 2)
    E(bics_reg, 1, 2)                      # clear Save busy only; preserve other bits
    E(str_imm, 1, 0, 0)
    E(mov_reg, 0, 6)
    E(bl, STOCK_NOTIFY_STORE)
    a.label("save_cb_error_cleanup")
    E(mov_reg, 0, 4)
    E(pop, [4, 5, 6], lr=True)
    E(b_w, STOCK_LOAD_ERROR_CLEANUP)


def emit_save_storage_result(a: Asm) -> None:
    """Defer an owned Project Save acknowledgement until Close completes.

    Write and Close both use real stock requests. Keep the application busy
    and retain an owned copy of its status across the two result events.
    """
    E = a.emit
    a.label("c_save_storage_result")
    E(push, [3, 4, 5, 6, 7], lr=True)       # 24 bytes
    E(mov_reg, 4, 0)                       # copied key/status pointer
    E(mov_reg, 7, 2)                       # actual filesystem return code
    E(ldr_sp, 5, 28)                       # original sixth argument = bridge
    E(ldr_imm, 6, 5, 4)
    E(cbz, "save_storage_consumed", 6)
    E(bl, "c_seq_state")
    E(cbz, "save_storage_generic", 0)
    E(ldr_imm, 1, 0, OFF_SAVE_OWNER)
    E(cbz, "save_storage_generic", 1)
    E(adds_imm8, 1, 0x10)
    E(cmp_reg, 1, 6)
    E(b_cond, "save_storage_generic", "ne")
    # Only one admitted Project Save can occupy the Close context.
    E(str_imm, 6, 0, OFF_CLOSE_CALLBACK)
    for offset in (0, 4, 8):
        E(ldr_imm, 1, 4, offset)
        E(str_imm, 1, 0, OFF_CLOSE_STATUS + offset)
    E(cbz, "save_storage_close", 7)
    E(movs_imm, 1, 3)                      # only own Project Save -> failure
    E(str_imm, 1, 0, OFF_CLOSE_STATUS)
    a.label("save_storage_close")
    E(mov_reg, 2, 0)                       # immutable state address as Close context
    E(adr, "c_save_close_result", 1)
    E(adds_imm8, 1, 1)                     # Thumb callback pointer
    E(mov_reg, 0, 4)                       # original file key for Close request
    E(bl, 0x080460C8)
    E(movs_imm, 2, 0)
    E(str_imm, 2, 5, 4)                    # original write bridge consumed once
    E(pop, [0, 4, 5, 6, 7], pc=True)

    a.label("save_storage_generic")
    E(mov_reg, 0, 4)
    E(movs_imm, 2, 0)
    a.imm32(1, 0x08047315)                 # preserve other clients' stock Close
    E(bl, 0x080460C8)
    E(movs_imm, 2, 0)
    E(str_imm, 2, 5, 4)
    E(mov_reg, 0, 6)
    E(mov_reg, 1, 4)
    E(movs_imm, 2, 0)                      # original bridge's callback ABI
    E(ldr_imm, 4, 0, 0)
    E(ldr_imm, 7, 4, 0)
    E(raw, bytes.fromhex("b847"))          # blx r7
    a.label("save_storage_consumed")
    E(pop, [0, 4, 5, 6, 7], pc=True)       # stock return r0 = saved input r3

    a.align(4)
    a.label("c_save_close_result")
    E(push, [4, 5, 6], lr=True)
    E(mov_reg, 6, 2)
    E(ldr_sp, 4, 20)                       # sixth argument supplied by real worker
    a.imm32(0, SEQ_STATE_ADDR)
    E(cmp_reg, 4, 0)
    E(b_cond, "save_close_exit", "ne")
    E(bl, "c_seq_state")                   # revalidate heap reservation at completion
    E(cbz, "save_close_exit", 0)
    E(ldr_imm, 5, 4, OFF_CLOSE_CALLBACK)
    E(cbz, "save_close_exit", 5)
    E(ldr_imm, 1, 4, OFF_SAVE_OWNER)
    E(cbz, "save_close_exit", 1)
    E(adds_imm8, 1, 0x10)
    E(cmp_reg, 1, 5)
    E(b_cond, "save_close_exit", "ne")
    E(cbz, "save_close_notify", 6)         # saved Close API result
    E(movs_imm, 1, 3)
    E(str_imm, 1, 4, OFF_CLOSE_STATUS)
    a.label("save_close_notify")
    E(movs_imm, 0, 0)
    E(str_imm, 0, 4, OFF_CLOSE_CALLBACK)    # consume before notifying application
    E(mov_reg, 0, 5)
    E(mov_reg, 1, 4)
    E(adds_imm8, 1, OFF_CLOSE_STATUS)
    E(movs_imm, 2, 0)                      # original application callback ABI
    E(ldr_imm, 3, 5, 0)
    E(ldr_imm, 3, 3, 0)
    E(raw, bytes.fromhex("9847"))          # blx r3
    a.label("save_close_exit")
    E(pop, [4, 5, 6], pc=True)


def emit_load_storage_result(a: Asm) -> None:
    """Own Project Load read/Close outcomes before reaching its apply function."""
    E = a.emit
    a.label("c_load_storage_result")
    E(push, [3, 4, 5, 6, 7], lr=True)
    E(mov_reg, 4, 0)
    E(mov_reg, 7, 2)                      # actual read result, lost by stock bridge
    E(ldr_sp, 5, 28)                      # sixth argument = read bridge
    E(ldr_imm, 6, 5, 0)
    E(cbz, "load_storage_consumed", 6)
    E(bl, "c_seq_state")
    E(cbz, "load_storage_generic", 0)
    E(ldr_imm, 1, 0, OFF_PROJ_CTRL_PTR)
    E(cbz, "load_storage_generic", 1)
    E(adds_imm8, 1, 0x0C)
    E(cmp_reg, 1, 6)
    E(b_cond, "load_storage_generic", "ne")
    E(str_imm, 6, 0, OFF_LOAD_CLOSE_CALLBACK)
    for offset in (0, 4, 8):
        E(ldr_imm, 1, 4, offset)
        E(str_imm, 1, 0, OFF_LOAD_CLOSE_STATUS + offset)
    E(cbz, "load_storage_close", 7)
    E(movs_imm, 1, 3)
    E(str_imm, 1, 0, OFF_LOAD_CLOSE_STATUS)
    a.label("load_storage_close")
    E(mov_reg, 2, 0)
    E(adr, "c_load_close_result", 1)
    E(adds_imm8, 1, 1)
    E(mov_reg, 0, 4)                      # copied original key for real stock Close
    E(bl, 0x080460C8)
    E(movs_imm, 2, 0)
    E(str_imm, 2, 5, 0)
    E(pop, [3, 4, 5, 6, 7], pc=True)
    a.label("load_storage_generic")
    E(movs_imm, 3, 0)
    E(str_imm, 3, 5, 0)                   # other read clients retain stock ABI/path
    E(mov_reg, 0, 6)
    E(mov_reg, 1, 4)
    E(ldr_imm, 2, 0, 0)
    E(ldr_imm, 7, 2, 0)
    E(raw, bytes.fromhex("b847"))
    a.label("load_storage_consumed")
    E(pop, [3, 4, 5, 6, 7], pc=True)

    a.align(4)
    a.label("c_load_close_result")
    E(push, [4, 5, 6], lr=True)
    E(mov_reg, 6, 2)
    E(ldr_sp, 4, 20)
    a.imm32(0, SEQ_STATE_ADDR)
    E(cmp_reg, 4, 0)
    E(b_cond, "load_close_exit", "ne")
    E(bl, "c_seq_state")
    E(cbz, "load_close_exit", 0)
    E(ldr_imm, 5, 4, OFF_LOAD_CLOSE_CALLBACK)
    E(cbz, "load_close_exit", 5)
    E(ldr_imm, 1, 4, OFF_PROJ_CTRL_PTR)
    E(cbz, "load_close_exit", 1)
    E(adds_imm8, 1, 0x0C)
    E(cmp_reg, 1, 5)
    E(b_cond, "load_close_exit", "ne")
    E(ldr_imm, 3, 4, OFF_LOAD_CLOSE_STATUS + 4)
    E(cmp_imm, 3, 64)
    E(b_cond, "load_close_exit", "hs")
    E(ldrb_imm, 1, 4, OFF_TRANS_STATE)
    E(cbz, "load_close_status", 1)
    E(cmp_imm, 1, 2)
    E(b_cond, "load_close_exit", "ne")
    E(ldrb_imm, 2, 4, OFF_TRANS_TARGET_SLOT)
    E(cmp_reg, 2, 3)
    E(b_cond, "load_close_exit", "ne")
    a.label("load_close_status")
    E(cbz, "load_close_notify", 6)
    E(movs_imm, 1, 3)
    E(str_imm, 1, 4, OFF_LOAD_CLOSE_STATUS)
    a.label("load_close_notify")
    E(movs_imm, 0, 0)
    E(str_imm, 0, 4, OFF_LOAD_CLOSE_CALLBACK)
    E(mov_reg, 0, 5)
    E(mov_reg, 1, 4)
    E(adds_imm8, 1, OFF_LOAD_CLOSE_STATUS)
    E(ldr_imm, 2, 5, 0)                   # original read-bridge application ABI
    E(ldr_imm, 6, 2, 0)
    E(movs_imm, 3, 0)
    E(raw, bytes.fromhex("b047"))          # blx r6
    a.label("load_close_exit")
    E(pop, [4, 5, 6], pc=True)


def emit_proj_timer_or_direct(a: Asm) -> None:
    """Preserve stock asynchronous scheduling and all five ABI arguments."""
    E = a.emit

    a.label("c_proj_timer_or_direct")
    E(b_w, STOCK_TIMER_SCHEDULE)


def emit_project_load_containment(a: Asm) -> None:
    """Temporary NO-GO containment: reject before raw-buffer read or New.

    The stock continuation aliases live patterns. No independently owned staging
    buffer exists yet. This deliberately disables this Load/New continuation;
    it is not a transactional-load implementation or a release-ready feature.
    """
    E = a.emit
    a.label("c_project_load_containment")
    E(push, [4], lr=True)
    E(mov_reg, 4, 0)
    E(bl, "c_seq_state")
    E(cbz, "load_containment_cleanup", 0)
    E(ldr_imm, 1, 0, OFF_PROJ_CTRL_PTR)
    E(cmp_reg, 1, 4)
    E(b_cond, "load_containment_cleanup", "ne")
    E(movs_imm, 1, 0)
    E(strb_imm, 1, 0, OFF_TRANS_STATE)
    # No read has occurred: preserve dirty/taint, mode, slot and Save ownership.
    a.label("load_containment_cleanup")
    E(mov_reg, 0, 4)
    E(pop, [4], lr=True)
    E(b_w, STOCK_LOAD_ERROR_CLEANUP)


def emit_step_routing_cave(a: Asm) -> None:
    """Emits all Phase 1 functions into the code cave."""
    emit_seq_state(a)
    emit_allocator_guard(a)
    emit_grid_press_gate(a)
    emit_resolve_subview(a)
    emit_transform_pad(a)
    emit_step_page_read(a)
    emit_comp_top_leds(a)
    emit_comp_bottom_memcpy(a)
    emit_grid_mode_cleanup(a)
    emit_proj_enter_page(a)
    emit_check_packs_allowed(a)
    emit_page_btn_mode0(a)
    emit_silence_active_samples(a)
    emit_button_mode_hook(a)
    emit_sample_trigger_gate(a)
    emit_metronome_trigger_gate(a)
    emit_sample_dsp_gate(a)
    emit_sample_preview_gate(a)
    emit_proj_led_bank(a)
    emit_proj_pad_gate(a)
    emit_proj_dispatch_guard(a)
    emit_save_btn_gate(a)
    emit_proj_load_complete(a)
    emit_proj_save_complete(a)
    emit_proj_load_cb(a)
    emit_proj_save_cb(a)
    emit_save_storage_result(a)
    emit_load_storage_result(a)
    emit_project_load_containment(a)
    emit_proj_timer_or_direct(a)
    emit_pattern_commit_dirty(a)
    emit_knob_dirty_gate(a)
    emit_save_snapshot(a)
    emit_direct_record_dirty(a)
    emit_record_start_guard(a)
    a.emit(bx_lr)


def emit_record_start_guard(a: Asm) -> None:
    E = a.emit
    a.label("c_record_start_guard")
    E(push, [0, 1, 2, 3, 6], lr=True)
    E(raw, bytes.fromhex("eff31086 72b6"))  # serialize admission + pending creation
    E(bl, "c_seq_state")
    E(cbz, "record_start_reject", 0)
    E(ldrb_imm, 1, 0, OFF_TRANS_STATE)
    E(cbnz, "record_start_reject", 1)
    E(mov_reg, 1, 7)                      # stock track id 16..23
    E(subs_imm8, 1, 16)
    E(cmp_imm, 1, 8)
    E(b_cond, "record_start_reject", "hs")
    E(lsls_imm, 1, 1, 2)
    E(adds_imm8, 1, OFF_RECORDERS)
    E(ldr_sp, 2, 0)
    E(str_reg, 2, 0, 1)
    E(movs_imm, 1, 1)
    E(strb_w, 1, 0, OFF_SAVE_EDITED)
    E(strb_imm, 1, 0, OFF_PROJECT_DIRTY)
    E(pop, [0, 1, 2, 3])
    E(raw, bytes.fromhex("04682568"))      # original vtable -> r4, slot0 -> r5
    E(raw, bytes.fromhex("a847"))          # original blx r5, now inside admission lock
    E(raw, bytes.fromhex("86f31088"))      # restore caller PRIMASK
    E(pop, [6], lr=True)
    E(b, "record_start_return")
    a.label("record_start_reject")
    E(raw, bytes.fromhex("86f31088"))
    E(pop, [0, 1, 2, 3, 6], lr=True)
    E(ldr_imm, 4, 0, 0)
    a.label("record_start_return")
    # Caller still executes BLX r5: point it at a no-op, never call twice.
    E(adr, "record_start_noop", 5)
    E(adds_imm8, 5, 1)
    E(bx_lr)
    a.align(4)
    a.label("record_start_noop")
    E(bx_lr)

    # r0=validated state. Preserve r0 and callee-saved registers; return r1.
    # Stock recorders are allocated once by the boot object graph (36A02).
    a.label("c_records_pending")
    E(push, [0, 4, 5], lr=True)
    E(movs_imm, 4, OFF_RECORDERS)
    a.label("records_scan_track")
    E(ldr_reg, 5, 0, 4)
    E(cbz, "records_next_track", 5)
    # Fail closed on an invalid pointer rather than dereference it.
    a.imm32(2, 0x20000000)
    E(cmp_reg, 5, 2)
    E(b_cond, "records_found", "lo")
    a.imm32(2, SEQ_STATE_ADDR - 0x294)
    E(cmp_reg, 5, 2)
    E(b_cond, "records_found", "hi")
    E(movs_imm, 2, 3)
    E(tst_reg, 5, 2)
    E(b_cond, "records_found", "ne")
    E(ldrb_w, 1, 5, 0x60)
    E(cbnz, "records_found", 1)
    E(adds_imm8, 5, 0x68)                 # pending words for notes 1..139
    E(movs_imm, 3, 139)
    a.label("records_scan_note")
    E(ldr_imm, 1, 5, 0)
    E(movs_imm, 2, 1)
    E(tst_reg, 1, 2)
    E(b_cond, "records_found", "ne")
    E(adds_imm8, 5, 4)
    E(subs_imm8, 3, 1)
    E(b_cond, "records_scan_note", "ne")
    a.label("records_next_track")
    E(adds_imm8, 4, 4)
    E(cmp_imm, 4, OFF_RECORDERS + 32)
    E(b_cond, "records_scan_track", "ne")
    E(movs_imm, 1, 0)
    E(pop, [0, 4, 5], pc=True)
    a.label("records_found")
    E(movs_imm, 1, 1)
    E(pop, [0, 4, 5], pc=True)


def emit_direct_record_dirty(a: Asm) -> None:
    """Dirty at verified direct pattern writes, including nonselected patterns.

    48F02 writes recorded microsteps before note/gate/velocity stores.
    490F0 forms the destination of the nonselected-pattern delay write.
    Neither continuation consumes incoming APSR flags.
    """
    for label, original in (
        ("c_record_note_dirty", "ac707869"),
        ("c_record_delay_dirty", "00ebc702"),
    ):
        E = a.emit
        a.label(label)
        E(push, [0, 1, 2, 3, 4], lr=True)
        E(bl, "c_seq_state")
        E(cbz, label[2:] + "_resume", 0)
        E(movs_imm, 1, 1)
        E(strb_w, 1, 0, OFF_SAVE_EDITED)
        E(strb_imm, 1, 0, OFF_PROJECT_DIRTY)
        a.label(label[2:] + "_resume")
        E(pop, [0, 1, 2, 3, 4], lr=True)
        E(raw, bytes.fromhex(original))
        E(bx_lr)


def emit_pattern_commit_dirty(a: Asm) -> None:
    """Mark ST1/ST2/settings writes, not selection/playback notifications.

    Stock 0x08048208 compares r1 against listener+1C/+20/+24 before
    writing pattern RAM. Preserve all incoming arguments and replay its push.
    """
    E = a.emit
    a.label("c_pattern_commit_dirty")
    E(push, [0, 1, 2, 3, 4], lr=True)
    for offset in (0x1C, 0x20, 0x24):
        E(ldr_imm, 3, 0, offset)
        E(cmp_reg, 1, 3)
        E(b_cond, "pattern_mark_dirty", "eq")
    E(b, "pattern_commit_resume")
    a.label("pattern_mark_dirty")
    E(bl, "c_seq_state")
    E(cbz, "pattern_commit_resume", 0)
    E(movs_imm, 1, 1)
    E(strb_w, 1, 0, OFF_SAVE_EDITED)
    E(strb_imm, 1, 0, OFF_PROJECT_DIRTY)
    a.label("pattern_commit_resume")
    E(pop, [0, 1, 2, 3, 4], lr=True)
    E(raw, bytes.fromhex("2de9f84f"))  # original push.w r3-r11,lr
    E(b_w, 0x0804820C)


def emit_knob_dirty_gate(a: Asm) -> None:
    """Conservative protection for controller knob input, including live macros.

    A nonzero delta marks dirty even if the downstream value is saturated.
    While a project transition is pending, do not forward knob edits.
    """
    E = a.emit
    a.label("c_knob_dirty_gate")
    E(push, [0, 1, 2, 3, 4], lr=True)
    E(bl, "c_seq_state")
    E(cbz, "knob_dirty_resume", 0)
    E(ldrb_imm, 1, 0, OFF_TRANS_STATE)
    E(cbnz, "knob_dirty_block", 1)
    E(ldr_sp, 1, 8)  # original delta
    E(cbz, "knob_dirty_resume", 1)
    E(movs_imm, 1, 1)
    E(strb_w, 1, 0, OFF_SAVE_EDITED)
    E(strb_imm, 1, 0, OFF_PROJECT_DIRTY)
    a.label("knob_dirty_resume")
    E(pop, [0, 1, 2, 3, 4], lr=True)
    E(raw, bytes.fromhex("70b50446"))  # stock push r4-r6,lr; mov r4,r0
    E(b_w, 0x0803DDE4)
    a.label("knob_dirty_block")
    E(pop, [0, 1, 2, 3, 4], pc=True)



def emit_save_snapshot(a: Asm) -> None:
    """Capture Save/Duplicate identity before stock serialization starts."""
    E = a.emit
    a.label("c_save_snapshot")
    E(push, [0, 1, 2, 3, 4], lr=True)
    E(bl, "c_seq_state")
    E(cbz, "save_snapshot_reject", 0)
    E(ldrb_w, 1, 0, OFF_PROJECT_TAINTED)
    E(cbnz, "save_snapshot_reject", 1)
    E(movs_imm, 1, 0)
    E(strb_w, 1, 0, OFF_SAVE_EDITED)
    E(ldr_sp, 1, 4)
    E(strb_w, 1, 0, OFF_SAVE_SLOT)
    E(ldr_sp, 1, 0)
    E(str_imm, 1, 0, OFF_SAVE_OWNER)
    a.label("save_snapshot_resume")
    E(pop, [0, 1, 2, 3, 4], lr=True)
    E(raw, bytes.fromhex("2de9f847"))
    E(b_w, 0x08037ED4)
    a.label("save_snapshot_reject")
    E(pop, [0, 1, 2, 3, 4], lr=True)
    E(movs_imm, 0, 1)
    E(bx_lr)


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
    """Builds the code-cave PatchHunk and all Phase 1 in-place Thumb-2 hook PatchHunks."""
    cave_bytes, labels = arm_code(base)

    resolve_addr = labels["c_resolve_subview"]
    transform_addr = labels["c_transform_pad"]
    page_read_addr = labels["c_step_page_read"]
    comp_top_addr = labels["c_comp_top_leds"]
    comp_bottom_addr = labels["c_comp_bottom_memcpy"]
    cleanup_addr = labels["c_grid_mode_cleanup"]
    proj_enter_addr = labels["c_proj_enter_page"]
    check_packs_addr = labels["c_check_packs_allowed"]
    page_btn_addr = labels["c_page_btn_mode0"]
    button_mode_addr = labels["c_button_mode_hook"]
    sample_gate_addr = labels["c_sample_trigger_gate"]
    metro_gate_addr = labels["c_metronome_trigger_gate"]
    dsp_gate_addr = labels["c_sample_dsp_gate"]
    preview_gate_addr = labels["c_sample_preview_gate"]
    proj_led_addr = labels["c_proj_led_bank"]
    proj_pad_addr = labels["c_proj_pad_gate"]
    proj_dispatch_addr = labels["c_proj_dispatch_guard"]
    save_btn_addr = labels["c_save_btn_gate"]
    load_complete_addr = labels["c_proj_load_complete"]
    save_complete_addr = labels["c_proj_save_complete"]
    load_cb_addr = labels["c_proj_load_cb"]
    timer_direct_addr = labels["c_proj_timer_or_direct"]

    return [
        PatchHunk(
            address=0x08037BD6,
            expected=bytes.fromhex("30b585b0"),
            replacement=b_w(0x08037BD6, labels["c_project_load_containment"]),
            name="project_load_disabled_until_transactional_storage",
        ),
        PatchHunk(
            address=0x080472A8,
            expected=bytes.fromhex("10b5039a"),
            replacement=b_w(0x080472A8, labels["c_load_storage_result"]),
            name="project_load_read_close_result_bridge",
        ),
        PatchHunk(
            address=0x08047304,
            expected=bytes.fromhex("38b50446"),
            replacement=b_w(0x08047304, labels["c_save_storage_result"]),
            name="project_save_storage_error_bridge",
        ),
        PatchHunk(
            address=0x080381D6,
            expected=bytes.fromhex("10380968"),
            replacement=b_w(0x080381D6, labels["c_proj_save_cb"]),
            name="save_error_snapshot_invalidation",
        ),
        PatchHunk(
            address=0x08036ABC,
            expected=bytes.fromhex("04682568"),
            replacement=bl(0x08036ABC, labels["c_record_start_guard"]),
            name="record_start_transition_dirty_guard",
        ),
        PatchHunk(
            address=0x08048F02,
            expected=bytes.fromhex("ac707869"),
            replacement=bl(0x08048F02, labels["c_record_note_dirty"]),
            name="direct_record_note_dirty_hook",
        ),
        PatchHunk(
            address=0x080490F0,
            expected=bytes.fromhex("00ebc702"),
            replacement=bl(0x080490F0, labels["c_record_delay_dirty"]),
            name="direct_record_delay_dirty_hook",
        ),
        PatchHunk(
            address=0x08037ED0,
            expected=bytes.fromhex("2de9f847"),
            replacement=b_w(0x08037ED0, labels["c_save_snapshot"]),
            name="save_snapshot_identity_hook",
        ),
        PatchHunk(
            address=0x0803DDE0,
            expected=bytes.fromhex("70b50446"),
            replacement=b_w(0x0803DDE0, labels["c_knob_dirty_gate"]),
            name="knob_dirty_transition_gate",
        ),
        PatchHunk(
            address=0x08048208,
            expected=bytes.fromhex("2de9f84f"),
            replacement=b_w(0x08048208, labels["c_pattern_commit_dirty"]),
            name="pattern_commit_dirty_hook",
        ),
        PatchHunk(
            address=STOCK_ALLOCATOR_ADDR,
            expected=EXPECTED_ALLOCATOR_ENTRY,
            replacement=b_w(STOCK_ALLOCATOR_ADDR, labels["c_allocator_guard"]),
            name="allocator_reservation_irq_guard",
        ),
        PatchHunk(
            address=HOOK_GRID_PRESS_GATE,
            expected=EXPECTED_GRID_PRESS_GATE,
            replacement=b_w(HOOK_GRID_PRESS_GATE, labels["c_grid_press_gate"]),
            name="grid_press_transition_gate",
        ),
        PatchHunk(
            address=HOOK_GRID_TRACK_CLEANUP,
            expected=EXPECTED_GRID_TRACK_CLEANUP,
            replacement=bl(HOOK_GRID_TRACK_CLEANUP, cleanup_addr),
            name="grid_track_cleanup_hook",
        ),
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
            address=HOOK_PROJ_ENTER_PAGE,
            expected=EXPECTED_PROJ_ENTER_PAGE,
            replacement=bl(HOOK_PROJ_ENTER_PAGE, proj_enter_addr),
            name="proj_enter_page_hook",
        ),
        PatchHunk(
            address=HOOK_PROJ_PAGE_LOCK,
            expected=EXPECTED_PROJ_PAGE_LOCK,
            replacement=REPLACEMENT_PROJ_PAGE_LOCK,
            name="proj_page_lock_patch",
        ),
        PatchHunk(
            address=HOOK_CHECK_PACKS,
            expected=EXPECTED_CHECK_PACKS,
            replacement=bl(HOOK_CHECK_PACKS, check_packs_addr),
            name="check_packs_hook",
        ),
        PatchHunk(
            address=HOOK_PAGE_BTN_MODE0,
            expected=EXPECTED_PAGE_BTN_MODE0,
            replacement=bl(HOOK_PAGE_BTN_MODE0, page_btn_addr),
            name="page_btn_mode0_hook",
        ),
        PatchHunk(
            address=HOOK_BUTTON_MODE,
            expected=EXPECTED_BUTTON_MODE,
            replacement=bl(HOOK_BUTTON_MODE, button_mode_addr),
            name="button_mode_hook",
        ),
        PatchHunk(
            address=HOOK_SAMPLE_TRIGGER_GATE,
            expected=EXPECTED_SAMPLE_TRIGGER_GATE,
            replacement=b_w(HOOK_SAMPLE_TRIGGER_GATE, sample_gate_addr),
            name="sample_trigger_gate_hook",
        ),
        PatchHunk(
            address=HOOK_METRONOME_TRIGGER_GATE,
            expected=EXPECTED_METRONOME_TRIGGER_GATE,
            replacement=b_w(HOOK_METRONOME_TRIGGER_GATE, metro_gate_addr),
            name="metronome_trigger_gate_hook",
        ),
        PatchHunk(
            address=HOOK_SAMPLE_DSP_GATE,
            expected=EXPECTED_SAMPLE_DSP_GATE,
            replacement=bl(HOOK_SAMPLE_DSP_GATE, dsp_gate_addr),
            name="sample_dsp_gate_hook",
        ),
        PatchHunk(
            address=HOOK_SAMPLE_PREVIEW_GATE,
            expected=EXPECTED_SAMPLE_PREVIEW_GATE,
            replacement=b_w(HOOK_SAMPLE_PREVIEW_GATE, preview_gate_addr),
            name="sample_preview_gate_hook",
        ),
        PatchHunk(
            address=HOOK_PROJ_LED_BANK,
            expected=EXPECTED_PROJ_LED_BANK,
            replacement=bl(HOOK_PROJ_LED_BANK, proj_led_addr),
            name="proj_led_bank_hook",
        ),
        PatchHunk(
            address=HOOK_PROJ_PAD_GATE,
            expected=EXPECTED_PROJ_PAD_GATE,
            replacement=bl(HOOK_PROJ_PAD_GATE, proj_pad_addr),
            name="proj_pad_gate_hook",
        ),
        PatchHunk(
            address=HOOK_PROJ_DISPATCH_GUARD,
            expected=EXPECTED_PROJ_DISPATCH_GUARD,
            replacement=bl(HOOK_PROJ_DISPATCH_GUARD, proj_dispatch_addr),
            name="proj_dispatch_guard_hook",
        ),
        PatchHunk(
            address=HOOK_SAVE_BTN_GATE,
            expected=EXPECTED_SAVE_BTN_GATE,
            replacement=bl(HOOK_SAVE_BTN_GATE, save_btn_addr),
            name="save_btn_gate_hook",
        ),
        PatchHunk(
            address=HOOK_PROJ_LOAD_COMPLETE,
            expected=EXPECTED_PROJ_LOAD_COMPLETE,
            replacement=bl(HOOK_PROJ_LOAD_COMPLETE, load_complete_addr),
            name="proj_load_complete_hook",
        ),
        PatchHunk(
            address=HOOK_PROJ_SAVE_COMPLETE,
            expected=EXPECTED_PROJ_SAVE_COMPLETE,
            replacement=bl(HOOK_PROJ_SAVE_COMPLETE, save_complete_addr),
            name="proj_save_complete_hook",
        ),
        PatchHunk(
            address=HOOK_PROJ_LOAD_CB,
            expected=EXPECTED_PROJ_LOAD_CB,
            replacement=b_w(HOOK_PROJ_LOAD_CB, load_cb_addr),
            name="proj_load_cb_hook",
        ),
        PatchHunk(
            address=HOOK_PROJ_TIMER_OR_DIRECT,
            expected=EXPECTED_PROJ_TIMER_OR_DIRECT,
            replacement=bl(HOOK_PROJ_TIMER_OR_DIRECT, timer_direct_addr),
            name="proj_timer_or_direct_hook",
        ),
        PatchHunk(
            address=base,
            expected=b"\xFF" * len(cave_bytes),
            replacement=cave_bytes,
            name="seq_step_routing_code_cave",
        ),
    ]


build_phase1_patches = build_step_routing_patches
build_seq_patches = build_step_routing_patches
