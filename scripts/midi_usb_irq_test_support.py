"""Native HAL submit/IRQ/FIFO/callback chain over explicit synthetic registers.

No USB/MIDI/device API. CPU-FIFO mode only; no real DMA, NVIC or cache model.
Earlier session fixture still provides the disable/flush contract.
"""
from collections import deque
from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_READ,UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_IPSR
import midi_usb_irq_prototype as irq
import midi_usb_session_prototype as session
from thumb_asm import b_w
from inspect_ui import load_image


class UsbIrqFixture:
    def __init__(self,h,control=False):
        self.h=h; self.ss=h.ss; self.base=0x40040000; self.handle=h.ss.handle
        self.ctrl=h.native.usb_controller; self.wrapper=0x2000A040
        self.root,self.vtable,self.tx_array,self.rx_array=0x2000A000,0x2000A080,0x2000A100,0x2000A110
        self.events=deque(); self.fifo_words=deque(); self.tx_fifo=[]
        self.flags={0x908+n*0x20:0 for n in range(4)}
        self.flags.update({0xB08+n*0x20:0 for n in range(4)})
        self.external=0; self.pop_count=self.copy_words=0; self.visits=[]
        self.control=control; self.global_flush_reads=0
        self.native_flush_owner=lambda:False
        self.native_flush_indices={1}
        self.barrier_flush_owner=lambda:False
        self.barrier_disable_controls=set()
        self.endpoint_count=6 if control else 4
        if control:
            for n in range(4,6): self.flags[0x908+n*0x20]=self.flags[0xB08+n*0x20]=0
        self.code,self.labels=irq.arm_code(); h.u.mem_write(irq.CODE_BASE,self.code)
        h.u.mem_write(irq.STATE_BASE-4,b'IBEG'); h.u.mem_write(irq.STATE_BASE+irq.STATE_SIZE,b'IEND')
        h.u.mem_write(irq.STATE_BASE,bytes(irq.STATE_SIZE))
        for off,val in ((0,irq.MAGIC),(irq.HANDLE,self.handle),(irq.CLASS,self.wrapper),(irq.CONTROLLER,self.ctrl)):
            h.word(irq.STATE_BASE+off,val)
        self.overlays=[]
        targets={irq.NATIVE_IRQ:'ib_irq',0x080268D0:'ib_tx_callback',0x08026988:'ib_rx_callback',0x0805261C:'ib_disconnect'}
        for address,original in irq.GATES.items():
            previous=next((o for o in h.recovery.overlays if o['address']==address),None)
            expected=previous['replacement'] if previous else original
            assert h.u.mem_read(address,len(expected))==expected and len(expected)==len(original)
            patch=b_w(address,self.labels[targets[address]])+b'\x00\xBF'*(len(original)//2-2)
            for other in h.recovery.overlays:
                if other is not previous:
                    assert address+len(original)<=other['address'] or other['address']+len(other['replacement'])<=address
            self.overlays.append(dict(address=address,expected=bytes(expected),replacement=patch))
            if previous: previous['replacement']=patch
            else: h.recovery.overlays.append(dict(address=address,original=original,replacement=patch))
            h.u.mem_write(address,patch)
        # Restore both hardware-boundary stubs: complete stock HAL code runs.
        stock=load_image()
        for address,original in ((0x0802C9B8,bytes.fromhex('80b5')),(0x08042FD8,bytes.fromhex('38b5'))):
            assert stock[address-0x08010000:address-0x08010000+2]==original
            assert h.u.mem_read(address,2)==bytes.fromhex('7047')
            h.u.mem_write(address,original)
            self.overlays.append(dict(address=address,expected=bytes.fromhex('7047'),replacement=original))
        # Native2C82A's pinned initialization prefix selects USBx40040000 and
        # CPU FIFO mode. Keep the handle in synthetic RAM; no full boot claim.
        h.u.mem_map(self.base,0x3000)
        h.word(self.handle,self.base); h.word(session.STATE_BASE+session.USB_BASE,self.base)
        h.word(self.handle+4,self.endpoint_count); h.word(self.handle+16,0); h.word(self.handle+0x400,self.ctrl)
        h.word(self.ctrl+0x26C,3); h.word(self.ctrl+0x28C,0x0806776C)
        assert h.read(0x08067780)==0x0802AB37 and h.read(0x08067784)==0x0802AB43
        h.word(0x20006F20,self.root); h.word(self.root+8,self.wrapper)
        h.word(self.wrapper,self.vtable); h.word(self.wrapper+4,self.tx_array); h.word(self.wrapper+8,self.rx_array)
        h.word(self.tx_array,h.native.usb_endpoint); h.word(self.rx_array,h.ingress.usb_port)
        for off in (0x3C+0x1C,0x1FC+0x1C):
            h.word(self.handle+off+8,64); h.u.mem_write(self.handle+off+3,b'\x02')
        for reg,value in ((0x18,irq.ALLOWED_GINT),(0x810,3),(0x814,0xB),
                          (0x938,64),(0x920,0x88040),(0xB20,0x88040)):
            self.ss.poke(reg,value)
        old_ack=self.ss.ack_disable
        def ack(ctl,ack=True):
            old_ack(ctl,ack=ack)
            reg=session.IN_INT if ctl==session.IN_CTL else session.OUT_INT
            self.flags[reg]=self.ss.regs[reg]
        self.ss.ack_disable=ack

        # Earlier model hooks record jobs and set return0 for a boundary stub.
        # Restore the native argument afterwards, then let the real HAL execute.
        def restore_submit(u,pc,size,data):
            u.reg_write(UC_ARM_REG_R0,self.ctrl if pc==0x0802C9B8 else self.handle)
            if u.reg_read(UC_ARM_REG_R1)!=(0x81 if pc==0x0802C9B8 else 1): return
            ctl=session.IN_CTL if pc==0x0802C9B8 else session.OUT_CTL
            self.ss.poke(ctl,self.ss.regs[ctl]|0x88040)
        for pc in (0x0802C9B8,0x08042FD8): h.u.hook_add(UC_HOOK_CODE,restore_submit,begin=pc,end=pc)

        def read(u,access,address,size,value,data):
            off=address-self.base
            if off==session.GRSTCTL and self.global_flush_reads:
                self.global_flush_reads-=1
                if not self.global_flush_reads: self.ss.regs[off]&=~0x30
            if off==0x14: val=self.gint()
            elif off==0x818: val=self.daint()
            elif off in self.flags: val=self.flags[off]
            elif off==0x20:
                assert self.events,'RX status pop without an event'
                val=self.events.popleft(); self.pop_count+=1
            elif off==0x1000:
                assert self.fifo_words,'CPU RX FIFO underflow'
                val=self.fifo_words.popleft(); self.copy_words+=1
            elif off in self.ss.regs: val=self.ss.regs[off]
            else: return
            u.mem_write(address,val.to_bytes(4,'little'))
        def write(u,access,address,size,value,data):
            off=address-self.base; self.ss.writes.append((off,value)); assert size==4
            if off in self.flags:
                self.flags[off]&=~value; self.ss.regs[off]=self.flags[off]
            elif off==0x14:
                self.external&=~value; self.ss.regs[off]=self.gint()
            elif off==0x2000: self.tx_fifo.append(value.to_bytes(4,'little'))
            elif off==session.GRSTCTL:
                index=(value>>6)&31
                assert (value==0x60 or self.control and value in (0x420,0x10)
                        or self.control and value&0x20 and index in self.native_flush_indices
                        and self.native_flush_owner()
                        or self.control and value==0xA0 and self.barrier_flush_owner())
                self.ss.flushes.append((value>>6)&31 if value&0x20 else 'RX')
                self.ss.regs[off]=0x80000000|value
                if value&0x20 and index in (1,16): self.tx_fifo.clear()
                manual_extra=value==0xA0 and self.barrier_flush_owner() and not self.native_flush_owner()
                if not manual_extra and (value!=0x60 or self.control and self.native_flush_owner()): self.global_flush_reads=2
                if value==0x10: self.events.clear(); self.fifo_words.clear()
            else:
                self.ss.regs[off]=value
                if off in {session.IN_CTL,session.OUT_CTL}|self.barrier_disable_controls and value&session.EPDIS:
                    self.ss.disable_requested.add(off)
        h.u.hook_add(UC_HOOK_MEM_READ,read,begin=self.base,end=self.base+0x2FFF)
        h.u.hook_add(UC_HOOK_MEM_WRITE,write,begin=self.base,end=self.base+0x2FFF)
        for pc in (irq.NATIVE_IRQ,0x0802C798,0x0802C7AC,0x08042614,0x08042690,
                   0x0802AB42,0x0802AB36,0x08040C46,0x08040C22,0x080526C8,
                   0x0805268E,0x080531CC,0x080531A6,0x08042FD8,0x0804301A):
            h.u.hook_add(UC_HOOK_CODE,lambda u,a,n,d:self.visits.append(a),begin=pc,end=pc)
        h.u.ctl_remove_cache(0x08010000,0x08080000)
        self.ss.flash=bytes(h.u.mem_read(0x08010000,0x70000))

    def daint(self):
        value=0
        for n in range(self.endpoint_count):
            imask=self.ss.regs.get(0x810,0)|((self.ss.regs.get(0x834,0)>>n&1)<<7)
            if self.flags[0x908+n*0x20]&imask: value|=1<<n
            if self.flags[0xB08+n*0x20]&self.ss.regs.get(0x814,0): value|=1<<(16+n)
        return value

    def gint(self):
        d=self.daint()&self.ss.regs[0x81C]
        return self.external|(16 if self.events else 0)|(1<<18 if d&0xFFFF else 0)|(1<<19 if d>>16 else 0)

    def status(self):
        return {name:self.h.read(irq.STATE_BASE+off) for name,off in (
            ('active',irq.ACTIVE),('invalid',irq.INVALID),('tx_seen',irq.TX_SEEN),('rx_seen',irq.RX_SEEN),
            ('tx_done',irq.TX_DONE),('rx_done',irq.RX_DONE),('rx_epoch',irq.RX_EPOCH),('rx_ticket',irq.RX_TICKET))}

    def run(self):
        h=self.h; old=self.status()['tx_done']; job=self.ss.tx_jobs[-1] if self.ss.tx_jobs else None
        previous=h.u.reg_read(UC_ARM_REG_IPSR); h.u.reg_write(UC_ARM_REG_IPSR,16)
        try: result=h.call(irq.NATIVE_IRQ,self.handle)
        finally: h.u.reg_write(UC_ARM_REG_IPSR,previous)
        if self.status()['tx_done']!=old:
            assert job is not None
            assert b''.join(self.tx_fifo)==job.snapshot,'Native TX FIFO bytes differ from owned job'
            h.native.usb_completed.append(job.snapshot); h.native.in_flight=None; self.tx_fifo.clear()
        return result

    def rx_data(self,packets,endpoint=1):
        assert len(packets)<=64
        self.events.append((2<<17)|(len(packets)<<4)|endpoint)
        padded=packets+bytes(-len(packets)%4)
        self.fifo_words.extend(int.from_bytes(padded[n:n+4],'little') for n in range(0,len(padded),4))

    def rx_complete(self,endpoint=1):
        self.flags[0xB08+endpoint*0x20]|=1
        reg=0xB00+endpoint*0x20
        self.ss.poke(reg,self.ss.regs.get(reg,0)&~session.EPENA)

    def tx_empty(self): self.flags[session.IN_INT]|=0x80
    def tx_complete(self):
        self.flags[session.IN_INT]|=1
        self.ss.poke(session.IN_CTL,self.ss.regs[session.IN_CTL]&~session.EPENA)

    def check(self):
        h=self.h
        h.assertEqual(h.u.mem_read(irq.STATE_BASE-4,4),b'IBEG')
        h.assertEqual(h.u.mem_read(irq.STATE_BASE+irq.STATE_SIZE,4),b'IEND')
        h.assertEqual(self.status()['active'],0); self.ss.check()
