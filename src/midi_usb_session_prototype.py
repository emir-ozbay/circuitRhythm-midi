"""EMULATION ONLY: bounded MIDI endpoint cancellation and tagged completions.

This experiment requires an IRQ bridge carrying immutable (epoch, ticket).
Stock callbacks carry no such token: registered untagged callbacks are denied.
The synthetic MMIO model is a contract, NOT evidence of real USB/DMA timing.
Only software-quiescent sessions can close; accepted RX debts and shared SysEx
readers are never discarded. No production builder imports this module.
"""
import midi_usb_lifecycle_prototype as life
import midi_usb_ledger_prototype as ledger
import midi_sysex_retry_prototype as retry
import midi_recovery_prototype as recovery
import seq_Patch as seq
from thumb_asm import (Asm, add_sp_imm, adds_imm8, ands_reg, b, b_cond_w, b_w,
                       bics_reg, bl, bx_lr, cbz, cmp_imm, cmp_reg, ldr_imm,
                       ldr_sp, ldr_w, ldrb_imm, ldrb_w, ldrh_imm, mov_reg,
                       movs_imm, orrs_reg, pop, push, raw, str_imm, str_w,
                       strb_imm, strh_imm, tst_reg)

CODE_BASE, STATE_BASE, STATE_SIZE = 0x08078000, 0x20047E00, 128
MAGIC = 0x31535355  # USS1
PHASE, USB_BASE, TX_ENDPOINT, RX_PORT, TX_PORT, DRIVER, EPOCH = 4,8,12,16,20,24,28
NEXT, TX_TICKET, RX_TICKET, TX_ACTIVE, RX_ACTIVE, BUSY = 32,36,40,44,48,52
NEED_ACK, DAINT, DEACH, CANCEL_TX, CANCEL_RX, ERRORS = 56,60,64,68,72,76
TX_EPOCH, RX_EPOCH, RX_LIMIT = 80,84,88
MAIN, ALT, BUFFER, TX_FIFO, TX_COUNTER, RAW, RX_BUFFER = 92,96,100,104,108,112,116
OPEN, CLOSING, WAIT_DISABLE, WAIT_FLUSH, SEALED, BROKEN = 1,2,3,4,5,6
EPENA, EPDIS, SNAK, ACK, CLEAR_INT = 0x80000000,0x40000000,0x08000000,2,0xFB7F
MIDI_MASK, MIDI_IN = 0x20002,2  # endpoint1 IN/OUT only
GRSTCTL, GINTSTS, DAINTMSK, DIEPEMPMSK, DEACHMSK = 0x10,0x14,0x81C,0x834,0x83C
IN_CTL, IN_INT, OUT_CTL, OUT_INT = 0x920,0x928,0xB20,0xB28


def gates():
    rc, rp = recovery.arm_code(); lc, lp = life.arm_code()
    result = {
        0x08026880: ('tx_arm', TX_ENDPOINT, bytes.fromhex('78b40446')),
        0x080268D0: ('tx_untagged', TX_ENDPOINT, bytes.fromhex('016a21b10022')),
        0x080269AC: ('rx_arm', RX_PORT, life.GATES[0x080269AC][2]),
        0x08026988: ('rx_untagged', RX_PORT, life.GATES[0x08026988][2]),
        0x080402B4: ('worker', TX_PORT, bytes.fromhex('10b50446')),
        0x080401AC: ('clear', TX_PORT, bytes.fromhex('10b50446')),
        0x0802C9D4: ('rx_lower', None, bytes.fromhex('80b5d0f89802')),
    }
    for name in ('rp_send','rp_sysex_send'):
        address = rp[name]
        result[address] = ('admission',TX_PORT,rc[address-recovery.CODE_BASE:address-recovery.CODE_BASE+4])
    for name in ('cl_reset','cl_resume'):
        address = lp[name]
        result[address] = ('lifecycle',None,lc[address-life.CODE_BASE:address-life.CODE_BASE+6])
    return result


