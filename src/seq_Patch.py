"""Shared-project 32-Step MIDI Sequencer: UI/sample and bounded USB RX hooks.

No project I/O hooks. USB polling yields after one received buffer per port so
the main loop can service output and other tasks before the next input buffer.

Retains upstream MIT License for the `c_rst` safe bump-allocator reservation pattern
from CIRCUIT-REMIX (tools/rhstate.py, Copyright (c) 2026 Ghillermo).

Active state: +00 magic, +04 seq_enabled, +08 grid_ptr, +14 ctrl_ptr.
MIDI receiver ownership: +68 four boot-lifetime receiver pointers, +78 sticky
context-overflow fault, +79 nested receiver-call count. No note mask is copied.
Output FIFO overflow latches +7A; mode switches stay closed until a fresh boot.
The 256-byte heap reservation/address is retained. Other offsets below are
legacy compatibility constants for historical tests/tools. The recovery profile
uses +64 for sticky failed-Load taint;mode admission rejects it. No bank/dirty
state is changed by the mode shortcut.
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
OFF_PROJECT_RECOVERY_HELD = 0x60
OFF_PROJECT_TAINTED = 0x64
OFF_PROJECT_RECOVERY_STAGE = 0x65
OFF_MIDI_RECEIVERS = 0x68
MIDI_RECEIVER_CAPACITY = 4
OFF_MIDI_CONTEXT_FAULT = 0x78
OFF_MIDI_ACTIVE_CALLS = 0x79
OFF_MIDI_TX_FAULT = 0x7A
HOOK_MIDI_TX_OVERFLOW = 0x08040228
EXPECTED_MIDI_TX_OVERFLOW = bytes.fromhex('e3f732fa')  # last BLEQ in ITEEE NE ->23690
STOCK_DIAGNOSTIC_NOOP = 0x08023690

# Bound USB RX work per main-loop pass. The stock main loop services output
# before input; an unlimited USB drain can fill its64-message output FIFO.
HOOK_USB_RX_YIELD = 0x08029B62
EXPECTED_USB_RX_YIELD = bytes.fromhex('cfda4068')  # bge29B04; ldr r0,[r0,#4]
STOCK_USB_RX_NEXT_PORT = 0x08029AF2
STOCK_USB_RX_PACKET_CONT = 0x08029B66

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
HOOK_MIDI_RECEIVE_ON = 0x0803F5A8
EXPECTED_MIDI_RECEIVE_ON = bytes.fromhex("f8b51d00")  # push r3-r7,lr; movs r5,r3
STOCK_MIDI_RECEIVE_ON_CONT = 0x0803F5AC

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
    "load_close_status": (OFF_LOAD_CLOSE_STATUS, 8),
    "project_recovery_held": (OFF_PROJECT_RECOVERY_HELD, 4),
    "project_tainted": (OFF_PROJECT_TAINTED, 1),
    "project_recovery_stage": (OFF_PROJECT_RECOVERY_STAGE, 1),
    "midi_receivers": (OFF_MIDI_RECEIVERS, 4 * MIDI_RECEIVER_CAPACITY),
    "midi_context_fault": (OFF_MIDI_CONTEXT_FAULT, 1),
    "midi_active_calls": (OFF_MIDI_ACTIVE_CALLS, 1),
    "midi_tx_fault": (OFF_MIDI_TX_FAULT, 1),
}


def check_layout() -> None:
    """Verifies that all state block fields are non-overlapping and fit within 256 bytes."""
    used = sorted(OFF.values())
    for (a, n), (b2, _) in zip(used, used[1:]):
        assert a + n <= b2, f"seq_Patch.OFF overlaps at offset {b2:#x}"
    assert used[-1][0] + used[-1][1] <= SEQ_STATE_SIZE, "seq_Patch.OFF exceeds SEQ_STATE_SIZE"


def emit_seq_state(a: Asm, extra_reserved_bytes: int = 0, extra_state_magic: int = 0) -> None:
    """Emits the `c_seq_state` Thumb-2 function into the given assembler instance."""
    check_layout()
    E = a.emit
    if extra_reserved_bytes < 0 or extra_reserved_bytes % 4 or extra_reserved_bytes > 0x1000:
        raise ValueError('Extra checked state reservation must be word-aligned and at most4KiB')
    reserve_limit = SEQ_STATE_ADDR - extra_reserved_bytes

    def imm32(rd: int, v: int) -> None:
        E(movw, rd, v & 0xFFFF)
        E(movt, rd, (v >> 16) & 0xFFFF)

    a.label("c_seq_state")
    E(push, [4], lr=True)
    E(raw, bytes.fromhex("eff31084 72b6"))  # mrs r4,primask; cpsid i
    imm32(0, SEQ_STATE_ADDR)                # r0 = 0x2004F660
    imm32(3, HEAP_LIMIT_PTR)                # r3 = 0x20002B54
    if extra_reserved_bytes:
        imm32(2, reserve_limit)
    # Validate current on EVERY path, including a damaged reserved block.
    E(ldr_imm, 1, 3, 4)
    E(cmp_reg, 1, 2 if extra_reserved_bytes else 0)
    E(b_cond, "seq_off", "hi")
    E(ldr_imm, 1, 3, 0)                     # r1 = [0x20002B54] (current heap limit)
    E(cmp_reg, 1, 2 if extra_reserved_bytes else 0) # already reserved?
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
    if extra_reserved_bytes:
        imm32(2, reserve_limit)
    E(cmp_reg, 1, 2 if extra_reserved_bytes else 0)
    E(b_cond, "seq_off", "hi")              # current > 0x2004F660 -> stay off (r0 = 0)
    E(str_imm, 2 if extra_reserved_bytes else 0, 3, 0)

    a.label("seq_init")
    if extra_reserved_bytes:
        imm32(0, reserve_limit)
    E(movs_imm, 1, 0)                       # r1 = 0
    E(movw, 2, SEQ_STATE_SIZE + extra_reserved_bytes)
    a.label("seq_clr")                      # zeroes +252 down to +0 (all 256 bytes)
    E(subs_imm8, 2, 4)
    E(str_reg, 1, 0, 2)                     # str r1, [r0, r2]
    E(cmp_imm, 2, 0)
    E(b_cond, "seq_clr", "ne")
    if extra_reserved_bytes:
        if extra_state_magic:
            imm32(2, extra_state_magic)
            E(str_imm, 2, 0)
        imm32(0, SEQ_STATE_ADDR)
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


def emit_allocator_guard(a: Asm, fail_stop: bool = False) -> None:
    """Serialize the stock bump allocator with lazy state reservation.
    The legacy profile returns the stock -1 failure value. Recovery uses a
    terminal fault: native new tests only for zero and can dereference -1.
    No generic NULL return can make all existing native callers recover safely.
    """
    E = a.emit
    a.label("c_allocator_guard")
    E(push, [4, 5], lr=True)
    E(sub_sp_imm, 4)                        # depth % 8 == 0
    E(mov_reg, 5, 0)                        # r5 = size requested
    E(raw, bytes.fromhex("eff31084 72b6"))  # mrs r4,primask; cpsid i
    E(bl, "c_seq_state")                    # ensure reservation
    if fail_stop:
        E(cmp_imm, 0, 0)
        E(b_cond, "alloc_oom", "eq")        # invalid/overlapping reservation is fatal too
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
    if fail_stop:
        # Terminal OOM, not an ordinary critical section. Do not return a
        # fabricated pointer to unchecked constructors or allow IRQs to observe
        # their partly initialized objects. No reset, MMIO, flash or RAM writes.
        E(raw, bytes.fromhex('72b6'))        # cpsid i
        a.label("alloc_fatal")
        E(b, "alloc_fatal")
    else:
        E(movs_imm, 0, 0)
        E(subs_imm8, 0, 1)                  # legacy stock sentinel
        E(b, "alloc_exit")


def emit_resolve_subview(a: Asm) -> None:
    """Emits `c_resolve_subview(r0=grid, r1=pad)` into `a`."""
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
    """Clear step owners while preserving stock non-step release ownership."""
    E = a.emit

    a.label("c_grid_mode_cleanup")
    E(push, [0, 1, 2, 3, 4, 5, 6, 7, 8], lr=True)  # 40B
    E(mov_reg, 5, 0)                            # r5 = grid at either call site
    E(movs_imm, 0, 0)
    E(mov_reg, 8, 0)                            # physical pads owned by Step View
    E(cmp_imm, 5, 0)
    E(b_cond_w, "cleanup_done", "eq")

    # r2 is the OLD grid mode at both native hook sites. Stock4DC50 routes
    # top pads to Step View only in modes0/1/2/3/5/6. Mode0 Sequencer adds
    # bottom pads. Other physical ownership belongs to stock subviews and
    # must survive when4DAAC retains the same subview (e.g.Note1<->7).
    E(cmp_imm, 2, 3)
    E(b_cond, "cleanup_top_steps", "ls")
    E(cmp_imm, 2, 5)
    E(b_cond, "cleanup_mask_ready", "lo")
    E(cmp_imm, 2, 6)
    E(b_cond, "cleanup_mask_ready", "hi")
    a.label("cleanup_top_steps")
    E(movs_imm, 0, 1)
    E(lsls_imm, 0, 0, 16)
    E(subs_imm8, 0, 1)
    E(mov_reg, 8, 0)                            # top16 physical step pads
    E(cmp_imm, 2, 0)
    E(b_cond, "cleanup_mask_ready", "ne")
    E(bl, "c_seq_state")
    E(cbz, "cleanup_mask_ready", 0)
    E(ldrb_imm, 1, 0, OFF_SEQ_ENABLED)
    E(cmp_imm, 1, 1)
    E(b_cond, "cleanup_mask_ready", "ne")
    E(movs_imm, 0, 0)
    E(raw, bytes.fromhex("c043"))               # mvns r0,r0 -> all32 step pads
    E(mov_reg, 8, 0)
    a.label("cleanup_mask_ready")

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
    # Native4DAAC has already released changed stock subviews. Retain its
    # remaining physical note/sample owners;only our cleared step owners
    # lose their physical bits. Otherwise4D7DE would skip their real release.
    E(ldr_w, 0, 5, 0x228)
    E(mov_reg, 1, 8)
    E(bics_reg, 0, 1)
    E(str_w, 0, 5, 0x228)
    E(movs_imm, 0, 0)                           # retain helper's old return value
    E(pop, [4, 5, 6, 7, 8], lr=True)
    E(bx_lr)


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
    """Shift + Sample Rec changes only the runtime mode of the current project."""
    E = a.emit
    a.label("c_button_mode_hook")
    E(push, [4, 5, 6, 7], lr=True)
    E(sub_sp_imm, 4)  # 24B; r4=controller, r5=stock button id
    E(mov_reg, 0, 4)
    E(adds_imm8, 0, 0xA0)
    E(mov_reg, 1, 5)
    E(bl, STOCK_CTRL_BUTTON_PRE)
    E(cmp_imm, 0, 0)
    E(b_cond_w, "btn_mode_handled", "ne")
    E(cmp_imm, 5, 18)
    E(b_cond_w, "btn_mode_orig", "ne")
    E(ldr_imm, 0, 4, 0x0C)
    E(cbz, "btn_mode_handled", 0)
    E(movs_imm, 1, 0)
    E(bl, STOCK_READ_STORE_WORD)
    E(ldrb_imm, 0, 0, 0)
    E(cbz, "btn_mode_orig", 0)
    E(bl, "c_seq_state")
    E(cbz, "btn_mode_handled", 0)
    E(mov_reg, 6, 0)
    # Serialize the final stopped/ownership check and single-byte mode commit.
    # Never call voice locks or grid notifications while interrupts are masked.
    E(raw, bytes.fromhex("eff31087 72b6"))  # mrs r7,primask; cpsid i
    E(cmp_imm, 7, 0)
    E(b_cond_w, "btn_mode_unlock", "ne")  # UI transition cannot run voice locks from masked callers
    E(mov_reg, 0, 4)
    E(bl, "c_mode_can_switch")
    E(cbz, "btn_mode_unlock", 0)
    E(ldr_imm, 0, 4, 0x3C)
    E(str_imm, 0, 6, OFF_GRID_PTR)
    E(str_imm, 4, 6, OFF_CTRL_PTR)
    E(ldrb_imm, 1, 6, OFF_SEQ_ENABLED)
    E(movs_imm, 2, 1)
    E(eors_reg, 1, 2)
    E(strb_imm, 1, 6, OFF_SEQ_ENABLED)
    E(raw, bytes.fromhex("87f31088"))  # restore caller PRIMASK
    E(cmp_imm, 1, 1)
    E(b_cond, "btn_mode_handled", "ne")
    E(bl, "c_silence_active_samples")
    E(b, "btn_mode_handled")
    a.label("btn_mode_unlock")
    E(raw, bytes.fromhex("87f31088"))
    a.label("btn_mode_handled")
    E(movs_imm, 0, 1)
    E(b, "btn_mode_exit")
    a.label("btn_mode_orig")
    E(movs_imm, 0, 0)
    a.label("btn_mode_exit")
    E(add_sp_imm, 4)
    E(pop, [4, 5, 6, 7], pc=True)


def emit_mode_can_switch(a: Asm) -> None:
    """r0=controller; return1 only for stopped, idle, unheld synthetic/stock graph.

    ctrl+18 is the store also passed to play-view+14 (3D3C0/501E8).
    Play-view50270..502A0 reads word0 to select start versus stop.
    ctrl+1C0..1DC ownership stores are cleared by stock3E448..3E478.
    Full external MIDI/scheduler integration remains a separate release gate.
    """
    E = a.emit
    a.label("c_mode_can_switch")
    E(push, [4, 5, 6], lr=True)
    E(mov_reg, 4, 0)
    E(bl, "c_midi_inputs_idle")
    E(cmp_imm, 0, 0)
    E(b_cond_w, "mode_check_reject", "eq")
    E(ldr_imm, 0, 4, 0x18)
    E(cmp_imm, 0, 0)
    E(b_cond_w, "mode_check_reject", "eq")
    E(movs_imm, 1, 0)
    E(bl, STOCK_READ_STORE_WORD)
    E(ldrb_imm, 1, 0, 0)
    E(cmp_imm, 1, 0)
    E(b_cond_w, "mode_check_reject", "ne")
    # Projects+24 is the shared readiness word: native4F0A4/4ED80 test bit3.
    # Its other bits are NOT project I/O flags (native idle boot reads0x0E).
    # Actual queued/running project I/O is checked below via phase word1.
    E(ldr_imm, 5, 4, 0x50)
    E(cmp_imm, 5, 0)
    E(b_cond_w, "mode_check_reject", "eq")
    E(ldr_imm, 0, 5, 0x24)
    E(cmp_imm, 0, 0)
    E(b_cond_w, "mode_check_reject", "eq")
    E(movs_imm, 1, 0)
    E(bl, STOCK_READ_STORE_WORD)
    E(ldrb_imm, 1, 0, 0)
    E(movs_imm, 2, 8)
    E(ands_reg, 1, 2)
    E(cmp_imm, 1, 8)
    E(b_cond_w, "mode_check_reject", "ne")
    E(ldr_imm, 0, 5, 0x28)
    E(cmp_imm, 0, 0)
    E(b_cond_w, "mode_check_reject", "eq")
    E(movs_imm, 1, 1)
    E(bl, STOCK_READ_STORE_WORD)
    E(ldrb_imm, 1, 0, 0)
    E(cmp_imm, 1, 0)
    E(b_cond_w, "mode_check_reject", "ne")
    # Refuse held controller notes on any track; never synthesize Note Off.
    E(mov_reg, 5, 4)
    E(adds_imm8, 5, 0xE0)
    E(adds_imm8, 5, 0xE0)  # ctrl+1C0
    E(movs_imm, 6, 8)
    a.label("mode_check_notes")
    E(ldr_imm, 0, 5, 0)
    E(cmp_imm, 0, 0)
    E(b_cond_w, "mode_check_reject", "eq")
    E(movs_imm, 1, 0)
    E(bl, STOCK_READ_STORE_WORD)
    E(ldr_imm, 1, 0, 0)
    E(cmp_imm, 1, 0)
    E(b_cond_w, "mode_check_reject", "ne")
    E(adds_imm8, 5, 4)
    E(subs_imm8, 6, 1)
    E(b_cond, "mode_check_notes", "ne")
    E(ldr_imm, 5, 4, 0x3C)
    E(cmp_imm, 5, 0)
    E(b_cond_w, "mode_check_reject", "eq")
    E(ldr_w, 1, 5, 0x228)
    E(cmp_imm, 1, 0)
    E(b_cond_w, "mode_check_reject", "ne")
    E(movs_imm, 6, 0)
    a.label("mode_check_steps")
    E(mov_reg, 0, 6)
    E(adds_imm8, 0, 0x74)
    E(ldr_reg, 0, 5, 0)
    E(cbz, "mode_check_next_step", 0)
    # B8 is short-click eligibility, not live ownership: native5CD32 leaves
    # it latched after a completed release; timer6 is then canceled5CD66.
    # Native5CE48 only removes C0 bits from B8 and cannot create a held pad.
    # Keep this history intact; C0 and per-step bit3 are the live owners.
    E(ldr_w, 1, 0, 0xC0)
    E(cmp_imm, 1, 0)
    E(b_cond_w, "mode_check_reject", "ne")
    # Reject stale per-step held bit3 too, before changing presentation.
    E(adds_imm8, 0, 0x74)
    E(movs_imm, 3, 32)
    a.label("mode_check_held_bit")
    E(ldrh_imm, 1, 0, 0)
    E(movs_imm, 2, 8)
    E(tst_reg, 1, 2)
    E(b_cond, "mode_check_reject", "ne")
    E(adds_imm8, 0, 2)
    E(subs_imm8, 3, 1)
    E(b_cond, "mode_check_held_bit", "ne")
    a.label("mode_check_next_step")
    E(adds_imm8, 6, 4)
    E(cmp_imm, 6, 32)
    E(b_cond, "mode_check_steps", "ne")
    E(movs_imm, 0, 1)
    E(pop, [4, 5, 6], pc=True)
    a.label("mode_check_reject")
    E(movs_imm, 0, 0)
    E(pop, [4, 5, 6], pc=True)


def emit_midi_receive_ownership(a: Asm) -> None:
    """Observe stock receiver ownership without changing notes or Note Off.

    Receiver+74 holds eight 20-byte masks, set/cleared by stock3F5A8/3F660.
    Keep up to four receiver addresses, never replace an occupied slot. More
    contexts or invalid pointers latch a fail-closed mode-switch fault. The
    stock callback itself runs outside the observer's IRQ-masked bookkeeping.
    """
    E = a.emit
    a.label("c_midi_receive_on")
    E(push, [0, 1, 2, 3, 4], lr=True)  # 24B; arguments then stock results share slots
    E(bl, "c_midi_observe_begin")
    E(mov_reg, 4, 0)  # validated state or0, preserved by stock callback
    for reg in range(4):
        E(ldr_sp, reg, reg * 4)
    E(bl, "c_midi_receive_on_stock")
    # Preserve the exact stock r0-r3 results too. AAPCS permits volatile
    # clobbering, but matching stock avoids assumptions about indirect callers.
    for reg in range(4):
        E(str_sp, reg, reg * 4)
    E(mov_reg, 0, 4)
    E(bl, "c_midi_observe_end")
    E(pop, [0, 1, 2, 3])
    E(pop, [4], pc=True)

    # MOVS must be replayed AFTER bookkeeping; stock branches on its flags.
    a.label("c_midi_receive_on_stock")
    E(raw, EXPECTED_MIDI_RECEIVE_ON)
    E(b_w, STOCK_MIDI_RECEIVE_ON_CONT)

    a.label("c_midi_observe_begin")
    E(push, [4, 5, 6], lr=True)
    E(mov_reg, 5, 0)
    E(bl, "c_seq_state")
    E(cbz, "midi_begin_exit", 0)
    E(mov_reg, 4, 0)
    E(raw, bytes.fromhex("eff31086 72b6"))  # mrs r6,primask; cpsid i
    E(ldrb_w, 1, 4, OFF_MIDI_ACTIVE_CALLS)
    E(cmp_imm, 1, 255)
    E(b_cond, "midi_begin_fault", "eq")
    E(adds_imm8, 1, 1)
    E(strb_w, 1, 4, OFF_MIDI_ACTIVE_CALLS)
    a.imm32(2, 0x20000000)
    E(cmp_reg, 5, 2)
    E(b_cond, "midi_begin_fault", "lo")
    a.imm32(2, SEQ_STATE_ADDR - 0x114)
    E(cmp_reg, 5, 2)
    E(b_cond, "midi_begin_fault", "hi")
    E(movs_imm, 2, 3)
    E(tst_reg, 5, 2)
    E(b_cond, "midi_begin_fault", "ne")
    E(movs_imm, 1, OFF_MIDI_RECEIVERS)
    # First search all slots for a match, then all slots for a vacancy. A
    # zero entry cannot hide a matching pointer later in a damaged table.
    a.label("midi_begin_find")
    E(ldr_reg, 2, 4, 1)
    E(cmp_reg, 2, 5)
    E(b_cond, "midi_begin_unlock", "eq")
    E(adds_imm8, 1, 4)
    E(cmp_imm, 1, OFF_MIDI_RECEIVERS + 4 * MIDI_RECEIVER_CAPACITY)
    E(b_cond, "midi_begin_find", "ne")
    E(movs_imm, 1, OFF_MIDI_RECEIVERS)
    a.label("midi_begin_vacancy")
    E(ldr_reg, 2, 4, 1)
    E(cbz, "midi_begin_store", 2)
    E(adds_imm8, 1, 4)
    E(cmp_imm, 1, OFF_MIDI_RECEIVERS + 4 * MIDI_RECEIVER_CAPACITY)
    E(b_cond, "midi_begin_vacancy", "ne")
    a.label("midi_begin_fault")
    E(movs_imm, 1, 1)
    E(strb_w, 1, 4, OFF_MIDI_CONTEXT_FAULT)
    E(b, "midi_begin_unlock")
    a.label("midi_begin_store")
    E(str_reg, 5, 4, 1)
    a.label("midi_begin_unlock")
    E(raw, bytes.fromhex("86f31088"))
    E(mov_reg, 0, 4)
    a.label("midi_begin_exit")
    E(pop, [4, 5, 6], pc=True)

    a.label("c_midi_observe_end")
    E(push, [4, 5], lr=True)
    E(sub_sp_imm, 4)
    E(mov_reg, 4, 0)
    E(bl, "c_seq_state")
    E(cbz, "midi_end_exit", 0)
    E(cmp_reg, 0, 4)
    E(b_cond, "midi_end_exit", "ne")
    E(raw, bytes.fromhex("eff31085 72b6"))
    E(ldrb_w, 1, 4, OFF_MIDI_ACTIVE_CALLS)
    E(cbz, "midi_end_unlock", 1)
    E(subs_imm8, 1, 1)
    E(strb_w, 1, 4, OFF_MIDI_ACTIVE_CALLS)
    a.label("midi_end_unlock")
    E(raw, bytes.fromhex("85f31088"))
    a.label("midi_end_exit")
    E(add_sp_imm, 4)
    E(pop, [4, 5], pc=True)

    a.label("c_midi_inputs_idle")
    E(push, [4, 5, 6], lr=True)
    E(bl, "c_seq_state")
    E(cbz, "midi_idle_exit", 0)
    E(mov_reg, 4, 0)
    E(ldrb_w, 1, 4, OFF_MIDI_ACTIVE_CALLS)
    E(ldrb_w, 2, 4, OFF_MIDI_CONTEXT_FAULT)
    E(orrs_reg, 1, 2)
    E(ldrb_w, 2, 4, OFF_MIDI_TX_FAULT)
    E(orrs_reg, 1, 2)
    E(ldrb_w, 2, 4, OFF_PROJECT_TAINTED)
    E(orrs_reg, 1, 2)
    E(ldr_imm, 2, 4, OFF_PROJECT_RECOVERY_HELD)
    E(orrs_reg, 1, 2)
    E(cbnz, "midi_idle_reject", 1)
    E(movs_imm, 5, OFF_MIDI_RECEIVERS)
    a.label("midi_idle_receiver")
    E(ldr_reg, 6, 4, 5)
    E(cbz, "midi_idle_next", 6)
    a.imm32(2, 0x20000000)
    E(cmp_reg, 6, 2)
    E(b_cond, "midi_idle_reject", "lo")
    a.imm32(2, SEQ_STATE_ADDR - 0x114)
    E(cmp_reg, 6, 2)
    E(b_cond, "midi_idle_reject", "hi")
    E(movs_imm, 2, 3)
    E(tst_reg, 6, 2)
    E(b_cond, "midi_idle_reject", "ne")
    E(adds_imm8, 6, 0x74)
    E(movs_imm, 3, 40)
    a.label("midi_idle_word")
    E(ldr_imm, 1, 6, 0)
    E(cbnz, "midi_idle_reject", 1)
    E(adds_imm8, 6, 4)
    E(subs_imm8, 3, 1)
    E(b_cond, "midi_idle_word", "ne")
    a.label("midi_idle_next")
    E(adds_imm8, 5, 4)
    E(cmp_imm, 5, OFF_MIDI_RECEIVERS + 4 * MIDI_RECEIVER_CAPACITY)
    E(b_cond, "midi_idle_receiver", "ne")
    E(movs_imm, 0, 1)
    E(b, "midi_idle_exit")
    a.label("midi_idle_reject")
    E(movs_imm, 0, 0)
    a.label("midi_idle_exit")
    E(pop, [4, 5, 6], pc=True)


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

    a.label("preview_trigger_orig")
    E(pop, [0, 1, 2, 3, 4], lr=True)
    E(b_w, STOCK_SAMPLE_PREVIEW_CONT)        # 0x080407F0

    a.label("preview_trigger_mute")
    E(pop, [0, 1, 2, 3, 4], lr=True)
    E(movs_imm, 0, 0)
    E(bx_lr)


def emit_usb_rx_yield(a: Asm) -> None:
    """Yield after one received USB buffer/port; keep remaining bytes queued.

    Entry uses CMP r5,r1 flags from29B60. No call, stack/RAM write or flag-
    changing instruction. LT replays the stolen LDR; GE advances to the next
    port rather than reading another buffer from the same port this pass.
    """
    a.label('c_usb_rx_yield')
    a.emit(b_cond, 'usb_rx_next_port', 'ge')
    a.emit(ldr_imm, 0, 0, 4)
    a.emit(b_w, STOCK_USB_RX_PACKET_CONT)
    a.label('usb_rx_next_port')
    a.emit(b_w, STOCK_USB_RX_NEXT_PORT)


def emit_midi_tx_overflow(a: Asm) -> None:
    """Latch a mode-admission fault only on the actual enqueue-loss branch.

    Stock23690 is a no-op. Preserve all input registers/APSR, restore caller
    PRIMASK through c_seq_state, then tail-call that unchanged no-op once.
    No retry, queue mutation or claim of recovering the lost message.
    """
    a.label('c_midi_tx_overflow')
    a.emit(push, [0, 1, 2, 3, 4, 5, 12], lr=True)  #32B, includes volatile r12
    a.emit(raw, bytes.fromhex('eff30084'))  # mrs r4,apsr
    a.emit(bl, 'c_seq_state')
    a.emit(cbz, 'midi_tx_fault_exit', 0)
    a.emit(movs_imm, 1, 1)
    a.emit(strb_w, 1, 0, OFF_MIDI_TX_FAULT)
    a.label('midi_tx_fault_exit')
    a.emit(raw, bytes.fromhex('84f3008c'))  # msr apsr_nzcvqg,r4
    a.emit(pop, [0, 1, 2, 3, 4, 5, 12], lr=True)
    a.emit(b_w, STOCK_DIAGNOSTIC_NOOP)


def emit_step_routing_cave(a: Asm, extra_reserved_bytes: int = 0, extra_state_magic: int = 0, allocator_fail_stop: bool = False) -> None:
    """Emits all Phase 1 functions into the code cave."""
    emit_seq_state(a, extra_reserved_bytes, extra_state_magic)
    emit_allocator_guard(a, allocator_fail_stop)
    emit_resolve_subview(a)
    emit_transform_pad(a)
    emit_step_page_read(a)
    emit_comp_top_leds(a)
    emit_comp_bottom_memcpy(a)
    emit_grid_mode_cleanup(a)
    emit_page_btn_mode0(a)
    emit_silence_active_samples(a)
    emit_button_mode_hook(a)
    emit_mode_can_switch(a)
    emit_midi_receive_ownership(a)
    emit_sample_trigger_gate(a)
    emit_metronome_trigger_gate(a)
    emit_sample_dsp_gate(a)
    emit_sample_preview_gate(a)
    emit_usb_rx_yield(a)
    emit_midi_tx_overflow(a)
    a.emit(bx_lr)


def arm_code(base: int = CODE_CAVE_BASE, *, extra_reserved_bytes: int = 0, extra_state_magic: int = 0, allocator_fail_stop: bool = False) -> tuple[bytes, dict[str, int]]:
    """Assembles the Sequencer Mode code cave at `base` and returns `(code_bytes, labels)`."""
    a = Asm(base)
    emit_step_routing_cave(a, extra_reserved_bytes, extra_state_magic, allocator_fail_stop)
    return a.assemble()


def c_seq_state(base: int = CODE_CAVE_BASE) -> bytes:
    """Produces the Thumb-2 machine code bytes for the code cave starting with `c_seq_state()` at `base`."""
    code, _ = arm_code(base)
    return code


def build_step_routing_patches(base: int = CODE_CAVE_BASE, *, extra_reserved_bytes: int = 0, extra_state_magic: int = 0, allocator_fail_stop: bool = False) -> list[PatchHunk]:
    """Builds the code-cave PatchHunk and all Phase 1 in-place Thumb-2 hook PatchHunks."""
    cave_bytes, labels = arm_code(base, extra_reserved_bytes=extra_reserved_bytes, extra_state_magic=extra_state_magic, allocator_fail_stop=allocator_fail_stop)


    return [
        PatchHunk(STOCK_ALLOCATOR_ADDR, EXPECTED_ALLOCATOR_ENTRY,
                  b_w(STOCK_ALLOCATOR_ADDR, labels["c_allocator_guard"]), "c_allocator_guard_hook"),
        PatchHunk(HOOK_GRID_TRACK_CLEANUP, EXPECTED_GRID_TRACK_CLEANUP,
                  bl(HOOK_GRID_TRACK_CLEANUP, labels["c_grid_mode_cleanup"]), "c_grid_mode_cleanup_hook"),
        PatchHunk(HOOK_GRID_MODE_CLEANUP, EXPECTED_GRID_MODE_CLEANUP,
                  bl(HOOK_GRID_MODE_CLEANUP, labels["c_grid_mode_cleanup"]), "c_grid_mode_cleanup_hook"),
        PatchHunk(HOOK_GRID_PRESS_RESOLVE, EXPECTED_GRID_PRESS_RESOLVE,
                  bl(HOOK_GRID_PRESS_RESOLVE, labels["c_resolve_subview"]), "c_resolve_subview_hook"),
        PatchHunk(HOOK_GRID_PRESS_TRANSFORM, EXPECTED_GRID_PRESS_TRANSFORM,
                  bl(HOOK_GRID_PRESS_TRANSFORM, labels["c_transform_pad"]), "c_transform_pad_hook"),
        PatchHunk(HOOK_GRID_RELEASE_RESOLVE, EXPECTED_GRID_RELEASE_RESOLVE,
                  bl(HOOK_GRID_RELEASE_RESOLVE, labels["c_resolve_subview"]), "c_resolve_subview_hook"),
        PatchHunk(HOOK_GRID_RELEASE_TRANSFORM, EXPECTED_GRID_RELEASE_TRANSFORM,
                  bl(HOOK_GRID_RELEASE_TRANSFORM, labels["c_transform_pad"]), "c_transform_pad_hook"),
        PatchHunk(HOOK_STEP_PRESS_PAGE, EXPECTED_STEP_PRESS_PAGE,
                  bl(HOOK_STEP_PRESS_PAGE, labels["c_step_page_read"]), "c_step_page_read_hook"),
        PatchHunk(HOOK_STEP_RELEASE_PAGE, EXPECTED_STEP_RELEASE_PAGE,
                  bl(HOOK_STEP_RELEASE_PAGE, labels["c_step_page_read"]), "c_step_page_read_hook"),
        PatchHunk(HOOK_COMP_TOP_LEDS, EXPECTED_COMP_TOP_LEDS,
                  bl(HOOK_COMP_TOP_LEDS, labels["c_comp_top_leds"]), "c_comp_top_leds_hook"),
        PatchHunk(HOOK_COMP_BOTTOM_MEMCPY, EXPECTED_COMP_BOTTOM_MEMCPY,
                  bl(HOOK_COMP_BOTTOM_MEMCPY, labels["c_comp_bottom_memcpy"]), "c_comp_bottom_memcpy_hook"),
        PatchHunk(HOOK_PAGE_BTN_MODE0, EXPECTED_PAGE_BTN_MODE0,
                  bl(HOOK_PAGE_BTN_MODE0, labels["c_page_btn_mode0"]), "c_page_btn_mode0_hook"),
        PatchHunk(HOOK_BUTTON_MODE, EXPECTED_BUTTON_MODE,
                  bl(HOOK_BUTTON_MODE, labels["c_button_mode_hook"]), "c_button_mode_hook_hook"),
        PatchHunk(HOOK_MIDI_RECEIVE_ON, EXPECTED_MIDI_RECEIVE_ON,
                  b_w(HOOK_MIDI_RECEIVE_ON, labels["c_midi_receive_on"]), "midi_receiver_ownership_observer"),
        PatchHunk(HOOK_USB_RX_YIELD, EXPECTED_USB_RX_YIELD,
                  b_w(HOOK_USB_RX_YIELD, labels['c_usb_rx_yield']), 'usb_rx_one_buffer_per_port'),
        PatchHunk(HOOK_MIDI_TX_OVERFLOW, EXPECTED_MIDI_TX_OVERFLOW,
                  bl(HOOK_MIDI_TX_OVERFLOW, labels['c_midi_tx_overflow']), 'midi_tx_overflow_mode_fault'),
        PatchHunk(HOOK_SAMPLE_TRIGGER_GATE, EXPECTED_SAMPLE_TRIGGER_GATE,
                  b_w(HOOK_SAMPLE_TRIGGER_GATE, labels["c_sample_trigger_gate"]), "c_sample_trigger_gate_hook"),
        PatchHunk(HOOK_METRONOME_TRIGGER_GATE, EXPECTED_METRONOME_TRIGGER_GATE,
                  b_w(HOOK_METRONOME_TRIGGER_GATE, labels["c_metronome_trigger_gate"]), "c_metronome_trigger_gate_hook"),
        PatchHunk(HOOK_SAMPLE_DSP_GATE, EXPECTED_SAMPLE_DSP_GATE,
                  bl(HOOK_SAMPLE_DSP_GATE, labels["c_sample_dsp_gate"]), "c_sample_dsp_gate_hook"),
        PatchHunk(HOOK_SAMPLE_PREVIEW_GATE, EXPECTED_SAMPLE_PREVIEW_GATE,
                  b_w(HOOK_SAMPLE_PREVIEW_GATE, labels["c_sample_preview_gate"]), "c_sample_preview_gate_hook"),
        PatchHunk(base, b"\xFF" * len(cave_bytes), cave_bytes,
                  "seq_shared_project_code_cave"),
    ]


build_phase1_patches = build_step_routing_patches
build_seq_patches = build_step_routing_patches
