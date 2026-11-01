"""Native128-slot pack loader with explicit RAM file/flash/UI boundaries.

No filesystem implementation or device access. The sample allocator, progress
observer and synchronous file API completion are modeled, not native ownership
proof. Real53E24/53E8C/4603A/WAV parser/watchdog and MSC/worker/IRQ run.
"""
import hashlib
import struct
from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_R5,UC_ARM_REG_PC,UC_ARM_REG_LR,UC_ARM_REG_SP,UC_ARM_REG_PRIMASK
from inspect_ui import load_image
from seq_Patch import SEQ_STATE_ADDR
from thumb_asm import Asm,b_w,bl,pop,push,raw,str_imm

PINS={
    (0x08053E24,664):'b3e2df4e9b497ad365e947a5b69bc1b7925a237093d1304d0d8175b83e6906c1',
    (0x08040E28,110):'ca63c717dab4fcb16428d65fb24930a8c00418dff7d7f6fc09829ba9920457f2',
    (0x0805B294,140):'7f54adc20d0cdc02b48187ac362be639103f3d4fbc0aa80aab2922a6082755aa',
    (0x0804603A,32):'574e93b03a56acd43e4ec337e9b2168b4dcce113984e433550d208587b9b7d37'}
BOUNDARIES={0x08045EB6:'2de9f04f',0x08031228:'f8b50d46',0x0803157E:'38b50446',
            0x080313D0:'38b50446',0x0803153C:'38b50446',0x08031626:'10b50446',
            0x08031608:'70b50446',0x08023690:'0eb403b0'}


def wav(payload):
    assert len(payload)%2==0
    return struct.pack('<4sI4s4sIHHIIHH4sI',b'RIFF',36+len(payload),b'WAVE',b'fmt ',16,
                       1,1,48000,96000,2,16,b'data',len(payload))+payload


def swapped(payload):
    return b''.join(payload[n:n+2][::-1] for n in range(0,len(payload),2))


