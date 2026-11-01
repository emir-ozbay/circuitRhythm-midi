"""EMULATION ONLY: synchronous stock completion IRQ bridge, CPU FIFO mode.

Snapshot the armed jobs BEFORE running stock IRQ4293E. Native callbacks merely
claim that snapshot; dispatch follows the native IRQ, after CPU FIFO copies.
This is not a hardware generation tag: old hardware status after a broken
cancellation barrier remains indistinguishable. DMA/control IRQs fail closed.
"""
import midi_usb_session_prototype as session
import midi_usb_lifecycle_prototype as life
from thumb_asm import (Asm, add_sp_imm, ands_reg, b, b_cond_w, b_w, bl, bx_lr,
                       cmp_imm, cmp_reg, ldr_imm, ldr_sp, ldr_w, mov_reg,
                       movs_imm, pop, push, raw, str_imm, tst_reg)

CODE_BASE, STATE_BASE, STATE_SIZE = 0x08079000,0x20047F00,96
MAGIC = 0x31514249  # IBQ1
HANDLE, ACTIVE, INVALID, TX_VALID, TX_EPOCH, TX_TICKET = 4,8,12,16,20,24
RX_VALID, RX_EPOCH, RX_TICKET, TX_SEEN, RX_SEEN, ERRORS = 28,32,36,40,44,48
GINT, CLASS, CONTROLLER, TX_DONE, RX_DONE, CANCEL_RX = 52,56,60,64,68,72
NATIVE_IRQ = 0x0804293E
IRQ_PROLOGUE = bytes.fromhex('2de9f04f')
ALLOWED_GINT = (1<<4)|(1<<18)|(1<<19)
GATES = {NATIVE_IRQ:IRQ_PROLOGUE,0x080268D0:session.gates()[0x080268D0][2],
         0x08026988:session.gates()[0x08026988][2],0x0805261C:bytes.fromhex('f8b50646')}


