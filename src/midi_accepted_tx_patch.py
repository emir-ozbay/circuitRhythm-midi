"""Bounded CPU-FIFO MIDI IN retirement and conservative closing-event replay.

Only the registered MAIN job is journalled. MMIO disable/ACK/flush is a
hardware contract to verify in emulation,not physical silicon evidence.
Unconfirmed Off/Stop may be replayed after ambiguous partial host delivery;
On/Clock/SysEx are never replayed. No changes to the bootloader or filesystem.
"""
import seq_Patch as seq
import midi_recovery_prototype as core
from thumb_asm import (Asm,adds_imm8,adds_reg,ands_reg,b_w,b_cond_w,bics_reg,bl,bx_lr,cmp_imm,cmp_reg,
    ldr_imm,ldr_w,ldr_sp,ldrb_imm,ldrb_w,ldrh_imm,lsrs_imm,mov_reg,movs_imm,orrs_reg,pop,push,raw,
    str_imm,str_w,str_sp,strb_imm,strb_w,strh_imm,subs_imm8,tst_reg)

CODE_BASE=0x0807F000
STATE_BASE=seq.SEQ_STATE_ADDR+0x80
STATE_SIZE=128
JOB,PHASE,EP,CTRL,DATA,LENGTH,GEN,CURSOR,SHADOW=0,4,8,12,16,20,24,28,32
DAINT,DEACH,NEED_ACK=96,100,104
INIT_CLASS,INIT_CONFIG,INIT_BUSY,IRQ_ACTIVE,IRQ_GEN=108,112,116,120,124
WAIT_CONFIG=CURSOR
IDLE,ARMING,ACTIVE,DONE=0,1,2,3
OPEN,REQUEST,WAIT_ACK,WAIT_FLUSH,REPLAY,BROKEN=0,1,2,3,4,5
USB_BASE=0x40040000
IN_CTL,IN_INT,GRSTCTL=0x920,0x928,0x10
DAINTMSK,DEACHMSK,EMPMSK=0x81C,0x83C,0x834
EPENA,EPDIS,SNAK=0x80000000,0x40000000,0x08000000
FULL=0x0802B4B2;FULL_BYTES=bytes.fromhex('80b58169')
DONE_SITE=0x080268D0;DONE_BYTES=bytes.fromhex('016a21b10022')
CLOSE_SITE=0x0805261C;CLOSE_BYTES=bytes.fromhex('f8b50646')
IRQ_SITE=0x0804293E;IRQ_BYTES=bytes.fromhex('2de9f04f')
INIT_SITE=0x08040B5A;INIT_BYTES=bytes.fromhex('f8b50446')
RESET_SITE=0x08042D20;RESET_BYTES=bytes.fromhex('69684908')


