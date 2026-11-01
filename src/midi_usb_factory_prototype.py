"""EMULATION ONLY: defer stock USB class factory until all old readers retire.

Native factory/root/descriptor/stop/start and init prefix execute. HAL init,
tick/NVIC/clock timing and inherited RTOS edges are synthetic test boundaries.
"""
import midi_usb_storage_prototype as storage
import midi_usb_msc_prototype as msc
import midi_usb_control_prototype as control
import midi_usb_composite_prototype as composite
import midi_usb_session_prototype as session
from thumb_asm import (Asm,adds_imm8,b,b_cond_w,b_w,bl,bx_lr,cmp_imm,cmp_reg,
                       ldr_imm,ldr_w,ldr_sp,ldrb_w,mov_reg,movs_imm,pop,push,raw,str_imm)

CODE_BASE,STATE_BASE,STATE_SIZE=0x0807BA00,0x20048220,128
MAGIC=0x31584655
ROOT,CONTROLLER,DESIRED,APPLIED,GENERATION,PENDING,RUNNING,BUSY,ERRORS,SWITCHES=4,8,12,16,20,24,28,32,36,40
GATES={0x080432A8:bytes.fromhex('31b5144d'),0x08040B7E:msc.GATES[0x08040B7E]}


def variants():
    options=dict(class_policy=CODE_BASE,config_ready=CODE_BASE+4)
    return storage.msc_variant(**options),storage.arm_code(msc_options=options)


