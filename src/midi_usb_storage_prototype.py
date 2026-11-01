"""EMULATION ONLY: readonly stock MSC READ10/CSW ownership and cancellation.

Native queued backend+drain is checked before releasing the shared4KB buffer.
Lower flash I/O, RTOS wake/yield and USB disable/flush are modeled boundaries.
"""
import midi_usb_msc_prototype as msc
import midi_usb_control_prototype as control
import midi_usb_session_prototype as session
from thumb_asm import (Asm,adds_imm8,b,b_cond_w,b_w,bl,bx_lr,cmp_imm,cmp_reg,
                       ldr_imm,ldr_w,ldrb_w,ldrh_imm,ldr_sp,mov_reg,movs_imm,
                       pop,push,raw,str_imm,str_w,strb_imm,str_sp,tst_reg)

CODE_BASE,STATE_BASE,STATE_SIZE=0x0807B400,0x20048140,128
MAGIC=0x3154534D
CONTROLLER,BACKEND,QUEUE,SCSI_BUSY,IO_BUSY,TX_ACTIVE,TX_PTR,TX_LEN=4,8,12,16,20,24,28,32
TX_EPOCH,TX_TICKET,NEXT,TX_VALID,TX_SEEN,IRQ_ACTIVE,SNAP_EPOCH,SNAP_TICKET=36,40,44,48,52,56,60,64
CANCEL_TX,ERRORS,READS,DONE,COMMAND,READ_RESULT=68,72,76,80,84,88
BUFFER,SCSI,OPS=0x40024000,0x20006DA8,0x20003888
GATES={0x080458D0:bytes.fromhex('2de9fe43'),0x08065128:bytes.fromhex('2de9f041'),
       0x0802C9B8:bytes.fromhex('80b5d0f89802'),0x080268D0:control.GATES[0x080268D0],
       0x0804293E:msc.GATES[0x0804293E],0x0802C328:bytes.fromhex('207603e0')}


def msc_variant(**options): return msc.arm_code(storage_policy=CODE_BASE,storage_finalize=CODE_BASE+4,**options)


