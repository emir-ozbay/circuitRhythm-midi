"""Native synchronous file FIFO/wait/worker over RAM-only file API and task edge.

No custom filesystem.45EB6/2ACA2/2ACB8/2ACF8/2AD40/FIFOs/semaphores run.
4113A is the lower file-API boundary; actual filesystem/flash and RTOS remain
outside this graph. The earlier allocator/UI/sample-flash models remain.
"""
import hashlib,struct
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_R6,UC_ARM_REG_SP,UC_ARM_REG_PC,UC_ARM_REG_LR
from midi_usb_long_loop_test_support import UsbLongLoopFixture
from thumb_asm import Asm,b_w,bl,ldr_imm,pop,push,raw,str_imm

PINS={
 (0x0802ACA2,62):'765fcc9b99fa4d14141a1a8fa9d832888052e3e95fc69cda2c9aae32cc057833',
 (0x0802ACF8,48):'23c54aa54891df2b56125e0bdfdd7a03e9a5dbe03dd5ca109edf1805f16e0437',
 (0x0802AD40,790):'bd33f3fa3a775d3c7c19fe68444c3dae4429b388bf9e4a486befa8adeb87e459',
 (0x08045EB6,82):'8314bcd7f25d9950f0f3c2f4da02c5b873c8d64ff4684ad1d184fb0d7550624c',
 (0x0802508C,8):'8f9a7f74e98b9db5952e74e180a9c7074629d39db28426485d83352be969876a',
 (0x08025056,24):'bc172b1b6e3da9c2e243f7bb7daa01ca5d2c0e3b9e685f946979874f5048d444',
 (0x0802CA6C,34):'88421ae367567e16ce27d663aa7fe1c9188224d7aa084900d3e594b6e86e9541',
 (0x08023CEA,38):'9010b580be21d4e2aba745a8914face1405c064f0444adf41ef2163a4fe8d89c'}