def arm_code(base=CODE_BASE,state=STATE_BASE):
    (mc_code,mc),(sd_code,sd)=variants(); _,cc=control.arm_code()
    if base!=CODE_BASE or state%4 or not 0x20048204<=state<state+STATE_SIZE<=0x20048300:
        raise ValueError('Factory state/code binding out of bounds')
    if storage.CODE_BASE+len(sd_code)>base:raise ValueError('Factory overlaps storage code')
    a=Asm(base);E=a.emit
    def imm(r,v):a.imm32(r,v)
    def bc(l,c):E(b_cond_w,l,c)
    def field(o,r=0):E(ldr_imm,r,4,o)
    def put(o,r=0):E(str_imm,r,4,o)
    def mask():E(raw,bytes.fromhex('eff3108372b6'))
    def restore():E(raw,bytes.fromhex('83f31088'))
    a.label('fx_class_policy');E(b_w,'class_body')
    a.label('fx_config_ready');E(b_w,'ready_body')
    a.label('class_body');E(push,[3,4,5],lr=True);imm(4,state)
    field(0);imm(1,MAGIC);E(cmp_reg,0,1);bc('class_no','ne')
    field(ROOT,5);imm(1,0x20006F20);E(ldr_imm,0,1);E(cmp_reg,0,5);bc('class_no','ne')
    E(ldr_imm,0,5,4);field(CONTROLLER,1);E(cmp_reg,0,1);bc('class_no','ne')
    imm(1,composite.STATE_BASE)
    E(ldr_imm,0,5,8);E(ldr_imm,2,1,composite.MIDI);E(cmp_reg,0,2);bc('class_no','ne')
    E(ldr_imm,0,5,16);E(cmp_imm,0,0);bc('class_no','ne')
    E(ldrb_w,0,5,0);E(cmp_imm,0,1);bc('class_pair','ne')
    E(ldr_imm,0,5,12);E(cmp_imm,0,0);bc('class_no','ne');E(b,'class_ok')
    a.label('class_pair');E(cmp_imm,0,2);bc('class_no','ne')
    E(ldr_imm,0,5,12);E(ldr_imm,2,1,composite.MSC);E(cmp_reg,0,2);bc('class_no','ne')
    a.label('class_ok');E(movs_imm,0,1);E(pop,[3,4,5],pc=True)
    a.label('class_no');E(movs_imm,0,0);E(pop,[3,4,5],pc=True)
    a.label('ready_body');E(push,[3,4,5],lr=True);E(bl,'class_body');E(cmp_imm,0,1);bc('class_no','ne')
    imm(4,state);field(ROOT,5);E(ldrb_w,0,5,0);imm(5,msc.STATE_BASE)
    E(cmp_imm,0,1);bc('ready_pair','ne')
    E(ldr_imm,0,5,msc.PHASE);E(cmp_imm,0,msc.SEALED);bc('class_no','ne')
    E(ldr_imm,0,5,msc.RX_ACTIVE);E(cmp_imm,0,0);bc('class_no','ne');E(b,'class_ok')
    a.label('ready_pair');E(ldr_imm,0,5,msc.PHASE);E(cmp_imm,0,msc.OPEN);bc('class_no','ne');E(b,'class_ok')

    # The stock ABI consumes only the low two bytes. The boot-derived caller
    #2CB18 leaves the upper stack halfword unspecified, so canonicalize it.
    a.label('fx_request');E(push,[3,4,5,6,7],lr=True);E(raw,bytes.fromhex('80b2'));E(mov_reg,6,0);imm(4,state)
    field(0);imm(1,MAGIC);E(cmp_reg,0,1);bc('request_no','ne')
    E(bl,'fx_binding');E(cmp_imm,0,1);bc('request_no','ne')
    E(cmp_imm,6,1);bc('request_ok_arg','eq')
    for value in (0x101,0x201,0x301):imm(1,value);E(cmp_reg,6,1);bc('request_ok_arg','eq')
    E(b,'request_no')
    a.label('request_ok_arg');mask();field(GENERATION);imm(1,0xFFFFFFFF);E(cmp_reg,0,1);bc('request_wrap','eq')
    E(adds_imm8,0,1);put(GENERATION);put(DESIRED,6);E(movs_imm,0,1);put(PENDING);restore()
    field(ROOT);field(CONTROLLER,1);E(movs_imm,2,0);E(bl,mc['mc_deinit_list'])
    E(movs_imm,0,0);E(pop,[3,4,5,6,7],pc=True)
    a.label('request_wrap');restore();E(movs_imm,0,1);put(ERRORS)
    a.label('request_no');E(movs_imm,0,1);E(pop,[3,4,5,6,7],pc=True)

    # Empty-list deinit inside40A30 is not a new host request. Old-list deinit
    # has already executed through mc_service before native factory is allowed.
    a.label('fx_deinit');E(push,[0,1,2,3,4,5,6],lr=True);imm(4,state)
    field(RUNNING);E(cmp_imm,0,1);bc('deinit_normal','ne')
    E(raw,bytes.fromhex('eff30583'));E(cmp_imm,3,0);bc('deinit_normal','ne')
    E(ldr_sp,3,28);imm(5,0x08040B51);E(cmp_reg,3,5);bc('deinit_normal','ne')
    E(ldr_sp,0,0)
    field(ROOT,3);E(cmp_reg,0,3);bc('deinit_normal','ne')
    field(CONTROLLER,3);E(cmp_reg,1,3);bc('deinit_normal','ne')
    E(pop,[0,1,2,3,4,5,6],lr=True);E(b_w,mc['mc_native_deinit'])
    a.label('deinit_normal');E(pop,[0,1,2,3,4,5,6],lr=True);E(b_w,mc['mc_deinit_list'])

    a.label('fx_service');E(push,[3,4,5,6,7],lr=True)
    E(raw,bytes.fromhex('eff31080'));E(cmp_imm,0,0);bc('service_no','ne')
    E(raw,bytes.fromhex('eff30580'));E(cmp_imm,0,0);bc('service_no','ne')
    imm(4,state);field(0);imm(1,MAGIC);E(cmp_reg,0,1);bc('service_no','ne')
    E(bl,'fx_binding');E(cmp_imm,0,1);bc('service_no','ne')
    field(BUSY);E(cmp_imm,0,0);bc('service_no','ne')
    E(movs_imm,0,1);put(BUSY);E(bl,mc['mc_service']);E(cmp_imm,0,0);bc('service_wait','ne')
    field(PENDING);E(cmp_imm,0,1);bc('service_done','ne')
    imm(5,msc.STATE_BASE);E(ldr_imm,0,5,msc.PHASE);E(cmp_imm,0,msc.SEALED);bc('service_wait','ne')
    imm(1,session.STATE_BASE);E(ldr_imm,0,1,session.PHASE);E(cmp_imm,0,session.SEALED);bc('service_wait','ne')
    field(GENERATION,7);field(DESIRED,6)
    E(movs_imm,0,1);put(RUNNING);E(str_imm,0,5,msc.NATIVE_TEAR)
    E(mov_reg,0,6);E(bl,'fx_native_factory')
    E(mov_reg,3,0);E(movs_imm,0,0);put(RUNNING);E(str_imm,0,5,msc.NATIVE_TEAR)
    E(cmp_imm,3,0);bc('service_bad','ne')
    put(APPLIED,6);field(SWITCHES);E(adds_imm8,0,1);put(SWITCHES)
    mask();field(GENERATION);E(cmp_reg,0,7);bc('service_race','ne')
    E(movs_imm,0,0);put(PENDING);restore()
    a.label('service_done');imm(1,control.STATE_BASE);E(ldr_imm,0,1,control.FLAGS)
    E(cmp_imm,0,0);bc('service_wait','ne')
    E(movs_imm,0,0);put(BUSY);E(pop,[3,4,5,6,7],pc=True)
    a.label('service_race');restore();E(b,'service_wait')
    a.label('service_bad');E(movs_imm,0,1);put(ERRORS)
    a.label('service_wait');E(movs_imm,0,0);put(BUSY)
    a.label('service_no');E(movs_imm,0,1);E(pop,[3,4,5,6,7],pc=True)
    a.label('fx_binding');field(ROOT);imm(1,0x200000D0);E(cmp_reg,0,1);bc('binding_no','ne')
    imm(1,0x20006F20);E(ldr_imm,1,1);E(cmp_reg,0,1);bc('binding_no','ne')
    E(ldr_imm,0,0,4);field(CONTROLLER,1);E(cmp_reg,0,1);bc('binding_no','ne')
    E(ldr_w,0,0,0x298);imm(1,0x200054B4);E(cmp_reg,0,1);bc('binding_no','ne')
    E(movs_imm,0,1);E(bx_lr)
    a.label('binding_no');E(movs_imm,0,0);E(bx_lr)
    a.label('fx_native_factory')
    # Relocate the pinned LDR r5,[pc,#50] while preserving pushed arg ABI.
    E(push,[0,4,5],lr=True);imm(5,0x200000D0);E(b_w,0x080432AC)
    code,labels=a.assemble();code+=b'\x00\xbf'*(-len(code)%4//2)
    if base+len(code)>0x08080000:raise ValueError('Factory code exceeds application flash')
    return code,labels
