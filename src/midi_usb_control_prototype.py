"""EMULATION ONLY: deferred native MIDI class reconfiguration after barrier.

IRQ reset/deinit freezes admission immediately; main service owns cancellation.
Native class init is queued, then runs after SEALED, before controlled resume.
No production patch builder imports this. Hardware cancellation is a contract.
"""
import midi_usb_irq_prototype as irq
import midi_usb_session_prototype as session
import midi_usb_lifecycle_prototype as life
from thumb_asm import (Asm, adds_imm8, ands_reg, b, b_cond_w, b_w, bics_reg, bl,
                       bx_lr, cmp_imm, cmp_reg, ldr_imm, ldr_sp, ldr_w, ldrb_w,
                       mov_reg, movs_imm, orrs_reg, pop, push, raw, str_imm,
                       tst_reg)

CODE_BASE, STATE_BASE, STATE_SIZE = 0x08079C00,0x20047F80,96
MAGIC=0x31434355  # UCC1
HANDLE, CONTROLLER, CLASS, FLAGS, BUSY, INIT_BUSY, CONFIG = 4,8,12,16,20,24,28
ERRORS, REQUESTS, RESTARTS, IRQ_DEPTH, RESET_SEEN, DEINIT_SEEN, INIT_SEEN = 32,36,40,44,48,52,56
INIT_DONE=60
RX_PAUSED=64
RESET_EVENT, DEINIT_EVENT, INIT_EVENT, PENDING = 1,2,4,8
CONTROL_GINT = irq.ALLOWED_GINT|(1<<3)|(1<<12)|(1<<13)
GATES={irq.NATIVE_IRQ:irq.IRQ_PROLOGUE,0x080525B2:bytes.fromhex('2de9f041'),
       0x0805261C:irq.GATES[0x0805261C],0x080268D0:irq.GATES[0x080268D0],
       0x0802C928:bytes.fromhex('80b5d0f89802'),
       0x080268EC:bytes.fromhex('38b50546'),
       0x0802C9D4:session.gates()[0x0802C9D4][2],
       0x080269AC:life.GATES[0x080269AC][2]}


def irq_variant():
    return irq.arm_code(allowed_gint=CONTROL_GINT,max_phase=session.SEALED)