def arm_code(recovery_state,flush_busy):
    _,rp=core.arm_code(base=0x0807D400,state=recovery_state)
    assert STATE_BASE+STATE_SIZE==seq.SEQ_STATE_ADDR+seq.SEQ_STATE_SIZE
    assert max(off+size for off,size in seq.OFF.values())<=0x80
    entry=recovery_state+core.HEADER_SIZE
    a=Asm(CODE_BASE);E=a.emit
    def imm(r,v):a.imm32(r,v)
    def bc(label,cond):E(b_cond_w,label,cond)
    def mask():E(raw,bytes.fromhex('eff31083 72b6'))
    def restore():E(raw,bytes.fromhex('83f31088'))
    def dsb():E(raw,bytes.fromhex('bff34f8f'))
    def phase(next_phase,exit_label):
        mask();E(ldr_imm,0,4,GEN);E(cmp_reg,0,7);bc('service_unlock_wait','ne')
        E(movs_imm,0,next_phase);E(str_imm,0,4,PHASE);restore();E(b_w,exit_label)
    def ram(r,size,fail):
        E(movs_imm,1,3);E(tst_reg,r,1);bc(fail,'ne')
        imm(1,0x20000000);E(cmp_reg,r,1);bc(fail,'lo')
        imm(1,recovery_state-size);E(cmp_reg,r,1);bc(fail,'hi')

    # Returns the registered first driver's endpoint. Scratch-only,no writes.
    a.label('tg_endpoint');imm(1,recovery_state);E(ldr_imm,2,1);imm(3,core.MAGIC);E(cmp_reg,2,3);bc('endpoint_no','ne')
    E(ldr_imm,1,1,core.HEADER_SIZE);E(cmp_imm,1,0);bc('endpoint_no','eq')
    E(ldr_imm,1,1,0x14);E(ldr_imm,2,1);imm(3,0x08068CA4);E(cmp_reg,2,3);bc('endpoint_no','ne')
    E(ldr_imm,1,1,4);E(ldr_imm,2,1);imm(3,0x0806919C);E(cmp_reg,2,3);bc('endpoint_no','ne')
    E(ldr_imm,0,1,4);E(bx_lr)
    a.label('endpoint_no');E(movs_imm,0,0);E(bx_lr)

    # The caller already owns the registered MAIN flush lease. Publish ARMING
    # before copying;close can freeze it but service waits for that lease.
    a.label('tg_prepare');E(push,[3,4,5,6,7],lr=True);E(mov_reg,5,0);E(mov_reg,6,1);E(mov_reg,7,2);imm(4,STATE_BASE)
    E(cmp_imm,7,4);bc('prepare_no','lo');E(cmp_imm,7,64);bc('prepare_no','hi');E(movs_imm,1,3);E(tst_reg,7,1);bc('prepare_no','ne')
    mask();E(ldr_imm,0,4,PHASE);E(ldr_imm,1,4,JOB);E(orrs_reg,0,1);E(cmp_imm,0,0);bc('prepare_unlock_no','ne')
    E(str_imm,5,4,EP);E(ldr_imm,0,5,0x10);E(str_imm,0,4,CTRL);E(str_imm,6,4,DATA);E(str_imm,7,4,LENGTH)
    E(movs_imm,0,ARMING);E(str_imm,0,4,JOB);restore()
    E(mov_reg,5,4);E(adds_imm8,5,SHADOW)
    a.label('copy_snapshot');E(ldr_imm,0,6);E(str_imm,0,5);E(adds_imm8,5,4);E(adds_imm8,6,4);E(subs_imm8,7,4);bc('copy_snapshot','ne')
    mask();E(ldr_imm,0,4,PHASE);E(cmp_imm,0,0);bc('prepare_aborted','ne');restore()
    E(movs_imm,0,1);E(pop,[3,4,5,6,7],pc=True)
    a.label('prepare_aborted');E(movs_imm,0,0);E(str_imm,0,4,JOB);E(str_imm,0,4,LENGTH)
    a.label('prepare_unlock_no');restore()
    a.label('prepare_no');E(movs_imm,0,0);E(pop,[3,4,5,6,7],pc=True)

    a.label('tg_finish');E(push,[4],lr=True);E(mov_reg,4,0);imm(2,STATE_BASE);mask()
    E(cmp_imm,4,0);bc('finish_idle','ne');E(ldr_imm,0,2,JOB);E(cmp_imm,0,DONE);bc('finish_idle','eq')
    E(movs_imm,0,ACTIVE);E(str_imm,0,2,JOB);E(b_w,'finish_restore')
    a.label('finish_idle');E(movs_imm,0,0);E(str_imm,0,2,JOB);E(str_imm,0,2,LENGTH)
    a.label('finish_restore');restore();E(mov_reg,0,4);E(pop,[4],pc=True)

    a.label('tg_blocked');imm(1,STATE_BASE);E(ldr_imm,0,1,JOB);E(ldr_imm,1,1,PHASE);E(orrs_reg,0,1);E(bx_lr)
    a.label('tg_pause');imm(1,recovery_state);E(ldr_imm,2,1);imm(3,core.MAGIC);E(cmp_reg,2,3);bc('pause_no','ne')
    E(ldr_imm,1,1,core.HEADER_SIZE);E(cmp_reg,0,1);bc('pause_no','ne');imm(1,STATE_BASE);E(ldr_imm,0,1,PHASE);E(bx_lr)
    a.label('pause_no');E(movs_imm,0,0);E(bx_lr)

    a.label('tg_full');E(push,[4],lr=True);E(mov_reg,4,0)
    imm(1,recovery_state);E(ldr_imm,2,1);imm(3,core.MAGIC);E(cmp_reg,2,3);bc('full_native','ne')
    E(ldr_imm,1,1,core.HEADER_SIZE);E(cmp_imm,1,0);bc('full_native','eq')
    E(ldr_imm,1,1,0x14);E(cmp_reg,1,4);bc('full_native','ne')
    E(bl,'tg_blocked');E(cmp_imm,0,0);bc('full_native','eq')
    E(movs_imm,0,1);E(pop,[4],pc=True)
    a.label('full_native');E(mov_reg,0,4);E(pop,[4],lr=True);E(b_w,'tg_native_full')
    a.label('tg_native_full');E(raw,FULL_BYTES);E(b_w,FULL+4)

    a.label('tg_done');E(push,[4,5,6],lr=True);E(mov_reg,4,0);E(mov_reg,6,14)
    E(bl,'tg_endpoint');E(cmp_imm,0,0);bc('done_native','eq');E(cmp_reg,0,4);bc('done_native','ne')
    imm(5,STATE_BASE);mask();E(ldr_imm,0,5,PHASE);E(cmp_imm,0,0);bc('done_reject','ne')
    E(ldr_imm,0,5,IRQ_ACTIVE);E(cmp_imm,0,0);bc('done_context_ok','eq')
    E(ldr_imm,0,5,GEN);E(ldr_imm,1,5,IRQ_GEN);E(cmp_reg,0,1);bc('done_reject','ne')
    a.label('done_context_ok')
    E(ldr_imm,0,5,JOB);E(cmp_imm,0,0);bc('done_unlock_native','eq')
    imm(1,0x080526A9);E(cmp_reg,6,1);bc('done_reject','ne')
    E(cmp_imm,0,ARMING);bc('done_arming','eq');E(movs_imm,0,0);E(str_imm,0,5,LENGTH);E(b_w,'done_store')
    a.label('done_arming');E(movs_imm,0,DONE)
    a.label('done_store');E(str_imm,0,5,JOB)
    a.label('done_unlock_native');restore()
    a.label('done_native');E(mov_reg,0,4);E(pop,[4,5,6],lr=True);E(b_w,'tg_native_done')
    a.label('done_reject');restore();E(movs_imm,0,0);E(pop,[4,5,6],pc=True)
    a.label('tg_native_done');E(ldr_imm,1,0,0x20);E(cmp_imm,1,0);bc('done_no_timer','eq');E(movs_imm,2,0);E(b_w,DONE_SITE+6)
    a.label('done_no_timer');E(b_w,0x080268DE)

    # Class matching and freeze occur before the stock destructive close.
    a.label('tg_close_gate');E(push,[0,1,2,3,4],lr=True);E(bl,'tg_close');E(pop,[0,1,2,3,4],lr=True);E(b_w,'tg_native_close')
    a.label('tg_native_close');E(raw,CLOSE_BYTES);E(b_w,CLOSE_SITE+4)
    a.label('tg_close');E(push,[3,4,5,6,7],lr=True);E(mov_reg,4,0);E(mov_reg,5,1)
    E(bl,'tg_endpoint');E(cmp_imm,0,0);bc('close_return','eq');E(mov_reg,6,0)
    E(ldr_imm,1,6,0x10);E(cmp_reg,1,5);bc('close_return','ne')
    E(ldr_imm,0,4,4);E(ldr_imm,0,0);E(cmp_reg,0,6);bc('close_return','ne')
    E(mov_reg,0,6);E(mov_reg,1,5);E(bl,'tg_request')
    a.label('close_return');E(pop,[3,4,5,6,7],pc=True)
    a.label('tg_request');E(push,[3,4,5,6,7],lr=True);E(mov_reg,6,0);E(mov_reg,5,1)
    E(ldr_w,7,5,0x298);ram(7,0x74,'close_invalid')
    E(ldr_imm,0,7,0x10);E(cmp_imm,0,0);bc('close_invalid','ne')
    E(ldr_imm,7,7);imm(1,USB_BASE);E(cmp_reg,7,1);bc('close_publish','eq')
    a.label('close_invalid');E(movs_imm,7,0)
    a.label('close_publish')
    imm(4,STATE_BASE);mask();E(str_imm,6,4,EP);E(str_imm,5,4,CTRL)
    E(ldr_imm,0,4,PHASE);E(cmp_imm,0,BROKEN);bc('close_unlock','eq')
    E(cmp_imm,7,0);bc('close_broken','eq')
    E(ldr_imm,0,4,PHASE);E(cmp_imm,0,0);bc('close_masks_saved','ne')
    for reg,save in ((DAINTMSK,DAINT),(DEACHMSK,DEACH)):
        E(ldr_w,0,7,reg);E(movs_imm,1,2);E(ands_reg,0,1);E(str_imm,0,4,save)
    a.label('close_masks_saved')
    E(ldr_imm,0,4,GEN);imm(1,0xFFFFFFFF);E(cmp_reg,0,1);bc('close_broken','eq')
    E(adds_imm8,0,1);E(str_imm,0,4,GEN);E(movs_imm,0,REQUEST);E(str_imm,0,4,PHASE)
    E(ldr_imm,0,4,JOB);E(cmp_imm,0,0);bc('close_unlock','eq')
    a.label('close_quarantine')
    imm(0,entry);E(ldrb_imm,1,0,core.FLAGS);E(movs_imm,2,core.FAULT);E(orrs_reg,1,2);E(strb_imm,1,0,core.FLAGS)
    imm(0,seq.SEQ_STATE_ADDR);E(movs_imm,1,1);E(strb_w,1,0,seq.OFF_MIDI_TX_FAULT)
    a.label('close_unlock');restore()
    a.label('request_return');E(pop,[3,4,5,6,7],pc=True)
    a.label('close_broken');E(movs_imm,0,BROKEN);E(str_imm,0,4,PHASE);E(b_w,'close_quarantine')

    # One bounded transition per poll. Only IN1 is masked/disabled/flushed.
    # RX/MSC endpoints and global RX FIFO are never stopped or flushed.
    a.label('tg_service');E(push,[3,4,5,6,7],lr=True);imm(4,STATE_BASE)
    E(raw,bytes.fromhex('eff31080'));E(cmp_imm,0,0);bc('service_return','ne')
    E(raw,bytes.fromhex('eff30580'));E(cmp_imm,0,0);bc('service_return','ne')
    E(ldr_imm,0,4,PHASE);E(cmp_imm,0,0);bc('service_return','eq');E(cmp_imm,0,BROKEN);bc('service_return','eq')
    imm(0,entry);E(ldrb_imm,1,0,core.BUSY);E(cmp_imm,1,1);bc('service_return','ne')
    E(ldrb_imm,1,0,flush_busy);E(cmp_imm,1,0);bc('service_return','ne')
    E(ldr_imm,7,4,GEN);E(ldr_imm,5,4,CTRL);ram(5,0x29C,'service_return')
    E(ldr_w,6,5,0x298);ram(6,0x74,'service_return')
    E(ldr_imm,5,6);imm(1,USB_BASE);E(cmp_reg,5,1);bc('service_return','ne')
    E(ldr_imm,0,6,0x10);E(cmp_imm,0,0);bc('service_return','ne')
    E(ldr_imm,0,4,PHASE);E(cmp_imm,0,REQUEST);bc('service_request','eq')
    E(cmp_imm,0,WAIT_ACK);bc('service_ack','eq');E(cmp_imm,0,WAIT_FLUSH);bc('service_flush','eq')
    E(cmp_imm,0,REPLAY);bc('service_replay','eq');E(b_w,'service_return')
    a.label('service_request')
    # Preserve unrelated mask bits even if close/re-init has modified IN1.
    mask()
    for reg in (DAINTMSK,DEACHMSK):
        E(ldr_w,0,5,reg);E(movs_imm,1,2);E(bics_reg,0,1);E(str_w,0,5,reg)
    E(ldr_w,0,5,EMPMSK);E(movs_imm,1,2);E(bics_reg,0,1);E(str_w,0,5,EMPMSK);restore()
    imm(0,0xFB7F);E(str_w,0,5,IN_INT)
    E(ldr_w,0,5,IN_CTL);imm(1,EPENA);E(movs_imm,2,0);E(tst_reg,0,1);bc('request_idle','eq')
    E(movs_imm,2,1);imm(1,EPDIS);E(orrs_reg,0,1)
    a.label('request_idle');E(str_imm,2,4,NEED_ACK);imm(1,SNAK);E(orrs_reg,0,1);E(str_w,0,5,IN_CTL);dsb()
    phase(WAIT_ACK,'service_return')
    a.label('service_ack');E(ldr_w,0,5,IN_CTL);imm(1,EPENA);E(tst_reg,0,1);bc('service_return','ne')
    E(ldr_imm,0,4,NEED_ACK);E(cmp_imm,0,0);bc('ack_idle','eq')
    E(ldr_w,0,5,IN_INT);E(movs_imm,1,2);E(tst_reg,0,1);bc('service_return','eq')
    a.label('ack_idle');E(ldr_w,0,5,GRSTCTL);E(movs_imm,1,0x30);E(tst_reg,0,1);bc('service_return','ne')
    imm(1,0x80000000);E(tst_reg,0,1);bc('service_return','eq')
    imm(0,0xFB7F);E(str_w,0,5,IN_INT);E(movs_imm,0,0x60);E(str_w,0,5,GRSTCTL);dsb()
    phase(WAIT_FLUSH,'service_return')
    a.label('service_flush');E(ldr_w,0,5,GRSTCTL);E(movs_imm,1,0x30);E(tst_reg,0,1);bc('service_return','ne')
    imm(1,0x80000000);E(tst_reg,0,1);bc('service_return','eq')
    E(ldr_w,0,5,IN_CTL);imm(1,EPENA);E(tst_reg,0,1);bc('service_return','ne')
    imm(0,0xFB7F);E(str_w,0,5,IN_INT);dsb();E(ldr_w,0,5,IN_INT);E(movs_imm,1,3);E(tst_reg,0,1);bc('service_return','ne')
    phase(REPLAY,'service_return')
    a.label('service_replay')
    E(ldr_imm,0,4,INIT_CLASS);E(cmp_imm,0,0);bc('service_no_init','eq')
    E(ldr_imm,0,4,INIT_BUSY);E(cmp_imm,0,0);bc('service_return','ne')
    E(ldr_imm,0,4,CTRL);E(ldrb_w,1,0,0x274);E(cmp_imm,1,3);bc('service_return','ne')
    mask();E(ldr_imm,0,4,GEN);E(cmp_reg,0,7);bc('service_unlock_wait','ne')
    E(movs_imm,0,1);E(str_imm,0,4,INIT_BUSY);restore()
    E(ldr_imm,0,4,INIT_CLASS);E(ldr_imm,1,4,CTRL);E(ldr_imm,2,4,INIT_CONFIG);E(bl,'tg_native_init');E(mov_reg,5,0)
    mask();E(movs_imm,0,0);E(str_imm,0,4,INIT_BUSY)
    E(ldr_imm,0,4,GEN);E(cmp_reg,0,7);bc('service_unlock_wait','ne')
    E(cmp_imm,5,0);bc('service_init_bad','ne')
    E(movs_imm,0,0);E(str_imm,0,4,INIT_CLASS);E(str_imm,0,4,INIT_CONFIG);E(str_imm,0,4,WAIT_CONFIG);restore()
    a.label('service_no_init');E(ldr_imm,0,4,WAIT_CONFIG);E(cmp_imm,0,0);bc('service_return','ne')
    E(ldr_imm,0,4,JOB);E(cmp_imm,0,ACTIVE);bc('replay_no_job','ne')
    # Preserve captured data if the binding or driver selection changed.
    imm(0,entry);E(ldr_imm,0,0);E(ldr_imm,5,0,0x14);E(ldr_imm,6,5,8)
    E(ldr_imm,0,5,0x18);E(cmp_reg,0,6);bc('service_return','ne')
    E(ldrb_imm,0,5,0x14);E(cmp_imm,0,0);bc('service_return','ne')
    E(ldr_imm,0,6,4);E(ldr_imm,1,4,DATA);E(cmp_reg,0,1);bc('service_return','ne')
    E(ldr_imm,6,6,4);E(mov_reg,5,4);E(adds_imm8,5,SHADOW);E(movs_imm,3,0)
    for n in range(16):
        skip=f'replay_skip_{n}';copy=f'replay_copy_{n}'
        E(ldr_imm,0,4,LENGTH);E(cmp_imm,0,n*4);bc(skip,'ls')
        E(ldr_imm,0,5,n*4);E(movs_imm,1,15);E(ands_reg,1,0);E(cmp_imm,1,8);bc(f'replay_off_{n}','eq')
        E(cmp_imm,1,9);bc(f'replay_realtime_{n}','ne')
        E(lsrs_imm,2,0,24);E(cmp_imm,2,0);bc(skip,'ne')
        E(lsrs_imm,2,0,8);E(movs_imm,1,0xF0);E(ands_reg,2,1);E(cmp_imm,2,0x90);bc(copy,'eq');E(b_w,skip)
        a.label(f'replay_off_{n}');E(lsrs_imm,2,0,8);E(movs_imm,1,0xF0);E(ands_reg,2,1);E(cmp_imm,2,0x80);bc(copy,'eq');E(b_w,skip)
        a.label(f'replay_realtime_{n}');E(cmp_imm,1,15);bc(skip,'ne')
        E(lsrs_imm,2,0,8);E(movs_imm,1,255);E(ands_reg,2,1);E(cmp_imm,2,0xFC);bc(skip,'ne')
        a.label(copy);E(adds_reg,2,6,3);E(str_imm,0,2);E(adds_imm8,3,4)
        a.label(skip)
    imm(0,entry);E(ldr_imm,0,0);E(ldr_imm,0,0,0x14);E(ldr_imm,0,0,8);E(strh_imm,3,0)
    # Freeze new musical production after an unconfirmed transfer. Existing
    # FIFO order and Stop debt stay intact;do not add a duplicate Stop.
    imm(0,entry);E(ldrb_imm,1,0,core.FLAGS);E(movs_imm,2,core.FAULT);E(orrs_reg,1,2);E(strb_imm,1,0,core.FLAGS)
    imm(0,seq.SEQ_STATE_ADDR);E(movs_imm,1,1);E(strb_w,1,0,seq.OFF_MIDI_TX_FAULT)
    a.label('replay_no_job');imm(5,USB_BASE);E(ldr_imm,6,4,CTRL);E(ldr_w,6,6,0x298)
    E(movs_imm,0,0)
    for off in (0x64,0x68,0x6C,0x70):E(str_w,0,6,off)
    E(ldr_imm,6,4,EP);E(strb_imm,0,6,0xC);E(ldr_imm,1,6,0x20);E(cmp_imm,1,0);bc('replay_no_timer','eq')
    E(strb_imm,0,1,8);E(ldr_imm,2,1);E(str_imm,2,1,4)
    a.label('replay_no_timer')
    mask();E(ldr_imm,0,4,GEN);E(cmp_reg,0,7);bc('service_unlock_wait','ne')
    for reg,save in ((DAINTMSK,DAINT),(DEACHMSK,DEACH)):
        E(ldr_w,0,5,reg);E(movs_imm,1,2);E(bics_reg,0,1);E(ldr_imm,2,4,save);E(orrs_reg,0,2);E(str_w,0,5,reg)
    E(movs_imm,0,1);E(strb_imm,0,6,0x1C);E(movs_imm,0,0);E(str_imm,0,4,JOB);E(str_imm,0,4,LENGTH);E(str_imm,0,4,PHASE);dsb();restore()
    E(b_w,'service_return')
    a.label('service_unlock_wait');restore()
    a.label('service_return');E(pop,[3,4,5,6,7],pc=True)
    a.label('service_init_bad');E(movs_imm,0,BROKEN);E(str_imm,0,4,PHASE);restore();E(b_w,'service_return')

    # Native USBRST does not call the class deinit callback. Freeze before
    # its global FIFO flush or any coalesced XFRC can consume the journal.
    a.label('tg_irq');E(push,[3,4,5,6,7],lr=True);E(mov_reg,7,0)
    E(bl,'tg_endpoint');E(cmp_imm,0,0);bc('irq_foreign','eq');E(mov_reg,6,0)
    E(ldr_imm,5,6,0x10);E(ldr_w,0,5,0x298);E(cmp_reg,0,7);bc('irq_foreign','ne')
    imm(4,STATE_BASE);mask();E(ldr_imm,0,4,IRQ_ACTIVE);E(cmp_imm,0,0);bc('irq_nested','ne')
    E(movs_imm,0,1);E(str_imm,0,4,IRQ_ACTIVE);restore()
    E(ldr_imm,0,7);imm(1,USB_BASE);E(cmp_reg,0,1);bc('irq_run','ne')
    E(ldr_w,0,0,0x14);E(ldr_imm,1,7);E(ldr_w,1,1,0x18);E(ands_reg,0,1)
    imm(1,1<<12);E(tst_reg,0,1);bc('irq_snapshot','eq')
    E(mov_reg,0,7);E(bl,'tg_reset_dispatch')
    a.label('irq_snapshot');E(ldr_imm,0,4,GEN);E(str_imm,0,4,IRQ_GEN)
    a.label('irq_run');E(mov_reg,0,7);E(bl,'tg_native_irq');E(mov_reg,5,0)
    mask();E(movs_imm,0,0);E(str_imm,0,4,IRQ_ACTIVE);restore();E(mov_reg,0,5);E(pop,[3,4,5,6,7],pc=True)
    a.label('irq_nested');restore();E(movs_imm,0,1);E(pop,[3,4,5,6,7],pc=True)
    a.label('irq_foreign');E(mov_reg,0,7);E(pop,[3,4,5,6,7],lr=True);E(b_w,'tg_native_irq')
    a.label('tg_native_irq');E(raw,IRQ_BYTES);E(b_w,IRQ_SITE+4)

    # Defer the entire native class list so the MIDI RX flush stays before
    # following MSC constructors/receives. Preserve stock constructor order.
    a.label('tg_init');E(push,[3,4,5,6,7],lr=True);E(mov_reg,4,0);E(mov_reg,5,1);E(mov_reg,6,2)
    E(bl,'tg_endpoint');E(cmp_imm,0,0);bc('init_foreign','eq');E(mov_reg,7,0)
    E(ldr_imm,1,0,0x10);E(cmp_reg,1,5);bc('init_foreign','ne')
    E(ldr_imm,1,4,8);E(cmp_imm,1,0);bc('init_foreign','eq')
    E(ldr_imm,1,1,4);E(ldr_imm,1,1);E(cmp_reg,1,7);bc('init_foreign','ne')
    imm(0,STATE_BASE);E(ldr_imm,1,0,GEN);E(str_sp,1,0)
    imm(0,STATE_BASE);E(ldr_imm,1,0,PHASE);E(cmp_imm,1,BROKEN);bc('init_bad','eq')
    E(ldr_imm,2,0,JOB);E(orrs_reg,1,2);E(ldr_imm,2,0,INIT_BUSY);E(orrs_reg,1,2);E(cmp_imm,1,0);bc('init_foreign','eq')
    E(ldr_imm,1,0,PHASE);E(cmp_imm,1,0);bc('init_request','eq')
    E(ldr_imm,1,0,INIT_BUSY);E(cmp_imm,1,0);bc('init_queue','eq')
    a.label('init_request');E(mov_reg,0,7);E(mov_reg,1,5);E(bl,'tg_request')
    E(ldr_sp,1,0);E(adds_imm8,1,1);E(str_sp,1,0)
    a.label('init_queue');imm(0,STATE_BASE);mask();E(ldr_imm,1,0,GEN);E(ldr_sp,2,0);E(cmp_reg,1,2);bc('init_stale','ne')
    E(ldr_imm,1,0,PHASE);E(cmp_imm,1,BROKEN);bc('init_stale','eq')
    E(str_imm,6,0,INIT_CONFIG);E(str_imm,4,0,INIT_CLASS)
    a.label('init_stale');restore()
    E(movs_imm,0,0);E(pop,[3,4,5,6,7],pc=True)
    a.label('init_bad');E(movs_imm,0,2);E(pop,[3,4,5,6,7],pc=True)
    a.label('init_foreign');E(mov_reg,0,4);E(mov_reg,1,5);E(mov_reg,2,6);E(pop,[3,4,5,6,7],lr=True);E(b_w,'tg_native_init')
    a.label('tg_native_init');E(raw,INIT_BYTES);E(b_w,INIT_SITE+4)

    # USBRST can arrive after IRQ entry. The real reset branch must freeze it
    # too;IRQ_ACTIVE bit1 prevents counting the same reset twice.
    a.label('tg_reset_branch');E(push,[0,1,2,3,4],lr=True);E(raw,bytes.fromhex('eff30084'))
    E(mov_reg,0,7);E(bl,'tg_reset_dispatch');E(raw,bytes.fromhex('84f3008c'));E(pop,[0,1,2,3,4],lr=True)
    E(raw,RESET_BYTES);E(b_w,RESET_SITE+4)
    a.label('tg_reset_dispatch');E(push,[3,4,5,6,7],lr=True);E(mov_reg,7,0)
    E(bl,'tg_endpoint');E(cmp_imm,0,0);bc('reset_return','eq');E(mov_reg,6,0)
    E(ldr_imm,5,6,0x10);E(ldr_w,0,5,0x298);E(cmp_reg,0,7);bc('reset_return','ne')
    imm(4,STATE_BASE);E(ldr_imm,0,4,IRQ_ACTIVE);E(movs_imm,1,2);E(tst_reg,0,1);bc('reset_return','ne')
    E(mov_reg,0,6);E(mov_reg,1,5);E(bl,'tg_request')
    mask();E(movs_imm,0,1);E(str_imm,0,4,WAIT_CONFIG);E(movs_imm,0,0);E(str_imm,0,4,INIT_CLASS);E(str_imm,0,4,INIT_CONFIG)
    E(ldr_imm,0,4,IRQ_ACTIVE);E(cmp_imm,0,0);bc('reset_snapshot','eq')
    E(movs_imm,0,3);E(str_imm,0,4,IRQ_ACTIVE)
    a.label('reset_snapshot');E(ldr_imm,0,4,GEN);E(str_imm,0,4,IRQ_GEN);restore()
    a.label('reset_return');E(pop,[3,4,5,6,7],pc=True)
    code,labels=a.assemble();code+=b'\x00\xbf'*(-len(code)%4//2)
    assert CODE_BASE+len(code)<=0x08080000
    return code,labels
