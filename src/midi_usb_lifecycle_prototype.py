"""EMULATION ONLY: guarded RX consumers/producer and quiescent reset handshake.

Protects the ledger's registered objects; other objects retain native paths.
Disconnect freezes RX ownership rather than clearing debts. Active TX/session
cancellation is deliberately NOT implemented and remains a release blocker.
"""
import midi_usb_ledger_prototype as ledger
import midi_usb_inquiry_prototype as rx
import midi_sysex_retry_prototype as retry
import seq_Patch as seq
from thumb_asm import (Asm, add_sp_imm, adds_imm8, b, b_cond_w, b_w, bl, bx_lr,
                       cmp_imm, cmp_reg, ldr_imm, ldr_sp, ldr_w, ldrb_imm,
                       ldrb_w, ldrh_imm, mov_reg, movs_imm, movw, movt,
                       pop, push, raw, str_imm)

CODE_BASE, STATE_BASE, STATE_SIZE = 0x08076000, 0x20047D00, 64
MAGIC = 0x3146434C  # LCF1
PHASE, FIFO, DATA, CAPACITY, PARSER, PORT, CONTROLLER = 4, 8, 12, 16, 20, 24, 28
BUSY, ERRORS, EPOCH, TX_ENDPOINT, PUBLISHING = 32, 36, 44, 48, 56
CLOSED, ACTIVE, FROZEN, RESETTING = 0, 1, 2, 3
BINDING_ERROR, LINK_ERROR, RX_ERROR = 1, 2, 4
GATES = {
    0x080269F0: ('port_pop', PORT, bytes.fromhex('8269002a')),
    0x08025B1A: ('message_pop', FIFO, bytes.fromhex('38b50446')),
    0x0802A470: ('raw_pop', FIFO, bytes.fromhex('f8b50546')),
    0x0802A426: ('byte_pop', FIFO, bytes.fromhex('10b4b0f90820')),
    0x0802A374: ('reset', FIFO, bytes.fromhex('0021c180')),
    0x08025ACC: ('constructor', FIFO, bytes.fromhex('38b50446')),
    0x08026828: ('constructor', PORT, bytes.fromhex('f8b50646')),
    0x080405D4: ('parser_reset', PARSER, bytes.fromhex('10b50446')),
    0x08040604: ('parser_select', PARSER, bytes.fromhex('38b50446')),
    0x080405F8: ('parser_select', PARSER, bytes.fromhex('00ebc300')),
    0x08025AEC: ('producer', FIFO, bytes.fromhex('38b50446')),
    0x0802A404: ('producer_raw', FIFO, bytes.fromhex('f8b51446')),
    0x0802A3BE: ('producer_byte', FIFO, bytes.fromhex('70b4b0f90830')),
    0x080269AC: ('rearm', PORT, bytes.fromhex('38b50546')),
    0x08026988: ('rx_completion', PORT, bytes.fromhex('10b50446')),
}


