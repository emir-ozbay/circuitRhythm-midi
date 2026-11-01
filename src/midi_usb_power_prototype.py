"""EMULATION ONLY: finish old readers before USB suspend clock-stop.

WKUP/reset wins over coalesced suspend. Native state save/restore and clock
ungate execute; clock-stop is generation-checked in a short atomic section.
CPU-FIFO, normal suspend only. No deep-system-sleep/LPM/silicon timing proof.
"""
import midi_usb_factory_prototype as factory
import midi_usb_storage_prototype as storage
import midi_usb_msc_prototype as msc
import midi_usb_control_prototype as control
import midi_usb_irq_prototype as irq
import midi_usb_session_prototype as session
import midi_usb_lifecycle_prototype as life
from thumb_asm import (Asm,adds_imm8,ands_reg,b,b_cond_w,b_w,bl,bx_lr,cmp_imm,cmp_reg,
                       ldr_imm,ldr_w,ldrb_w,mov_reg,movs_imm,orrs_reg,pop,push,raw,str_imm,str_w,tst_reg)

CODE_BASE,STATE_BASE,STATE_SIZE=0x0807C000,0x20048320,96
MAGIC=0x31575055
HANDLE,CONTROLLER,DESIRED,GENERATION,BUSY,ASLEEP,SAVED_CONFIG,PENDING=4,8,12,16,20,24,28,32
ERRORS,SUSPENDS,WAKES,IRQ_DEPTH,RESUME_STAGE,CAUSES=36,40,44,48,52,56
ALLOW_RESUME=60
SAVED_GINT=64
AWAKE,SLEEP=0,1
SUSPEND,WAKE,RESET=1<<11,1<<31,1<<12
POWER_GINT=control.CONTROL_GINT|SUSPEND|WAKE
GATES={0x0804293E:irq.IRQ_PROLOGUE,0x0802C7E6:bytes.fromhex('10b50446'),
       0x0802C802:bytes.fromhex('d0f80004')}


def irq_variant():return irq.arm_code(allowed_gint=POWER_GINT,max_phase=session.SEALED)