class UsbLongLoopFixture:
    def __init__(self,h,files=None):
        self.h=h;self.files=files or {};self.reads=[];self.writes=[];self.metadata={};self.progress=[]
        self.allocations=[];self.polls=0;self.native_polls=0;self.watchdogs=[];self.slots=[];self.messages=[]
        self.flash_cursor=None;self.completed=0;self.boundary_calls=[]
        # Earlier isolated MIDI fixtures put synthetic vtables/SysEx objects
        # inside the native sample scratch buffer. Move those fixture objects,
        # and their RAM references, before exercising the real buffer. This is
        # NOT a proposed production RAM layout or evidence of a stock alias bug.
        low,high,dest=0x20004B00,0x20005000,0x2000E000
        assert not any(h.u.mem_read(dest,0x600))
        h.u.mem_write(dest,bytes(h.u.mem_read(low,high-low)));h.u.mem_write(low,bytes(high-low))
        ram=bytes(h.u.mem_read(0x20000000,0x50000));self.relocated_references=[]
        for offset,(value,) in enumerate(struct.iter_unpack('<I',ram)):
            if low<=value<high:
                p=0x20000000+offset*4;h.word(p,value+dest-low);self.relocated_references.append(p)
        for obj in (h,h.recovery,h.playback):
            for name,value in list(vars(obj).items()):
                if isinstance(value,int) and low<=value<high:setattr(obj,name,value+dest-low)
        stock=load_image()
        for (p,n),digest in PINS.items():
            assert hashlib.sha256(stock[p-0x08010000:p-0x08010000+n]).hexdigest()==digest
            assert h.u.mem_read(p,n)==stock[p-0x08010000:p-0x08010000+n]
        # Model vtable methods in a separate checked emulator-only cave. Do not
        # replace any native loader or poll instructions.
        self.cave=0x08071200;self.code=bytes.fromhex('704700bf')*6
        assert self.cave%4==0 and 0x0806A570<=self.cave<self.cave+len(self.code)<=0x08080000
        assert not any(h.u.mem_read(self.cave,0x40))
        assert all(self.cave+len(self.code)<=o['address'] or o['address']+len(o['replacement'])<=self.cave for o in h.recovery.overlays)
        h.u.mem_write(self.cave,self.code)
        self.manager,self.manager_vt,self.progress_vt,self.pack=0x20003380,0x200033C0,0x20003400,0x20003440
        assert not any(h.u.mem_read(self.manager,0xD0))
        h.word(self.manager,self.manager_vt);h.word(self.manager_vt+0x10,self.cave+1);h.word(self.manager_vt+0xC,self.cave+5)
        h.word(0x20006F24,self.manager)
        for off,target in ((0,8),(0xC,12),(8,16),(0x10,20)):h.word(self.progress_vt+off,self.cave+target+1)
        h.word(0x20000A8C,self.progress_vt)
        # Already-mounted pack0; execute the real40E28/2745A selector fast path.
        h.word(0x20006E1C+8,self.pack);h.word(0x20006E24,self.pack);h.word(self.pack,0)
        # Native26DD6 writes the watchdog reload register. This is mapped RAM.
        h.u.mem_map(0x40003000,0x1000)
        h.u.hook_add(UC_HOOK_MEM_WRITE,lambda u,k,a,n,v,d:self.watchdogs.append(v),begin=0x40003000,end=0x40003003)
        h.u.mem_write(0x20003F90,b'LBEG');h.u.mem_write(0x20004F94,b'LEND')
        h.u.mem_write(0x20006AD4,b'HBEG');h.u.mem_write(0x20006B18,b'HEND')
        for p,expected in BOUNDARIES.items():
            assert h.u.mem_read(p,4)==bytes.fromhex(expected)
            assert all(p+4<=o['address'] or o['address']+len(o['replacement'])<=p for o in h.recovery.overlays)
            h.u.hook_add(UC_HOOK_CODE,self.boundary,begin=p,end=p)
        h.u.hook_add(UC_HOOK_CODE,self.observer,begin=self.cave,end=self.cave+len(self.code)-1)
        for p in (0x08053E70,0x08053E7E,0x0802762A):h.u.hook_add(UC_HOOK_CODE,self.observe_native,begin=p,end=p)
        h.u.ctl_remove_cache(self.cave,self.cave+0x40)
        h.ss.flash=bytes(h.u.mem_read(0x08010000,0x70000))

    def observe_native(self,u,p,n,d):
        if p==0x08053E70:self.slots.append(u.reg_read(UC_ARM_REG_R5))
        elif p==0x08053E7E:self.polls+=1
        else:self.native_polls+=1

    def observer(self,u,p,n,d):
        h=self.h;r0,r1,r2=[u.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2)]
        off=p-self.cave
        if off==0:h.assertEqual(r0,self.manager);self.allocations.clear()
        elif off==4:
            h.assertEqual(r0,self.manager);h.assertLess(r1,128)
            address=0x40000+r1*0x10000+sum(s==r1 for s in self.allocations)*0x1000
            self.allocations.append(r1);u.reg_write(UC_ARM_REG_R0,address)
        elif off in (8,12,16,20):
            h.assertEqual(r0,0x20000A8C)
            self.progress.append((off,r1,r2) if off==16 else (off,))
            if off==20:self.completed+=1

    def boundary(self,u,p,n,d):
        h=self.h;r0,r1,r2,r3=[u.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)]
        self.boundary_calls.append(p)
        if p==0x08045EB6:
            h.assertEqual(r0,6);kind,slot,pack=struct.unpack('<IIB3x',u.mem_read(r1,12))
            h.assertEqual((kind,pack),(4,0xFE));h.assertLess(slot,128)
            offset,dest,length=struct.unpack('<III',u.mem_read(r2,12));h.assertEqual(r3,0)
            h.assertTrue((dest==0x20006AD8 and length==64) or (dest in (0x20003F94,0x20004794) and 0<length<=2048))
            body=self.files.get(slot,b'');part=body[offset:offset+length]
            # Immediate read completion, with deterministic zero-fill for short
            # reads. File-task scheduling/errors/partial-read semantics are open.
            u.mem_write(dest,part+bytes(length-len(part)))
            self.reads.append((slot,offset,dest,length))
        elif p==0x08031228:
            h.assertEqual(r0,0);h.assertTrue(0x30000<=r2<0x30200);self.metadata[r2]=r1
        elif p==0x080313D0:h.assertEqual(r0,0);self.flash_cursor=r1<<8
        elif p==0x08031608:
            h.assertEqual(r0,0);h.assertIn(r1,(0x20003F94,0x20004794));h.assertTrue(0<r2<=2048)
            h.assertIsNotNone(self.flash_cursor);self.writes.append((self.flash_cursor,bytes(u.mem_read(r1,r2))))
            self.flash_cursor+=r2//2
        elif p==0x08023690:self.messages.append(r0)
        else:h.assertEqual(r0,0)
        u.reg_write(UC_ARM_REG_R0,0);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))

    def run(self,pack=0,after_slot=None):
        h=self.h;pause=[];resume=[False];hook=None
        if after_slot:
            def checkpoint(u,p,n,d):
                if resume[0]:resume[0]=False;return
                pause.append(self.polls+1);u.emu_stop()
            hook=h.u.hook_add(UC_HOOK_CODE,checkpoint,begin=0x08053E7C,end=0x08053E7C)
        try:
            # h.call's100k cap is enough for missing slots; valid sample loops
            # need a larger explicit bounded budget. Check the same ABI.
            from test_phase1_safety import STOP,SAVED
            saved=[h.u.reg_read(r) for r in SAVED]
            h.u.reg_write(UC_ARM_REG_R0,pack);h.u.reg_write(UC_ARM_REG_SP,0x20040000);h.u.reg_write(UC_ARM_REG_LR,STOP|1)
            pc=0x08053E24
            for _ in range(130):
                h.u.emu_start(pc|1,STOP,count=200000)
                pc=h.u.reg_read(UC_ARM_REG_PC)
                if pc==STOP:break
                h.assertEqual(pc,0x08053E7C,'native long-loop instruction budget exhausted')
                context=h.u.context_save();stack=bytes(h.u.mem_read(0x2003F000,0x1000))
                # External IRQ helpers use h.call's fixed test stack. Preserve
                # the suspended loader stack as well as its CPU context.
                after_slot(pause[-1]);h.u.mem_write(0x2003F000,stack);h.u.context_restore(context);resume[0]=True
            h.assertEqual(h.u.reg_read(UC_ARM_REG_PC),STOP)
            h.assertEqual(h.u.reg_read(UC_ARM_REG_SP),0x20040000)
            h.assertEqual([h.u.reg_read(r) for r in SAVED],saved)
            return h.u.reg_read(UC_ARM_REG_R0)
        finally:
            if hook:h.u.hook_del(hook)

    def inject(self,pc,calls):
        # Keep stimulus results outside both2KB sample buffers as well.
        h=self.h;address,results=0x08071000,0x2000E580
        a=Asm(address);a.emit(push,list(range(13)),lr=True)
        a.emit(raw,bytes.fromhex('eff30084'));a.emit(push,[4,5])
        for n,(target,args) in enumerate(calls):
            assert 0x08010200<=target<0x08080000 and target%2==0
            for r,value in enumerate(args):a.imm32(r,value)
            a.emit(bl,target);a.imm32(3,results+n*4);a.emit(str_imm,0,3)
        a.emit(pop,[4,5]);a.emit(raw,bytes.fromhex('84f3008c'))
        a.emit(pop,list(range(13)),lr=True);a.emit(b_w,pc)
        code,_=a.assemble();assert len(code)<=256 and not any(h.u.mem_read(address,256))
        assert 0x0806A570<=address<address+len(code)<=0x08080000
        assert all(address+len(code)<=o['address'] or o['address']+len(o['replacement'])<=address for o in h.recovery.overlays)
        h.u.mem_write(address,code);h.u.ctl_remove_cache(address,address+256);h.ss.record_nested_trampoline()
        injected=[]
        def inject(u,p,n,d):
            if injected:return
            h.assertEqual(u.reg_read(UC_ARM_REG_PRIMASK),0);injected.append(p);u.reg_write(UC_ARM_REG_PC,address|1)
        h.u.hook_add(UC_HOOK_CODE,inject,begin=pc,end=pc)
        return injected,lambda:[h.read(results+n*4) for n in range(len(calls))]

    def check(self):
        h=self.h
        for p,b in ((0x20003F90,b'LBEG'),(0x20004F94,b'LEND'),(0x20006AD4,b'HBEG'),(0x20006B18,b'HEND')):h.assertEqual(h.u.mem_read(p,4),b)
        for (p,n),digest in PINS.items():h.assertEqual(hashlib.sha256(h.u.mem_read(p,n)).hexdigest(),digest)
        h.assertEqual(bytes(h.u.mem_read(0x08010000,0x70000)),h.ss.flash);h.cy.check()

    def record(self,name):
        if hasattr(type(self.h),'evidence'):
            h=self.h
            type(h).evidence.append(dict(test=name,mode=h.u.mem_read(SEQ_STATE_ADDR+4,1)[0],
                loader_poll_calls=self.polls,native_poll_bodies=self.native_polls,header_reads=sum(o==0 for _,o,_,_ in self.reads),
                file_reads=len(self.reads),sample_write_bytes=sum(len(b) for _,b in self.writes),metadata_words=len(self.metadata),
                completed=self.completed,watchdog_reloads=len(self.watchdogs),storage_reads=h.sd.status()['reads'],
                packets=[dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest()) for b in h.sd.sent],main_frames=h.ut.status()['frames']))