def arm_code(base=CODE_BASE, state=STATE_BASE):
    lc, ul = ledger.arm_code()
    if (base % 4 or state % 4 or not ledger.CODE_BASE+len(lc) <= base < 0x08080000
            or not ledger.STATE_BASE+ledger.STATE_SIZE < state
            or not state+STATE_SIZE < 0x20048000):
        raise ValueError('Lifecycle code/state overlaps or exceeds bounds')
    from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB, CS_MODE_MCLASS
    md = Cs(CS_ARCH_ARM, CS_MODE_THUMB | CS_MODE_MCLASS)
    pop_sites = [i.address+4 | 1 for i in md.disasm(lc, ledger.CODE_BASE)
                 if i.mnemonic == 'bl' and i.op_str == '#0x80269f0']
    assert len(pop_sites) == 1
    _, seq_labels = seq.arm_code()
    a = Asm(base); E = a.emit; fixups = []
    def imm(r, value):
        a.imm32(r, value)
    def ptr(r, label):
        name = 'fix_'+str(len(fixups)); a.label(name); imm(r, 0)
        fixups.append((name, r, label))
    def bc(label, cond):
        E(b_cond_w, label, cond)
    def mask(r=3):
        E(raw, bytes([0xEF,0xF3,0x10,0x80|r])); E(raw, bytes.fromhex('72b6'))
    def restore(r=3):
        E(raw, bytes([0x80|r,0xF3,0x10,0x88]))
    def main_check(fail):
        E(raw, bytes.fromhex('eff31080')); E(cmp_imm, 0, 0); bc(fail, 'ne')
        E(raw, bytes.fromhex('eff30580')); E(cmp_imm, 0, 0); bc(fail, 'ne')
        imm(4, state); E(ldr_imm, 0, 4); imm(1, MAGIC)
        E(cmp_reg, 0, 1); bc(fail, 'ne')
    def field(off, reg=0):
        E(ldr_imm, reg, 4, off)
    def zero(off, fail):
        field(off); E(cmp_imm, 0, 0); bc(fail, 'ne')

    # No writes; validates the registered object identity, not just read index.
    a.label('cl_binding')
    E(push, [4,5], lr=True)  # leaf, no calls
    imm(4, state); field(PORT, 5)
    E(ldr_imm, 0, 5, 24); field(FIFO, 1); E(cmp_reg, 0, 1); bc('binding_bad', 'ne')
    imm(2, ledger.STATE_BASE); E(ldr_imm, 0, 2); imm(3, ledger.MAGIC)
    E(cmp_reg, 0, 3); bc('binding_bad', 'ne')
    E(ldr_w, 0, 2, ledger.FIFO)
    E(cmp_reg, 0, 1); bc('binding_bad', 'ne')
    E(ldr_imm, 0, 1); field(DATA, 3); E(cmp_reg, 0, 3); bc('binding_bad', 'ne')
    E(ldrh_imm, 0, 1, 4); field(CAPACITY, 3); E(cmp_reg, 0, 3); bc('binding_bad', 'ne')
    E(ldr_imm, 0, 2, ledger.PARSER); field(PARSER, 1); E(cmp_reg, 0, 1); bc('binding_bad', 'ne')
    E(ldr_imm, 0, 2, ledger.PORT); E(cmp_reg, 0, 5); bc('binding_bad', 'ne')
    E(ldr_imm, 0, 5, 16); field(CONTROLLER, 1); E(cmp_reg, 0, 1); bc('binding_bad', 'ne')
    E(movs_imm, 0, 1); E(pop, [4,5], pc=True)
    a.label('binding_bad'); E(movs_imm, 0, 0); E(pop, [4,5], pc=True)

    # Quiescence predicate; no cancellation and no side effects.
    a.label('cl_idle')
    E(push, [3,4,5], lr=True); imm(4, state)
    zero(PUBLISHING, 'idle_no')
    imm(5, ledger.STATE_BASE)
    for off in (ledger.BUSY, ledger.PENDING, ledger.SCANNED, ledger.FAULT):
        E(ldr_w, 0, 5, off); E(cmp_imm, 0, 0); bc('idle_no', 'ne')
    imm(1, retry.STATE_BASE)
    for off in (retry.BUSY, retry.ACTIVE, retry.PRODUCER_BUSY):
        E(ldrb_imm, 0, 1, off); E(cmp_imm, 0, 0); bc('idle_no', 'ne')
    E(ldr_w, 0, 1, retry.REQUEST); E(cmp_imm, 0, 0); bc('idle_no', 'ne')
    field(TX_ENDPOINT); E(cmp_imm, 0, 0); bc('idle_no_endpoint', 'eq')
    E(ldrb_imm, 0, 0, 28); E(cmp_imm, 0, 0); bc('idle_no', 'eq')
    a.label('idle_no_endpoint')
    field(FIFO); E(bl, 0x0802A37E); E(cmp_imm, 0, 0); bc('idle_no', 'ne')
    field(PARSER, 5); E(ldrb_imm, 0, 5); E(cmp_imm, 0, 0); bc('idle_no', 'ne')
    E(ldrb_imm, 0, 5, 2); E(cmp_imm, 0, 1); bc('idle_no', 'hi')
    E(ldr_imm, 0, 5, 12); E(bl, 0x0802A37E); E(cmp_imm, 0, 0); bc('idle_no', 'ne')
    E(bl, seq_labels['c_midi_inputs_idle']); E(cmp_imm, 0, 1); bc('idle_no', 'ne')
    E(movs_imm, 0, 1); E(pop, [3,4,5], pc=True)
    a.label('idle_no'); E(movs_imm, 0, 0); E(pop, [3,4,5], pc=True)

    a.label('cl_poll')
    E(push, [3,4,5], lr=True); main_check('poll_no'); zero(BUSY, 'poll_no')
    field(PHASE); E(cmp_imm, 0, ACTIVE); bc('poll_no', 'ne')
    E(bl, 'cl_binding'); E(cmp_imm, 0, 1); bc('poll_binding_bad', 'ne')
    field(CONTROLLER); E(ldrb_w, 0, 0, 0x274); E(cmp_imm, 0, 3); bc('poll_link_bad', 'ne')
    E(movs_imm, 0, 1); E(str_imm, 0, 4, BUSY)
    E(bl, ul['ul_poll']); E(mov_reg, 5, 0)
    E(movs_imm, 0, 0); E(str_imm, 0, 4, BUSY)
    E(cmp_imm, 5, 0); bc('poll_return', 'eq')
    E(movs_imm, 0, RX_ERROR); E(b, 'poll_freeze')
    a.label('poll_binding_bad'); E(movs_imm, 0, BINDING_ERROR); E(b, 'poll_freeze')
    a.label('poll_link_bad'); E(movs_imm, 0, LINK_ERROR)
    a.label('poll_freeze')
    E(str_imm, 0, 4, ERRORS); E(movs_imm, 0, FROZEN); E(str_imm, 0, 4, PHASE)
    a.label('poll_no'); E(movs_imm, 5, 1)
    a.label('poll_return'); E(mov_reg, 0, 5); E(pop, [3,4,5], pc=True)

    # Reset closes producer admission atomically, then performs native RAM-only
    # reset calls with IRQs enabled. Failure restores the previous phase.
    a.label('cl_reset')
    E(push, [3,4,5], lr=True); main_check('reset_no'); zero(BUSY, 'reset_no')
    E(bl, 'cl_binding'); E(cmp_imm, 0, 1); bc('reset_no', 'ne')
    field(EPOCH); imm(1, 0xFFFFFFFF); E(cmp_reg, 0, 1); bc('reset_no', 'eq')
    mask(); field(PUBLISHING); E(cmp_imm, 0, 0); bc('reset_mask_no', 'ne')
    field(PHASE, 5); E(movs_imm, 0, RESETTING); E(str_imm, 0, 4, PHASE)
    E(movs_imm, 0, 1); E(str_imm, 0, 4, BUSY); restore()
    E(bl, 'cl_idle'); E(cmp_imm, 0, 1); bc('reset_restore', 'ne')
    field(FIFO); E(bl, 0x0802A374); a.label('reset_after_fifo')
    field(PARSER); E(bl, 0x080405D4); a.label('reset_after_parser')
    imm(1, ledger.STATE_BASE); E(movs_imm, 0, 0)
    E(str_imm, 0, 1, ledger.SCANNED); E(str_imm, 0, 1, ledger.EXPECTED_READ)
    E(str_imm, 0, 4, PHASE); E(str_imm, 0, 4, BUSY)
    field(EPOCH, 1); E(adds_imm8, 1, 1); E(str_imm, 1, 4, EPOCH)
    E(pop, [3,4,5], pc=True)
    a.label('reset_restore')
    E(str_imm, 5, 4, PHASE); E(movs_imm, 0, 0); E(str_imm, 0, 4, BUSY); E(b, 'reset_no')
    a.label('reset_mask_no'); restore()
    a.label('reset_no'); E(movs_imm, 0, 1); E(pop, [3,4,5], pc=True)

    a.label('cl_resume')
    E(push, [3,4,5], lr=True); main_check('resume_no'); zero(BUSY, 'resume_no')
    field(PHASE); E(cmp_imm, 0, CLOSED); bc('resume_no', 'ne')
    E(bl, 'cl_binding'); E(cmp_imm, 0, 1); bc('resume_no', 'ne')
    field(CONTROLLER); E(ldrb_w, 0, 0, 0x274); E(cmp_imm, 0, 3); bc('resume_no', 'ne')
    E(bl, 'cl_idle'); E(cmp_imm, 0, 1); bc('resume_no', 'ne')
    E(movs_imm, 0, ACTIVE); E(str_imm, 0, 4, PHASE)
    E(movs_imm, 0, 0); E(pop, [3,4,5], pc=True)
    a.label('resume_no'); E(movs_imm, 0, 1); E(pop, [3,4,5], pc=True)

    for address, (kind, registered, original) in GATES.items():
        suffix = f'{address:08x}'
        allow, deny, foreign = 'allow_'+suffix, 'deny_'+suffix, 'foreign_'+suffix
        a.label('cl_gate_'+suffix)
        E(push, [0,1,2,3,4,5,6], lr=True)
        imm(4, state); field(registered, 1); E(cmp_reg, 0, 1); bc(foreign, 'ne')
        E(ldr_imm, 0, 4); imm(1, MAGIC); E(cmp_reg, 0, 1); bc(deny, 'ne')
        if kind == 'producer':
            mask(); field(PHASE); E(cmp_imm, 0, ACTIVE); bc('producer_mask_no', 'ne')
            field(PUBLISHING); E(cmp_imm, 0, 0); bc('producer_mask_no', 'ne')
            E(movs_imm, 0, 1); E(str_imm, 0, 4, PUBLISHING); restore()
            E(ldr_sp, 0, 0); E(ldr_sp, 1, 4); E(ldr_sp, 2, 8); E(ldr_sp, 3, 12)
            E(bl, 'cl_trampoline_'+suffix); E(mov_reg, 5, 0)
            mask(); E(movs_imm, 0, 0); E(str_imm, 0, 4, PUBLISHING); restore()
            E(mov_reg, 0, 5); E(add_sp_imm, 4); E(pop, [1,2,3,4,5,6], pc=True)
            a.label('producer_mask_no'); restore(); E(b, deny)
        elif kind == 'constructor':
            E(b, deny)
        elif kind in ('rearm', 'rx_completion'):
            field(PHASE); E(cmp_imm, 0, ACTIVE); bc(deny, 'ne')
            field(PORT, 0); E(ldr_imm, 0, 0, 16); field(CONTROLLER, 1)
            E(cmp_reg, 0, 1); bc(deny, 'ne')
            E(ldrb_w, 0, 0, 0x274); E(cmp_imm, 0, 3); bc(allow, 'eq'); E(b, deny)
        elif kind in ('producer_raw', 'producer_byte'):
            field(PHASE); E(cmp_imm, 0, ACTIVE); bc(deny, 'ne')
            field(PUBLISHING); E(cmp_imm, 0, 1); bc(deny, 'ne')
            E(ldr_sp, 5, 28)
            for value in ([0x08025B0D, 0x08025B17] if kind == 'producer_raw' else [0x0802A41D]):
                imm(1, value); E(cmp_reg, 5, 1); bc(allow, 'eq')
            E(b, deny)
        else:
            E(raw, bytes.fromhex('eff30580')); E(cmp_imm, 0, 0); bc(deny, 'ne')
            E(raw, bytes.fromhex('eff31080')); E(cmp_imm, 0, 0); bc(deny, 'ne')
            E(ldr_sp, 5, 28)  # native caller LR, before guard prologue
            if kind in ('reset', 'parser_reset'):
                field(PHASE); E(cmp_imm, 0, RESETTING); bc('not_reset_'+suffix, 'ne')
                field(BUSY); E(cmp_imm, 0, 1); bc(deny, 'ne')
                ptr(1, 'reset_after_fifo' if kind == 'reset' else 'reset_after_parser')
                E(cmp_reg, 5, 1); bc(allow, 'eq'); E(b, deny)
                a.label('not_reset_'+suffix)
            if kind in ('parser_reset', 'parser_select'):
                field(PHASE); E(cmp_imm, 0, ACTIVE); bc(deny, 'ne')
                if kind == 'parser_reset':
                    field(BUSY); E(cmp_imm, 0, 1); bc('parser_idle_'+suffix, 'ne')
                    imm(1, 0x0804059D); E(cmp_reg, 5, 1); bc(allow, 'eq'); E(b, deny)
                    a.label('parser_idle_'+suffix)
                field(BUSY); E(cmp_imm, 0, 0); bc(deny, 'ne')
                E(bl, 'cl_idle'); E(cmp_imm, 0, 1); bc(allow, 'eq'); E(b, deny)
            elif kind == 'reset':
                E(b, deny)
            else:
                field(PHASE); E(cmp_imm, 0, ACTIVE); bc(deny, 'ne')
                field(BUSY); E(cmp_imm, 0, 1); bc(deny, 'ne')
                imm(0, ledger.STATE_BASE); E(ldr_imm, 0, 0, ledger.BUSY)
                E(cmp_imm, 0, 1); bc(deny, 'ne')
                lrs = pop_sites if kind in ('port_pop', 'message_pop') else (
                    [0x08025B3B, 0x08025B5F] if kind == 'raw_pop' else [0x0802A487])
                for value in lrs:
                    imm(1, value); E(cmp_reg, 5, 1); bc(allow, 'eq')
                E(b, deny)
        a.label(allow); a.label(foreign)
        E(pop, [0,1,2,3,4,5,6], lr=True); E(b_w, 'cl_trampoline_'+suffix)
        a.label(deny)
        E(pop, [0,1,2,3,4,5,6], lr=True)
        E(movs_imm, 0, 1 if kind in ('reset', 'parser_reset', 'parser_select') else 0); E(bx_lr)
        a.label('cl_trampoline_'+suffix); E(raw, original); E(b_w, address+len(original))
    code, labels = a.assemble(); code = bytearray(code)
    for name, reg, target in fixups:
        offset = labels[name]-base
        assert code[offset:offset+8] == movw(reg, 0)+movt(reg, 0)
        value = labels[target] | 1
        code[offset:offset+8] = movw(reg, value & 0xFFFF)+movt(reg, value >> 16)
    if base+len(code) > 0x08080000:
        raise ValueError('Lifecycle code exceeds application flash')
    return bytes(code), labels
