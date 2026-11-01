"""EMULATION ONLY: service the prototypes from the native main-loop USB slot.

The existing output/input span stays native. One SysEx retry and one power
service precede at most one MSC poll. Native READ may still yield to a modeled
RTOS worker; nested or IRQ service never tears down that in-progress reader.
"""
import midi_usb_power_prototype as power
import midi_usb_factory_prototype as factory
import midi_usb_msc_prototype as msc
import midi_usb_storage_prototype as storage
import midi_usb_control_prototype as control
import midi_usb_irq_prototype as irq
import midi_sysex_retry_prototype as retry
from thumb_asm import (Asm,adds_imm8,b,b_cond_w,bl,bx_lr,cmp_imm,cmp_reg,ldr_imm,
                       ldrb_imm,mov_reg,movs_imm,pop,push,raw,str_imm)

CODE_BASE,STATE_BASE,STATE_SIZE=0x0807C800,0x20048420,64
MAGIC=0x314B5354
ROUTER,BUSY,FRAMES,REJECTS,LAST_POWER,LAST_POLL,ERRORS=4,8,12,16,20,24,28
MAIN_ENTRY,MAIN_CALL,MAIN_END=0x08025870,0x0802587C,0x08025880
GATES={MAIN_CALL:bytes.fromhex('01f0d2fe')}


def arm_code(base=CODE_BASE,state=STATE_BASE):
    pc,pw=power.arm_code();_,sr=retry.arm_code(notifications=True,reservations=True)
    if base!=CODE_BASE or state%4 or not power.STATE_BASE+power.STATE_SIZE<state<state+STATE_SIZE<=0x20048500:
        raise ValueError('Task code/state exceeds registered bounds')
    if power.CODE_BASE+len(pc)>base:raise ValueError('Task overlaps power code')
    a=Asm(base);E=a.emit
    def imm(r,v):a.imm32(r,v)
    def bc(l,c):E(b_cond_w,l,c)
    def field(o,r=0):E(ldr_imm,r,4,o)
    def put(o,r=0):E(str_imm,r,4,o)
    a.label('ut_main');E(push,[3,4,5],lr=True)
    E(raw,bytes.fromhex('eff31080'));E(cmp_imm,0,0);bc('main_no','ne')
    E(raw,bytes.fromhex('eff30580'));E(cmp_imm,0,0);bc('main_no','ne')
    imm(4,state);field(0);imm(1,MAGIC);E(cmp_reg,0,1);bc('main_no','ne')
    field(BUSY);E(cmp_imm,0,0);bc('main_busy','ne')
    # No native worker/drain/class/IRQ ownership may be released recursively.
    for st,offsets in ((storage.STATE_BASE,(storage.IO_BUSY,storage.SCSI_BUSY,storage.IRQ_ACTIVE)),
                       (msc.STATE_BASE,(msc.TASK_BUSY,msc.ARM_BUSY,msc.IRQ_ACTIVE,msc.BUSY)),
                       (control.STATE_BASE,(control.IRQ_DEPTH,control.INIT_BUSY,control.BUSY)),
                       (power.STATE_BASE,(power.IRQ_DEPTH,power.BUSY)),
                       (factory.STATE_BASE,(factory.RUNNING,factory.BUSY)),(irq.STATE_BASE,(irq.ACTIVE,))):
        imm(1,st)
        for o in offsets:E(ldr_imm,0,1,o);E(cmp_imm,0,0);bc('main_busy','ne')
    field(ROUTER,5);imm(1,0x20006F04);E(ldr_imm,0,1);E(cmp_reg,0,5);bc('main_bad','ne')
    imm(1,retry.STATE_BASE);E(ldr_imm,0,1,retry.ROUTER);E(cmp_reg,0,5);bc('main_bad','ne')
    E(movs_imm,0,1);put(BUSY);field(FRAMES);E(adds_imm8,0,1);put(FRAMES)
    E(mov_reg,0,5);E(bl,sr['sr_service'])
    E(bl,pw['pw_service']);put(LAST_POWER)
    imm(1,power.STATE_BASE);E(ldr_imm,0,1,power.ASLEEP);E(cmp_imm,0,0);bc('main_skipped','ne')
    imm(1,msc.STATE_BASE);E(ldr_imm,0,1,msc.PHASE);E(cmp_imm,0,msc.OPEN);bc('main_skipped','ne')
    E(ldr_imm,0,1,msc.OP);E(cmp_imm,0,0);bc('main_skipped','ne')
    # This entry still passes through the existing storage/MSC ownership gates.
    E(bl,0x08027624);put(LAST_POLL);E(b,'main_done')
    a.label('main_skipped');E(movs_imm,0,1);put(LAST_POLL)
    a.label('main_done');E(movs_imm,0,0);put(BUSY);E(pop,[3,4,5],pc=True)
    a.label('main_bad');E(movs_imm,0,1);put(ERRORS);E(b,'main_no')
    a.label('main_busy');field(REJECTS);E(adds_imm8,0,1);put(REJECTS)
    a.label('main_no');E(movs_imm,0,1);E(pop,[3,4,5],pc=True)
    code,labels=a.assemble();code+=b'\x00\xbf'*(-len(code)%4//2)
    if base+len(code)>0x08080000:raise ValueError('Task code exceeds application flash')
    return code,labels
