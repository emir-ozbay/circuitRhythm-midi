"""EMULATION ONLY: cancel an MSC CBW receive before native USB teardown/reset.

CPU FIFO + explicit disable/ACK/AHB/flush contract. Storage commands already
executing, TX/data phases, full boot/task wiring and real silicon are unproven.
"""
import midi_usb_composite_prototype as composite
import midi_usb_control_prototype as control
import midi_usb_irq_prototype as irq
import midi_usb_lifecycle_prototype as life
import midi_usb_session_prototype as session
from thumb_asm import (Asm, adds_imm8, adds_reg, ands_reg, b, b_cond_w, b_w, bics_reg,
                       bl, bx_lr, cmp_imm, cmp_reg, ldr_imm, ldr_sp, ldr_w,
                       ldrb_w, mov_reg, movs_imm, orrs_reg, pop, push, raw,
                       str_imm, str_w, str_sp, strb_imm, tst_reg, lsrs_imm, lsls_imm)

CODE_BASE, STATE_BASE, STATE_SIZE = 0x0807A800,0x20048020,256
MAGIC=0x3143534D
HANDLE,CONTROLLER,ROOT,RX_PORT,TX_PORT=4,8,12,16,20
PHASE,OP,BUSY,TASK_BUSY,ARM_BUSY,NATIVE_TEAR,NATIVE_RESET,TEAR_CFG=24,28,32,36,40,44,48,52
NEED_ACK,DAINT,DEACH,EMP,EPOCH,NEXT,RX_ACTIVE,RX_TICKET,RX_BUFFER,RX_LENGTH=56,60,64,68,72,76,80,84,88,92
CANCEL_RX,ERRORS,IRQ_ACTIVE,RX_VALID,RX_SEEN,SNAP_EPOCH,SNAP_TICKET=96,100,104,108,112,116,120
SCRATCH,RESET_DONE,IRQ_DONE,SUBMITS,TEARDOWNS,BLOCKED=128,192,196,200,204,208
OPEN,CLOSING,WAIT_DISABLE,WAIT_FLUSH,SEALED,BROKEN=1,2,3,4,5,6
TEARDOWN,BOT_RESET,CONFIGURE=1,2,4
CBW,BOT=0x20006CB0,0x20006DD4
IN_CTL,IN_INT,OUT_CTL,OUT_INT,MASK=0x940,0x948,0xB40,0xB48,0x40004
GATES={0x08040B5A:composite.GATES[0x08040B5A],0x08040B7E:bytes.fromhex('f8b50446'),
       irq.NATIVE_IRQ:irq.IRQ_PROLOGUE,0x08026988:irq.GATES[0x08026988],
       0x0802C9D4:control.GATES[0x0802C9D4],0x0802EFF8:bytes.fromhex('5b490022'),
       0x08027624:bytes.fromhex('10b507f098fc'),0x0802F014:bytes.fromhex('10b50446'),
       0x0802F04A:bytes.fromhex('70b50446'),0x080531CC:bytes.fromhex('d21c9208')}


def generated_gates():
    code,cc=control.arm_code()
    return {cc['cc_request']:(code[cc['cc_request']-control.CODE_BASE:cc['cc_request']-control.CODE_BASE+4],'mc_cc_request'),
            cc['cc_service']:(code[cc['cc_service']-control.CODE_BASE:cc['cc_service']-control.CODE_BASE+6],'mc_service')}


