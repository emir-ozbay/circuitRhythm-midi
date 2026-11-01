import sys,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'src'),str(ROOT/'tests')]
from patch_firmware import unpack_syx
from recovery_timer_test_support import boot_timer_session
from recovery_uart_test_support import NativeUARTPeer
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import *

out=ROOT/'logs/recovery-load-short-read-20261031/explore-native-v2'
out.mkdir(exist_ok=False)
before={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ('src','scripts','tests','build','stock') for p in (ROOT/folder).glob('*') if p.is_file()}
(out/'before.json').write_text(json.dumps(before,indent=2))
image=unpack_syx((ROOT/'build/circuitrhythm-5706-phase1-recovery.syx').read_bytes(),allow_extended=True)['image']
s,timer=boot_timer_session(image,sample_status=[0]*8192,compare_credits=6000,
    record_status=[0xFFFFFF]*4000,adc_scan=(1500,3700,2048),adc_frame_credits=256);h=s.h
uart=NativeUARTPeer(s,txe_credits=10000)
events=[];shorten=False;clipped=[]
def watch(u,pc,size,_):
    row=dict(pc=hex(pc),task=h.task_by_tcb[h.running_tcb]['name'],regs=[u.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)],lr=hex(u.reg_read(UC_ARM_REG_LR)))
    events.append(row)
    print(row,flush=True)
for pc in (0x08037BD6,0x08037ED0,0x080381C8,0x080381D6,0x08037DD0,0x08037E3C,0x0804113A,0x080411D8,0x08041906,0x0802AEAA,0x08047304,0x0802B064,0x080411C0,0x0802AE32,0x080472A8):h.u.hook_add(UC_HOOK_CODE,watch,begin=pc,end=pc)
def clip(u,pc,size,_):
    if shorten and u.reg_read(UC_ARM_REG_R1)==s.raw:
        assert u.reg_read(UC_ARM_REG_R2)==0x29484 and not clipped
        clipped.append(dict(pc=hex(pc),before=0x29484,after=741))
        u.reg_write(UC_ARM_REG_R2,741)
h.u.hook_add(UC_HOOK_CODE,clip,begin=0x080411BE,end=0x080411BE)
def cycle():
    uart.service();timer.deliver(1);s.cycle(budget=2000000);uart.service()
try:
    print('BOOT',s.snapshot(),flush=True)
    s._invoke(0x08037ED0,(s.project,1,0,0),label='native_Save_slot1',budget=2000000)
    for i in range(2000):
        cycle()
        if i%32==0:print('CYCLE',i,s.snapshot()['phase'],s.snapshot()['project_flags'],flush=True)
        if not s.snapshot()['phase']:break
    print('SAVED',s.snapshot(),flush=True)
    assert s.snapshot()['phase']==0
    s.shortcut();s.input('pad_down',0);s.input('pad_up',0);s.shortcut()
    before_load=bytes(h.u.mem_read(s.raw,0x29484));print('BEFORE',before_load[0x2e4:0x2ec].hex(),flush=True)
    shorten=True
    s._invoke(0x08037B8C,(s.project,1,0,0),label='native_Load_slot1',budget=2000000)
    for i in range(64):cycle()
    print('LOADED',s.snapshot(),clipped,flush=True)
    print('AFTER',bytes(h.u.mem_read(s.raw+0x2e4,8)).hex(),flush=True)
    print('SHORTCUT',s.shortcut(),flush=True)
    (out/'explore-medium.bin').write_bytes(bytes(h.medium.data))
    (out/'explore-raw.bin').write_bytes(bytes(h.u.mem_read(s.raw,0x29484)))
finally:
    (out/'explore-events.json').write_text(json.dumps(events,indent=2))
    (out/'explore-state.json').write_text(json.dumps(dict(snapshot=s.snapshot(),io=s.io,trace=list(h.trace)),indent=2))