def arm_code(base=CODE_BASE,state=STATE_BASE,allowed_gint=ALLOWED_GINT,max_phase=session.WAIT_FLUSH):
    sc,ss=session.arm_code()
    if (base%4 or state%4 or not session.CODE_BASE+len(sc)<=base<0x08080000
            or not session.STATE_BASE+session.STATE_SIZE<state<state+STATE_SIZE<0x20048000):
        raise ValueError('IRQ bridge code/state overlaps or exceeds bounds')
    if not 0<=allowed_gint<=0xFFFFFFFF or not session.OPEN<=max_phase<=session.SEALED:
        raise ValueError('Invalid experimental IRQ policy')
    a=Asm(base); E=a.emit
    def imm(r,v): a.imm32(r,v)
    def bc(label,cond): E(b_cond_w,label,cond)
    def field(off,r=0): E(ldr_imm,r,4,off)
    def freeze():
        E(movs_imm,0,1); E(str_imm,0,4,INVALID); E(str_imm,0,4,ERRORS)
        imm(1,session.STATE_BASE); E(movs_imm,0,session.BROKEN); E(str_imm,0,1,session.PHASE)
        imm(1,life.STATE_BASE); E(movs_imm,0,life.FROZEN); E(str_imm,0,1,life.PHASE)

    a.label('ib_irq')
    E(push,[3,4,5,6,7],lr=True); E(mov_reg,7,0); imm(4,state)
    field(HANDLE,1); E(cmp_reg,0,1); bc('irq_foreign','ne')
    field(0); imm(1,MAGIC); E(cmp_reg,0,1); bc('irq_no','ne')
    field(ACTIVE); E(cmp_imm,0,0); bc('irq_no','ne')
    # Known CPU-FIFO completion subset only. Unsupported control/reset/DMA
    # interrupts are release blockers, never converted to synthetic success.
    E(ldr_imm,0,7,16); E(cmp_imm,0,0); bc('irq_bad','ne')
    E(ldr_imm,5,7); imm(6,session.STATE_BASE); E(ldr_imm,0,6,session.USB_BASE)
    E(cmp_reg,0,5); bc('irq_bad','ne')
    E(ldr_w,0,7,0x400); field(CONTROLLER,1); E(cmp_reg,0,1); bc('irq_bad','ne')
    E(ldr_w,0,5,0x14); E(ldr_w,1,5,0x18); E(ands_reg,0,1); E(str_imm,0,4,GINT)
    imm(1,0xFFFFFFFF^allowed_gint); E(tst_reg,0,1); bc('irq_bad','ne')
    E(ldr_imm,0,6,session.PHASE); E(cmp_imm,0,session.OPEN); bc('irq_bad','lo')
    E(cmp_imm,0,max_phase); bc('irq_bad','hi')
    E(ldr_imm,0,6,session.BUSY); E(cmp_imm,0,0); bc('irq_no','ne')
    E(movs_imm,0,1); E(str_imm,0,4,ACTIVE)
    E(movs_imm,0,0); E(str_imm,0,4,INVALID); E(str_imm,0,4,TX_SEEN); E(str_imm,0,4,TX_VALID)
    E(ldr_imm,0,6,session.PHASE); E(cmp_imm,0,session.OPEN); bc('capture_invalid','ne')
    imm(1,life.STATE_BASE); E(ldr_imm,0,1,life.PHASE)
    E(cmp_imm,0,life.ACTIVE); bc('capture_invalid','ne')
    # A pending old RX frame may survive a FIFO-drain IRQ, but never an epoch.
    field(RX_SEEN); E(cmp_imm,0,0); bc('capture_rx','eq')
    field(RX_EPOCH); E(ldr_imm,1,6,session.EPOCH); E(cmp_reg,0,1); bc('capture_tx','eq')
    field(CANCEL_RX); E(raw,bytes.fromhex('401c')); E(str_imm,0,4,CANCEL_RX)
    E(movs_imm,0,0); E(str_imm,0,4,RX_SEEN); E(str_imm,0,4,RX_VALID)
    a.label('capture_rx')
    E(movs_imm,0,0); E(str_imm,0,4,RX_VALID)
    # Capture only masked XFRC on endpoint1. The token is copied once, before
    # any native callback/port rearm; callback time never reads current tokens.
    for kind,bit,daint,irq,mask,valid,epoch,ticket,sa,se,st in (
            ('rx',1<<19,1<<17,session.OUT_INT,0x814,RX_VALID,RX_EPOCH,RX_TICKET,session.RX_ACTIVE,session.RX_EPOCH,session.RX_TICKET),
            ('tx',1<<18,2,session.IN_INT,0x810,TX_VALID,TX_EPOCH,TX_TICKET,session.TX_ACTIVE,session.TX_EPOCH,session.TX_TICKET)):
        if kind=='tx': a.label('capture_tx')
        field(GINT); imm(1,bit); E(tst_reg,0,1); bc('capture_next_'+kind,'eq')
        E(ldr_w,0,5,0x818); E(ldr_w,1,5,0x81C); E(ands_reg,0,1)
        imm(1,daint); E(tst_reg,0,1); bc('capture_next_'+kind,'eq')
        E(ldr_w,0,5,irq); E(ldr_w,1,5,mask); E(ands_reg,0,1)
        E(movs_imm,1,1); E(tst_reg,0,1); bc('capture_next_'+kind,'eq')
        E(ldr_imm,0,6,sa); E(cmp_imm,0,1); bc('capture_next_'+kind,'ne')
        for src,dst in ((se,epoch),(st,ticket)):
            E(ldr_imm,0,6,src); E(str_imm,0,4,dst)
        E(movs_imm,0,1); E(str_imm,0,4,valid)
        a.label('capture_next_'+kind)
    E(b,'irq_native')
    a.label('capture_invalid'); E(movs_imm,0,1); E(str_imm,0,4,INVALID)
    a.label('irq_native')
    E(mov_reg,0,7); E(bl,'ib_native_irq'); a.label('ib_after_native_irq')
    field(INVALID); E(cmp_imm,0,0); bc('irq_finish','ne')
    # Native IRQ has retired. Callback claims are still pinned to its snapshot.
    field(TX_SEEN); E(cmp_imm,0,1); bc('dispatch_rx','ne')
    field(TX_EPOCH); field(TX_TICKET,1); E(bl,ss['ss_tx_done'])
    E(cmp_imm,0,1); bc('irq_bad_active','ne')
    field(TX_DONE); E(raw,bytes.fromhex('401c')); E(str_imm,0,4,TX_DONE)
    a.label('dispatch_rx')
    field(RX_SEEN); E(cmp_imm,0,1); bc('irq_finish','ne')
    E(ldr_w,0,5,0x14); E(movs_imm,1,16); E(tst_reg,0,1); bc('irq_finish','ne')
    field(RX_EPOCH); field(RX_TICKET,1); E(ldr_w,2,7,0x230)
    E(bl,ss['ss_rx_done']); E(cmp_imm,0,1); bc('irq_bad_active','ne')
    field(RX_DONE); E(raw,bytes.fromhex('401c')); E(str_imm,0,4,RX_DONE)
    E(movs_imm,0,0); E(str_imm,0,4,RX_SEEN); E(str_imm,0,4,RX_VALID)
    a.label('irq_finish'); E(movs_imm,0,0); E(str_imm,0,4,ACTIVE)
    E(pop,[3,4,5,6,7],pc=True)
    a.label('irq_bad_active'); E(movs_imm,0,0); E(str_imm,0,4,ACTIVE)
    a.label('irq_bad'); freeze()
    a.label('irq_no'); E(movs_imm,0,1); E(pop,[3,4,5,6,7],pc=True)
    a.label('irq_foreign'); E(mov_reg,0,7); E(pop,[3,4,5,6,7],lr=True); E(b_w,'ib_native_irq')
    a.label('ib_native_irq'); E(raw,IRQ_PROLOGUE); E(b_w,NATIVE_IRQ+4)

    for kind,native,registered,valid,seen,lr in (
            ('tx',0x080268D0,session.TX_ENDPOINT,TX_VALID,TX_SEEN,0x080526A9),
            ('rx',0x08026988,session.RX_PORT,RX_VALID,RX_SEEN,0x080526ED)):
        a.label('ib_'+kind+'_callback')
        E(push,[0,1,2,3,4,5,6],lr=True); imm(4,state); imm(6,session.STATE_BASE)
        E(ldr_imm,1,6,registered); E(cmp_reg,0,1); bc(kind+'_foreign','ne')
        field(0); imm(1,MAGIC); E(cmp_reg,0,1); bc(kind+'_deny','ne')
        for off,value in ((ACTIVE,1),(INVALID,0),(valid,1),(seen,0)):
            field(off); E(cmp_imm,0,value); bc(kind+'_deny','ne')
        E(ldr_sp,0,28); imm(1,lr); E(cmp_reg,0,1); bc(kind+'_deny','ne')
        E(movs_imm,0,1); E(str_imm,0,4,seen)
        a.label(kind+'_deny'); E(pop,[0,1,2,3,4,5,6],lr=True); E(movs_imm,0,0); E(bx_lr)
        a.label(kind+'_foreign'); E(pop,[0,1,2,3,4,5,6],lr=True)
        E(b_w,ss[f'ss_native_{native:08x}'])

    a.label('ib_disconnect')
    E(push,[0,1,2,3,4,5,6],lr=True); imm(4,state)
    field(0,2); imm(3,MAGIC); E(cmp_reg,2,3); bc('disconnect_forward','ne')
    field(CLASS,2); E(cmp_reg,0,2); bc('disconnect_forward','ne')
    field(CONTROLLER,2); E(cmp_reg,1,2); bc('disconnect_forward','ne')
    freeze()
    a.label('disconnect_forward'); E(pop,[0,1,2,3,4,5,6],lr=True)
    a.label('ib_native_disconnect'); E(raw,GATES[0x0805261C]); E(b_w,0x08052620)
    code,labels=a.assemble()
    if base+len(code)>0x08080000: raise ValueError('IRQ bridge exceeds app bounds')
    return code,labels