def arm_code(base=CODE_BASE,state=STATE_BASE):
    ic,ib=irq_variant(); _,ss=session.arm_code()
    if (base%4 or state%4 or not irq.CODE_BASE+len(ic)<=base<0x08080000
            or not irq.STATE_BASE+irq.STATE_SIZE<state<state+STATE_SIZE<0x20048000):
        raise ValueError('Control code/state overlaps or exceeds bounds')
    a=Asm(base); E=a.emit
    def imm(r,v): a.imm32(r,v)
    def bc(label,cond): E(b_cond_w,label,cond)
    def field(off,r=0): E(ldr_imm,r,4,off)
    def mask(): E(raw,bytes.fromhex('eff3108372b6'))
    def restore(): E(raw,bytes.fromhex('83f31088'))
    def main(fail):
        E(raw,bytes.fromhex('eff31080')); E(cmp_imm,0,0); bc(fail,'ne')
        E(raw,bytes.fromhex('eff30580')); E(cmp_imm,0,0); bc(fail,'ne')
        imm(4,state); field(0); imm(1,MAGIC); E(cmp_reg,0,1); bc(fail,'ne')
        field(BUSY); E(cmp_imm,0,0); bc(fail,'ne')
    def fail_closed():
        E(movs_imm,0,1); E(str_imm,0,4,ERRORS)
        imm(1,session.STATE_BASE); E(movs_imm,0,session.BROKEN); E(str_imm,0,1,session.PHASE)
        imm(1,life.STATE_BASE); E(movs_imm,0,life.FROZEN); E(str_imm,0,1,life.PHASE)

    # r0=event reason. This does not clear a queue, payload, held note or epoch.
    a.label('cc_request')
    E(push,[3,4,5],lr=True); E(mov_reg,5,0); imm(4,state)
    field(0); imm(1,MAGIC); E(cmp_reg,0,1); bc('request_no','ne')
    mask(); field(REQUESTS); imm(1,0xFFFFFFFF); E(cmp_reg,0,1); bc('request_wrap','eq')
    E(adds_imm8,0,1); E(str_imm,0,4,REQUESTS)
    E(movs_imm,0,0); E(str_imm,0,4,INIT_DONE); E(str_imm,0,4,RX_PAUSED)
    field(FLAGS); E(cmp_imm,5,INIT_EVENT); bc('request_keep_pending','eq')
    E(movs_imm,1,PENDING); E(bics_reg,0,1)
    a.label('request_keep_pending'); E(orrs_reg,0,5); E(str_imm,0,4,FLAGS)
    imm(1,irq.STATE_BASE); E(movs_imm,0,1); E(str_imm,0,1,irq.INVALID)
    imm(1,session.STATE_BASE); E(ldr_imm,0,1,session.PHASE)
    E(cmp_imm,0,session.BROKEN); bc('request_restore_no','eq')
    E(cmp_imm,0,session.SEALED); bc('request_freeze','ne')
    field(INIT_BUSY); E(cmp_imm,0,0); bc('request_already_sealed','eq')
    a.label('request_freeze')
    E(movs_imm,0,session.CLOSING); E(str_imm,0,1,session.PHASE)
    imm(1,life.STATE_BASE); E(movs_imm,0,life.FROZEN); E(str_imm,0,1,life.PHASE)
    a.label('request_already_sealed'); restore(); E(movs_imm,0,0); E(pop,[3,4,5],pc=True)
    a.label('request_restore_no'); restore(); E(b,'request_no')
    a.label('request_wrap'); restore(); fail_closed()
    a.label('request_no'); E(movs_imm,0,1); E(pop,[3,4,5],pc=True)

    # Handle-scoped IRQ preflight: reset must invalidate completion snapshots
    # before stock4293E observes the coalesced causes.
    a.label('cc_irq')
    E(push,[3,4,5],lr=True); E(mov_reg,5,0); imm(4,state)
    field(HANDLE,1); E(cmp_reg,0,1); bc('irq_forward','ne')
    field(0); imm(1,MAGIC); E(cmp_reg,0,1); bc('irq_no','ne')
    field(IRQ_DEPTH); E(cmp_imm,0,0); bc('irq_no','ne')
    E(movs_imm,0,1); E(str_imm,0,4,IRQ_DEPTH)
    E(ldr_imm,1,5); E(ldr_w,0,1,0x14); E(ldr_w,1,1,0x18); E(ands_reg,0,1)
    imm(1,1<<12); E(tst_reg,0,1); bc('irq_body','eq')
    field(RESET_SEEN); E(adds_imm8,0,1); E(str_imm,0,4,RESET_SEEN)
    E(movs_imm,0,RESET_EVENT); E(bl,'cc_request'); E(cmp_imm,0,0); bc('irq_finish_no','ne')
    a.label('irq_body'); E(mov_reg,0,5); E(bl,ib['ib_irq']); E(mov_reg,5,0)
    E(movs_imm,0,0); E(str_imm,0,4,IRQ_DEPTH); E(mov_reg,0,5); E(pop,[3,4,5],pc=True)
    a.label('irq_finish_no'); E(movs_imm,0,0); E(str_imm,0,4,IRQ_DEPTH)
    a.label('irq_no'); E(movs_imm,0,1); E(pop,[3,4,5],pc=True)
    a.label('irq_forward'); E(mov_reg,0,5); E(pop,[3,4,5],lr=True); E(b_w,ib['ib_irq'])

    # Bound class/controller only. Native configuration1 is queued, not run in
    # an IRQ while an old hardware job can still own the staging buffer.
    a.label('cc_init')
    E(push,[3,4,5,6,7],lr=True); imm(4,state)
    field(CLASS,3); E(cmp_reg,0,3); bc('init_foreign','ne')
    field(CONTROLLER,3); E(cmp_reg,1,3); bc('init_foreign','ne')
    field(0,3); imm(5,MAGIC); E(cmp_reg,3,5); bc('init_no','ne')
    E(cmp_imm,2,1); bc('init_no','ne')
    field(INIT_BUSY); E(cmp_imm,0,0); bc('init_no','ne')
    field(FLAGS); E(movs_imm,1,PENDING); E(tst_reg,0,1); bc('init_ok','ne')
    E(movs_imm,0,INIT_EVENT); E(bl,'cc_request'); E(cmp_imm,0,0); bc('init_no','ne')
    E(movs_imm,0,1); E(str_imm,0,4,CONFIG)
    field(FLAGS); E(movs_imm,1,PENDING); E(orrs_reg,0,1); E(str_imm,0,4,FLAGS)
    field(INIT_SEEN); E(adds_imm8,0,1); E(str_imm,0,4,INIT_SEEN)
    a.label('init_ok'); E(movs_imm,0,0); E(pop,[3,4,5,6,7],pc=True)
    a.label('init_no'); E(movs_imm,0,1); E(pop,[3,4,5,6,7],pc=True)
    a.label('init_foreign'); E(pop,[3,4,5,6,7],lr=True); E(b_w,'cc_native_init')
    a.label('cc_native_init'); E(raw,GATES[0x080525B2]); E(b_w,0x080525B6)

    a.label('cc_deinit')
    E(push,[0,1,2,3,4,5,6],lr=True); imm(4,state)
    field(0,3); imm(5,MAGIC); E(cmp_reg,3,5); bc('deinit_forward','ne')
    field(CLASS,3); E(cmp_reg,0,3); bc('deinit_forward','ne')
    field(CONTROLLER,3); E(cmp_reg,1,3); bc('deinit_forward','ne')
    field(DEINIT_SEEN); E(adds_imm8,0,1); E(str_imm,0,4,DEINIT_SEEN)
    E(movs_imm,0,DEINIT_EVENT); E(bl,'cc_request')
    a.label('deinit_forward'); E(pop,[0,1,2,3,4,5,6],lr=True)
    E(b_w,ib['ib_native_disconnect'])

    # 525FE bootstrap is an availability initialization, not wire completion.
    a.label('cc_tx_callback')
    E(push,[0,1,2,3,4,5,6],lr=True); imm(4,state)
    imm(5,session.STATE_BASE); E(ldr_imm,1,5,session.TX_ENDPOINT)
    E(cmp_reg,0,1); bc('tx_normal','ne')
    field(0); imm(1,MAGIC); E(cmp_reg,0,1); bc('tx_normal','ne')
    field(INIT_BUSY); E(cmp_imm,0,1); bc('tx_normal','ne')
    E(ldr_sp,0,28); imm(1,0x08052603); E(cmp_reg,0,1); bc('tx_deny','ne')
    E(ldr_imm,0,5,session.PHASE); E(cmp_imm,0,session.SEALED); bc('tx_deny','ne')
    E(ldr_imm,0,5,session.TX_ACTIVE); E(cmp_imm,0,0); bc('tx_deny','ne')
    E(pop,[0,1,2,3,4,5,6],lr=True); E(b_w,ss['ss_native_080268d0'])
    a.label('tx_deny'); E(pop,[0,1,2,3,4,5,6],lr=True); E(movs_imm,0,0); E(bx_lr)
    a.label('tx_normal'); E(pop,[0,1,2,3,4,5,6],lr=True); E(b_w,ib['ib_tx_callback'])

    # Native525B2's OUT flush is GLOBAL RX flush. The completed MIDI barrier
    # already owns quiescence; do not erase another interface's shared FIFO.
    a.label('cc_flush')
    E(push,[0,1,2,3,4,5,6],lr=True); imm(4,state)
    field(CONTROLLER,3); E(cmp_reg,0,3); bc('flush_foreign','ne')
    E(cmp_imm,1,1); bc('flush_foreign','ne')
    field(INIT_BUSY); E(cmp_imm,0,1); bc('flush_foreign','ne')
    field(0); imm(1,MAGIC); E(cmp_reg,0,1); bc('flush_bad','ne')
    E(ldr_sp,0,28); imm(1,0x080525CB); E(cmp_reg,0,1); bc('flush_bad','ne')
    imm(1,session.STATE_BASE); E(ldr_imm,0,1,session.PHASE)
    E(cmp_imm,0,session.SEALED); bc('flush_cancelled','ne')
    E(ldr_imm,0,1,session.RX_ACTIVE); E(cmp_imm,0,0); bc('flush_bad','ne')
    E(pop,[0,1,2,3,4,5,6],lr=True); E(movs_imm,0,0); E(bx_lr)
    a.label('flush_cancelled'); E(pop,[0,1,2,3,4,5,6],lr=True); E(movs_imm,0,1); E(bx_lr)
    a.label('flush_bad'); fail_closed(); E(pop,[0,1,2,3,4,5,6],lr=True); E(movs_imm,0,1); E(bx_lr)
    a.label('flush_foreign'); E(pop,[0,1,2,3,4,5,6],lr=True)
    a.label('cc_native_flush'); E(raw,GATES[0x0802C928]); E(b_w,0x0802C92E)

    # Native SOF268EC publishes partial bytes via2691E, bypassing completion
    # ownership. One-MTU RX jobs complete every USB packet; do not split them
    # into extra FIFO records behind the session/ledger's reservation.
    a.label('cc_rx_poll')
    E(push,[0,1,2,3,4,5,6],lr=True); imm(4,session.STATE_BASE)
    E(ldr_imm,1,4,session.RX_PORT); E(cmp_reg,0,1); bc('rx_poll_foreign','ne')
    E(pop,[0,1,2,3,4,5,6],lr=True); E(movs_imm,0,0); E(bx_lr)
    a.label('rx_poll_foreign'); E(pop,[0,1,2,3,4,5,6],lr=True)
    a.label('cc_native_rx_poll'); E(raw,GATES[0x080268EC]); E(b_w,0x080268F0)

    a.label('cc_rx_submit')
    E(push,[0,1,2,3,4,5,6],lr=True); imm(4,state)
    field(CONTROLLER,2); E(cmp_reg,0,2); bc('rx_submit_foreign','ne')
    E(cmp_imm,1,1); bc('rx_submit_foreign','ne')
    E(ldr_sp,3,12); E(cmp_imm,3,64); bc('rx_submit_no','lo')
    E(pop,[0,1,2,3,4,5,6],lr=True); E(movs_imm,3,64); E(b_w,ss['ss_gate_0802c9d4'])
    a.label('rx_submit_no'); E(pop,[0,1,2,3,4,5,6],lr=True); E(movs_imm,0,1); E(bx_lr)
    a.label('rx_submit_foreign'); E(pop,[0,1,2,3,4,5,6],lr=True); E(b_w,ss['ss_gate_0802c9d4'])

    # Reserve a job only when one complete MTU record fits. Otherwise leave
    # RX unarmed, with explicit pause ownership, until main service retries.
    a.label('cc_rx_rearm')
    E(push,[0,1,2,3,4,5,6],lr=True); imm(4,state); imm(6,session.STATE_BASE)
    E(ldr_imm,1,6,session.RX_PORT); E(cmp_reg,0,1); bc('rearm_forward','ne')
    E(ldr_imm,0,6,session.PHASE); E(cmp_imm,0,session.OPEN); bc('rearm_forward','ne')
    E(ldr_imm,0,6,session.RX_ACTIVE); E(cmp_imm,0,1); bc('rearm_forward','eq')
    E(cmp_imm,0,0); bc('rearm_capacity','eq')
    E(cmp_imm,0,2); bc('rearm_forward','ne')
    E(ldr_sp,0,28); imm(1,ss['ss_rx_done_after_native']|1); E(cmp_reg,0,1); bc('rearm_forward','ne')
    a.label('rearm_capacity')
    E(ldr_imm,0,6,session.RX_PORT); E(ldr_imm,0,0,24); E(bl,0x0802A39E)
    E(cmp_imm,0,66); bc('rearm_ready','hs')
    E(movs_imm,0,0); E(str_imm,0,6,session.RX_ACTIVE)
    E(movs_imm,0,1); E(str_imm,0,4,RX_PAUSED)
    E(pop,[0,1,2,3,4,5,6],lr=True); E(movs_imm,0,0); E(bx_lr)
    a.label('rearm_ready'); E(movs_imm,0,0); E(str_imm,0,4,RX_PAUSED)
    a.label('rearm_forward'); E(pop,[0,1,2,3,4,5,6],lr=True); E(b_w,ss['ss_gate_080269ac'])

    a.label('cc_service')
    E(push,[3,4,5,6,7],lr=True); main('service_no')
    imm(1,irq.STATE_BASE); E(ldr_imm,0,1,irq.ACTIVE); E(cmp_imm,0,0); bc('service_no','ne')
    field(IRQ_DEPTH); E(cmp_imm,0,0); bc('service_no','ne')
    field(FLAGS); E(cmp_imm,0,0); bc('service_rx_pause','eq')
    E(movs_imm,0,1); E(str_imm,0,4,BUSY); field(REQUESTS,7)
    imm(6,session.STATE_BASE); E(ldr_imm,0,6,session.PHASE)
    E(cmp_imm,0,session.SEALED); bc('service_sealed','eq')
    E(bl,ss['ss_step']); field(REQUESTS); E(cmp_reg,0,7); bc('service_restart','ne')
    E(ldr_imm,0,6,session.PHASE); E(cmp_imm,0,session.SEALED); bc('service_wait','ne')
    a.label('service_sealed')
    field(FLAGS); E(movs_imm,1,PENDING); E(tst_reg,0,1); bc('service_closed','eq')
    field(CONTROLLER); E(ldrb_w,0,0,0x274); E(cmp_imm,0,3); bc('service_wait','ne')
    E(bl,ss['ss_binding']); E(cmp_imm,0,1); bc('service_bad','ne')
    E(bl,ss['ss_quiet']); E(cmp_imm,0,1); bc('service_wait','ne')
    field(INIT_DONE); E(cmp_imm,0,1); bc('service_resume','eq')
    # Recheck the barrier before allowing native endpoint reconfiguration.
    E(ldr_imm,5,6,session.USB_BASE)
    for reg,bits in ((session.IN_CTL,session.EPENA),(session.OUT_CTL,session.EPENA),
                     (session.IN_INT,3),(session.OUT_INT,3),(session.GRSTCTL,0x30),(session.GINTSTS,16)):
        E(ldr_w,0,5,reg); imm(1,bits); E(tst_reg,0,1); bc('service_wait','ne')
    E(movs_imm,0,1); E(str_imm,0,4,INIT_BUSY)
    field(CLASS); field(CONTROLLER,1); field(CONFIG,2); E(bl,'cc_native_init')
    E(mov_reg,5,0); E(movs_imm,0,0); E(str_imm,0,4,INIT_BUSY)
    field(REQUESTS); E(cmp_reg,0,7); bc('service_restart','ne')
    E(cmp_imm,5,0); bc('service_bad','ne')
    E(movs_imm,0,1); E(str_imm,0,4,INIT_DONE)
    a.label('service_resume')
    E(ldr_imm,5,6,session.USB_BASE)
    for reg,save in ((session.DAINTMSK,session.DAINT),(session.DEACHMSK,session.DEACH)):
        E(ldr_w,0,5,reg); imm(1,session.MIDI_MASK); E(ands_reg,0,1); E(str_imm,0,6,save)
    E(bl,ss['ss_resume']); E(cmp_imm,0,0); bc('service_wait','ne')
    field(REQUESTS); E(cmp_reg,0,7); bc('service_restart','ne')
    field(RESTARTS); E(adds_imm8,0,1); E(str_imm,0,4,RESTARTS)
    a.label('service_closed')
    mask(); field(REQUESTS); E(cmp_reg,0,7); bc('service_commit_race','ne')
    E(movs_imm,0,0); E(str_imm,0,4,FLAGS); E(str_imm,0,4,BUSY); restore()
    a.label('service_done'); E(movs_imm,0,0); E(pop,[3,4,5,6,7],pc=True)
    a.label('service_restart')
    E(movs_imm,0,session.CLOSING); E(str_imm,0,6,session.PHASE)
    imm(1,life.STATE_BASE); E(movs_imm,0,life.FROZEN); E(str_imm,0,1,life.PHASE)
    E(b,'service_wait')
    a.label('service_commit_race'); restore(); E(b,'service_restart')
    a.label('service_rx_pause')
    field(RX_PAUSED); E(cmp_imm,0,1); bc('service_done','ne')
    imm(1,session.STATE_BASE); E(ldr_imm,0,1,session.RX_PORT); E(bl,'cc_rx_rearm')
    field(RX_PAUSED); E(cmp_imm,0,0); bc('service_no','ne'); E(b,'service_done')
    a.label('service_bad'); fail_closed()
    a.label('service_wait'); E(movs_imm,0,0); E(str_imm,0,4,BUSY)
    a.label('service_no'); E(movs_imm,0,1); E(pop,[3,4,5,6,7],pc=True)
    code,labels=a.assemble()
    if base+len(code)>0x08080000: raise ValueError('Control code exceeds application flash')
    return code,labels