def arm_code(base=CODE_BASE, state=STATE_BASE):
    old, lp = life.arm_code(); _, sp = seq.arm_code()
    if (base % 4 or state % 4 or not life.CODE_BASE+len(old) <= base < 0x08080000
            or not life.STATE_BASE+life.STATE_SIZE < state < state+STATE_SIZE < 0x20048000):
        raise ValueError('Session code/state overlaps or exceeds bounds')
    a = Asm(base); E = a.emit; fixups=[]
    def imm(r,v): a.imm32(r,v)
    def bc(label,cond): E(b_cond_w,label,cond)
    def field(off,r=0): E(ldr_imm,r,4,off)
    def zero_ptr(r,off,fail,byte=False):
        E(ldrb_imm if byte else ldr_w,0,r,off); E(cmp_imm,0,0); bc(fail,'ne')
    def mask(): E(raw,bytes.fromhex('eff3108372b6'))
    def restore(): E(raw,bytes.fromhex('83f31088'))
    def main(fail):
        E(raw,bytes.fromhex('eff31080')); E(cmp_imm,0,0); bc(fail,'ne')
        E(raw,bytes.fromhex('eff30580')); E(cmp_imm,0,0); bc(fail,'ne')
        imm(4,state); field(0); imm(1,MAGIC); E(cmp_reg,0,1); bc(fail,'ne')
        field(BUSY); E(cmp_imm,0,0); bc(fail,'ne')
    def trampoline(address): return f'ss_native_{address:08x}'
    def ptr(r,label):
        name='fix_'+str(len(fixups)); a.label(name); imm(r,0); fixups.append((name,r,label))

    # No writes. The controller/handle/base chain is synthetic but native-shaped.
    a.label('ss_binding')
    E(push,[3,4,5],lr=True); imm(4,state)
    E(bl,lp['cl_binding']); E(cmp_imm,0,1); bc('binding_no','ne')
    imm(5,life.STATE_BASE)
    for ss,cl in ((RX_PORT,life.PORT),(TX_ENDPOINT,life.TX_ENDPOINT),(EPOCH,life.EPOCH)):
        field(ss); E(ldr_imm,1,5,cl); E(cmp_reg,0,1); bc('binding_no','ne')
    field(TX_ENDPOINT); E(ldrb_imm,1,0); E(cmp_imm,1,0x81); bc('binding_no','ne')
    E(ldr_imm,0,0,16); E(ldr_imm,1,5,life.CONTROLLER)
    E(cmp_reg,0,1); bc('binding_no','ne')
    E(ldr_w,0,0,0x298); E(ldr_imm,0,0); field(USB_BASE,1)
    E(cmp_reg,0,1); bc('binding_no','ne')
    imm(2,0x50000000); E(cmp_reg,0,2); bc('base_ok','eq')
    imm(2,0x40040000); E(cmp_reg,0,2); bc('binding_no','ne')
    a.label('base_ok'); field(RX_PORT); E(ldrb_imm,1,0); E(cmp_imm,1,1); bc('binding_no','ne')
    field(TX_PORT); E(ldr_imm,0,0,20); field(DRIVER,1)
    E(cmp_reg,0,1); bc('binding_no','ne')
    field(DRIVER,5)
    E(ldr_imm,0,5); imm(1,0x08068CA4); E(cmp_reg,0,1); bc('binding_no','ne')
    for native,registered in ((4,RAW),(8,MAIN),(12,ALT)):
        E(ldr_imm,0,5,native); field(registered,1); E(cmp_reg,0,1); bc('binding_no','ne')
    field(MAIN); E(ldr_imm,0,0,4); field(BUFFER,1); E(cmp_reg,0,1); bc('binding_no','ne')
    field(RAW,5); E(ldr_imm,0,5); imm(1,0x0806919C)
    E(cmp_reg,0,1); bc('binding_no','ne')
    E(ldr_imm,0,5,4); field(TX_ENDPOINT,1); E(cmp_reg,0,1); bc('binding_no','ne')
    field(TX_PORT,5)
    for native,registered in ((4,TX_FIFO),(16,TX_COUNTER)):
        E(ldr_imm,0,5,native); field(registered,1); E(cmp_reg,0,1); bc('binding_no','ne')
    field(RX_PORT,5); E(ldrh_imm,0,5,2); E(cmp_imm,0,64); bc('binding_no','ne')
    E(ldr_imm,0,5,20); field(RX_BUFFER,1); E(cmp_reg,0,1); bc('binding_no','ne')
    E(movs_imm,0,1); E(pop,[3,4,5],pc=True)
    a.label('binding_no'); E(movs_imm,0,0); E(pop,[3,4,5],pc=True)

    # Reader lifetime, RX debts and musical ownership survive closure attempts.
    a.label('ss_quiet')
    E(push,[3,4,5],lr=True); imm(4,state)
    imm(5,life.STATE_BASE)
    for off in (life.BUSY,life.PUBLISHING): zero_ptr(5,off,'quiet_no')
    imm(5,retry.STATE_BASE)
    for off in (retry.BUSY,retry.ACTIVE,retry.PRODUCER_BUSY): zero_ptr(5,off,'quiet_no',True)
    zero_ptr(5,retry.REQUEST,'quiet_no')
    imm(5,ledger.STATE_BASE)
    for off in (ledger.BUSY,ledger.PENDING,ledger.SCANNED,ledger.FAULT): zero_ptr(5,off,'quiet_no')
    imm(5,recovery.STATE_BASE+recovery.HEADER_SIZE)
    for off in (recovery.FLAGS,recovery.BUSY): zero_ptr(5,off,'quiet_no',True)
    E(ldrh_imm,0,5,recovery.COUNT); E(cmp_imm,0,0); bc('quiet_no','ne')
    field(TX_PORT,5); E(ldr_imm,1,5,16)
    E(ldrh_imm,0,1); E(ldrh_imm,1,1,2); E(cmp_reg,0,1); bc('quiet_no','ne')
    E(ldr_imm,0,5,4); E(bl,0x0802A37E); E(cmp_imm,0,0); bc('quiet_no','ne')
    imm(5,life.STATE_BASE); E(ldr_imm,0,5,life.FIFO)
    E(bl,0x0802A37E); E(cmp_imm,0,0); bc('quiet_no','ne')
    E(ldr_imm,5,5,life.PARSER)
    E(ldrb_imm,0,5); E(cmp_imm,0,0); bc('quiet_no','ne')
    E(ldrb_imm,0,5,2); E(cmp_imm,0,1); bc('quiet_no','hi')
    E(ldr_imm,0,5,12); E(bl,0x0802A37E); E(cmp_imm,0,0); bc('quiet_no','ne')
    E(bl,sp['c_midi_inputs_idle']); E(cmp_imm,0,1); bc('quiet_no','ne')
    E(movs_imm,0,1); E(pop,[3,4,5],pc=True)
    a.label('quiet_no'); E(movs_imm,0,0); E(pop,[3,4,5],pc=True)

    a.label('ss_begin')
    E(push,[3,4,5],lr=True); main('begin_no')
    field(PHASE); E(cmp_imm,0,OPEN); bc('begin_no','ne')
    E(bl,'ss_binding'); E(cmp_imm,0,1); bc('begin_no','ne')
    field(EPOCH); imm(1,0xFFFFFFFF); E(cmp_reg,0,1); bc('begin_no','eq')
    E(bl,'ss_quiet'); E(cmp_imm,0,1); bc('begin_no','ne')
    # Publish/freeze handshake: no call or loop with interrupts forced off.
    imm(5,life.STATE_BASE); mask()
    E(ldr_imm,0,5,life.PUBLISHING); E(cmp_imm,0,0); bc('begin_mask_no','ne')
    E(ldr_imm,0,5,life.BUSY); E(cmp_imm,0,0); bc('begin_mask_no','ne')
    E(movs_imm,0,CLOSING); E(str_imm,0,4,PHASE)
    E(movs_imm,0,life.FROZEN); E(str_imm,0,5,life.PHASE); restore()
    E(movs_imm,0,0); E(pop,[3,4,5],pc=True)
    a.label('begin_mask_no'); restore()
    a.label('begin_no'); E(movs_imm,0,1); E(pop,[3,4,5],pc=True)

    # One bounded state transition per service call. No endpoint/global stop.
    a.label('ss_step')
    E(push,[3,4,5,6,7],lr=True); main('step_wait')
    E(bl,'ss_binding'); E(cmp_imm,0,1); bc('step_broken','ne')
    field(USB_BASE,5); field(PHASE)
    E(cmp_imm,0,CLOSING); bc('step_start','eq')
    E(cmp_imm,0,WAIT_DISABLE); bc('step_disabled','eq')
    E(cmp_imm,0,WAIT_FLUSH); bc('step_flushed','eq')
    E(cmp_imm,0,SEALED); bc('step_ok','eq'); E(b,'step_wait')
    a.label('step_start')
    E(bl,'ss_quiet'); E(cmp_imm,0,1); bc('step_wait','ne')
    for reg,save in ((DAINTMSK,DAINT),(DEACHMSK,DEACH)):
        E(ldr_w,0,5,reg); imm(1,MIDI_MASK); E(mov_reg,2,0); E(ands_reg,2,1)
        E(str_imm,2,4,save); E(bics_reg,0,1); E(str_w,0,5,reg)
    E(ldr_w,0,5,DIEPEMPMSK); E(movs_imm,1,MIDI_IN); E(bics_reg,0,1); E(str_w,0,5,DIEPEMPMSK)
    E(movs_imm,6,0)
    for ctl,irq,bit in ((IN_CTL,IN_INT,1),(OUT_CTL,OUT_INT,2)):
        imm(0,CLEAR_INT); E(str_w,0,5,irq)
        E(ldr_w,0,5,ctl); imm(1,EPENA); E(tst_reg,0,1)
        bc(f'disable_idle_{bit}','eq')
        E(movs_imm,1,bit); E(orrs_reg,6,1); imm(1,EPDIS); E(orrs_reg,0,1)
        a.label(f'disable_idle_{bit}'); imm(1,SNAK); E(orrs_reg,0,1); E(str_w,0,5,ctl)
    E(str_imm,6,4,NEED_ACK); E(raw,bytes.fromhex('bff34f8f'))  # DSB SY
    E(movs_imm,0,WAIT_DISABLE); E(str_imm,0,4,PHASE); E(b,'step_wait')
    a.label('step_disabled')
    field(NEED_ACK,6)
    for ctl,irq,bit in ((IN_CTL,IN_INT,1),(OUT_CTL,OUT_INT,2)):
        E(ldr_w,0,5,ctl); imm(1,EPENA); E(tst_reg,0,1); bc('step_wait','ne')
        E(movs_imm,1,bit); E(tst_reg,6,1); bc(f'ack_ok_{bit}','eq')
        E(ldr_w,0,5,irq); E(movs_imm,1,ACK); E(tst_reg,0,1); bc('step_wait','eq')
        a.label(f'ack_ok_{bit}')
    E(ldr_w,0,5,GINTSTS); E(movs_imm,1,16); E(tst_reg,0,1); bc('step_wait','ne')
    E(ldr_w,0,5,GRSTCTL); E(movs_imm,1,0x30); E(tst_reg,0,1); bc('step_wait','ne')
    imm(1,0x80000000); E(tst_reg,0,1); bc('step_wait','eq')  # AHB idle contract
    for irq in (IN_INT,OUT_INT): imm(0,CLEAR_INT); E(str_w,0,5,irq)
    E(movs_imm,0,0x60); E(str_w,0,5,GRSTCTL)  # TX FIFO1 only, never global RX
    E(movs_imm,0,WAIT_FLUSH); E(str_imm,0,4,PHASE); E(b,'step_wait')
    a.label('step_flushed')
    E(ldr_w,0,5,GRSTCTL); E(movs_imm,1,0x30); E(tst_reg,0,1); bc('step_wait','ne')
    E(ldr_w,0,5,GINTSTS); E(movs_imm,1,16); E(tst_reg,0,1); bc('step_wait','ne')
    for ctl in (IN_CTL,OUT_CTL):
        E(ldr_w,0,5,ctl); imm(1,EPENA); E(tst_reg,0,1); bc('step_broken','ne')
    for irq in (IN_INT,OUT_INT):
        imm(0,CLEAR_INT); E(str_w,0,5,irq)
    E(raw,bytes.fromhex('bff34f8f'))
    for irq in (IN_INT,OUT_INT):
        E(ldr_w,0,5,irq); E(movs_imm,1,3); E(tst_reg,0,1); bc('step_wait','ne')
    E(bl,'ss_quiet'); E(cmp_imm,0,1); bc('step_wait','ne')
    E(movs_imm,0,1); E(str_imm,0,4,BUSY)
    # DMA/queued callback jobs own the old buffers until this barrier completes.
    field(TX_PORT); E(bl,trampoline(0x080401AC))
    field(TX_PORT,6); E(movs_imm,0,0); E(str_imm,0,6,8); E(str_imm,0,6,12)
    field(DRIVER,6)
    E(ldr_imm,7,6,8); E(strh_imm,0,7)
    E(ldr_imm,1,6,12); E(strh_imm,0,1); E(str_imm,0,1,4)
    E(strh_imm,0,6,18); E(strb_imm,0,6,20); E(str_imm,7,6,24)
    E(ldrh_imm,1,6,16); E(strh_imm,1,6,30)
    field(TX_ENDPOINT,6); E(strb_imm,0,6,12); E(movs_imm,1,1); E(strb_imm,1,6,28)
    E(ldr_imm,1,6,32); E(cmp_imm,1,0); bc('no_timer','eq')
    E(strb_imm,0,1,8)
    a.label('no_timer'); field(RX_PORT,6); E(str_imm,0,6,28)
    # Clear native HAL transfer pointers/counts only after endpoint quiescence.
    imm(1,life.STATE_BASE); E(ldr_imm,1,1,life.CONTROLLER); E(ldr_w,1,1,0x298)
    for desc in (0x3C+0x1C,0x1FC+0x1C):
        for off in (12,16,20,24): E(str_w,0,1,desc+off)
    for active,count in ((TX_ACTIVE,CANCEL_TX),(RX_ACTIVE,CANCEL_RX)):
        field(active,1); field(count,2); E(raw,bytes.fromhex('5218'))  # adds r2,r2,r1
        E(str_imm,2,4,count); E(str_imm,0,4,active)
    E(bl,trampoline(lp['cl_reset'])); E(cmp_imm,0,0); bc('seal_fail','ne')
    imm(1,life.STATE_BASE); E(ldr_imm,1,1,life.EPOCH); E(str_imm,1,4,EPOCH)
    E(movs_imm,0,SEALED); E(str_imm,0,4,PHASE); E(movs_imm,0,0); E(str_imm,0,4,BUSY)
    E(b,'step_ok')
    a.label('seal_fail'); E(movs_imm,0,0); E(str_imm,0,4,BUSY)
    a.label('step_broken')
    E(movs_imm,0,BROKEN); E(str_imm,0,4,PHASE); E(movs_imm,0,1); E(str_imm,0,4,ERRORS)
    imm(1,life.STATE_BASE); E(movs_imm,0,life.FROZEN); E(str_imm,0,1,life.PHASE)
    a.label('step_wait'); E(movs_imm,0,1); E(pop,[3,4,5,6,7],pc=True)
    a.label('step_ok'); E(movs_imm,0,0); E(pop,[3,4,5,6,7],pc=True)

    a.label('ss_resume')
    E(push,[3,4,5],lr=True); main('resume_no')
    field(PHASE); E(cmp_imm,0,SEALED); bc('resume_no','ne')
    E(bl,'ss_binding'); E(cmp_imm,0,1); bc('resume_no','ne')
    field(USB_BASE,5)
    for reg,bits in ((IN_CTL,EPENA),(OUT_CTL,EPENA),(IN_INT,3),(OUT_INT,3),
                     (GRSTCTL,0x30),(GINTSTS,16)):
        E(ldr_w,0,5,reg); imm(1,bits); E(tst_reg,0,1); bc('resume_no','ne')
    E(bl,trampoline(lp['cl_resume'])); E(cmp_imm,0,0); bc('resume_no','ne')
    field(USB_BASE,5)
    for reg,save in ((DAINTMSK,DAINT),(DEACHMSK,DEACH)):
        E(ldr_w,0,5,reg); imm(1,MIDI_MASK); E(bics_reg,0,1); field(save,1)
        E(orrs_reg,0,1); E(str_w,0,5,reg)
    E(movs_imm,0,OPEN); E(str_imm,0,4,PHASE)
    field(RX_PORT); E(bl,0x080269AC)
    field(PHASE); E(cmp_imm,0,OPEN); bc('resume_no','ne')
    E(movs_imm,0,0); E(pop,[3,4,5],pc=True)
    a.label('resume_no'); E(movs_imm,0,1); E(pop,[3,4,5],pc=True)

    # Only the bridge may call these APIs. Epoch/ticket belong to immutable jobs,
    # never copied from the CURRENT endpoint at the time a callback arrives.
    for kind,active,ticket,epoch,endpoint,native in (
            ('tx',TX_ACTIVE,TX_TICKET,TX_EPOCH,TX_ENDPOINT,0x080268D0),
            ('rx',RX_ACTIVE,RX_TICKET,RX_EPOCH,RX_PORT,0x08026988)):
        a.label('ss_'+kind+'_done')
        E(push,[3,4,5],lr=True); imm(4,state)
        if kind=='rx': E(mov_reg,5,2)  # r2=received bytes from immutable IRQ job
        field(0,2); imm(3,MAGIC); E(cmp_reg,2,3); bc(kind+'_done_no','ne')
        field(PHASE,2); E(cmp_imm,2,OPEN); bc(kind+'_done_no','ne')
        imm(2,life.STATE_BASE); E(ldr_imm,3,2,life.PHASE)
        E(cmp_imm,3,life.ACTIVE); bc(kind+'_done_no','ne')
        E(ldr_imm,2,2,life.CONTROLLER); E(ldrb_w,2,2,0x274)
        E(cmp_imm,2,3); bc(kind+'_done_no','ne')
        mask()
        field(PHASE,2); E(cmp_imm,2,OPEN); bc(kind+'_done_mask_no','ne')
        field(active,2); E(cmp_imm,2,1); bc(kind+'_done_mask_no','ne')
        field(epoch,2); E(cmp_reg,0,2); bc(kind+'_done_mask_no','ne')
        field(EPOCH,2); E(cmp_reg,0,2); bc(kind+'_done_mask_no','ne')
        field(ticket,2); E(cmp_reg,1,2); bc(kind+'_done_mask_no','ne')
        if kind=='rx':
            E(mov_reg,1,5); field(RX_LIMIT,2); E(cmp_reg,1,2); bc(kind+'_done_mask_no','hi')
        E(movs_imm,0,2); E(str_imm,0,4,active)  # completing, not available for reuse
        restore()
        field(endpoint); E(bl,trampoline(native))
        a.label('ss_'+kind+'_done_after_native')
        if kind=='tx': E(movs_imm,0,0); E(str_imm,0,4,active)
        E(movs_imm,0,1); E(pop,[3,4,5],pc=True)
        a.label(kind+'_done_mask_no'); restore()
        a.label(kind+'_done_no'); E(movs_imm,0,0); E(pop,[3,4,5],pc=True)

    for address,(kind,registered,original) in gates().items():
        suffix = f'{address:08x}'; deny,allow = 'deny_'+suffix,'allow_'+suffix
        a.label('ss_gate_'+suffix); E(push,[0,1,2,3,4,5,6],lr=True); imm(4,state)
        if kind=='rx_lower':
            imm(1,life.STATE_BASE); E(ldr_imm,1,1,life.CONTROLLER)
            E(cmp_reg,0,1); bc(allow,'ne')
            E(ldr_sp,1,4); E(cmp_imm,1,1); bc(allow,'ne')
        elif registered is not None:
            field(registered,1); E(cmp_reg,0,1); bc(allow,'ne')
        field(0); imm(1,MAGIC); E(cmp_reg,0,1); bc(deny,'ne')
        if kind in ('lifecycle','clear','tx_untagged','rx_untagged'):
            E(b,deny)
        else:
            field(PHASE); E(cmp_imm,0,OPEN); bc(deny,'ne')
            imm(1,life.STATE_BASE); E(ldr_imm,0,1,life.PHASE)
            E(cmp_imm,0,life.ACTIVE); bc(deny,'ne')
            E(ldr_imm,1,1,life.CONTROLLER); E(ldrb_w,0,1,0x274)
            E(cmp_imm,0,3); bc(deny,'ne')
            if kind=='rx_lower':
                field(RX_ACTIVE); E(cmp_imm,0,1); bc(deny,'ne')
                E(ldr_sp,0,12); E(str_imm,0,4,RX_LIMIT); E(b,allow)
            elif kind in ('tx_arm','rx_arm'):
                active,ticket,epoch = (TX_ACTIVE,TX_TICKET,TX_EPOCH) if kind=='tx_arm' else (RX_ACTIVE,RX_TICKET,RX_EPOCH)
                if kind=='tx_arm':
                    field(TX_ENDPOINT); E(ldrb_imm,0,0,28); E(cmp_imm,0,1); bc(deny,'ne')
                mask()
                field(PHASE); E(cmp_imm,0,OPEN); bc('arm_mask_no_'+suffix,'ne')
                field(active); E(cmp_imm,0,0); bc('arm_empty_'+suffix,'eq')
                if kind=='rx_arm':
                    E(cmp_imm,0,2); bc('arm_mask_no_'+suffix,'ne')
                    E(ldr_sp,0,28); ptr(1,'ss_rx_done_after_native')
                    E(cmp_reg,0,1); bc('arm_mask_no_'+suffix,'ne')
                else: E(b,'arm_mask_no_'+suffix)
                a.label('arm_empty_'+suffix)
                field(NEXT); imm(1,0xFFFFFFFF); E(cmp_reg,0,1); bc('ticket_wrap_'+suffix,'eq')
                E(adds_imm8,0,1); E(str_imm,0,4,NEXT); E(str_imm,0,4,ticket)
                field(EPOCH); E(str_imm,0,4,epoch); E(movs_imm,0,1); E(str_imm,0,4,active)
                restore()
                for r in range(4): E(ldr_sp,r,r*4)
                E(bl,trampoline(address)); E(mov_reg,5,0)
                # Native lower status0 is acceptance. Failure pins the session.
                E(cmp_imm,5,0); bc('arm_ok_'+suffix,'eq')
                E(movs_imm,0,BROKEN); E(str_imm,0,4,PHASE)
                imm(1,life.STATE_BASE); E(movs_imm,0,life.FROZEN); E(str_imm,0,1,life.PHASE)
                a.label('arm_ok_'+suffix); E(mov_reg,0,5); E(add_sp_imm,4); E(pop,[1,2,3,4,5,6],pc=True)
                a.label('ticket_wrap_'+suffix)
                restore()
                E(movs_imm,0,BROKEN); E(str_imm,0,4,PHASE)
                imm(1,life.STATE_BASE); E(movs_imm,0,life.FROZEN); E(str_imm,0,1,life.PHASE); E(b,deny)
                a.label('arm_mask_no_'+suffix); restore(); E(b,deny)
            else: E(b,allow)
        a.label(deny); E(pop,[0,1,2,3,4,5,6],lr=True)
        E(movs_imm,0,1 if kind in ('lifecycle','tx_arm','rx_arm','rx_lower') else 0); E(bx_lr)
        a.label(allow); E(pop,[0,1,2,3,4,5,6],lr=True); E(b_w,trampoline(address))
        a.label(trampoline(address))
        if address == 0x080268D0:
            # The original CBZ is PC-relative. Relocate without changing flags.
            E(ldr_imm,1,0,32); E(cbz,'tx_timer_absent',1)
            E(movs_imm,2,0); E(b_w,address+6)
            a.label('tx_timer_absent'); E(b_w,0x080268DE)
        else:
            E(raw,original); E(b_w,address+len(original))
    code,labels = a.assemble(); code=bytearray(code)
    from thumb_asm import movw,movt
    for name,r,target in fixups:
        offset=labels[name]-base; value=labels[target]|1
        assert code[offset:offset+8]==movw(r,0)+movt(r,0)
        code[offset:offset+8]=movw(r,value&0xFFFF)+movt(r,value>>16)
    if base+len(code)>0x08080000: raise ValueError('Session code exceeds application flash')
    return bytes(code),labels
