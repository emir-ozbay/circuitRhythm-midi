"""EMULATION ONLY: retained USB RX cursor and one owned identity obligation.

One configured USB endpoint, cable0 only. No production heap/init integration.
The native byte parser, short dispatcher, software FIFO pop, and TX retry run
as Thumb code. A rejected identity reply remains pending; the retained buffer
is not overwritten. Realtime bytes in that buffer bypass the stalled cursor
once. No promise is made about realtime behind OTHER queued non-RT buffers.
Other SysEx goes through the native void dispatcher (its retry is still open).

ordered=True separates up to8 identical inquiry obligations from the RX byte
cursor. Musical bytes always enter the native parser in order; there is no
realtime bypass. At capacity a new F0 is retained BEFORE parsing and nothing
after it can overtake it. This preserves order but can delay later realtime.
The default legacy variant is retained byte-for-byte for negative controls.
"""
import midi_sysex_retry_prototype as retry
import midi_recovery_prototype as recovery
from thumb_asm import (Asm, add_sp_imm, sub_sp_imm, adds_imm8, adds_reg,
                       ands_reg, b, b_cond_w, bl, bx_lr, cmp_imm, cmp_reg,
                       ldr_imm, ldr_sp, ldrb_imm, ldrb_reg, ldrh_imm,
                       mov_reg, movs_imm, pop, push, raw, str_imm, str_sp,
                       strb_reg, subs_imm8)

CODE_BASE, STATE_BASE, STATE_SIZE = 0x08074000, 0x20047C00, 172
MAGIC = 0x31584955  # UIX1; synthetic arena is NOT free production RAM
ORDERED_MAGIC, MAX_PENDING = 0x32584955, 8  # UIX2: counted obligations, not a bit
PORT, PARSER, ROUTER, BUSY, PENDING = 4, 8, 12, 16, 20
DESC, PACKET, SUB, BUFFER, SEEN, FAULT = 24, 32, 36, 40, 104, 168
NATIVE_POLL, POLL_PROLOGUE = 0x08029AC8, bytes.fromhex('2de9f84f')
SERVICE, CIN_TABLE = 0x20006DC0, 0x08029C7C
INQUIRY = bytes.fromhex('f07e7f0601f7')
REPLY_ADDR = 0x080270D8
REPLY = bytes.fromhex('f07e0006020020290163000001012c4af7')
CIN_LENGTHS = bytes.fromhex('00000203030102030303030302020301')