class UsbFileQueueFixture(UsbLongLoopFixture):
    def __init__(self,h,files=None):
        self.dispatches=0;self.submissions=[];self.dequeued=[];self.results=[];self.waits=0;self.workers=0
        self.faults={};self.active=None;self.credit_events=[]
        super().__init__(h,files)
        for (p,n),digest in PINS.items():assert hashlib.sha256(h.u.mem_read(p,n)).hexdigest()==digest
        assert h.u.mem_read(0x0804113A,4)==bytes.fromhex('2de9fc41')
        # Test-only external RAM keeps the complete live project span intact.
        h.u.mem_map(0x22000000,0x3000)
        self.worker,self.fifo,self.tcb=0x22000020,0x22000100,0x22001000
        h.u.mem_write(0x22000000,b'FBEG');h.u.mem_write(0x22002FFC,b'FEND')
        h.call(0x08040D9C,self.fifo,72,2) # native FIFO constructor/ring allocator
        h.word(self.worker+0x14,self.fifo);h.u.mem_write(self.worker+0x10,b'\x02\x02\x00\x01')
        h.word(0x20006CA8,self.worker)
        assert h.read(0x20006550)==0 # native kernel current-TCB field,synthetic binding
        h.word(0x20006550,self.tcb);h.word(self.tcb+0x50,0)
        # Model a task switch only at the native synchronous wait's yield BL.
        # Native worker drains the actual FIFO and publishes result/credit.
        self.queue_cave=0x08071300
        a=Asm(self.queue_cave);a.emit(push,list(range(13)),lr=True)
        a.emit(raw,bytes.fromhex('eff30084'));a.emit(push,[4,5])
        a.imm32(4,self.tcb+0x50);a.emit(ldr_imm,5,4);a.imm32(0,self.worker);a.emit(str_imm,0,4)
        a.emit(bl,0x0802AD40);a.emit(str_imm,5,4)
        a.emit(pop,[4,5]);a.emit(raw,bytes.fromhex('84f3008c'))
        a.emit(pop,list(range(13)),lr=True);a.emit(b_w,0x0802AD16)
        self.queue_code,_=a.assemble()
        assert self.queue_cave%4==0 and len(self.queue_code)<=256
        assert 0x0806A570<=self.queue_cave<self.queue_cave+len(self.queue_code)<=0x08080000
        assert not any(h.u.mem_read(self.queue_cave,256))
        assert all(self.queue_cave+len(self.queue_code)<=o['address'] or o['address']+len(o['replacement'])<=self.queue_cave for o in h.recovery.overlays)
        h.u.mem_write(self.queue_cave,self.queue_code)
        for p in (0x0802ACB8,0x0802AD12,0x0802AD40,0x0802AD76,0x0804113A,0x0802B00C,0x0802B038):
            h.u.hook_add(UC_HOOK_CODE,self.queue_event,begin=p,end=p)
        h.u.ctl_remove_cache(self.queue_cave,self.queue_cave+256)
        h.ss.flash=bytes(h.u.mem_read(0x08010000,0x70000))

    def boundary(self,u,p,n,d):
        if p==0x08045EB6:
            self.dispatches+=1
            return # execute native dispatcher,not the older immediate-copy hook
        super().boundary(u,p,n,d)

    def queue_event(self,u,p,n,d):
        h=self.h
        if p==0x0802ACB8:
            h.assertEqual(u.reg_read(UC_ARM_REG_R0),self.worker)
            source=u.reg_read(UC_ARM_REG_R1);packet=bytes(u.mem_read(source,72))
            h.assertEqual(packet[0],6);self.submissions.append(packet)
        elif p==0x0802AD12:
            self.waits+=1;u.reg_write(UC_ARM_REG_PC,self.queue_cave|1)
        elif p==0x0802AD40:
            h.assertEqual(u.reg_read(UC_ARM_REG_R0),self.worker);self.workers+=1
        elif p==0x0802AD76:
            packet=bytes(u.mem_read(u.reg_read(UC_ARM_REG_SP)+0x38,72));self.dequeued.append(packet)
            h.assertEqual(packet,self.submissions[len(self.dequeued)-1]);self.active=packet
        elif p==0x0804113A:
            h.assertIsNotNone(self.active)
            key,offset,dest,length=[u.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)]
            kind,slot,pack=struct.unpack('<IIB3x',u.mem_read(key,12));h.assertEqual((kind,pack),(4,0xFE))
            h.assertEqual((offset,dest,length),struct.unpack_from('<III',self.active,0x10))
            h.assertEqual(h.u.mem_read(self.worker+0x10,1),b'\x01') # caller credit still owned
            h.assertEqual(h.read(self.tcb+0x50),self.worker)
            body=self.files.get(slot);part=b'' if body is None else body[offset:offset+length]
            result=5 if body is None else (0 if len(part)==length else 4)
            if (slot,offset) in self.faults:
                result,actual=self.faults[slot,offset];part=part[:actual]
            if part:u.mem_write(dest,part)
            count=h.read(u.reg_read(UC_ARM_REG_SP));h.word(count,len(part))
            self.reads.append((slot,offset,dest,length));self.results.append((slot,offset,result,len(part)))
            u.reg_write(UC_ARM_REG_R0,result);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
        elif p==0x0802B00C:
            result=u.reg_read(UC_ARM_REG_R6);h.assertEqual(result,self.results[-1][2])
            h.assertEqual(h.u.mem_read(self.worker+0x10,1),b'\x01')
            self.credit_events.append(('result',result,1))
        else:
            self.credit_events.append(('released',self.h.u.mem_read(self.worker+0x10,1)[0]));self.active=None

    def run(self,pack=0,after_slot=None):
        # Bounded per-slot chunks avoid treating128 native queue/worker passes
        # as one100k-instruction leaf. No main service is introduced here.
        return super().run(pack,after_slot or (lambda n:None))

    def check(self):
        h=self.h;super().check()
        h.assertEqual(h.u.mem_read(0x22000000,4),b'FBEG');h.assertEqual(h.u.mem_read(0x22002FFC,4),b'FEND')
        h.assertEqual(self.submissions,self.dequeued);h.assertEqual(h.u.mem_read(self.worker+0x10,4),b'\x02\x02\x01\x01')
        h.assertEqual(h.u.mem_read(self.fifo+6,2),h.u.mem_read(self.fifo+8,2));h.assertEqual(h.read(self.tcb+0x50),0)
        h.assertIsNone(self.active)
        for (p,n),digest in PINS.items():h.assertEqual(hashlib.sha256(h.u.mem_read(p,n)).hexdigest(),digest)

    def record(self,name):
        super().record(name)
        if hasattr(type(self.h),'evidence'):
            type(self.h).evidence[-1].update(native_dispatches=self.dispatches,queued=len(self.submissions),dequeued=len(self.dequeued),
                waits=self.waits,workers=self.workers,file_errors=sum(r!=0 for _,_,r,_ in self.results),
                result_credit_events=len(self.credit_events))