def arm_code(base=CODE_BASE,state=STATE_BASE,msc_options=None):
    mc_code,mc=msc_variant(**(msc_options or {})); _,cc=control.arm_code(); _,ss=session.arm_code()
    if base!=CODE_BASE or state%4 or not 0x20048124<=state<state+STATE_SIZE<0x20048200:
        raise ValueError('Storage policy/state must use disjoint registered addresses')
    if msc.CODE_BASE+len(mc_code)>base: raise ValueError('Storage code overlaps MSC code')
    a=Asm(base); E=a.emit
    def imm(r,v): a.imm32(r,v)
    def bc(l,c): E(b_cond_w,l,c)
    def field(o,r=0): E(ldr_imm,r,4,o)
    def put(o,r=0): E(str_imm,r,4,o)
    def mask(): E(raw,bytes.fromhex('eff3108372b6'))
    def restore(): E(raw,bytes.fromhex('83f31088'))
    def open_(fail):
        imm(5,msc.STATE_BASE); E(ldr_imm,0,5,msc.PHASE); E(cmp_imm,0,msc.OPEN); bc(fail,'ne')
        E(ldr_imm,0,5,msc.OP); E(cmp_imm,0,0); bc(fail,'ne')
    def native(name,address): a.label(name); E(raw,GATES[address]); E(b_w,address+len(GATES[address]))
    a.label('sd_policy'); E(b_w,'policy_body')
    a.label('sd_finalize'); E(b_w,'finalize_body')
    a.label('policy_body'); E(push,[3,4,5,6,7],lr=True); imm(4,state)
    E(bl,'sd_quiet'); E(cmp_imm,0,1); bc('policy_no','ne')
    imm(5,msc.STATE_BASE); E(ldr_imm,0,5,msc.RX_ACTIVE); E(cmp_imm,0,0); bc('policy_bot','eq')
    E(ldr_imm,0,5,msc.RX_BUFFER); imm(1,msc.CBW); E(cmp_reg,0,1); bc('policy_no','ne')
    E(ldr_imm,0,5,msc.RX_LENGTH); E(cmp_imm,0,31); bc('policy_no','ne')
    a.label('policy_bot'); imm(1,msc.BOT); E(ldrb_w,0,1,0x10)
    E(cmp_imm,0,0); bc('policy_tx','eq')
    E(cmp_imm,0,2); bc('policy_read','eq'); E(cmp_imm,0,3); bc('policy_no','ne')
    a.label('policy_read'); field(COMMAND); E(cmp_imm,0,0x28); bc('policy_no','ne')
    a.label('policy_tx'); field(TX_ACTIVE); E(cmp_imm,0,1); bc('policy_ok','eq')
    E(ldr_imm,0,5,msc.HANDLE); E(ldr_imm,0,0); E(ldr_w,0,0,msc.IN_CTL)
    imm(1,session.EPENA); E(tst_reg,0,1); bc('policy_no','ne')
    a.label('policy_ok'); E(movs_imm,0,1); E(pop,[3,4,5,6,7],pc=True)
    a.label('policy_no'); E(movs_imm,0,0); E(pop,[3,4,5,6,7],pc=True)

    a.label('sd_quiet')
    field(0); imm(1,MAGIC); E(cmp_reg,0,1); bc('quiet_no','ne')
    for off in (IO_BUSY,SCSI_BUSY,IRQ_ACTIVE): field(off); E(cmp_imm,0,0); bc('quiet_no','ne')
    imm(1,0x200038AC); E(ldr_imm,0,1); imm(1,OPS); E(cmp_reg,0,1); bc('quiet_no','ne')
    for off,expected in ((0,0x080650D1),(4,0x080650D5),(8,0x080650E5),(12,0x080650E9),(16,0x08065129),(20,0x08065195)):
        E(ldr_imm,0,1,off); imm(2,expected); E(cmp_reg,0,2); bc('quiet_no','ne')
    field(BACKEND,2); imm(1,0x20006E60); E(ldr_imm,0,1); E(cmp_reg,0,2); bc('quiet_no','ne')
    E(ldr_imm,0,2); imm(1,0x08068698); E(cmp_reg,0,1); bc('quiet_no','ne')
    E(ldrb_w,0,2,12); E(cmp_imm,0,0); bc('quiet_no','ne')
    E(ldr_imm,0,2,16); E(cmp_imm,0,0); bc('quiet_no','ne')
    E(ldr_imm,0,2,8); field(QUEUE,1); E(cmp_reg,0,1); bc('quiet_no','ne')
    E(ldrh_imm,0,1,6); E(ldrh_imm,1,1,8); E(cmp_reg,0,1); bc('quiet_no','ne')
    E(movs_imm,0,1); E(bx_lr)
    a.label('quiet_no'); E(movs_imm,0,0); E(bx_lr)

    a.label('finalize_body'); E(push,[3,4,5,6,7],lr=True); imm(4,state)
    E(bl,'policy_body'); E(cmp_imm,0,1); bc('policy_no','ne')
    imm(5,msc.STATE_BASE); E(ldr_imm,0,5,msc.PHASE); E(cmp_imm,0,msc.WAIT_FLUSH); bc('policy_no','ne')
    field(CANCEL_TX,0); field(TX_ACTIVE,1); E(raw,bytes.fromhex('4018')); put(CANCEL_TX)
    E(movs_imm,0,0); put(TX_ACTIVE); put(TX_VALID); put(TX_SEEN)
    E(ldr_imm,6,5,msc.HANDLE)
    for off in (12,16,20,24): E(str_w,0,6,0x3C+2*0x1C+off)
    E(ldr_imm,6,5,msc.TX_PORT); E(strb_imm,0,6,28)
    imm(6,msc.BOT); E(strb_imm,0,6,16)
    E(movs_imm,0,1); E(pop,[3,4,5,6,7],pc=True)

    a.label('sd_scsi')
    E(push,[0,1,2,3,4,5,6],lr=True); imm(4,state); field(CONTROLLER,3); E(cmp_reg,0,3); bc('scsi_foreign','ne')
    open_('scsi_no'); field(TX_ACTIVE); E(cmp_imm,0,0); bc('scsi_no','ne')
    field(SCSI_BUSY); E(cmp_imm,0,0); bc('scsi_no','ne')
    imm(1,0x200038AC); E(ldr_imm,0,1); imm(1,OPS); E(cmp_reg,0,1); bc('scsi_no','ne')
    for off,expected in ((12,0x080650E9),(16,0x08065129)):
        E(ldr_imm,0,1,off); imm(2,expected); E(cmp_reg,0,2); bc('scsi_no','ne')
    E(ldr_sp,0,8); E(ldrb_w,0,0,0); put(COMMAND)
    E(movs_imm,0,1); put(SCSI_BUSY)
    for r in range(4): E(ldr_sp,r,4*r)
    E(bl,'sd_native_scsi'); E(str_sp,0,0); E(movs_imm,0,0); put(SCSI_BUSY)
    E(pop,[0,1,2,3,4,5,6],lr=True); E(bx_lr)
    a.label('scsi_no'); E(pop,[0,1,2,3,4,5,6],lr=True); imm(0,0xFFFFFFFF); E(bx_lr)
    a.label('scsi_foreign'); E(pop,[0,1,2,3,4,5,6],lr=True)
    native('sd_native_scsi',0x080458D0)

    a.label('sd_read')
    E(push,[0,1,2,3,4,5,6],lr=True); imm(4,state); imm(5,BUFFER); E(cmp_reg,1,5); bc('read_no','ne')
    E(cmp_imm,3,1); bc('read_no','ne')  # the pinned block size is4096B
    open_('read_no'); field(TX_ACTIVE); E(cmp_imm,0,0); bc('read_no','ne')
    field(IO_BUSY); E(cmp_imm,0,0); bc('read_no','ne')
    E(movs_imm,0,1); put(IO_BUSY); field(READS); E(adds_imm8,0,1); put(READS)
    imm(0,0xFFFFFFFF); put(READ_RESULT)
    for r in range(4): E(ldr_sp,r,4*r)
    E(bl,'sd_native_read'); E(str_sp,0,0); E(movs_imm,0,0); put(IO_BUSY)
    field(READ_RESULT); E(cmp_imm,0,0); bc('read_return','eq')
    imm(0,0xFFFFFFFF); E(str_sp,0,0)
    a.label('read_return')
    E(pop,[0,1,2,3,4,5,6],lr=True); E(bx_lr)
    a.label('read_no'); E(pop,[0,1,2,3,4,5,6],lr=True); imm(0,0xFFFFFFFF); E(bx_lr)
    native('sd_native_read',0x08065128)

    # Capture the matching queued read result, not the backend's last status:
    # another queued request can overwrite that shared status before drain ends.
    a.label('sd_worker_result'); E(push,[0,1,2,3,4,5,6],lr=True); imm(4,state)
    field(BACKEND,2); E(ldr_sp,3,16); E(cmp_reg,2,3); bc('worker_forward','ne')
    field(IO_BUSY); E(cmp_imm,0,1); bc('worker_forward','ne')
    E(ldr_sp,5,20); E(ldrh_imm,0,5); E(cmp_imm,0,1); bc('worker_forward','ne')
    E(ldr_imm,0,5,8); imm(1,BUFFER); E(cmp_reg,0,1); bc('worker_forward','ne')
    E(ldr_imm,0,5,12); imm(1,4096); E(cmp_reg,0,1); bc('worker_forward','ne')
    E(ldr_sp,0,0); put(READ_RESULT)
    a.label('worker_forward'); E(pop,[0,1,2,3,4,5,6],lr=True)
    a.label('sd_native_worker_result'); E(strb_imm,0,4,24); E(b_w,0x0802C334)

    a.label('sd_tx_submit')
    E(push,[0,1,2,3,4,5,6],lr=True); imm(4,state)
    field(CONTROLLER,3); E(cmp_reg,0,3); bc('tx_foreign','ne')
    E(cmp_imm,1,0x82); bc('tx_foreign','ne')
    open_('tx_no'); field(TX_ACTIVE); E(cmp_imm,0,0); bc('tx_no','ne')
    E(ldr_sp,2,8); E(ldr_sp,3,12); imm(0,BUFFER); E(cmp_reg,2,0); bc('tx_csw','ne')
    E(cmp_imm,3,0); bc('tx_no','eq'); imm(0,4096); E(cmp_reg,3,0); bc('tx_no','hi'); E(b,'tx_ready')
    a.label('tx_csw'); imm(0,msc.BOT); E(cmp_reg,2,0); bc('tx_no','ne'); E(cmp_imm,3,13); bc('tx_no','ne')
    a.label('tx_ready'); mask(); open_('tx_mask_no')
    field(NEXT); imm(1,0xFFFFFFFF); E(cmp_reg,0,1); bc('tx_mask_no','eq')
    E(adds_imm8,0,1); put(NEXT); put(TX_TICKET)
    E(ldr_imm,0,5,msc.EPOCH); put(TX_EPOCH); E(movs_imm,0,1); put(TX_ACTIVE)
    E(ldr_sp,0,8); put(TX_PTR); E(ldr_sp,0,12); put(TX_LEN); restore()
    for r in range(4): E(ldr_sp,r,4*r)
    E(bl,'sd_native_tx'); E(str_sp,0,0); E(pop,[0,1,2,3,4,5,6],lr=True); E(bx_lr)
    a.label('tx_mask_no'); restore()
    a.label('tx_no'); E(pop,[0,1,2,3,4,5,6],lr=True); E(movs_imm,0,1); E(bx_lr)
    a.label('tx_foreign'); E(pop,[0,1,2,3,4,5,6],lr=True)
    native('sd_native_tx',0x0802C9B8)

    a.label('sd_poll'); E(push,[0,1,2,3,4,5,6],lr=True); imm(4,state)
    for off in (TX_ACTIVE,SCSI_BUSY,IO_BUSY): field(off); E(cmp_imm,0,0); bc('poll_no','ne')
    E(pop,[0,1,2,3,4,5,6],lr=True); E(b_w,'sd_native_poll')
    a.label('poll_no'); E(pop,[0,1,2,3,4,5,6],lr=True); E(movs_imm,0,0); E(bx_lr)
    a.label('sd_native_poll'); offset=mc['mc_poll']-msc.CODE_BASE
    E(raw,mc_code[offset:offset+6]); E(b_w,mc['mc_poll']+6)

    a.label('sd_tx_callback'); E(push,[0,1,2,3,4,5,6],lr=True); imm(4,state)
    imm(5,msc.STATE_BASE); E(ldr_imm,1,5,msc.TX_PORT); E(cmp_reg,0,1); bc('callback_foreign','ne')
    field(TX_ACTIVE); E(cmp_imm,0,0); bc('callback_foreign','eq')
    for off,val in ((IRQ_ACTIVE,1),(TX_VALID,1),(TX_SEEN,0)):
        field(off); E(cmp_imm,0,val); bc('callback_no','ne')
    E(ldr_imm,0,5,msc.PHASE); E(cmp_imm,0,msc.OPEN); bc('callback_no','ne')
    E(ldr_sp,0,28); imm(1,0x080526A9); E(cmp_reg,0,1); bc('callback_no','ne')
    E(movs_imm,0,1); put(TX_SEEN)
    a.label('callback_no'); E(pop,[0,1,2,3,4,5,6],lr=True); E(movs_imm,0,0); E(bx_lr)
    a.label('callback_foreign'); E(pop,[0,1,2,3,4,5,6],lr=True); E(b_w,cc['cc_tx_callback'])

    a.label('sd_irq'); E(push,[3,4,5,6,7],lr=True); E(mov_reg,7,0); imm(4,state)
    imm(5,msc.STATE_BASE); E(ldr_imm,1,5,msc.HANDLE); E(cmp_reg,7,1); bc('irq_foreign','ne')
    field(IRQ_ACTIVE); E(cmp_imm,0,0); bc('irq_no','ne')
    E(movs_imm,0,1); put(IRQ_ACTIVE); E(movs_imm,0,0); put(TX_VALID); put(TX_SEEN)
    E(ldr_imm,0,5,msc.PHASE); E(cmp_imm,0,msc.OPEN); bc('irq_native','ne')
    field(TX_ACTIVE); E(cmp_imm,0,1); bc('irq_native','ne')
    E(ldr_imm,6,7); E(ldr_w,0,6,msc.IN_INT); E(movs_imm,1,1); E(tst_reg,0,1); bc('irq_native','eq')
    field(TX_EPOCH); put(SNAP_EPOCH); field(TX_TICKET); put(SNAP_TICKET)
    E(movs_imm,0,1); put(TX_VALID)
    a.label('irq_native'); E(mov_reg,0,7); E(bl,mc['mc_irq']); E(mov_reg,6,0)
    field(TX_SEEN); E(cmp_imm,0,1); bc('irq_finish','ne')
    E(ldr_imm,0,5,msc.PHASE); E(cmp_imm,0,msc.OPEN); bc('irq_finish','ne')
    field(TX_EPOCH); field(SNAP_EPOCH,1); E(cmp_reg,0,1); bc('irq_finish','ne')
    field(TX_TICKET); field(SNAP_TICKET,1); E(cmp_reg,0,1); bc('irq_finish','ne')
    E(movs_imm,0,0); put(TX_ACTIVE); E(ldr_imm,0,5,msc.TX_PORT); E(bl,ss['ss_native_080268d0'])
    field(DONE); E(adds_imm8,0,1); put(DONE)
    a.label('irq_finish'); E(movs_imm,0,0); put(IRQ_ACTIVE); E(mov_reg,0,6); E(pop,[3,4,5,6,7],pc=True)
    a.label('irq_no'); E(movs_imm,0,1); E(pop,[3,4,5,6,7],pc=True)
    a.label('irq_foreign'); E(mov_reg,0,7); E(pop,[3,4,5,6,7],lr=True); E(b_w,mc['mc_irq'])
    code,labels=a.assemble(); code+=b'\x00\xbf'*(-len(code)%4//2)
    if base+len(code)>0x08080000: raise ValueError('Storage code exceeds application flash')
    return code,labels
