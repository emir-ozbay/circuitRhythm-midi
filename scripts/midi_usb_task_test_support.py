"""Native main MIDI/USB span plus explicit bus/RTOS/flash model stimuli."""
import struct
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_SP
from inspect_ui import load_image
from thumb_asm import Asm,b_w,bl,pop,push
import midi_usb_task_prototype as task
import midi_usb_msc_prototype as msc
import midi_usb_session_prototype as session
import midi_usb_storage_prototype as storage


class UsbTaskFixture:
    def __init__(self,h,overlay=True):
        self.h=h;self.code,self.labels=task.arm_code();self.events=[];self.overlays=[]
        self.hw_ack=True;self.hw_flush=True;self.hw_tx=True
        # Native29BDA always walks the DIN driver array. Empty is an explicit
        # synthetic choice here; DIN input hardware remains outside this graph.
        self.din_ports=0x20003000;h.word(self.din_ports,0);h.word(h.ingress.usb_service+8,self.din_ports)
        assert h.read(0x20006F04)==h.output.router
        assert not any(h.u.mem_read(task.CODE_BASE,len(self.code)))
        h.u.mem_write(task.CODE_BASE,self.code)
        h.u.mem_write(task.STATE_BASE-4,b'TBEG');h.u.mem_write(task.STATE_BASE+task.STATE_SIZE,b'TEND')
        h.u.mem_write(task.STATE_BASE,bytes(task.STATE_SIZE))
        h.word(task.STATE_BASE,task.MAGIC);h.word(task.STATE_BASE+task.ROUTER,h.output.router)
        p=task.MAIN_CALL;expected=task.GATES[p];stock=load_image()
        assert stock[p-0x08010000:p-0x08010000+4]==expected and h.u.mem_read(p,4)==expected
        if overlay:
            assert 0x08010200<=p<p+4<=0x08080000
            assert all(p+4<=o['address'] or o['address']+len(o['replacement'])<=p for o in h.recovery.overlays)
            patch=bl(p,self.labels['ut_main']);h.u.mem_write(p,patch)
            h.recovery.overlays.append(dict(address=p,original=expected,replacement=patch))
            self.overlays.append(dict(address=hex(p),expected=expected.hex(),replacement=patch.hex()))
        # Model a task switch at the existing drain-yield boundary. Execute
        # the stock flash-backend worker loop648AE..648B8, rather than having
        # Python clear ready/drain or call a worker out of band. Its wait/return
        # edge is explicit: full RTOS task dispatch is still not emulated.
        assert h.read(0x080648C8)==0x20006E60
        a=Asm(0x0800ED80);a.emit(push,[0,1,2,3,4,5,6],lr=True)
        a.imm32(6,0x20006E60);a.emit(b_w,0x080648AE)
        a.label('worker_return');a.emit(pop,[0,1,2,3,4,5,6],pc=True)
        stub,stub_labels=a.assemble();h.u.mem_write(a.base,stub)
        for p,expected,replacement in ((0x08024138,b_w(0x08024138,0x0800ED40),b_w(0x08024138,a.base)),
                (0x080648B8,bytes.fromhex('f0e70000'),b_w(0x080648B8,stub_labels['worker_return']))):
            assert 0x08010200<=p<p+len(expected)<=0x08080000
            assert h.u.mem_read(p,len(expected))==expected
            assert all(p+len(expected)<=o['address'] or o['address']+len(o['replacement'])<=p for o in h.recovery.overlays)
            h.u.mem_write(p,replacement)
            self.overlays.append(dict(address=hex(p),expected=expected.hex(),replacement=replacement.hex(),boundary='RTOS worker wait edge'))
        for name,p in (('output',0x080297DE),('input',0x08029ABC),('msc_slot',task.MAIN_CALL),
                       ('task',self.labels['ut_main']),('worker',0x0802C278),('worker_loop',0x080648AE),('drain_yield',0x08024138)):
            def see(u,p,n,d,name=name):self.events.append(name)
            h.u.hook_add(UC_HOOK_CODE,see,begin=p,end=p)
        h.u.ctl_remove_cache(0x08000000,0x08080000);h.ss.flash=bytes(h.u.mem_read(0x08010000,0x70000))

    def status(self):
        return {n:self.h.read(task.STATE_BASE+o) for n,o in (('frames',task.FRAMES),('busy',task.BUSY),
            ('rejects',task.REJECTS),('power',task.LAST_POWER),('poll',task.LAST_POLL),('errors',task.ERRORS))}
    def frame(self,hardware=True):
        result=self.h.call(task.MAIN_ENTRY,end=task.MAIN_END)
        self.h.assertEqual(self.h.u.reg_read(UC_ARM_REG_SP),0x20040000)
        if hardware:self.bus()
        return result
    def bus(self):
        # Model external ACK/flush completion; task service is never called here.
        h=self.h
        if self.hw_ack:
            for ctl in tuple(h.ss.disable_requested):
                if ctl in (msc.IN_CTL,msc.OUT_CTL):
                    if h.mc.status()['phase']==msc.WAIT_DISABLE:h.mc.ack(ctl)
                elif h.ss.status()['phase']==session.WAIT_DISABLE:h.ss.ack_disable(ctl)
        if self.hw_flush:
            if h.mc.status()['phase']==msc.WAIT_FLUSH:h.mc.finish_flush()
            if h.ss.status()['phase']==session.WAIT_FLUSH:h.ss.finish_flush()
        if h.sd.job and not h.sd.status()['tx_active']:
            h.sd.cancelled.append(h.sd.job[2]);h.sd.job=None;h.sd.tx_fifo.clear()
        if not self.hw_tx:return
        if h.native.in_flight is not None and h.ss.status()['phase']==session.OPEN:
            h.ib.tx_empty();h.ib.run();h.ib.tx_complete();h.ib.run()
        if h.sd.job and h.sd.status()['tx_active'] and h.mc.status()['phase']==msc.OPEN:
            h.ib.flags[msc.IN_INT]|=0x80;h.ib.run()
            count=h.read(h.ib.handle+0x3C+2*0x1C+24)
            if count>=h.sd.job[1]:
                h.assertEqual(b''.join(h.sd.tx_fifo)[:h.sd.job[1]],h.sd.job[2])
                h.ib.flags[msc.IN_INT]|=1;h.ss.poke(msc.IN_CTL,h.ss.regs[msc.IN_CTL]&~session.EPENA)
                h.ib.run();h.assertEqual(h.sd.status()['tx_active'],0)
                h.sd.sent.append(h.sd.job[2]);h.sd.job=None;h.sd.tx_fifo.clear()
    def frames(self,n=16,hardware=True):
        for _ in range(n):self.frame(hardware=hardware)
    def queue_read(self,blocks=1):
        h=self.h;h.call(0x080650D4,0,storage.SCSI+8,storage.SCSI+4)
        cdb=bytes([0x28,0,0,0,0,0,0,blocks>>8,blocks&255,0])+bytes(6)
        packet=struct.pack('<4sIIBBB',b'USBC',0x12345678,blocks*4096,0x80,0,10)+cdb
        h.ib.rx_data(packet,endpoint=2);h.ib.rx_complete(endpoint=2);h.ib.run()
    def inquiry(self):
        h=self.h;h.ib.rx_data(h.inquiries);h.ib.rx_complete();h.ib.run()
    def check(self):
        h=self.h;h.assertEqual(h.u.mem_read(task.STATE_BASE-4,4),b'TBEG')
        h.assertEqual(h.u.mem_read(task.STATE_BASE+task.STATE_SIZE,4),b'TEND')
        h.assertEqual(self.status()['busy'],0);h.assertEqual(self.status()['errors'],0);h.pw.check()