def arm_code(base=CODE_BASE,state=STATE_BASE,storage_policy=None,storage_finalize=None,class_policy=None,config_ready=None):
    old,xc=composite.arm_code(); cc_code,cc=control.arm_code(); _,ss=session.arm_code()
    if (base%4 or state%4 or base<composite.CODE_BASE+len(old)
            or not 0x20048004<=state<state+STATE_SIZE<=0x20048200):
        raise ValueError('MSC code/state overlaps or exceeds bounds')
    if (storage_policy is None)!=(storage_finalize is None):
        raise ValueError('Both storage policy hooks are required')
    if storage_policy is not None and any(not isinstance(p,int) or p%2 or not 0x08010200<=p<0x08080000
                                          for p in (storage_policy,storage_finalize)):
        raise ValueError('Storage policy hooks must be aligned application addresses')
    if (class_policy is None)!=(config_ready is None): raise ValueError('Both class policy hooks are required')
    if class_policy is not None and any(not isinstance(p,int) or p%2 or not 0x08010200<=p<0x08080000
                                      for p in (class_policy,config_ready)):
        raise ValueError('Class policy hooks must be aligned application addresses')
    a=Asm(base); E=a.emit
    def imm(r,v): a.imm32(r,v)
    def bc(label,c): E(b_cond_w,label,c)
    def field(off,r=0): E(ldr_imm if off<=124 else ldr_w,r,4,off)
    def put(off,r=0): E(str_imm if off<=124 else str_w,r,4,off)
    def mask(): E(raw,bytes.fromhex('eff3108372b6'))
    def restore(): E(raw,bytes.fromhex('83f31088'))
    def native(name,address):
        a.label(name); E(raw,GATES[address]); E(b_w,address+len(GATES[address]))
    def bad():
        E(movs_imm,0,1); put(ERRORS); E(movs_imm,0,BROKEN); put(PHASE)
        imm(1,session.STATE_BASE); E(movs_imm,0,session.CLOSING); E(str_imm,0,1,session.PHASE)
        imm(1,life.STATE_BASE); E(movs_imm,0,life.FROZEN); E(str_imm,0,1,life.PHASE)
    def changed(label):
        imm(1,control.STATE_BASE); E(ldr_imm,0,1,control.REQUESTS); E(cmp_reg,0,7); bc(label,'ne')
    def main(fail):
        E(raw,bytes.fromhex('eff31080')); E(cmp_imm,0,0); bc(fail,'ne')
        E(raw,bytes.fromhex('eff30580')); E(cmp_imm,0,0); bc(fail,'ne')
        imm(4,state); field(0); imm(1,MAGIC); E(cmp_reg,0,1); bc(fail,'ne')
    def phase(fail,value=SEALED): field(PHASE); E(cmp_imm,0,value); bc(fail,'ne')

    # Every control generation first freezes MSC admission. Only our deferred
    # native teardown may swallow its own redundant MIDI deinit notification.
    a.label('mc_cc_request')
    E(push,[0,1,2,3,4,5,6],lr=True); E(mov_reg,6,0); imm(4,state)
    field(0); imm(1,MAGIC); E(cmp_reg,0,1); bc('request_forward','ne')
    E(cmp_imm,6,control.DEINIT_EVENT); bc('request_not_internal','ne')
    field(NATIVE_TEAR); E(cmp_imm,0,1); bc('request_not_internal','ne')
    E(raw,bytes.fromhex('eff30580')); E(cmp_imm,0,0); bc('request_not_internal','ne')
    E(ldr_sp,0,28); imm(1,cc['cc_deinit']+55); E(cmp_reg,0,1); bc('request_internal','eq')
    a.label('request_not_internal')
    E(cmp_imm,6,control.RESET_EVENT); bc('request_freeze','ne')
    E(movs_imm,0,TEARDOWN); put(OP); E(movs_imm,0,0); put(TEAR_CFG); put(RESET_DONE)
    a.label('request_freeze'); E(movs_imm,0,0); put(RESET_DONE)
    field(PHASE); E(cmp_imm,0,OPEN); bc('freeze_now','eq')
    E(cmp_imm,0,SEALED); bc('request_forward','ne')
    a.label('freeze_now'); E(movs_imm,0,CLOSING); put(PHASE)
    a.label('request_forward'); E(pop,[0,1,2,3,4,5,6],lr=True); E(b_w,'mc_native_request')
    a.label('request_internal'); E(pop,[0,1,2,3,4,5,6],lr=True); E(movs_imm,0,0); E(bx_lr)
    a.label('mc_native_request'); E(raw,generated_gates()[cc['cc_request']][0]); E(b_w,cc['cc_request']+4)

    for name,address,op,reason in (('mc_init_list',0x08040B5A,CONFIGURE,control.INIT_EVENT),
                                   ('mc_deinit_list',0x08040B7E,TEARDOWN,control.DEINIT_EVENT)):
        a.label(name); E(push,[0,1,2,3,4,5,6],lr=True); imm(4,state)
        field(ROOT,3); E(cmp_reg,0,3); bc(name+'_foreign','ne')
        field(CONTROLLER,3); E(cmp_reg,1,3); bc(name+'_foreign','ne')
        field(0); imm(1,MAGIC); E(cmp_reg,0,1); bc(name+'_no','ne')
        if op==CONFIGURE:
            E(cmp_imm,2,1); bc(name+'_no','ne')
            # Known two-class list only, same bindings as the earlier layer.
            if class_policy is None:
                field(ROOT,5); E(ldrb_w,0,5,0); E(cmp_imm,0,2); bc(name+'_no','ne')
                imm(6,composite.STATE_BASE)
                for off,bound in ((8,composite.MIDI),(12,composite.MSC)):
                    E(ldr_imm,0,5,off); E(ldr_imm,1,6,bound); E(cmp_reg,0,1); bc(name+'_no','ne')
                E(ldr_imm,0,5,16); E(cmp_imm,0,0); bc(name+'_no','ne')
            else:
                E(bl,class_policy); E(cmp_imm,0,1); bc(name+'_no','ne')
                imm(6,composite.STATE_BASE)
            field(OP); E(movs_imm,1,TEARDOWN); E(ands_reg,0,1)
            E(movs_imm,1,CONFIGURE); E(orrs_reg,0,1); put(OP)
            E(ldr_imm,0,6,composite.MIDI); field(CONTROLLER,1); E(movs_imm,2,1); E(bl,cc['cc_init'])
            E(cmp_imm,0,0); bc(name+'_no','ne')
            imm(1,control.STATE_BASE); E(ldr_imm,0,1,control.REQUESTS); E(str_imm,0,6,composite.GENERATION)
            E(movs_imm,0,1); E(str_imm,0,6,composite.PENDING)
        else:
            E(ldr_sp,0,8); put(TEAR_CFG); E(movs_imm,0,TEARDOWN); put(OP)
            E(movs_imm,0,0); put(RESET_DONE)
            E(movs_imm,0,reason); E(bl,cc['cc_request'])
        E(pop,[0,1,2,3,4,5,6],lr=True); E(movs_imm,0,0); E(bx_lr)
        a.label(name+'_no'); E(pop,[0,1,2,3,4,5,6],lr=True); E(movs_imm,0,1); E(bx_lr)
        a.label(name+'_foreign'); E(pop,[0,1,2,3,4,5,6],lr=True)
        E(b_w,xc['xc_init_list'] if op==CONFIGURE else 'mc_native_deinit')
    native('mc_native_deinit',0x08040B7E)

    a.label('mc_bot_reset')
    E(push,[3,4,5,6,7],lr=True); E(mov_reg,6,0); imm(4,state)
    field(CONTROLLER,1); E(cmp_reg,6,1); bc('bot_foreign','ne')
    field(0); imm(1,MAGIC); E(cmp_reg,0,1); bc('bot_no','ne')
    E(movs_imm,0,BOT_RESET); put(OP); E(movs_imm,0,0); put(RESET_DONE)
    E(movs_imm,0,control.DEINIT_EVENT); E(bl,cc['cc_request'])
    E(pop,[3,4,5,6,7],pc=True)
    a.label('bot_no'); E(movs_imm,0,1); E(pop,[3,4,5,6,7],pc=True)
    a.label('bot_foreign'); E(mov_reg,0,6); E(pop,[3,4,5,6,7],lr=True)
    a.label('mc_native_bot_reset')
    # Relocate the pinned PC-relative LDR; retain the remaining native body.
    imm(1,BOT); E(movs_imm,2,0); E(b_w,0x0802EFFC)

    # Track endpoint2 lower submissions before HAL can own the buffer. A reset
    # interrupt may freeze us mid-submit; ARM_BUSY retains that job until return.
    a.label('mc_rx_lower')
    E(push,[0,1,2,3,4,5,6],lr=True); imm(4,state)
    field(CONTROLLER,3); E(cmp_reg,0,3); bc('lower_foreign','ne')
    E(cmp_imm,1,2); bc('lower_foreign','ne')
    field(0); imm(1,MAGIC); E(cmp_reg,0,1); bc('lower_no','ne')
    field(RX_ACTIVE); E(cmp_imm,0,0); bc('lower_no','ne')
    field(PHASE); E(cmp_imm,0,OPEN); bc('lower_open','eq')
    E(cmp_imm,0,SEALED); bc('lower_no','ne')
    field(NATIVE_RESET); E(cmp_imm,0,1); bc('lower_authorized','eq')
    imm(1,control.STATE_BASE); E(ldr_imm,0,1,control.INIT_BUSY); E(cmp_imm,0,1); bc('lower_no','ne')
    imm(1,composite.STATE_BASE); E(ldr_imm,0,1,composite.CURRENT); E(ldr_imm,1,1,composite.MSC)
    E(cmp_reg,0,1); bc('lower_no','ne'); E(b,'lower_authorized')
    a.label('lower_open'); field(OP); E(cmp_imm,0,0); bc('lower_no','ne')
    a.label('lower_authorized'); mask()
    field(PHASE); E(cmp_imm,0,SEALED); bc('lower_reserve','eq')
    E(cmp_imm,0,OPEN); bc('lower_mask_no','ne')
    field(OP); E(cmp_imm,0,0); bc('lower_mask_no','ne')
    a.label('lower_reserve'); field(RX_ACTIVE); E(cmp_imm,0,0); bc('lower_mask_no','ne')
    field(NEXT); imm(1,0xFFFFFFFF); E(cmp_reg,0,1); bc('lower_wrap','eq')
    E(adds_imm8,0,1); put(NEXT); put(RX_TICKET)
    E(ldr_sp,0,8); put(RX_BUFFER); E(ldr_sp,0,12); put(RX_LENGTH)
    E(movs_imm,0,1); put(ARM_BUSY); put(RX_ACTIVE); E(movs_imm,0,OPEN); put(PHASE)
    restore()
    field(SUBMITS); E(adds_imm8,0,1); put(SUBMITS)
    E(ldr_sp,0,0); E(ldr_sp,1,4); E(ldr_sp,2,8); E(ldr_sp,3,12)
    E(bl,cc['cc_rx_submit']); E(mov_reg,6,0)
    E(movs_imm,0,0); put(ARM_BUSY); E(cmp_imm,6,0); bc('lower_return','eq')
    E(movs_imm,0,CLOSING); put(PHASE)
    a.label('lower_return'); E(str_sp,6,0)
    E(pop,[0,1,2,3,4,5,6],lr=True); E(bx_lr)
    a.label('lower_wrap'); restore(); bad(); E(b,'lower_no')
    a.label('lower_mask_no'); restore()
    a.label('lower_no'); E(pop,[0,1,2,3,4,5,6],lr=True); E(movs_imm,0,1); E(bx_lr)
    a.label('lower_foreign'); E(pop,[0,1,2,3,4,5,6],lr=True); E(b_w,cc['cc_rx_submit'])

    # Freeze the stock consumer before it can turn an old ready CBW into media
    # I/O. TASK_BUSY protects code already inside the synchronous native poll.
    a.label('mc_poll')
    E(push,[3,4,5,6,7],lr=True); main('poll_no')
    phase('poll_no',OPEN); field(OP); E(cmp_imm,0,0); bc('poll_no','ne')
    field(TASK_BUSY); E(cmp_imm,0,0); bc('poll_no','ne')
    E(movs_imm,0,1); put(TASK_BUSY); E(bl,'mc_native_poll'); E(mov_reg,6,0)
    E(movs_imm,0,0); put(TASK_BUSY); E(mov_reg,0,6); E(pop,[3,4,5,6,7],pc=True)
    a.label('poll_no'); E(movs_imm,0,0); E(pop,[3,4,5,6,7],pc=True)
    a.label('mc_native_poll'); E(push,[4],lr=True); E(bl,0x0802EF5A); E(b_w,0x0802762A)
    for address in (0x0802F014,0x0802F04A):
        name=f'mc_bot_{address:08x}'; a.label(name)
        E(push,[0,1,2,3,4,5,6],lr=True); imm(4,state)
        field(CONTROLLER,2); E(cmp_reg,0,2); bc(name+'_forward','ne')
        phase(name+'_no',OPEN); field(OP); E(cmp_imm,0,0); bc(name+'_no','ne')
        a.label(name+'_forward'); E(pop,[0,1,2,3,4,5,6],lr=True)
        a.label(name+'_native')
        E(raw,GATES[address]); E(b_w,address+4)
        a.label(name+'_no'); E(pop,[0,1,2,3,4,5,6],lr=True); E(movs_imm,0,0); E(bx_lr)

    a.label('mc_step')
    E(push,[3,4,5,6,7],lr=True); imm(4,state); field(HANDLE,5); E(ldr_imm,5,5)
    for off in (TASK_BUSY,ARM_BUSY): field(off); E(cmp_imm,0,0); bc('step_wait','ne')
    field(PHASE); E(cmp_imm,0,SEALED); bc('step_ok','eq')
    E(cmp_imm,0,CLOSING); bc('step_start','eq')
    E(cmp_imm,0,WAIT_DISABLE); bc('step_disabled','eq')
    E(cmp_imm,0,WAIT_FLUSH); bc('step_flushed','eq'); E(b,'step_wait')
    a.label('step_start')
    if storage_policy is None:
        imm(1,BOT); E(ldrb_w,0,1,0x10); E(cmp_imm,0,0); bc('step_blocked','ne')
        E(ldr_w,0,5,IN_CTL); imm(1,session.EPENA); E(tst_reg,0,1); bc('step_blocked','ne')
        field(RX_ACTIVE); E(cmp_imm,0,0); bc('step_idle','eq')
        field(RX_BUFFER); imm(1,CBW); E(cmp_reg,0,1); bc('step_blocked','ne')
        field(RX_LENGTH); E(cmp_imm,0,31); bc('step_blocked','ne')
    else:
        E(bl,storage_policy); E(cmp_imm,0,1); bc('step_blocked','ne')
    a.label('step_idle')
    for reg,save in ((session.DAINTMSK,DAINT),(session.DEACHMSK,DEACH)):
        E(ldr_w,0,5,reg); imm(1,MASK); E(mov_reg,2,0); E(ands_reg,2,1); put(save,2)
        E(bics_reg,0,1); E(str_w,0,5,reg)
    E(ldr_w,0,5,session.DIEPEMPMSK); E(movs_imm,1,4); E(ands_reg,1,0); put(EMP,1)
    E(movs_imm,1,4); E(bics_reg,0,1); E(str_w,0,5,session.DIEPEMPMSK)
    E(movs_imm,6,0)
    for ctl,irqreg,bit in ((IN_CTL,IN_INT,1),(OUT_CTL,OUT_INT,2)):
        imm(0,session.CLEAR_INT); E(str_w,0,5,irqreg)
        E(ldr_w,0,5,ctl); imm(1,session.EPENA); E(tst_reg,0,1); bc(f'mc_idle_{bit}','eq')
        E(movs_imm,1,bit); E(orrs_reg,6,1); imm(1,session.EPDIS); E(orrs_reg,0,1)
        a.label(f'mc_idle_{bit}'); imm(1,session.SNAK); E(orrs_reg,0,1); E(str_w,0,5,ctl)
    put(NEED_ACK,6); E(raw,bytes.fromhex('bff34f8f'))
    E(movs_imm,0,WAIT_DISABLE); put(PHASE); E(b,'step_wait')
    a.label('step_disabled'); field(NEED_ACK,6)
    for ctl,irqreg,bit in ((IN_CTL,IN_INT,1),(OUT_CTL,OUT_INT,2)):
        E(ldr_w,0,5,ctl); imm(1,session.EPENA); E(tst_reg,0,1); bc('step_wait','ne')
        E(movs_imm,1,bit); E(tst_reg,6,1); bc(f'mc_ack_{bit}','eq')
        E(ldr_w,0,5,irqreg); E(movs_imm,1,session.ACK); E(tst_reg,0,1); bc('step_wait','eq')
        a.label(f'mc_ack_{bit}')
    E(ldr_w,0,5,session.GINTSTS); E(movs_imm,1,16); E(tst_reg,0,1); bc('step_wait','ne')
    E(ldr_w,0,5,session.GRSTCTL); E(movs_imm,1,0x30); E(tst_reg,0,1); bc('step_wait','ne')
    imm(1,0x80000000); E(tst_reg,0,1); bc('step_wait','eq')
    for reg in (IN_INT,OUT_INT): imm(0,session.CLEAR_INT); E(str_w,0,5,reg)
    E(movs_imm,0,0xA0); E(str_w,0,5,session.GRSTCTL)
    E(movs_imm,0,WAIT_FLUSH); put(PHASE); E(b,'step_wait')
    a.label('step_flushed')
    E(ldr_w,0,5,session.GRSTCTL); E(movs_imm,1,0x30); E(tst_reg,0,1); bc('step_wait','ne')
    E(ldr_w,0,5,session.GINTSTS); E(movs_imm,1,16); E(tst_reg,0,1); bc('step_wait','ne')
    for ctl in (IN_CTL,OUT_CTL):
        E(ldr_w,0,5,ctl); imm(1,session.EPENA); E(tst_reg,0,1); bc('step_bad','ne')
    for reg in (IN_INT,OUT_INT):
        E(ldr_w,0,5,reg); E(movs_imm,1,3); E(tst_reg,0,1); bc('step_wait','ne')
    if storage_finalize is not None:
        E(bl,storage_finalize); E(cmp_imm,0,1); bc('step_wait','ne')
    field(EPOCH); imm(1,0xFFFFFFFF); E(cmp_reg,0,1); bc('step_bad','eq')
    E(adds_imm8,0,1); put(EPOCH); E(movs_imm,0,0)
    field(HANDLE,6)
    for off in (12,16,20,24): E(str_w,0,6,0x1FC+2*0x1C+off)
    field(RX_PORT,6); E(strb_imm,0,6,28)  # preserve native semaphore capacity+29
    field(CANCEL_RX,1); field(RX_ACTIVE,2); E(raw,bytes.fromhex('8918')); put(CANCEL_RX,1)
    E(movs_imm,0,0); put(RX_ACTIVE); put(RX_VALID); put(RX_SEEN)
    E(raw,bytes.fromhex('bff34f8f')); E(movs_imm,0,SEALED); put(PHASE); E(b,'step_ok')
    a.label('step_blocked'); E(movs_imm,0,1); put(BLOCKED); E(b,'step_wait')
    a.label('step_bad'); bad()
    a.label('step_wait'); E(movs_imm,0,1); E(pop,[3,4,5,6,7],pc=True)
    a.label('step_ok'); E(movs_imm,0,0); E(pop,[3,4,5,6,7],pc=True)

    a.label('mc_service')
    E(push,[3,4,5,6,7],lr=True); main('service_no')
    for off in (BUSY,TASK_BUSY,ARM_BUSY,IRQ_ACTIVE): field(off); E(cmp_imm,0,0); bc('service_no','ne')
    imm(1,control.STATE_BASE); E(ldr_imm,0,1,control.IRQ_DEPTH); E(cmp_imm,0,0); bc('service_no','ne')
    E(ldr_imm,7,1,control.REQUESTS); E(movs_imm,0,1); put(BUSY)
    field(OP); E(cmp_imm,0,0); bc('service_pending','ne')
    field(PHASE); E(cmp_imm,0,OPEN); bc('service_normal','eq')
    E(cmp_imm,0,SEALED); bc('service_normal','eq')
    a.label('service_pending')
    field(RESET_DONE); E(cmp_imm,0,1); bc('service_midi','eq')
    E(bl,'mc_step'); E(cmp_imm,0,0); bc('service_wait','ne'); changed('service_wait')
    a.label('service_midi'); imm(1,session.STATE_BASE); E(ldr_imm,0,1,session.PHASE)
    E(cmp_imm,0,session.SEALED); bc('service_sealed','eq')
    E(bl,ss['ss_step']); E(cmp_imm,0,0); bc('service_wait','ne'); changed('service_wait')
    a.label('service_sealed')
    field(OP); E(movs_imm,1,TEARDOWN); E(tst_reg,0,1); bc('service_reset','eq')
    E(movs_imm,0,1); put(NATIVE_TEAR)
    field(ROOT); field(CONTROLLER,1); field(TEAR_CFG,2); E(bl,'mc_native_deinit')
    E(movs_imm,0,0); put(NATIVE_TEAR); changed('service_wait')
    field(TEARDOWNS); E(adds_imm8,0,1); put(TEARDOWNS)
    mask(); changed('service_race')
    field(OP); E(movs_imm,1,TEARDOWN); E(bics_reg,0,1); put(OP); restore()
    a.label('service_reset'); field(OP); E(movs_imm,1,BOT_RESET); E(tst_reg,0,1); bc('service_normal','eq')
    field(CONTROLLER); E(ldrb_w,0,0,0x274); E(cmp_imm,0,3); bc('service_wait','ne')
    E(bl,'mc_native_service'); changed('service_wait')
    field(RESET_DONE); E(cmp_imm,0,1); bc('service_resume','eq')
    E(movs_imm,0,1); put(NATIVE_RESET); field(CONTROLLER); E(bl,'mc_native_bot_reset')
    E(movs_imm,0,0); put(NATIVE_RESET); changed('service_wait')
    mask(); changed('service_race'); E(movs_imm,0,1); put(RESET_DONE); restore()
    field(HANDLE,5); E(ldr_imm,5,5)
    for reg,save in ((session.DAINTMSK,DAINT),(session.DEACHMSK,DEACH)):
        E(ldr_w,0,5,reg); imm(1,MASK); E(bics_reg,0,1); field(save,1); E(orrs_reg,0,1); E(str_w,0,5,reg)
    a.label('service_resume'); changed('service_refreeze')
    E(bl,ss['ss_resume']); E(mov_reg,6,0); changed('service_refreeze')
    E(cmp_imm,6,0); bc('service_wait','ne')
    E(b,'service_commit')
    a.label('service_normal'); E(bl,'mc_native_service'); E(cmp_imm,0,0); bc('service_wait','ne')
    changed('service_refreeze')
    field(PHASE); E(cmp_imm,0,BROKEN); bc('service_refreeze','eq')
    field(OP); E(movs_imm,1,CONFIGURE); E(tst_reg,0,1); bc('service_commit','eq')
    if config_ready is None:
        field(PHASE); E(cmp_imm,0,OPEN); bc('service_msc_failed','ne')
    else:
        E(bl,config_ready); E(cmp_imm,0,1); bc('service_msc_failed','ne')
    a.label('service_commit'); mask(); changed('service_race')
    E(movs_imm,0,0); put(OP); put(RESET_DONE); put(BUSY); restore()
    E(movs_imm,0,0); E(pop,[3,4,5,6,7],pc=True)
    a.label('service_race'); restore()
    a.label('service_refreeze')
    imm(1,session.STATE_BASE); E(movs_imm,0,session.CLOSING); E(str_imm,0,1,session.PHASE)
    imm(1,life.STATE_BASE); E(movs_imm,0,life.FROZEN); E(str_imm,0,1,life.PHASE)
    E(b,'service_wait')
    a.label('service_msc_failed'); bad()
    a.label('service_wait'); E(movs_imm,0,0); put(BUSY)
    a.label('service_no'); E(movs_imm,0,1); E(pop,[3,4,5,6,7],pc=True)
    a.label('mc_native_service'); E(raw,generated_gates()[cc['cc_service']][0]); E(b_w,cc['cc_service']+6)

    # Native CPU read copies whole words. Bound the32B-padded CBW object and
    # drain a bad <=64B USB packet into private scratch, never adjacent RAM.
    a.label('mc_fifo_read')
    E(push,[0,1,2,3,4,5,6],lr=True); imm(4,state)
    field(HANDLE,6); E(ldr_imm,3,6); E(cmp_reg,0,3); bc('fifo_forward','ne')
    E(ldr_w,3,6,0x1FC+2*0x1C+12); E(cmp_reg,1,3); bc('fifo_forward','ne')
    field(RX_BUFFER,3); imm(5,CBW); E(cmp_reg,3,5); bc('fifo_forward','ne')
    field(RX_LENGTH,3); E(cmp_imm,3,31); bc('fifo_forward','ne')
    field(PHASE,3); E(cmp_imm,3,BROKEN); bc('fifo_bad','eq')
    field(RX_ACTIVE,3); E(cmp_imm,3,1); bc('fifo_bad','ne')
    imm(3,CBW); E(cmp_reg,1,3); bc('fifo_bad','lo')
    imm(3,CBW+32); E(cmp_reg,1,3); bc('fifo_bad','hs')
    # Require both actual bytes and rounded native writes within this object.
    E(adds_reg,3,1,2); imm(5,CBW+31); E(cmp_reg,3,5); bc('fifo_bad','hi')
    E(mov_reg,3,2); E(adds_imm8,3,3); E(lsrs_imm,3,3,2); E(lsls_imm,3,3,2)
    E(adds_reg,3,3,1); imm(5,CBW+32); E(cmp_reg,3,5); bc('fifo_bad','hi')
    E(b,'fifo_forward')
    a.label('fifo_bad'); bad(); E(ldr_sp,2,8); E(cmp_imm,2,64); bc('fifo_stopped','hi')
    imm(1,state+SCRATCH); E(str_sp,1,4)
    a.label('fifo_forward'); E(pop,[0,1,2,3,4,5,6],lr=True)
    a.label('mc_native_fifo'); E(raw,GATES[0x080531CC]); E(b_w,0x080531D0)
    a.label('fifo_stopped'); E(pop,[0,1,2,3,4,5,6],lr=True); E(mov_reg,0,1); E(bx_lr)

    # MSC completion mirrors the MIDI bridge: claim in native callback, publish
    # after the IRQ has copied every shared RX FIFO record. No hardware tags.
    a.label('mc_irq')
    E(push,[3,4,5,6,7],lr=True); E(mov_reg,7,0); imm(4,state)
    field(HANDLE,1); E(cmp_reg,7,1); bc('irq_foreign','ne')
    field(0); imm(1,MAGIC); E(cmp_reg,0,1); bc('irq_no','ne')
    field(IRQ_ACTIVE); E(cmp_imm,0,0); bc('irq_no','ne')
    E(movs_imm,0,1); put(IRQ_ACTIVE)
    field(PHASE); E(cmp_imm,0,OPEN); bc('irq_native','ne')
    field(RX_SEEN); E(cmp_imm,0,1); bc('irq_native','eq')
    E(movs_imm,0,0); put(RX_VALID); field(RX_ACTIVE); E(cmp_imm,0,1); bc('irq_native','ne')
    E(ldr_imm,5,7); E(ldr_w,0,5,OUT_INT); E(ldr_w,1,5,0x814); E(ands_reg,0,1)
    E(movs_imm,1,1); E(tst_reg,0,1); bc('irq_native','eq')
    E(ldr_w,0,5,session.DAINTMSK); imm(1,1<<18); E(tst_reg,0,1); bc('irq_native','eq')
    field(EPOCH); put(SNAP_EPOCH); field(RX_TICKET); put(SNAP_TICKET)
    E(movs_imm,0,1); put(RX_VALID)
    a.label('irq_native'); E(mov_reg,0,7); E(bl,cc['cc_irq']); E(mov_reg,6,0)
    E(cmp_imm,6,0); bc('irq_bad','ne')
    phase('irq_finish',OPEN); field(RX_SEEN); E(cmp_imm,0,1); bc('irq_finish','ne')
    field(EPOCH); field(SNAP_EPOCH,1); E(cmp_reg,0,1); bc('irq_finish','ne')
    field(RX_TICKET); field(SNAP_TICKET,1); E(cmp_reg,0,1); bc('irq_finish','ne')
    E(ldr_imm,5,7); E(ldr_w,0,5,session.GINTSTS); E(movs_imm,1,16); E(tst_reg,0,1); bc('irq_finish','ne')
    E(ldr_w,1,7,0x1FC+2*0x1C+24); field(RX_LENGTH,0); E(cmp_reg,1,0); bc('irq_bad','hi')
    E(movs_imm,0,0); put(RX_ACTIVE); put(RX_VALID); put(RX_SEEN)
    field(RX_PORT); E(bl,ss['ss_native_08026988'])
    field(IRQ_DONE); E(adds_imm8,0,1); put(IRQ_DONE); E(b,'irq_finish')
    a.label('irq_bad'); bad()
    a.label('irq_finish'); E(movs_imm,0,0); put(IRQ_ACTIVE); E(mov_reg,0,6); E(pop,[3,4,5,6,7],pc=True)
    a.label('irq_no'); E(movs_imm,0,1); E(pop,[3,4,5,6,7],pc=True)
    a.label('irq_foreign'); E(mov_reg,0,7); E(pop,[3,4,5,6,7],lr=True); E(b_w,cc['cc_irq'])

    a.label('mc_rx_callback')
    E(push,[0,1,2,3,4,5,6],lr=True); imm(4,state)
    field(RX_PORT,2); E(cmp_reg,0,2); bc('callback_foreign','ne')
    field(0); imm(1,MAGIC); E(cmp_reg,0,1); bc('callback_no','ne')
    phase('callback_no',OPEN)
    for off,val in ((IRQ_ACTIVE,1),(RX_VALID,1),(RX_SEEN,0),(RX_ACTIVE,1)):
        field(off); E(cmp_imm,0,val); bc('callback_no','ne')
    E(ldr_sp,0,28); imm(1,0x080526ED); E(cmp_reg,0,1); bc('callback_no','ne')
    E(movs_imm,0,1); put(RX_SEEN)
    a.label('callback_no'); E(pop,[0,1,2,3,4,5,6],lr=True); E(movs_imm,0,0); E(bx_lr)
    a.label('callback_foreign'); E(pop,[0,1,2,3,4,5,6],lr=True)
    _,ib=irq.arm_code(); E(b_w,ib['ib_rx_callback'])
    code,labels=a.assemble()
    code+=b'\x00\xBF'*(-len(code)%4//2)  # word-aligned cave extent; unreachable NOP
    if base+len(code)>0x08080000: raise ValueError('MSC code exceeds application flash')
    return code,labels
