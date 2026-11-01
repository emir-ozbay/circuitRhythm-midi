"""Explicit USB register contract and immutable transfer jobs, no device APIs.

The model deliberately permits delayed disable/flush/queued callbacks. It does
not execute the complete stock USB IRQ or establish silicon/DMA behavior.
"""
from dataclasses import dataclass
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3
import midi_usb_session_prototype as session
import midi_usb_lifecycle_prototype as life
from thumb_asm import b_w


@dataclass(frozen=True)
class Transfer:
    epoch: int
    ticket: int
    pointer: int
    size: int
    snapshot: bytes


class UsbSessionFixture:
    def __init__(self,h):
        self.h=h; self.base=0x50000000; self.handle=0x20008400
        self.code,self.labels=session.arm_code()
        self.regs={session.GRSTCTL:0x80000000,session.GINTSTS:0,
                   session.DAINTMSK:0xA000A,session.DEACHMSK:0xA000A,
                   session.DIEPEMPMSK:0xA, session.IN_CTL:0,session.OUT_CTL:0,
                   session.IN_INT:0,session.OUT_INT:0}
        self.writes=[]; self.tx_jobs=[]; self.rx_jobs=[]; self.flushes=[]
        self.disable_requested=set(); self.tx_status=self.rx_status=0
        h.u.mem_map(self.base,0x2000)
        for off,val in self.regs.items(): self.poke(off,val)
        h.word(h.native.usb_controller+0x298,self.handle); h.word(self.handle,self.base)
        h.u.mem_write(h.ingress.usb_port,b'\x01')
        h.u.mem_write(h.ingress.usb_port+2,b'\x40\x00')
        h.word(h.ingress.usb_port+20,0x20009000)
        h.u.mem_write(session.CODE_BASE,self.code)
        h.u.mem_write(session.STATE_BASE-4,b'SBEG')
        h.u.mem_write(session.STATE_BASE+session.STATE_SIZE,b'SEND')
        h.u.mem_write(session.STATE_BASE,bytes(session.STATE_SIZE))
        for off,val in ((0,session.MAGIC),(session.PHASE,session.OPEN),
                        (session.USB_BASE,self.base),(session.TX_ENDPOINT,h.native.usb_endpoint),
                        (session.RX_PORT,h.ingress.usb_port),(session.TX_PORT,h.output.ports[0]),
                        (session.DRIVER,h.output.drivers[0]),(session.EPOCH,1),
                        (session.MAIN,h.read(h.output.drivers[0]+8)),
                        (session.ALT,h.read(h.output.drivers[0]+12)),
                        (session.BUFFER,h.read(h.read(h.output.drivers[0]+8)+4)),
                        (session.TX_FIFO,h.read(h.output.ports[0]+4)),
                        (session.TX_COUNTER,h.read(h.output.ports[0]+16)),
                        (session.RAW,h.native.usb_raw),(session.RX_BUFFER,0x20009000)):
            h.word(session.STATE_BASE+off,val)
        self.overlays=[]
        for address,(_,_,original) in session.gates().items():
            previous=next((o for o in h.recovery.overlays if o['address']==address),None)
            expected=previous['replacement'] if previous else original
            assert h.u.mem_read(address,len(expected))==expected,(hex(address),expected.hex())
            assert len(expected)==len(original)
            replacement=b_w(address,self.labels[f'ss_gate_{address:08x}'])+b'\x00\xBF'*(len(original)//2-2)
            assert 0x08010200<=address<address+len(original)<=0x08080000
            for other in h.recovery.overlays:
                if other is not previous:
                    assert address+len(original)<=other['address'] or other['address']+len(other['replacement'])<=address
            self.overlays.append(dict(address=address,expected=bytes(expected),replacement=replacement))
            if previous: previous['replacement']=replacement
            else: h.recovery.overlays.append(dict(address=address,original=original,replacement=replacement))
            h.u.mem_write(address,replacement)
        assert h.u.mem_read(0x08042FD8,2)==bytes.fromhex('38b5')
        h.u.mem_write(0x08042FD8,bytes.fromhex('7047'))
        self.overlays.append(dict(address=0x08042FD8,expected=bytes.fromhex('38b5'),replacement=bytes.fromhex('7047')))
        h.u.ctl_remove_cache(0x08010000,0x08080000)
        # Earlier helpers compare only the original image length. These gates
        # also overlay generated cave functions, so snapshot the full flash.
        self.flash=bytes(h.u.mem_read(0x08010000,0x70000))
        def recovery_check():
            import midi_recovery_prototype as rp
            h.assertEqual(h.u.mem_read(rp.STATE_BASE-4,4),b'BEG!')
            h.assertEqual(h.u.mem_read(rp.STATE_BASE+rp.STATE_SIZE,4),b'END!')
            h.assertEqual(bytes(h.u.mem_read(0x08010000,0x70000)),self.flash)
        h.recovery.check_canaries=recovery_check

        def read(u,access,address,size,value,data):
            off=address-self.base
            if off in self.regs: u.mem_write(address,self.regs[off].to_bytes(4,'little'))
        def write(u,access,address,size,value,data):
            off=address-self.base; self.writes.append((off,value))
            assert size==4
            if off in (session.IN_INT,session.OUT_INT): self.regs[off]&=~value
            elif off in (session.IN_CTL,session.OUT_CTL):
                self.regs[off]=value
                if value&session.EPDIS: self.disable_requested.add(off)
            elif off==session.GRSTCTL:
                assert value==0x60,'Only MIDI TX FIFO1 flush is permitted'
                self.flushes.append(1); self.regs[off]=0x80000000|value
            else: self.regs[off]=value
        h.u.hook_add(UC_HOOK_MEM_READ,read,begin=self.base,end=self.base+0x1FFF)
        h.u.hook_add(UC_HOOK_MEM_WRITE,write,begin=self.base,end=self.base+0x1FFF)

        def submit(u,pc,size,data):
            endpoint=u.reg_read(UC_ARM_REG_R1)
            if endpoint!=(0x81 if pc==0x0802C9B8 else 1):
                return  # native EP0/other-interface paths do not own MIDI jobs
            pointer,length=u.reg_read(UC_ARM_REG_R2),u.reg_read(UC_ARM_REG_R3)
            if pc==0x0802C9B8:
                assert self.status()['tx_active']==1
                self.tx_jobs.append(Transfer(self.status()['epoch'],self.status()['tx_ticket'],pointer,length,
                                             bytes(u.mem_read(pointer,length))))
                self.poke(session.IN_CTL,session.EPENA)
                u.reg_write(UC_ARM_REG_R0,self.tx_status)
            else:
                assert self.status()['rx_active']==1 and length>0
                self.rx_jobs.append(Transfer(self.status()['epoch'],self.status()['rx_ticket'],pointer,length,b''))
                self.poke(session.OUT_CTL,session.EPENA)
                u.reg_write(UC_ARM_REG_R0,self.rx_status)
        for pc in (0x0802C9B8,0x08042FD8): h.u.hook_add(UC_HOOK_CODE,submit,begin=pc,end=pc)

    def poke(self,off,val):
        self.regs[off]=val; self.h.word(self.base+off,val)

    def status(self):
        return {name:self.h.read(session.STATE_BASE+off) for name,off in (
            ('phase',session.PHASE),('epoch',session.EPOCH),('next',session.NEXT),
            ('tx_ticket',session.TX_TICKET),('rx_ticket',session.RX_TICKET),
            ('tx_active',session.TX_ACTIVE),('rx_active',session.RX_ACTIVE),
            ('cancel_tx',session.CANCEL_TX),('cancel_rx',session.CANCEL_RX),('busy',session.BUSY))}

    def begin(self): return self.h.call(self.labels['ss_begin'])
    def step(self): return self.h.call(self.labels['ss_step'])
    def resume(self): return self.h.call(self.labels['ss_resume'])
    def arm_rx(self): return self.h.call(0x080269AC,self.h.ingress.usb_port)

    def ack_disable(self,ctl,ack=True):
        assert ctl in self.disable_requested
        self.poke(ctl,self.regs[ctl]&~(session.EPENA|session.EPDIS))
        irq=session.IN_INT if ctl==session.IN_CTL else session.OUT_INT
        if ack: self.poke(irq,self.regs[irq]|session.ACK)

    def finish_flush(self):
        assert self.flushes
        self.poke(session.GRSTCTL,0x80000000)
        # Explicit contract: disabled endpoint + completed FIFO flush releases
        # the old hardware reader. Delayed software callback still keeps its job.
        self.h.native.in_flight=None

    def close(self):
        self.h.assertEqual(self.begin(),0); self.h.assertEqual(self.step(),1)
        for ctl in tuple(self.disable_requested): self.ack_disable(ctl)
        self.h.assertEqual(self.step(),1); self.finish_flush()
        self.h.assertEqual(self.step(),0)
        self.h.assertEqual(self.status()['phase'],session.SEALED)

    def tx_done(self,job):
        accepted=self.h.call(self.labels['ss_tx_done'],job.epoch,job.ticket)
        if accepted:
            assert bytes(self.h.u.mem_read(job.pointer,job.size))==job.snapshot
            self.h.native.usb_completed.append(job.snapshot)
            self.h.native.in_flight=None
            self.poke(session.IN_CTL,self.regs[session.IN_CTL]&~session.EPENA)
        return accepted

    def rx_done(self,job,packets):
        # A cancelled hardware job cannot write new DMA bytes. Queued callback
        # injection uses its immutable token, WITHOUT touching current buffers.
        s=self.status()
        current=s['phase']==session.OPEN and s['rx_active']==1 and (s['epoch'],s['rx_ticket'])==(job.epoch,job.ticket)
        if current:
            assert len(packets)<=job.size
            self.h.u.mem_write(job.pointer,packets)
            self.poke(session.OUT_CTL,self.regs[session.OUT_CTL]&~session.EPENA)
        return self.h.call(self.labels['ss_rx_done'],job.epoch,job.ticket,len(packets))

    def check(self):
        h=self.h
        h.assertEqual(h.u.mem_read(session.STATE_BASE-4,4),b'SBEG')
        h.assertEqual(h.u.mem_read(session.STATE_BASE+session.STATE_SIZE,4),b'SEND')
        h.assertEqual(self.status()['busy'],0); h.lc.check()

    def record_nested_trampoline(self):
        # install_nested_calls owns this separate, fixed test-only cave.
        off=0x08071000-0x08010000
        assert self.flash[off:off+256]==bytes(256)
        expected=bytearray(self.flash)
        expected[off:off+256]=self.h.u.mem_read(0x08071000,256)
        self.flash=bytes(expected)
