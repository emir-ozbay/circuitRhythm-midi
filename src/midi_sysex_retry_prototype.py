"""EMULATION ONLY: one owned SysEx transaction, bounded per-port retries.

Explicit API, NOT a drop-in production router: submit0 means a local immutable
copy was accepted, not all ports or wire completion. The default variant has no
notification. Optional notifications=True snapshots the native event/owner and
dispatches event0 once all selected ports accept, using native24B68. It never
claims wire completion. Full/reentrant admission fails1; callers
which ignore failure still require upstream backpressure. Failed ports pin the
slot, with no automatic reset. This is deliberately separate from the earlier
native-router experiment and the production builder.

Optional reservations=True also guards five upper formatters before mutation,
forwarding their native stack arguments. This requires notifications=True and
main context. Native USB/DIN dispatch still consumes requests on ignored reject.
"""
import midi_recovery_prototype as recovery
from thumb_asm import (Asm, add_sp_imm, sub_sp_imm, adds_imm8, ands_reg, b, b_cond_w, bics_reg, bl,
                       b_w, blx_reg, bx_lr, cmp_imm, cmp_reg, ldr_imm, ldr_sp, ldr_w, ldrb_imm, ldrb_reg,
                       mov_reg, movs_imm, movt, movw, orrs_reg, pop, push,
                       raw, str_imm, str_sp, str_w, strb_imm, subs_imm8, tst_reg)

CODE_BASE, STATE_BASE = 0x08072000, 0x20047800  # synthetic only, NOT free heap
MAGIC = 0x31515253  # SRQ1
CAPACITY, STATE_SIZE = 360, 384
ROUTER, BUSY, ACTIVE, WAITING, ACCEPTED, FAILED, ERRORS = 4, 8, 9, 10, 11, 12, 13
PRODUCER_BUSY = 14
NOTICE = 15  # optional extension:0 waiting for admission,2 dispatching,3 notified
OWNER_FN, OWNER_CTX, EVENT = 384, 388, 392
NOTIFICATION_STATE_SIZE = 424  # owned function/context plus native32B event snapshot
REQUEST, REQUEST_STATE_SIZE = 424, 428  # reserved native lower-call return PC
NATIVE_EVENT, NATIVE_EVENT_VTABLE, NATIVE_NOTIFY = 0x20000920, 0x08069460, 0x08024B68
NATIVE_OWNER, NATIVE_OWNER_ADAPTER = 0x20006EE0, 0x080468ED
DESCRIPTOR, PAYLOAD = 16, 24
REJECTED, REENTRANT, PORT_FAULT, BAD_STATE = 1, 2, 4, 8
NATIVE_COPY = 0x08022CF0
# Optional emulator-only guards run BEFORE shared formatter/callback writes.
# PC-relative first instructions in DE84/ED88 are relocated explicitly below.
CALLER_GATES = {
    0x08026F0C: bytes.fromhex('1cb50968'), 0x0802CBB8: bytes.fromhex('feb50546'),
    0x0802CD60: bytes.fromhex('2de9fc41'), 0x0802CDF8: bytes.fromhex('38b584b0'),
    0x0802CEE4: bytes.fromhex('38b586b0'), 0x0802D0B0: bytes.fromhex('7cb50546'),
    0x0802D0F8: bytes.fromhex('3eb50546'), 0x0802D134: bytes.fromhex('38b596b0'),
    0x0802DE84: bytes.fromhex('15480a46'), 0x0802ED88: bytes.fromhex('30b4294b'),
    0x08042160: bytes.fromhex('2de9fe43'), 0x0804691A: bytes.fromhex('f8b50446'),
}
REQUEST_GATES = {
    # entry -> original prologue, return PC after4691A call, stack arguments
    0x08032120: (bytes.fromhex('70b584b0'), 0x08032151, 2),
    0x08032154: (bytes.fromhex('70b584b0'), 0x08032185, 2),
    0x08032188: (bytes.fromhex('70b584b0'), 0x080321B9, 2),
    0x080321BC: (bytes.fromhex('f0b585b0'), 0x080321F1, 3),
    0x080321F4: (bytes.fromhex('70b584b0'), 0x08032225, 2),
}