def arm_code(base=CODE_BASE,state=STATE_BASE):
    fc,fx=factory.arm_code();(_,mc),(_,sd)=factory.variants();_,cc=control.arm_code()
    if base!=CODE_BASE or state%4 or not factory.STATE_BASE+factory.STATE_SIZE<state<state+STATE_SIZE<=0x20048400:
        raise ValueError('Power code/state binding outside registered bounds')
    if factory.CODE_BASE+len(fc)>base:raise ValueError('Power overlaps factory code')
    a=Asm(base);E=a.emit
    def imm(r,v):a.imm32(r,v)
    def bc(l,c):E(b_cond_w,l,c)
    def field(o,r=0):E(ldr_imm,r,4,o)
    def put(o,r=0):E(str_imm,r,4,o)
    def mask():E(raw,bytes.fromhex('eff3108372b6'))
    def restore():E(raw,bytes.fromhex('83f31088'))
    def changed(l):field(GENERATION);E(cmp_reg,0,7);bc(l,'ne')
    def bad():
        E(movs_imm,0,1);put(ERRORS)
        imm(1,session.STATE_BASE);E(movs_imm,0,session.BROKEN);E(str_imm,0,1,session.PHASE)
        imm(1,msc.STATE_BASE);E(str_imm,0,1,msc.PHASE)
        imm(1,life.STATE_BASE);E(movs_imm,0,life.FROZEN);E(str_imm,0,1,life.PHASE)

    a.label('pw_request');E(push,[3,4,5],lr=True);E(mov_reg,5,0);imm(4,state)
    E(bl,'pw_binding');E(cmp_imm,0,1);bc('request_no','ne')
    E(cmp_imm,5,1);bc('request_no','hi')
    mask();field(PENDING);E(cmp_imm,0,1);bc('request_same','eq')
    field(ASLEEP);E(cmp_imm,0,1);bc('request_same','eq')
    E(cmp_imm,5,AWAKE);bc('request_duplicate','eq');E(b,'request_new')
    a.label('request_same');field(DESIRED);E(cmp_reg,0,5);bc('request_duplicate','eq')
    a.label('request_new');field(GENERATION);imm(1,0xFFFFFFFF);E(cmp_reg,0,1);bc('request_wrap','eq')
    E(adds_imm8,0,1);put(GENERATION);put(DESIRED,5);E(movs_imm,0,1);put(PENDING)
    E(movs_imm,0,0);put(RESUME_STAGE)
    E(cmp_imm,5,SLEEP);bc('request_wake_count','ne')
    E(movs_imm,0,1);put(ALLOW_RESUME)
    field(SUSPENDS);E(adds_imm8,0,1);put(SUSPENDS);E(b,'request_frozen')
    a.label('request_wake_count');field(WAKES);E(adds_imm8,0,1);put(WAKES)
    a.label('request_frozen');restore();E(movs_imm,0,control.DEINIT_EVENT);E(bl,cc['cc_request'])
    E(pop,[3,4,5],pc=True)
    a.label('request_duplicate');restore();E(movs_imm,0,0);E(pop,[3,4,5],pc=True)
    a.label('request_wrap');restore();bad()
    a.label('request_no');E(movs_imm,0,1);E(pop,[3,4,5],pc=True)

    a.label('pw_wake_event');E(push,[3,4,5],lr=True);imm(4,state)
    E(movs_imm,0,AWAKE);E(bl,'pw_request');E(cmp_imm,0,0);bc('wake_no','ne')
    field(ASLEEP);E(cmp_imm,0,1);bc('wake_ok','ne')
    # This native routine clears PCGCCTL.STOPCLK then restores USB state.
    field(HANDLE);E(movs_imm,1,0);E(bl,0x0802C9F8)
    field(HANDLE);E(ldr_imm,1,0);field(SAVED_GINT);E(str_w,0,1,0x18)
    E(movs_imm,0,0);put(ASLEEP)
    a.label('wake_ok');E(movs_imm,0,0);E(pop,[3,4,5],pc=True)
    a.label('wake_no');E(movs_imm,0,1);E(pop,[3,4,5],pc=True)

    a.label('pw_irq');E(push,[3,4,5,6,7],lr=True);E(mov_reg,6,0);imm(4,state)
    field(HANDLE,1);E(cmp_reg,6,1);bc('irq_foreign','ne')
    E(bl,'pw_binding');E(cmp_imm,0,1);bc('irq_bad','ne')
    field(IRQ_DEPTH);E(cmp_imm,0,0);bc('irq_no','ne')
    E(movs_imm,0,1);put(IRQ_DEPTH)
    E(ldr_imm,5,6);E(ldr_w,0,5,0x14);E(ldr_w,1,5,0x18);E(ands_reg,0,1);put(CAUSES)
    imm(1,RESET);E(tst_reg,0,1);bc('irq_cause_ready','eq')
    E(movs_imm,1,0);put(ALLOW_RESUME,1)
    a.label('irq_cause_ready')
    imm(1,WAKE|RESET);E(tst_reg,0,1);bc('irq_suspend','eq')
    E(bl,'pw_wake_event');E(cmp_imm,0,0);bc('irq_finish','ne');E(b,'irq_native')
    a.label('irq_suspend');field(ASLEEP,1);E(cmp_imm,1,1);bc('irq_sleeping','eq')
    imm(1,SUSPEND);E(tst_reg,0,1);bc('irq_native','eq')
    E(ldr_w,0,5,0x808);E(movs_imm,1,1);E(tst_reg,0,1);bc('irq_native','eq')
    E(movs_imm,0,SLEEP);E(bl,'pw_request');E(cmp_imm,0,0);bc('irq_finish','ne')
    a.label('irq_native');E(mov_reg,0,6);E(bl,sd['sd_irq'])
    E(b,'irq_finish')
    a.label('irq_sleeping');E(movs_imm,0,0)
    a.label('irq_finish');E(cmp_imm,0,0);bc('irq_success','eq');bad();E(movs_imm,0,1)
    a.label('irq_success');E(mov_reg,5,0);E(movs_imm,0,0);put(IRQ_DEPTH);E(mov_reg,0,5);E(pop,[3,4,5,6,7],pc=True)
    a.label('irq_bad');bad()
    a.label('irq_no');E(movs_imm,0,1);E(pop,[3,4,5,6,7],pc=True)
    a.label('irq_foreign');E(mov_reg,0,6);E(pop,[3,4,5,6,7],lr=True);E(b_w,sd['sd_irq'])

    for name,address in (('pw_suspend',0x0802C7E6),('pw_wakeup',0x0802C802)):
        a.label(name);E(push,[3,4,5],lr=True);E(mov_reg,5,0);imm(4,state)
        field(HANDLE,1);E(cmp_reg,5,1);bc(name+'_foreign','ne')
        if name=='pw_suspend':
            field(IRQ_DEPTH);E(cmp_imm,0,1);bc('suspend_request','ne')
            field(CAUSES);imm(1,WAKE|RESET);E(tst_reg,0,1);bc('suspend_ignore','ne')
            a.label('suspend_request');E(movs_imm,0,SLEEP);E(bl,'pw_request');E(pop,[3,4,5],pc=True)
            a.label('suspend_ignore');E(movs_imm,0,0);E(pop,[3,4,5],pc=True)
        else:E(bl,'pw_wake_event');E(pop,[3,4,5],pc=True)
        a.label(name+'_foreign');E(mov_reg,0,5);E(pop,[3,4,5],lr=True)
        a.label(name+'_native');E(raw,GATES[address]);E(b_w,address+4)

    a.label('pw_service');E(push,[3,4,5,6,7],lr=True)
    E(raw,bytes.fromhex('eff31080'));E(cmp_imm,0,0);bc('service_no','ne')
    E(raw,bytes.fromhex('eff30580'));E(cmp_imm,0,0);bc('service_no','ne')
    imm(4,state);E(bl,'pw_binding');E(cmp_imm,0,1);bc('service_no','ne')
    for off in (BUSY,IRQ_DEPTH):field(off);E(cmp_imm,0,0);bc('service_no','ne')
    E(movs_imm,0,1);put(BUSY)
    field(ASLEEP);E(cmp_imm,0,1);bc('service_done','eq')
    field(GENERATION,7);E(bl,fx['fx_service']);E(cmp_imm,0,0);bc('service_wait','ne');changed('service_wait')
    field(PENDING);E(cmp_imm,0,1);bc('service_done','ne')
    field(DESIRED);E(cmp_imm,0,SLEEP);bc('service_awake','ne')
    for st,off in ((msc.STATE_BASE,msc.PHASE),(session.STATE_BASE,session.PHASE)):
        imm(1,st);E(ldr_imm,0,1,off);E(cmp_imm,0,session.SEALED);bc('service_wait','ne')
    field(CONTROLLER,5);E(ldrb_w,0,5,0x274);E(cmp_imm,0,1);bc('service_bad','lo');E(cmp_imm,0,3);bc('service_bad','hi')
    put(SAVED_CONFIG);E(mov_reg,0,5);E(bl,0x0804279E)
    # Save/restore is native; gate the clock only if no wake/reset raced it.
    mask();changed('service_sleep_race')
    field(HANDLE);E(ldr_imm,5,0);E(ldr_w,0,5,0x18);put(SAVED_GINT)
    imm(0,WAKE|RESET);E(str_w,0,5,0x18)
    E(raw,bytes.fromhex('bff34f8f'))
    E(ldr_w,0,5,0xE00);E(movs_imm,1,1);E(orrs_reg,0,1);E(str_w,0,5,0xE00)
    E(movs_imm,0,1);put(ASLEEP);E(movs_imm,0,0);put(PENDING);put(RESUME_STAGE);restore();E(b,'service_done')
    a.label('service_sleep_race');restore();field(ALLOW_RESUME);E(cmp_imm,0,0);bc('service_wait','eq')
    field(CONTROLLER,5);E(ldrb_w,0,5,0x274);E(cmp_imm,0,4);bc('service_wait','ne')
    E(mov_reg,0,5);E(bl,0x080427AE);E(b,'service_wait')
    a.label('service_awake');field(ALLOW_RESUME);E(cmp_imm,0,0);bc('service_commit','eq')
    field(CONTROLLER,5);E(ldrb_w,0,5,0x274)
    E(cmp_imm,0,4);bc('service_bad','hs');E(cmp_imm,0,3);bc('service_commit','ne')
    imm(1,session.STATE_BASE);E(ldr_imm,0,1,session.PHASE);E(cmp_imm,0,session.OPEN);bc('service_ready','eq')
    field(RESUME_STAGE);E(cmp_imm,0,1);bc('service_wait','eq')
    imm(0,0x200000D0);E(mov_reg,1,5);E(movs_imm,2,1);E(bl,mc['mc_init_list']);E(cmp_imm,0,0);bc('service_bad','ne')
    changed('service_wait');E(movs_imm,0,1);put(RESUME_STAGE);E(b,'service_wait')
    a.label('service_ready');E(bl,fx['fx_config_ready']);E(cmp_imm,0,1);bc('service_wait','ne')
    a.label('service_commit');mask();changed('service_commit_race')
    E(movs_imm,0,0);put(PENDING);put(RESUME_STAGE);restore();E(b,'service_done')
    a.label('service_commit_race');restore();E(b,'service_wait')
    a.label('service_bad');bad();E(b,'service_wait')
    a.label('service_done');E(movs_imm,0,0);put(BUSY);E(pop,[3,4,5,6,7],pc=True)
    a.label('service_wait');E(movs_imm,0,0);put(BUSY)
    a.label('service_no');E(movs_imm,0,1);E(pop,[3,4,5,6,7],pc=True)

    a.label('pw_binding');field(0);imm(1,MAGIC);E(cmp_reg,0,1);bc('binding_no','ne')
    field(HANDLE,2);imm(1,0x200054B4);E(cmp_reg,2,1);bc('binding_no','ne')
    E(ldr_imm,0,2);imm(1,0x40040000);E(cmp_reg,0,1);bc('binding_no','ne')
    for off in (16,32):E(ldr_imm,0,2,off);E(cmp_imm,0,0);bc('binding_no','ne')
    E(ldr_w,0,2,0x400);field(CONTROLLER,1);E(cmp_reg,0,1);bc('binding_no','ne')
    E(ldr_w,0,0,0x298);E(cmp_reg,0,2);bc('binding_no','ne')
    imm(0,0x200000D0);E(ldr_imm,0,0,4);E(cmp_reg,0,1);bc('binding_no','ne')
    E(movs_imm,0,1);E(bx_lr)
    a.label('binding_no');E(movs_imm,0,0);E(bx_lr)
    code,labels=a.assemble();code+=b'\x00\xbf'*(-len(code)%4//2)
    if base+len(code)>0x08080000:raise ValueError('Power code exceeds application flash')
    return code,labels