def arm_code(base=CODE_BASE, state=STATE_BASE, ordered=False):
    retry_code, tx = retry.arm_code(notifications=True, reservations=True)
    if (base % 4 or state % 4 or not retry.CODE_BASE+len(retry_code) <= base < 0x08080000
            or not retry.STATE_BASE+retry.REQUEST_STATE_SIZE < state
            or not state+STATE_SIZE < 0x20048000):
        raise ValueError('USB experiment overlaps existing synthetic code/state')
    a = Asm(base)
    E = a.emit
    def imm(r, value):
        a.imm32(r, value)
    def bc(label, cond):
        E(b_cond_w, label, cond)

    # Main context only. BUSY covers the whole pass including all native calls;
    # no IRQ mask is introduced. Single task/main-thread ownership is assumed.
    a.label('ui_poll')
    E(push, [3, 4, 5, 6, 7], lr=True)
    E(raw, bytes.fromhex('eff31080'))  # mrs r0,primask
    E(cmp_imm, 0, 0); bc('poll_reject', 'ne')
    E(raw, bytes.fromhex('eff30580'))  # mrs r0,ipsr
    E(cmp_imm, 0, 0); bc('poll_reject', 'ne')
    imm(4, state)
    E(ldr_imm, 0, 4); imm(1, ORDERED_MAGIC if ordered else MAGIC)
    E(cmp_reg, 0, 1); bc('poll_reject', 'ne')
    E(ldr_imm, 0, 4, BUSY)
    E(cmp_imm, 0, 0); bc('poll_reject', 'ne')
    imm(0, state+FAULT); E(ldr_imm, 0, 0)
    E(cmp_imm, 0, 0); bc('poll_reject', 'ne')
    if ordered:
        E(ldr_imm, 0, 4, PENDING)
        E(cmp_imm, 0, MAX_PENDING); bc('poll_reject', 'hi')
    # Match the initialized endpoint/parser to the live native table before pop.
    imm(0, SERVICE)
    E(ldr_imm, 1, 0, 4); E(ldr_imm, 2, 1, 4)
    E(cmp_imm, 2, 0); bc('poll_reject', 'ne')  # no second USB endpoint
    E(ldr_imm, 1, 1); E(ldr_imm, 2, 4, PORT)
    E(cmp_imm, 1, 0); bc('poll_reject', 'eq')
    E(cmp_reg, 1, 2); bc('poll_reject', 'ne')
    E(cmp_imm, 2, 0); bc('poll_reject', 'eq')
    E(ldr_imm, 1, 0, 12); E(ldr_imm, 1, 1)
    E(ldr_imm, 2, 4, PARSER)
    E(cmp_reg, 1, 2); bc('poll_reject', 'ne')
    E(cmp_imm, 2, 0); bc('poll_reject', 'eq')
    E(movs_imm, 0, 1); E(str_imm, 0, 4, BUSY)
    if not ordered:
        E(ldr_imm, 0, 4, PENDING)
        E(cmp_imm, 0, 0); bc('poll_buffer', 'eq')
        E(mov_reg, 0, 4); E(bl, 'ui_try_reply')
    a.label('poll_buffer')
    E(ldr_imm, 0, 4, DESC)
    E(cmp_imm, 0, 0); bc('poll_have_buffer', 'ne')
    E(ldr_imm, 0, 4, PORT); E(ldr_imm, 0, 0, 24)
    E(bl, 0x0802A37E)  # native queued byte count (includes two-byte length)
    E(cmp_imm, 0, 6); bc('poll_empty', 'lo')
    E(movs_imm, 0, 64); E(str_imm, 0, 4, DESC)
    E(mov_reg, 1, 4); E(adds_imm8, 1, DESC)
    E(ldr_imm, 0, 4, PORT)
    E(bl, 0x080269F0)  # exactly one native FIFO pop per pass, own destination
    E(ldr_imm, 5, 4, DESC)
    E(cmp_imm, 5, 64); bc('poll_fault', 'hi')
    E(cmp_imm, 5, 0); bc('poll_fault', 'eq')
    E(movs_imm, 0, 3); E(ands_reg, 0, 5)
    E(cmp_imm, 0, 0); bc('poll_fault', 'ne')
    E(str_imm, 0, 4, PACKET); E(str_imm, 0, 4, SUB)
    if not ordered:
        E(mov_reg, 6, 4); E(adds_imm8, 6, SEEN)
        E(movs_imm, 1, 64)
        a.label('clear_seen')
        E(subs_imm8, 1, 1); E(strb_reg, 0, 6, 1)
        bc('clear_seen', 'ne')
    # Reject unsupported cable IDs without dispatching any of this buffer.
    E(mov_reg, 6, 4); E(adds_imm8, 6, BUFFER)
    E(movs_imm, 7, 0)
    a.label('validate_cables')
    E(ldrb_reg, 0, 6, 7); E(cmp_imm, 0, 16)
    bc('poll_fault', 'hs')
    E(adds_imm8, 7, 4); E(cmp_reg, 7, 5)
    bc('validate_cables', 'lo')
    a.label('poll_have_buffer')
    if not ordered:
        E(ldr_imm, 0, 4, PENDING)
        E(cmp_imm, 0, 0); bc('poll_scan', 'ne')
    a.label('poll_bytes')
    if ordered:
        # Saved BEFORE ui_next, including packet rollover. Roll back only an
        # unparsed byte; never replay one already delivered to the parser.
        E(ldr_imm, 6, 4, PACKET); E(ldr_imm, 7, 4, SUB)
    E(mov_reg, 0, 4); E(bl, 'ui_next')
    E(cmp_imm, 0, 0); bc('poll_clear', 'eq')
    E(mov_reg, 5, 0)
    if not ordered:
        E(mov_reg, 1, 4); E(adds_imm8, 1, SEEN)
        E(ldrb_reg, 0, 1, 5)
        E(cmp_imm, 0, 0); bc('poll_bytes', 'ne')
    E(mov_reg, 1, 4); E(adds_imm8, 1, BUFFER)
    E(ldrb_reg, 1, 1, 5); E(mov_reg, 0, 4)
    if ordered:
        E(ldr_imm, 2, 4, PENDING)
        E(cmp_imm, 2, MAX_PENDING); bc('poll_deliver', 'lo')
        E(cmp_imm, 1, 0xF0); bc('poll_hold', 'eq')
        # Conservative guard for an already active SysEx parser at capacity.
        # Normally impossible under this sole-consumer lifecycle, but protects
        # externally seeded partial input without consuming its final F7.
        E(ldr_imm, 2, 4, PARSER); E(ldrb_imm, 2, 2)
        E(cmp_imm, 2, 0); bc('poll_deliver', 'eq')
        a.label('poll_hold')
        E(str_imm, 6, 4, PACKET); E(str_imm, 7, 4, SUB)
        E(b, 'poll_done')
        a.label('poll_deliver')
    E(bl, 'ui_byte')
    if ordered:
        E(b, 'poll_bytes')
    else:
        E(ldr_imm, 0, 4, PENDING)
        E(cmp_imm, 0, 0); bc('poll_bytes', 'eq')
        a.label('poll_scan')
        E(mov_reg, 0, 4); E(bl, 'ui_scan_realtime')
        E(b, 'poll_done')
    a.label('poll_clear')
    E(movs_imm, 0, 0); E(str_imm, 0, 4, DESC)
    E(str_imm, 0, 4, PACKET); E(str_imm, 0, 4, SUB)
    E(b, 'poll_done')
    a.label('poll_empty')
    # Native rearm contract is preserved, but unarmed hardware paths are NOT
    # exercised by the synthetic tests (endpoint is already armed).
    E(ldr_imm, 0, 4, PORT); E(ldrb_imm, 1, 0, 28)
    E(cmp_imm, 1, 0); bc('poll_done', 'ne')
    E(bl, 0x080269AC)
    E(b, 'poll_done')
    a.label('poll_fault')
    imm(1, state+FAULT); E(movs_imm, 0, 1); E(str_imm, 0, 1)
    a.label('poll_done')
    if ordered:
        # One admission attempt per pass, after ordered RX dispatch. New tokens
        # cannot consume an unbounded service budget and TX busy never reorders RX.
        E(ldr_imm, 0, 4, PENDING)
        E(cmp_imm, 0, 0); bc('poll_unlock', 'eq')
        E(mov_reg, 0, 4); E(bl, 'ui_try_reply')
        a.label('poll_unlock')
    E(movs_imm, 0, 0); E(str_imm, 0, 4, BUSY)
    E(pop, [3, 4, 5, 6, 7], pc=True)
    a.label('poll_reject')
    E(movs_imm, 0, 1); E(pop, [3, 4, 5, 6, 7], pc=True)

    # State -> next meaningful data offset, or0. Advances before delivery;
    # the pending token is then the owner of a completed inquiry, not parser RAM.
    a.label('ui_next')
    E(push, [4, 5, 6], lr=True); E(mov_reg, 4, 0)
    a.label('next_packet')
    E(ldr_imm, 5, 4, PACKET); E(ldr_imm, 0, 4, DESC)
    E(cmp_reg, 5, 0); bc('next_end', 'hs')
    E(mov_reg, 0, 4); E(adds_imm8, 0, BUFFER)
    E(ldrb_reg, 1, 0, 5); E(movs_imm, 0, 15); E(ands_reg, 1, 0)
    imm(0, CIN_TABLE); E(ldrb_reg, 1, 0, 1)
    E(ldr_imm, 6, 4, SUB)
    E(cmp_reg, 6, 1); bc('next_byte', 'lo')
    E(adds_imm8, 5, 4); E(str_imm, 5, 4, PACKET)
    E(movs_imm, 0, 0); E(str_imm, 0, 4, SUB)
    E(b, 'next_packet')
    a.label('next_byte')
    E(adds_imm8, 6, 1); E(str_imm, 6, 4, SUB)
    E(adds_reg, 0, 5, 6); E(pop, [4, 5, 6], pc=True)
    a.label('next_end')
    E(movs_imm, 0, 0); E(pop, [4, 5, 6], pc=True)

    # A known six-byte inquiry is represented by one token and cable0. Only
    # successful owned TX admission acknowledges it. Busy/fault leaves it set.
    a.label('ui_try_reply')
    E(push, [4], lr=True); E(sub_sp_imm, 8); E(mov_reg, 4, 0)
    imm(0, REPLY_ADDR); E(str_sp, 0, 0)
    E(movs_imm, 0, len(REPLY)); E(str_sp, 0, 4)
    E(ldr_imm, 0, 4, ROUTER); E(movs_imm, 1, 1)
    E(mov_reg, 2, 13); E(bl, tx['sr_submit'])
    E(cmp_imm, 0, 0); bc('reply_return', 'ne')
    if ordered:
        E(ldr_imm, 1, 4, PENDING); E(subs_imm8, 1, 1)
        E(str_imm, 1, 4, PENDING)
    else:
        E(str_imm, 0, 4, PENDING)
    a.label('reply_return')
    E(add_sp_imm, 8); E(pop, [4], pc=True)

    # Native404BC parser -> native short pop/dispatcher or SysEx dispatcher.
    # Only the EXACT read-only inquiry is taken over; no update handler retry.
    a.label('ui_byte')
    E(push, [4, 5, 6], lr=True); E(sub_sp_imm, 16)
    E(mov_reg, 4, 0); E(ldr_imm, 0, 4, PARSER)
    E(bl, 0x080404BC)
    E(cmp_imm, 0, 1); bc('byte_short', 'eq')
    E(cmp_imm, 0, 2); bc('byte_return', 'ne')
    E(ldr_imm, 0, 4, PARSER); E(ldr_imm, 0, 0, 36)
    E(ldrh_imm, 6, 0); E(ldr_imm, 5, 0, 4)
    E(str_sp, 5, 0); E(str_sp, 6, 4)
    E(cmp_imm, 6, len(INQUIRY)); bc('byte_other_sysex', 'ne')
    for n, value in enumerate(INQUIRY):
        E(ldrb_imm, 0, 5, n); E(cmp_imm, 0, value)
        bc('byte_other_sysex', 'ne')
    if ordered:
        E(ldr_imm, 0, 4, PENDING); E(adds_imm8, 0, 1)
        E(str_imm, 0, 4, PENDING)
    else:
        E(movs_imm, 0, 1); E(str_imm, 0, 4, PENDING)
        E(mov_reg, 0, 4); E(bl, 'ui_try_reply')
    E(b, 'byte_return')
    a.label('byte_other_sysex')
    imm(0, 0x20000900); E(movs_imm, 1, 0); E(mov_reg, 2, 13)
    E(bl, 0x08024B68); E(b, 'byte_return')
    a.label('byte_short')
    E(mov_reg, 0, 13); E(adds_imm8, 0, 8); E(str_sp, 0, 4)
    E(movs_imm, 0, 3); E(str_sp, 0, 0)
    E(mov_reg, 1, 13); E(ldr_imm, 0, 4, PARSER)
    E(ldr_imm, 0, 0, 12); E(bl, 0x08025B1A)
    imm(0, 0x200008E0); E(movs_imm, 1, 0); E(ldr_sp, 2, 4)
    E(bl, 0x08024B68)
    a.label('byte_return')
    E(add_sp_imm, 16); E(pop, [4, 5, 6], pc=True)

    # The ordered variant has no alternate delivery path at all.
    if ordered:
        code, labels = a.assemble()
        if base+len(code) > 0x08080000:
            raise ValueError('USB prototype exceeds application flash')
        return code, labels

    # At most48 meaningful bytes in ONE retained64B buffer. Advance a private
    # cursor, marking realtime once before dispatch. Restore the ordered cursor
    # if any non-RT byte remains; otherwise release this buffer while token stays.
    a.label('ui_scan_realtime')
    E(push, [3, 4, 5, 6, 7], lr=True); E(sub_sp_imm, 8)
    E(mov_reg, 4, 0); E(ldr_imm, 0, 4, PACKET); E(str_sp, 0, 0)
    E(ldr_imm, 0, 4, SUB); E(str_sp, 0, 4)
    E(movs_imm, 7, 0)
    a.label('scan_byte')
    E(mov_reg, 0, 4); E(bl, 'ui_next')
    E(cmp_imm, 0, 0); bc('scan_end', 'eq')
    E(mov_reg, 5, 0); E(mov_reg, 6, 4); E(adds_imm8, 6, SEEN)
    E(ldrb_reg, 0, 6, 5); E(cmp_imm, 0, 0); bc('scan_byte', 'ne')
    E(mov_reg, 0, 4); E(adds_imm8, 0, BUFFER); E(ldrb_reg, 2, 0, 5)
    E(cmp_imm, 2, 0xF8); bc('scan_nonrt', 'lo')
    E(movs_imm, 0, 1); E(strb_reg, 0, 6, 5)
    E(ldr_imm, 0, 4, PARSER); E(movs_imm, 1, 0)
    E(bl, 0x08029C1A)  # native RT does not change SysEx/running status
    E(b, 'scan_byte')
    a.label('scan_nonrt')
    E(movs_imm, 7, 1); E(b, 'scan_byte')
    a.label('scan_end')
    E(cmp_imm, 7, 0); bc('scan_restore', 'ne')
    E(movs_imm, 0, 0); E(str_imm, 0, 4, DESC)
    E(str_imm, 0, 4, PACKET); E(str_imm, 0, 4, SUB)
    E(b, 'scan_return')
    a.label('scan_restore')
    E(ldr_sp, 0, 0); E(str_imm, 0, 4, PACKET)
    E(ldr_sp, 0, 4); E(str_imm, 0, 4, SUB)
    a.label('scan_return')
    E(add_sp_imm, 8); E(pop, [3, 4, 5, 6, 7], pc=True)
    code, labels = a.assemble()
    if base+len(code) > 0x08080000:
        raise ValueError('USB prototype exceeds application flash')
    return code, labels
