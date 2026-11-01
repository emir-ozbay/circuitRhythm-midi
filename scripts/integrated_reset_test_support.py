"""Real68A2C parent/297C0 reset path with a bounded full-RX-ring binding.

No reset/recovery overlay. Native29AB0/269AC sees no RX ring capacity,so it
takes its native semaphore path instead of requiring an actual USB receive.
"""
import struct
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_PC,UC_ARM_REG_PRIMASK
from thumb_asm import Asm,b_w,bl,pop,push,raw,str_imm


class IntegratedResetFixture:
    PARENT=0x08068A2C
    def __init__(self,h,out):
        self.h,self.out=h,out;self.events=[]
        # Controlled drivers also need the reset slot used by native401AC.
        for driver in out.drivers:
            if h.read(driver)==0x20001F00:h.word(0x20001F00+0x10,0x0800EB0D)
        self.port,self.ports,self.fifo,self.buffer=0x20006000,0x20006040,0x20006100,0x20006200
        h.word(0x20006DC0+4,self.ports);h.word(self.ports,self.port)
        h.u.mem_write(self.port+2,struct.pack('<H',64));h.word(self.port+0x18,self.fifo)
        h.u.mem_write(self.port+0x1C,b'\x01\x01')
        h.u.mem_write(self.fifo,struct.pack('<I4H',self.buffer,67,0,66,64)) # full ring,free0
        h.u.mem_write(self.buffer,b'\xA5'*67)
        for name,pc in (('parent',self.PARENT),('router_clear',0x080297C0),('port_clear',0x080401AC),('rx_rearm',0x08029AB0)):
            h.u.hook_add(UC_HOOK_CODE,lambda u,p,n,d,name=name:self.events.append(name),begin=pc,end=pc)
        h.u.ctl_remove_cache(0x08010000,0x08080000)
    def parent(self):return self.h.call(self.PARENT)
    def snapshot(self):
        h=self.h
        return dict(ports=[bytes(h.u.mem_read(p,24)) for p in self.out.ports],
                    queues=[bytes(h.u.mem_read(h.read(p+4),12)) for p in self.out.ports],
                    pending=[self.out.pending(n) for n in range(3)])
    def check_rx(self):self.h.assertEqual(self.h.u.mem_read(self.buffer,67),b'\xA5'*67)
    def inject_once(self,pc,calls):
        h=self.h;address,results=0x08071000,0x20005200
        a=Asm(address);a.emit(push,list(range(13)),lr=True);a.emit(raw,bytes.fromhex('eff30084'));a.emit(push,[4,5])
        for n,(target,args) in enumerate(calls):
            for r,v in enumerate(args):a.imm32(r,v)
            a.emit(bl,target);a.imm32(3,results+n*4);a.emit(str_imm,0,3)
        a.emit(pop,[4,5]);a.emit(raw,bytes.fromhex('84f3008c'));a.emit(pop,list(range(13)),lr=True);a.emit(b_w,pc)
        code,_=a.assemble();assert len(code)<=256 and 0x0806A570<=address<address+len(code)<=0x08080000
        assert bytes(h.u.mem_read(address,256))==b'\xFF'*256
        h.u.mem_write(address,code);injected=[]
        def enter(u,p,n,d):
            if injected:return
            h.assertEqual(u.reg_read(UC_ARM_REG_PRIMASK),0);injected.append(p);u.reg_write(UC_ARM_REG_PC,address|1)
        h.u.hook_add(UC_HOOK_CODE,enter,begin=pc,end=pc);h.u.ctl_remove_cache(0x08010000,0x08080000)
        return injected,lambda:[h.read(results+n*4) for n in range(len(calls))]
