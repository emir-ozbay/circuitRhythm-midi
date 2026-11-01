"""EMULATION ONLY: musical RX order with inquiry ownership retained in RX FIFO.

Each fresh packet enters the native parser once. Its consumer-owned header
becomes0 (processed) or81 (processed, one identity reply still owed). SCANNED
is the provenance boundary:81 is accepted ONLY in an already processed record.
Fresh host cable IDs other than0 fail closed. No record with an owed reply is
acknowledged. One fully processed head record may be popped per pass.

Guarantees cover committed, admitted RX records; not host data that cannot yet
enter a full USB FIFO. Single main consumer/SPSC assumptions are emulated,
not actual IRQ/DMA, full boot or production integration proof.
"""
import midi_usb_inquiry_prototype as prior
import midi_sysex_retry_prototype as retry
from thumb_asm import (Asm, add_sp_imm, sub_sp_imm, adds_imm8, adds_reg,
                       ands_reg, b, b_cond_w, bl, bx_lr, cmp_imm, cmp_reg,
                       ldr_imm, ldr_sp, ldrb_imm, ldrb_reg, ldrh_imm, lsls_imm,
                       mov_reg, movs_imm, orrs_reg, pop, push, raw, str_imm,
                       str_sp, strb_imm, strb_reg, subs_imm8, subs_reg)

CODE_BASE, STATE_BASE, STATE_SIZE = 0x08075000, prior.STATE_BASE, prior.STATE_SIZE
MAGIC, MAX_PENDING, MAX_RING = 0x33584955, prior.MAX_PENDING, 2048
PORT, PARSER, ROUTER, BUSY, PENDING = prior.PORT, prior.PARSER, prior.ROUTER, prior.BUSY, prior.PENDING
DESC, BUFFER, FAULT = prior.DESC, prior.BUFFER, prior.FAULT
SCANNED, EXPECTED_READ = 32, 36
SNAPSHOT, OFFSET, LENGTH, FRESH, HEAD_READY, RECORD_READY = 104, 108, 112, 116, 120, 124
FIFO = 128
OWED = 0x81  # private marker, never valid fresh cable0 input