def arm_code(base=CODE_BASE, state=STATE_BASE, notifications=False, reservations=False):
    if reservations and not notifications:
        raise ValueError('Request reservation experiment requires owned notifications')
    arena_size = REQUEST_STATE_SIZE if reservations else NOTIFICATION_STATE_SIZE if notifications else STATE_SIZE
    if (base % 4 or state % 4 or not 0x0806A570 <= base < 0x08080000
            or not 0x20000000 <= state < state+arena_size <= 0x2004F660
            or not (state+arena_size <= recovery.STATE_BASE
                    or recovery.STATE_BASE+recovery.STATE_SIZE <= state)):
        raise ValueError('Retry experiment outside bounds or overlaps recovery arena')
    _, rp = recovery.arm_code()
    a = Asm(base)
    E = a.emit

    def imm(rd, value):
        E(movw, rd, value & 0xFFFF)
        E(movt, rd, value >> 16)

    def bc(label, condition):
        E(b_cond_w, label, condition)

    def mask(rd):
        E(raw, bytes([0xEF, 0xF3, 0x10, 0x80 | rd]))
        E(raw, bytes.fromhex('72b6'))

    def restore(rn):
        E(raw, bytes([0x80 | rn, 0xF3, 0x10, 0x88]))

    # r0=registered router; returns locked arena or0. Never dereferences r0.
    a.label('sr_lock')
    imm(2, state)
    E(ldr_imm, 1, 2)
    imm(3, MAGIC)
    E(cmp_reg, 1, 3)
    bc('lock_reject', 'ne')
    E(cmp_imm, 0, 0)
    bc('lock_reject', 'eq')
    E(ldr_imm, 1, 2, ROUTER)
    E(cmp_reg, 0, 1)
    bc('lock_reject', 'ne')
    mask(3)
    E(cmp_imm, 3, 0)
    bc('lock_busy', 'ne')
    E(ldrb_imm, 1, 2, BUSY)
    E(cmp_imm, 1, 0)
    bc('lock_busy', 'ne')
    E(movs_imm, 1, 1)
    E(strb_imm, 1, 2, BUSY)
    E(mov_reg, 0, 2)
    restore(3)
    E(bx_lr)
    a.label('lock_busy')
    E(ldrb_imm, 0, 2, ERRORS)
    E(movs_imm, 1, REENTRANT)
    E(orrs_reg, 0, 1)
    E(strb_imm, 0, 2, ERRORS)
    restore(3)
    a.label('lock_reject')
    E(movs_imm, 0, 0)
    E(bx_lr)

    a.label('sr_unlock')
    mask(3)
    E(movs_imm, 1, 0)
    E(strb_imm, 1, 0, BUSY)
    restore(3)
    E(bx_lr)

    # r0=router,r1=mask,r2=descriptor. Reject BEFORE copying if slot owned.
    a.label('sr_submit')
    E(push, [3, 4, 5, 6, 7], lr=True)
    E(mov_reg, 5, 1)
    E(mov_reg, 6, 2)
    E(bl, 'sr_lock')
    E(cmp_imm, 0, 0)
    bc('submit_reject', 'eq')
    E(mov_reg, 4, 0)
    if reservations:
        E(ldr_w, 0, 4, REQUEST)
        E(cmp_imm, 0, 0)
        bc('submit_unreserved', 'eq')
        E(raw, bytes.fromhex('eff30580'))  #mrs r0,IPSR
        E(cmp_imm, 0, 0)
        bc('submit_bad', 'ne')
        E(ldr_sp, 0, 20)  # original LR of this router submission
        a.label('request_submit_return_pointer')
        imm(1, 0)  # resolved after layout to gate_native_return_0804691a|1
        E(cmp_reg, 0, 1)
        bc('submit_bad', 'ne')
        E(ldrb_imm, 0, 4, PRODUCER_BUSY)
        E(cmp_imm, 0, 1)
        bc('submit_bad', 'ne')
        a.label('submit_unreserved')
    E(ldrb_imm, 0, 4, ACTIVE)
    E(cmp_imm, 0, 0)
    bc('submit_bad', 'ne')
    E(movs_imm, 0, 7)
    E(ands_reg, 5, 0)  # stock broadcast0xFF -> the three registered ports
    E(cmp_imm, 5, 0)
    bc('submit_bad', 'eq')
    for n in range(recovery.PORTS):
        E(movs_imm, 0, 1 << n)
        E(tst_reg, 5, 0)
        bc('submit_port_ok_'+str(n), 'eq')
        imm(7, recovery.STATE_BASE+recovery.HEADER_SIZE+n*recovery.ENTRY_SIZE)
        E(ldr_imm, 0, 7)
        E(bl, rp['rp_lookup'])
        E(cmp_reg, 0, 7)
        bc('submit_bad', 'ne')
        E(ldrb_imm, 0, 7, recovery.FLAGS)
        E(movs_imm, 1, recovery.FAULT)
        E(tst_reg, 0, 1)
        bc('submit_bad', 'ne')
        a.label('submit_port_ok_'+str(n))
    E(ldr_imm, 7, 6, 4)
    E(cmp_imm, 7, 2)
    bc('submit_bad', 'lo')
    E(movw, 0, CAPACITY)
    E(cmp_reg, 7, 0)
    bc('submit_bad', 'hi')
    E(ldr_imm, 6, 6)
    E(ldrb_imm, 0, 6)
    E(cmp_imm, 0, 0xF0)
    bc('submit_bad', 'ne')
    E(mov_reg, 2, 7)
    E(subs_imm8, 2, 1)
    E(ldrb_reg, 0, 6, 2)
    E(cmp_imm, 0, 0xF7)
    bc('submit_bad', 'ne')
    E(movs_imm, 1, 1)
    a.label('submit_validate')
    E(cmp_reg, 1, 2)
    bc('submit_copy', 'hs')
    E(ldrb_reg, 0, 6, 1)
    E(cmp_imm, 0, 128)
    bc('submit_bad', 'hs')
    E(adds_imm8, 1, 1)
    E(b, 'submit_validate')
    a.label('submit_copy')
    if notifications:
        E(mov_reg, 0, 4)
        E(bl, 'sr_snapshot_event')
        E(cmp_imm, 0, 0)
        bc('submit_bad', 'eq')
    E(mov_reg, 0, 4)
    E(adds_imm8, 0, PAYLOAD)
    E(mov_reg, 1, 6)
    E(mov_reg, 2, 7)
    E(bl, NATIVE_COPY)  # interrupts enabled, BUSY prevents nested slot reuse
    E(mov_reg, 0, 4)
    E(adds_imm8, 0, PAYLOAD)
    mask(3)
    E(str_imm, 0, 4, DESCRIPTOR)
    E(str_imm, 7, 4, DESCRIPTOR+4)
    E(strb_imm, 5, 4, WAITING)
    E(movs_imm, 0, 0)
    E(strb_imm, 0, 4, ACCEPTED)
    E(strb_imm, 0, 4, FAILED)
    if notifications:
        E(strb_imm, 0, 4, NOTICE)
    E(movs_imm, 1, 1)
    E(strb_imm, 1, 4, ACTIVE)  # publish only after complete payload copy
    restore(3)
    E(movs_imm, 7, 0)
    E(b, 'submit_release')
    a.label('submit_bad')
    mask(3)
    E(ldrb_imm, 0, 4, ERRORS)
    E(movs_imm, 1, REJECTED)
    E(orrs_reg, 0, 1)
    E(strb_imm, 0, 4, ERRORS)
    restore(3)
    E(movs_imm, 7, 1)
    a.label('submit_release')
    E(mov_reg, 0, 4)
    E(bl, 'sr_unlock')
    E(mov_reg, 0, 7)
    E(b, 'submit_return')
    a.label('submit_reject')
    E(movs_imm, 0, 1)
    a.label('submit_return')
    E(pop, [3, 4, 5, 6, 7], pc=True)

    # One attempt per waiting port per invocation; accepted bits NEVER retried.
    # Caller/scheduler invokes again later. No timer or hardware event is faked.
    a.label('sr_service')
    E(push, [3, 4, 5, 6, 7], lr=True)
    E(bl, 'sr_lock')
    E(cmp_imm, 0, 0)
    bc('service_return', 'eq')
    E(mov_reg, 4, 0)
    if reservations:
        E(ldr_w, 0, 4, REQUEST)
        E(cmp_imm, 0, 0)
        bc('service_release', 'ne')  # formatter has not returned yet
    E(ldrb_imm, 0, 4, ACTIVE)
    E(cmp_imm, 0, 0)
    bc('service_release', 'eq')
    E(cmp_imm, 0, 1)
    bc('service_bad', 'ne')
    if notifications:
        E(ldrb_imm, 0, 4, NOTICE)
        E(cmp_imm, 0, 0)
        bc('service_notice_ok', 'eq')
        E(cmp_imm, 0, 3)
        bc('service_bad', 'ne')
        a.label('service_notice_ok')
    E(ldrb_imm, 0, 4, WAITING)
    E(ldrb_imm, 1, 4, ACCEPTED)
    E(tst_reg, 0, 1)
    bc('service_bad', 'ne')
    E(ldrb_imm, 2, 4, FAILED)
    E(bics_reg, 2, 0)
    E(cmp_imm, 2, 0)
    bc('service_bad', 'ne')
    E(orrs_reg, 0, 1)
    E(cmp_imm, 0, 0)
    bc('service_bad', 'eq')
    E(cmp_imm, 0, 7)
    bc('service_bad', 'hi')
    E(ldr_imm, 0, 4, DESCRIPTOR)
    imm(1, state+PAYLOAD)
    E(cmp_reg, 0, 1)
    bc('service_bad', 'ne')
    E(ldr_imm, 0, 4, DESCRIPTOR+4)
    E(cmp_imm, 0, 2)
    bc('service_bad', 'lo')
    E(movw, 1, CAPACITY)
    E(cmp_reg, 0, 1)
    bc('service_bad', 'hi')
    if notifications:
        imm(5, state+EVENT)
        E(ldr_imm, 0, 5)
        imm(1, NATIVE_EVENT_VTABLE)
        E(cmp_reg, 0, 1)
        bc('service_bad', 'ne')
        E(ldrb_imm, 0, 5, 4)
        E(cmp_imm, 0, 3)
        bc('service_bad', 'hi')
    for n in range(recovery.PORTS):
        bit = 1 << n
        suffix = str(n)
        E(ldrb_imm, 0, 4, WAITING)
        E(movs_imm, 6, bit)
        E(tst_reg, 0, 6)
        bc('service_next_'+suffix, 'eq')
        imm(7, recovery.STATE_BASE+recovery.HEADER_SIZE+n*recovery.ENTRY_SIZE)
        E(ldr_imm, 5, 7)
        E(mov_reg, 0, 5)
        E(bl, rp['rp_lookup'])
        E(cmp_reg, 0, 7)
        bc('service_fault_'+suffix, 'ne')
        E(ldrb_imm, 0, 7, recovery.FLAGS)
        E(movs_imm, 1, recovery.FAULT)
        E(tst_reg, 0, 1)
        bc('service_fault_'+suffix, 'ne')
        E(mov_reg, 0, 5)
        E(mov_reg, 1, 4)
        E(adds_imm8, 1, DESCRIPTOR)
        E(bl, rp['rp_sysex_send'])
        E(cmp_imm, 0, 0)
        bc('service_next_'+suffix, 'eq')
        mask(3)
        E(ldrb_imm, 0, 4, WAITING)
        E(bics_reg, 0, 6)
        E(strb_imm, 0, 4, WAITING)
        E(ldrb_imm, 0, 4, ACCEPTED)
        E(orrs_reg, 0, 6)
        E(strb_imm, 0, 4, ACCEPTED)
        restore(3)
        E(b, 'service_next_'+suffix)
        a.label('service_fault_'+suffix)
        mask(3)
        E(ldrb_imm, 0, 4, FAILED)
        E(orrs_reg, 0, 6)
        E(strb_imm, 0, 4, FAILED)
        E(ldrb_imm, 0, 4, ERRORS)
        E(movs_imm, 1, PORT_FAULT)
        E(orrs_reg, 0, 1)
        E(strb_imm, 0, 4, ERRORS)
        restore(3)
        a.label('service_next_'+suffix)
    E(ldrb_imm, 0, 4, WAITING)
    E(cmp_imm, 0, 0)
    bc('service_release', 'ne')
    if notifications:
        # Stock299B0 notifies synchronously at ALL-PORT ADMISSION, before
        # payload drain. Hold queue BUSY/ACTIVE through the entire native fanout.
        E(ldrb_imm, 0, 4, NOTICE)
        E(cmp_imm, 0, 3)
        bc('service_notified', 'eq')
        E(movs_imm, 0, 2)
        E(strb_imm, 0, 4, NOTICE)
        E(ldr_imm, 2, 4, ROUTER)
        E(movs_imm, 0, 1)
        E(strb_imm, 0, 2, 0x19)
        imm(0, state+EVENT)
        E(movs_imm, 1, 0)
        E(bl, NATIVE_NOTIFY)
        E(movs_imm, 0, 3)
        E(strb_imm, 0, 4, NOTICE)
        a.label('service_notified')
    for n in range(recovery.PORTS):
        E(ldrb_imm, 0, 4, ACCEPTED)
        E(movs_imm, 1, 1 << n)
        E(tst_reg, 0, 1)
        bc('service_drained_'+str(n), 'eq')
        imm(0, recovery.STATE_BASE+recovery.HEADER_SIZE+n*recovery.ENTRY_SIZE)
        E(ldr_imm, 0, 0)
        E(bl, rp['rp_sysex_pending'])
        E(cmp_imm, 0, 0)
        bc('service_release', 'ne')
        a.label('service_drained_'+str(n))
    E(movs_imm, 0, 0)
    E(strb_imm, 0, 4, ACTIVE)  # all borrowed payload readers finished
    E(b, 'service_release')
    a.label('service_bad')
    mask(3)
    E(ldrb_imm, 0, 4, ERRORS)
    E(movs_imm, 1, BAD_STATE)
    E(orrs_reg, 0, 1)
    E(strb_imm, 0, 4, ERRORS)
    restore(3)
    a.label('service_release')
    E(mov_reg, 0, 4)
    E(bl, 'sr_unlock')
    E(ldrb_imm, 0, 4, ACTIVE)
    a.label('service_return')
    E(pop, [3, 4, 5, 6, 7], pc=True)

    # r0=arena only if magic is valid, no active transaction/copy/producer and
    # incoming PRIMASK0. Each caller wrapper preserves its native result.
    a.label('sr_producer_begin')
    if reservations:
        E(mov_reg, 12, 0)  # original native call-return PC from4691A gate
    imm(2, state)
    E(ldr_imm, 0, 2)
    imm(1, MAGIC)
    E(cmp_reg, 0, 1)
    bc('producer_reject', 'ne')
    E(ldr_imm, 0, 2, ROUTER)
    E(cmp_imm, 0, 0)
    bc('producer_reject', 'eq')
    imm(1, 0x20006F04)
    E(ldr_imm, 1, 1)
    E(cmp_reg, 0, 1)
    bc('producer_reject', 'ne')
    mask(3)
    E(cmp_imm, 3, 0)
    bc('producer_busy', 'ne')
    E(ldrb_imm, 0, 2, ACTIVE)
    E(ldrb_imm, 1, 2, BUSY)
    E(orrs_reg, 0, 1)
    E(ldrb_imm, 1, 2, PRODUCER_BUSY)
    E(orrs_reg, 0, 1)
    E(cmp_imm, 0, 0)
    bc('producer_busy', 'ne')
    if reservations:
        E(ldr_w, 0, 2, REQUEST)
        E(cmp_imm, 0, 0)
        bc('producer_reservation_ok', 'eq')
        E(cmp_reg, 0, 12)
        bc('producer_busy', 'ne')
        E(raw, bytes.fromhex('eff30580'))  #mrs r0,IPSR
        E(cmp_imm, 0, 0)
        bc('producer_busy', 'ne')
        a.label('producer_reservation_ok')
    E(movs_imm, 0, 1)
    E(strb_imm, 0, 2, PRODUCER_BUSY)
    E(mov_reg, 0, 2)
    restore(3)
    E(bx_lr)
    a.label('producer_busy')
    E(ldrb_imm, 0, 2, ERRORS)
    E(movs_imm, 1, REJECTED)
    E(orrs_reg, 0, 1)
    E(strb_imm, 0, 2, ERRORS)
    restore(3)
    a.label('producer_reject')
    E(movs_imm, 0, 0)
    E(bx_lr)

    if reservations:
        # Reserve capacity BEFORE any upper formatter/source mutation. The
        # five audited entries return failure1 to their original caller if full.
        # This does NOT retrofit retry into the void input registry dispatch.
        a.label('sr_request_begin')
        E(push, [2, 3, 4, 5, 6], lr=True)
        E(mov_reg, 5, 0)
        E(mov_reg, 6, 1)
        E(raw, bytes.fromhex('eff30580'))
        E(cmp_imm, 0, 0)
        bc('request_reject', 'ne')
        for _, return_pc, _ in REQUEST_GATES.values():
            imm(0, return_pc)
            E(cmp_reg, 5, 0)
            bc('request_valid_pc', 'eq')
        E(b, 'request_reject')
        a.label('request_valid_pc')
        imm(0, 0x20006F04)
        E(ldr_imm, 0, 0)
        E(bl, 'sr_lock')
        E(cmp_imm, 0, 0)
        bc('request_reject', 'eq')
        E(mov_reg, 4, 0)
        E(ldrb_imm, 0, 4, ACTIVE)
        E(ldrb_imm, 1, 4, PRODUCER_BUSY)
        E(orrs_reg, 0, 1)
        E(cmp_imm, 0, 0)
        bc('request_full', 'ne')
        E(ldr_w, 0, 4, REQUEST)
        E(cmp_imm, 0, 0)
        bc('request_full', 'ne')
        E(movs_imm, 0, 7)
        E(ands_reg, 6, 0)
        E(cmp_imm, 6, 0)
        bc('request_full', 'eq')
        for n in range(recovery.PORTS):
            E(movs_imm, 0, 1 << n)
            E(tst_reg, 6, 0)
            bc('request_port_ok_'+str(n), 'eq')
            imm(0, recovery.STATE_BASE+recovery.HEADER_SIZE+n*recovery.ENTRY_SIZE)
            E(ldr_imm, 0, 0)
            E(bl, rp['rp_lookup'])
            E(cmp_imm, 0, 0)
            bc('request_full', 'eq')
            E(ldrb_imm, 0, 0, recovery.FLAGS)
            E(movs_imm, 1, recovery.FAULT)
            E(tst_reg, 0, 1)
            bc('request_full', 'ne')
            a.label('request_port_ok_'+str(n))
        mask(3)
        E(str_w, 5, 4, REQUEST)
        restore(3)
        E(mov_reg, 5, 4)
        E(b, 'request_release')
        a.label('request_full')
        mask(3)
        E(ldrb_imm, 0, 4, ERRORS)
        E(movs_imm, 1, REJECTED)
        E(orrs_reg, 0, 1)
        E(strb_imm, 0, 4, ERRORS)
        restore(3)
        E(movs_imm, 5, 0)
        a.label('request_release')
        E(mov_reg, 0, 4)
        E(bl, 'sr_unlock')
        E(mov_reg, 0, 5)
        E(b, 'request_return')
        a.label('request_reject')
        E(movs_imm, 0, 0)
        a.label('request_return')
        E(pop, [2, 3, 4, 5, 6], pc=True)

    if notifications:
        # Snapshot the fixed stock event registry and global owner atomically.
        # Native scatter-load initializes its vtable; registration supports3
        # listeners. No general arbitrary object/registry is accepted here.
        a.label('sr_snapshot_event')
        E(push, [3, 4, 5, 6, 7], lr=True)
        E(mov_reg, 4, 0)
        E(ldr_imm, 0, 4, ROUTER)
        E(ldr_imm, 0, 0, 0x20)
        imm(1, NATIVE_EVENT)
        E(cmp_reg, 0, 1)
        bc('snapshot_reject', 'ne')
        imm(0, state+EVENT)
        imm(6, NATIVE_EVENT_VTABLE)
        mask(7)
        E(ldr_imm, 2, 1)
        E(cmp_reg, 2, 6)
        bc('snapshot_masked_reject', 'ne')
        E(ldrb_imm, 2, 1, 4)
        E(cmp_imm, 2, 3)
        bc('snapshot_masked_reject', 'hi')
        # LDMIA r1!,{r2,r3,r5,r6}; STMIA r0!,{r2,r3,r5,r6}, twice.
        E(raw, bytes.fromhex('6cc96cc06cc96cc0'))
        imm(2, NATIVE_OWNER)
        E(ldr_imm, 3, 2)
        E(ldr_imm, 5, 2, 4)
        E(str_w, 3, 4, OWNER_FN)
        E(str_w, 5, 4, OWNER_CTX)
        restore(7)
        # Preserve ordinary listeners/context. Replace only the global-owner
        # adapter with a transaction-owned adapter in the PRIVATE event copy.
        imm(5, state+EVENT)
        imm(6, NATIVE_OWNER_ADAPTER)
        for n in range(3):
            E(ldr_imm, 0, 5, 8+n*4)
            E(cmp_reg, 0, 6)
            bc('snapshot_next_'+str(n), 'ne')
            a.label('snapshot_adapter_pointer_'+str(n))
            imm(0, 0)  # resolved below after final label layout
            E(str_imm, 0, 5, 8+n*4)
            E(str_imm, 4, 5, 0x14+n*4)
            a.label('snapshot_next_'+str(n))
        E(movs_imm, 0, 1)
        E(b, 'snapshot_return')
        a.label('snapshot_masked_reject')
        restore(7)
        a.label('snapshot_reject')
        E(movs_imm, 0, 0)
        a.label('snapshot_return')
        E(pop, [3, 4, 5, 6, 7], pc=True)

        # Native24B68 supplies r0=event0,r1=router,r2=listener context.
        # The private event binds r2 to the owned arena. Match468EC's uxtb ABI.
        a.label('sr_owned_callback')
        E(push, [4], lr=True)
        E(ldr_w, 4, 2, OWNER_FN)
        E(cmp_imm, 4, 0)
        bc('owned_callback_return', 'eq')
        E(ldr_w, 1, 2, OWNER_CTX)
        E(raw, bytes.fromhex('c0b2'))  # uxtb r0,r0
        E(mov_reg, 2, 4)  #468EC leaves its owner function pointer in r2
        a.label('owned_callback_call')
        E(blx_reg, 4)
        a.label('owned_callback_return')
        E(pop, [4], pc=True)

    for entry, expected in CALLER_GATES.items():
        suffix = f'{entry:08x}'
        a.label('sr_gate_'+suffix)
        E(push, list(range(7)), lr=True)  #32B, original r0-r3 on stack
        if reservations:
            if entry == 0x0804691A:
                E(ldr_sp, 0, 28)
            else:
                E(movs_imm, 0, 0)
        E(bl, 'sr_producer_begin')
        E(cmp_imm, 0, 0)
        bc('gate_reject_'+suffix, 'eq')
        E(mov_reg, 4, 0)
        for reg in range(4):
            E(ldr_sp, reg, reg*4)
        E(bl, 'caller_trampoline_'+suffix)
        a.label('gate_native_return_'+suffix)
        E(str_sp, 0)  # retain the exact native return, including discarded r0
        mask(3)
        E(movs_imm, 1, 0)
        E(strb_imm, 1, 4, PRODUCER_BUSY)
        restore(3)
        E(b, 'gate_return_'+suffix)
        a.label('gate_reject_'+suffix)
        E(movs_imm, 0, 1)
        E(str_sp, 0)
        a.label('gate_return_'+suffix)
        E(pop, list(range(7)), pc=True)

    if reservations:
        for entry, (_, return_pc, stack_words) in REQUEST_GATES.items():
            suffix = f'{entry:08x}'
            a.label('sr_request_gate_'+suffix)
            E(push, list(range(7)), lr=True)
            E(sub_sp_imm, 16)  # native outgoing stack arguments,8-byte alignment
            imm(0, return_pc)
            E(ldr_sp, 1, 20)  # original native port mask
            E(bl, 'sr_request_begin')
            E(cmp_imm, 0, 0)
            bc('request_gate_reject_'+suffix, 'eq')
            E(mov_reg, 4, 0)
            for n in range(stack_words):
                E(ldr_sp, 0, 48+n*4)
                E(str_sp, 0, n*4)
            for n in range(4):
                E(ldr_sp, n, 16+n*4)
            E(bl, 'request_trampoline_'+suffix)
            E(str_sp, 0, 16)
            mask(3)
            E(movs_imm, 0, 0)
            E(str_w, 0, 4, REQUEST)
            restore(3)
            E(b, 'request_gate_return_'+suffix)
            a.label('request_gate_reject_'+suffix)
            E(movs_imm, 0, 1)
            E(str_sp, 0, 16)
            a.label('request_gate_return_'+suffix)
            E(add_sp_imm, 16)
            E(pop, list(range(7)), pc=True)

    for entry, expected in CALLER_GATES.items():
        a.label(f'caller_trampoline_{entry:08x}')
        if entry == 0x0802DE84:
            imm(0, 0x20006F04)
            E(mov_reg, 2, 1)
        elif entry == 0x0802ED88:
            E(push, [4, 5])
            imm(3, 0x20006F58)
        else:
            E(raw, expected)
        E(b_w, entry+4)
    if reservations:
        for entry, (original, _, _) in REQUEST_GATES.items():
            a.label(f'request_trampoline_{entry:08x}')
            E(raw, original)
            E(b_w, entry+4)
    code, labels = a.assemble()
    if notifications:
        generated = bytearray(code)
        pointer = labels['sr_owned_callback'] | 1
        for n in range(3):
            offset = labels['snapshot_adapter_pointer_'+str(n)]-base
            assert generated[offset:offset+8] == movw(0, 0)+movt(0, 0)
            generated[offset:offset+8] = movw(0, pointer & 0xFFFF)+movt(0, pointer >> 16)
        code = bytes(generated)
    if reservations:
        generated = bytearray(code)
        offset = labels['request_submit_return_pointer']-base
        assert generated[offset:offset+8] == movw(1, 0)+movt(1, 0)
        pointer = labels['gate_native_return_0804691a'] | 1
        generated[offset:offset+8] = movw(1, pointer & 0xFFFF)+movt(1, pointer >> 16)
        code = bytes(generated)
    if (base+len(code) > 0x08080000 or
            base < recovery.CODE_BASE+len(recovery.arm_code()[0]) and
            recovery.CODE_BASE < base+len(code)):
        raise ValueError('Retry code exceeds flash bounds or overlaps recovery code')
    return code, labels