def arm_code(base=CODE_BASE, state=STATE_BASE):
    old_code, _ = prior.arm_code()
    _, tx = retry.arm_code(notifications=True, reservations=True)
    if (base % 4 or state % 4 or not prior.CODE_BASE+len(old_code) <= base < 0x08080000
            or not retry.STATE_BASE+retry.REQUEST_STATE_SIZE < state
            or not state+STATE_SIZE < 0x20048000):
        raise ValueError('Ledger overlaps synthetic code/state or exceeds bounds')
    a = Asm(base)
    E = a.emit
    def imm(r, value):
        a.imm32(r, value)
    def bc(label, condition):
        E(b_cond_w, label, condition)
    def load(r, off):
        if off <= 124:
            E(ldr_imm, r, 4, off)
        else:
            imm(r, state+off); E(ldr_imm, r, r)
    def save(r, off):
        if off <= 124:
            E(str_imm, r, 4, off)
        else:
            imm(3, state+off); E(str_imm, r, 3)

    a.label('ul_poll')
    E(push, [3, 4, 5, 6, 7], lr=True)
    E(raw, bytes.fromhex('eff31080')); E(cmp_imm, 0, 0); bc('poll_reject', 'ne')
    E(raw, bytes.fromhex('eff30580')); E(cmp_imm, 0, 0); bc('poll_reject', 'ne')
    imm(4, state); E(ldr_imm, 0, 4); imm(1, MAGIC)
    E(cmp_reg, 0, 1); bc('poll_reject', 'ne')
    load(0, BUSY); E(cmp_imm, 0, 0); bc('poll_reject', 'ne')
    load(0, FAULT); E(cmp_imm, 0, 0); bc('poll_reject', 'ne')
    load(0, PENDING); E(cmp_imm, 0, MAX_PENDING); bc('poll_reject', 'hi')
    imm(0, prior.SERVICE); E(ldr_imm, 1, 0, 4)
    E(ldr_imm, 2, 1, 4); E(cmp_imm, 2, 0); bc('poll_reject', 'ne')
    E(ldr_imm, 1, 1); load(2, PORT)
    E(cmp_imm, 2, 0); bc('poll_reject', 'eq')
    E(cmp_reg, 1, 2); bc('poll_reject', 'ne')
    E(ldr_imm, 1, 0, 12); E(ldr_imm, 1, 1); load(2, PARSER)
    E(cmp_imm, 2, 0); bc('poll_reject', 'eq')
    E(cmp_reg, 1, 2); bc('poll_reject', 'ne')
    load(0, PORT); E(ldr_imm, 5, 0, 24)
    E(cmp_imm, 5, 0); bc('poll_reject', 'eq')
    load(0, FIFO); E(cmp_reg, 5, 0); bc('poll_reject', 'ne')
    E(ldrh_imm, 6, 5, 4)
    E(cmp_imm, 6, 6); bc('poll_reject', 'lo')
    imm(0, MAX_RING); E(cmp_reg, 6, 0); bc('poll_reject', 'hi')
    E(ldrb_imm, 0, 5, 10); E(cmp_imm, 0, 64); bc('poll_reject', 'ne')
    E(ldrh_imm, 0, 5, 6); E(cmp_reg, 0, 6); bc('poll_reject', 'hs')
    E(ldrh_imm, 0, 5, 8); E(cmp_reg, 0, 6); bc('poll_reject', 'hs')
    load(1, EXPECTED_READ); E(cmp_reg, 0, 1); bc('poll_reject', 'ne')
    E(ldr_imm, 0, 5); imm(1, 0x20000000)
    E(cmp_reg, 0, 1); bc('poll_reject', 'lo')
    E(adds_reg, 0, 0, 6); imm(1, 0x2004F660)
    E(cmp_reg, 0, 1); bc('poll_reject', 'hi')
    E(mov_reg, 0, 5); E(bl, 0x0802A37E)
    load(1, SCANNED); E(cmp_reg, 1, 0); bc('poll_reject', 'hi')
    save(0, SNAPSHOT)
    E(movs_imm, 0, 0); save(0, OFFSET); save(0, HEAD_READY)
    E(movs_imm, 0, 1); save(0, BUSY)
    a.label('poll_record')
    load(6, OFFSET); load(0, SNAPSHOT)
    E(subs_reg, 0, 0, 6); E(cmp_imm, 0, 2); bc('poll_finish', 'lo')
    E(mov_reg, 0, 5); E(mov_reg, 1, 6); E(bl, 'ul_address'); E(ldrb_imm, 7, 0)
    E(mov_reg, 0, 5); E(mov_reg, 1, 6); E(adds_imm8, 1, 1); E(bl, 'ul_address')
    E(ldrb_imm, 0, 0); E(lsls_imm, 0, 0, 8); E(orrs_reg, 7, 0)
    # Native25AEC publishes length and payload one byte at a time. A snapshot
    # ending within a record is neither dispatched nor acknowledged.
    E(mov_reg, 0, 7); E(adds_imm8, 0, 2); E(adds_reg, 0, 0, 6)
    load(1, SNAPSHOT); E(cmp_reg, 0, 1); bc('poll_finish', 'hi')
    E(cmp_imm, 7, 4); bc('poll_fault', 'lo')
    E(cmp_imm, 7, 64); bc('poll_fault', 'hi')
    E(movs_imm, 0, 3); E(ands_reg, 0, 7); E(cmp_imm, 0, 0); bc('poll_fault', 'ne')
    save(7, LENGTH)
    load(0, SCANNED); E(cmp_reg, 6, 0); bc('record_fresh', 'hs')
    E(mov_reg, 1, 6); E(adds_reg, 1, 1, 7); E(adds_imm8, 1, 2)
    E(cmp_reg, 1, 0); bc('poll_fault', 'hi')
    E(movs_imm, 0, 0); E(b, 'record_kind')
    a.label('record_fresh')
    E(cmp_reg, 6, 0); bc('poll_fault', 'ne')
    E(movs_imm, 0, 1)
    a.label('record_kind')
    save(0, FRESH); E(movs_imm, 7, 0)
    a.label('copy_byte')
    E(adds_reg, 1, 6, 7); E(adds_imm8, 1, 2); E(mov_reg, 0, 5)
    E(bl, 'ul_address'); E(ldrb_imm, 2, 0)
    E(mov_reg, 0, 4); E(adds_imm8, 0, BUFFER); E(strb_reg, 2, 0, 7)
    E(adds_imm8, 7, 1); load(0, LENGTH); E(cmp_reg, 7, 0); bc('copy_byte', 'lo')
    # Validate the whole record before executing any of its callbacks.
    E(movs_imm, 7, 0)
    a.label('validate_header')
    E(mov_reg, 0, 4); E(adds_imm8, 0, BUFFER); E(ldrb_reg, 1, 0, 7)
    load(0, FRESH); E(cmp_imm, 0, 0); bc('validate_private', 'eq')
    E(cmp_imm, 1, 16); bc('poll_fault', 'hs'); E(b, 'validate_next')
    a.label('validate_private')
    E(cmp_imm, 1, 0); bc('validate_next', 'eq')
    E(cmp_imm, 1, OWED); bc('poll_fault', 'ne')
    a.label('validate_next')
    E(adds_imm8, 7, 4); load(0, LENGTH); E(cmp_reg, 7, 0); bc('validate_header', 'lo')
    E(movs_imm, 0, 1); save(0, RECORD_READY); E(movs_imm, 6, 0)
    a.label('record_packet')
    load(0, FRESH); E(cmp_imm, 0, 0); bc('packet_private', 'eq')
    E(mov_reg, 0, 4); E(adds_imm8, 0, BUFFER); E(ldrb_reg, 1, 0, 6)
    imm(0, prior.CIN_TABLE); E(ldrb_reg, 7, 0, 1)
    E(sub_sp_imm, 8); E(str_sp, 7, 0); E(movs_imm, 0, 0); E(str_sp, 0, 4)
    E(movs_imm, 7, 0)
    a.label('packet_byte')
    E(ldr_sp, 0, 0); E(cmp_reg, 7, 0); bc('packet_parsed', 'hs')
    E(mov_reg, 0, 4); E(adds_imm8, 0, BUFFER)
    E(adds_reg, 1, 6, 7); E(adds_imm8, 1, 1); E(ldrb_reg, 1, 0, 1)
    E(mov_reg, 0, 4); E(bl, 'ul_byte')
    E(ldr_sp, 1, 4); E(adds_reg, 1, 1, 0); E(str_sp, 1, 4)
    E(adds_imm8, 7, 1); E(b, 'packet_byte')
    a.label('packet_parsed')
    E(ldr_sp, 7, 4); E(add_sp_imm, 8)
    E(cmp_imm, 7, 1); bc('poll_fault', 'hi')
    E(cmp_imm, 7, 0); bc('packet_publish', 'eq')
    E(movs_imm, 7, OWED); E(b, 'packet_publish')
    a.label('packet_private')
    E(mov_reg, 0, 4); E(adds_imm8, 0, BUFFER); E(ldrb_reg, 7, 0, 6)
    E(cmp_imm, 7, 0); bc('packet_publish', 'eq')
    load(0, PENDING); E(cmp_imm, 0, MAX_PENDING); bc('packet_publish', 'hs')
    E(adds_imm8, 0, 1); save(0, PENDING); E(movs_imm, 7, 0)
    a.label('packet_publish')
    E(cmp_imm, 7, 0); bc('packet_address', 'eq')
    E(movs_imm, 0, 0); save(0, RECORD_READY)
    a.label('packet_address')
    load(1, OFFSET); E(adds_reg, 1, 1, 6); E(adds_imm8, 1, 2)
    E(mov_reg, 0, 5); E(bl, 'ul_address'); E(strb_imm, 7, 0)
    E(adds_imm8, 6, 4); load(0, LENGTH); E(cmp_reg, 6, 0); bc('record_packet', 'lo')
    load(0, OFFSET); E(cmp_imm, 0, 0); bc('record_advance', 'ne')
    load(1, RECORD_READY); save(1, HEAD_READY)
    a.label('record_advance')
    load(1, LENGTH); E(adds_reg, 0, 0, 1); E(adds_imm8, 0, 2); save(0, OFFSET)
    load(1, FRESH); E(cmp_imm, 1, 0); bc('poll_record', 'eq')
    save(0, SCANNED); E(b, 'poll_record')
    a.label('poll_finish')
    load(0, HEAD_READY); E(cmp_imm, 0, 0); bc('poll_rearm', 'eq')
    # Ack only after every byte ran and every inquiry obligation transferred.
    E(movs_imm, 0, 64); save(0, DESC)
    E(mov_reg, 1, 4); E(adds_imm8, 1, DESC); load(0, PORT); E(bl, 0x080269F0)
    load(0, DESC); E(adds_imm8, 0, 2); load(1, SCANNED)
    E(subs_reg, 1, 1, 0); save(1, SCANNED)
    E(ldrh_imm, 0, 5, 8); save(0, EXPECTED_READ)
    a.label('poll_rearm')
    load(0, PORT); E(ldrb_imm, 1, 0, 28)
    E(cmp_imm, 1, 0); bc('poll_reply', 'ne')
    E(bl, 0x080269AC)  # unarmed peripheral path is not exercised by the tests
    a.label('poll_reply')
    load(0, PENDING); E(cmp_imm, 0, 0); bc('poll_unlock', 'eq')
    E(mov_reg, 0, 4); E(bl, 'ul_try_reply')
    a.label('poll_unlock')
    E(movs_imm, 0, 0); save(0, BUSY); E(pop, [3, 4, 5, 6, 7], pc=True)
    a.label('poll_fault')
    E(movs_imm, 0, 1); save(0, FAULT)
    E(movs_imm, 0, 0); save(0, BUSY)
    a.label('poll_reject')
    E(movs_imm, 0, 1); E(pop, [3, 4, 5, 6, 7], pc=True)

    # fifo,distance -> RAM byte address. Distance<capacity, so one subtraction.
    a.label('ul_address')
    E(ldrh_imm, 2, 0, 8); E(adds_reg, 1, 1, 2)
    E(ldrh_imm, 2, 0, 4); E(cmp_reg, 1, 2); bc('address_nowrap', 'lo')
    E(subs_reg, 1, 1, 2)
    a.label('address_nowrap')
    E(ldr_imm, 0, 0); E(adds_reg, 0, 0, 1); E(bx_lr)

    a.label('ul_try_reply')
    E(push, [4], lr=True); E(sub_sp_imm, 8); E(mov_reg, 4, 0)
    imm(0, prior.REPLY_ADDR); E(str_sp, 0, 0)
    E(movs_imm, 0, len(prior.REPLY)); E(str_sp, 0, 4)
    load(0, ROUTER); E(movs_imm, 1, 1); E(mov_reg, 2, 13); E(bl, tx['sr_submit'])
    E(cmp_imm, 0, 0); bc('reply_return', 'ne')
    load(1, PENDING); E(subs_imm8, 1, 1); save(1, PENDING)
    a.label('reply_return')
    E(add_sp_imm, 8); E(pop, [4], pc=True)

    # state,byte ->1 only for an exact inquiry requiring a retained marker.
    a.label('ul_byte')
    E(push, [4, 5, 6], lr=True); E(sub_sp_imm, 16); E(mov_reg, 4, 0)
    load(0, PARSER); E(bl, 0x080404BC)
    E(cmp_imm, 0, 1); bc('byte_short', 'eq')
    E(cmp_imm, 0, 2); bc('byte_zero', 'ne')
    load(0, PARSER); E(ldr_imm, 0, 0, 36)
    E(ldrh_imm, 6, 0); E(ldr_imm, 5, 0, 4); E(str_sp, 5, 0); E(str_sp, 6, 4)
    E(cmp_imm, 6, len(prior.INQUIRY)); bc('byte_other_sysex', 'ne')
    for n, value in enumerate(prior.INQUIRY):
        E(ldrb_imm, 0, 5, n); E(cmp_imm, 0, value); bc('byte_other_sysex', 'ne')
    load(0, PENDING); E(cmp_imm, 0, MAX_PENDING); bc('byte_owed', 'hs')
    E(adds_imm8, 0, 1); save(0, PENDING); E(b, 'byte_zero')
    a.label('byte_other_sysex')
    imm(0, 0x20000900); E(movs_imm, 1, 0); E(mov_reg, 2, 13); E(bl, 0x08024B68)
    E(b, 'byte_zero')
    a.label('byte_short')
    E(mov_reg, 0, 13); E(adds_imm8, 0, 8); E(str_sp, 0, 4)
    E(movs_imm, 0, 3); E(str_sp, 0, 0)
    E(mov_reg, 1, 13); load(0, PARSER); E(ldr_imm, 0, 0, 12); E(bl, 0x08025B1A)
    imm(0, 0x200008E0); E(movs_imm, 1, 0); E(ldr_sp, 2, 4); E(bl, 0x08024B68)
    a.label('byte_zero')
    E(movs_imm, 0, 0); E(b, 'byte_return')
    a.label('byte_owed')
    E(movs_imm, 0, 1)
    a.label('byte_return')
    E(add_sp_imm, 16); E(pop, [4, 5, 6], pc=True)
    code, labels = a.assemble()
    if base+len(code) > 0x08080000:
        raise ValueError('Ledger exceeds application flash')
    return code, labels
