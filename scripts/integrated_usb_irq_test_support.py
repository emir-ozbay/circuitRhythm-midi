"""Packaged recovery SYX + native HAL/FIFO/IRQ/EP0;no recovery overlay.

Only modeled MMIO events/ACK/flush and UART draining. Configuration travels
through native setup packets. No physical device,NVIC,DMA or elapsed timing.
"""
from collections import deque
from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_READ,UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_IPSR
from integrated_usb_tx_test_support import IntegratedUsbTxFixture
import midi_accepted_tx_patch as guard


class IntegratedUsbIrqFixture(IntegratedUsbTxFixture):
    def __init__(self,h,out):
        super().__init__(h,out)
        self.handle=0x200054B4 # actual static handle selected by native646D0
        h.word(self.native.usb_controller+0x298,self.handle);h.word(self.handle,guard.USB_BASE);h.word(self.handle+0x10,0)
        self.allowed_flushes.update((0x420,0x20,0x10))
        self.external=0;self.events=deque();self.fifo_words=deque();self.tx_fifo=[]
        self.irq_visits=[];self.flush_reads=0;self.release_on_flush=False;self.hold_flush=False
        self.flags={0x908+n*0x20:0 for n in range(6)}
        self.flags.update({0xB08+n*0x20:0 for n in range(6)})
        for reg,value in ((0x18,(1<<3)|(1<<4)|(1<<12)|(1<<13)|(1<<18)|(1<<19)),(0x810,3),(0x814,0xB),
                          (0x938,64),(0x81C,0x10003),(0x900,0x8000),(0xB00,0x8000)):
            self.regs[reg]=value;h.word(guard.USB_BASE+reg,value)
        self.root=0x2000A000;h.word(0x20006F20,self.root);h.word(self.root+8,self.wrapper);h.word(self.root+12,0)
        h.word(self.rx_array,self.reset.port);h.word(self.rx_array+4,0)
        h.u.mem_write(self.reset.port,b'\x01');h.u.mem_write(self.reset.port+6,b'\x02')
        h.word(self.reset.port+0x10,self.native.usb_controller)
        h.word(self.native.usb_controller+0x26C,3);h.word(self.native.usb_controller+0x28C,0x0806776C)
        h.word(self.native.usb_controller+4,1);h.word(self.native.usb_controller+0x24,64)
        h.word(self.handle+4,6);h.word(self.handle+0x400,self.native.usb_controller)
        h.u.mem_write(self.native.usb_endpoint+6,b'\x02')
        for off in (0x3C,0x58,0x1FC):
            h.word(self.handle+off+8,64);h.u.mem_write(self.handle+off+3,b'\x02')
        assert h.u.mem_read(0x0802C9B8,2)==bytes.fromhex('7047')
        h.u.mem_write(0x0802C9B8,bytes.fromhex('80b5'))
        h.u.hook_add(UC_HOOK_CODE,lambda u,p,n,d:u.reg_write(UC_ARM_REG_R0,self.native.usb_controller),begin=0x0802C9B8,end=0x0802C9B8)
        def read(u,access,address,size,value,data):
            off=address-guard.USB_BASE
            if off==guard.GRSTCTL and self.flush_reads and not self.hold_flush:
                self.flush_reads-=1
                if not self.flush_reads:
                    self.regs[off]&=~0x30
                    if self.release_on_flush:self.native.in_flight=None;self.cancel_pending=False;self.release_on_flush=False
            if off==0x14:val=self.gint()
            elif off==0x818:val=self.daint()
            elif off in self.flags:val=self.flags[off]
            elif off==0x20:
                assert self.events;val=self.events.popleft()
            elif off==0x1000:
                assert self.fifo_words;val=self.fifo_words.popleft()
            elif off in self.regs:val=self.regs[off]
            else:return
            u.mem_write(address,val.to_bytes(4,'little'))
        def write(u,access,address,size,value,data):
            off=address-guard.USB_BASE
            if off in self.flags:self.flags[off]&=~value;self.regs[off]=self.flags[off]
            elif off==0x14:self.external&=~value;self.regs[off]=self.gint()
            elif off==0x2000:self.tx_fifo.append(value.to_bytes(4,'little'))
            elif off==guard.GRSTCTL:
                index=value>>6&31;self.regs[off]=0x80000000|value;self.flush_reads=2
                if value&0x20 and index in (1,16):
                    self.tx_fifo.clear()
                    if self.native.in_flight is not None:
                        if not self.cancel_pending:self.cancelled.append(bytes(u.mem_read(*self.native.in_flight)))
                        self.cancel_pending=True;self.release_on_flush=True
                if value==0x10:self.events.clear();self.fifo_words.clear()
        h.u.hook_add(UC_HOOK_MEM_READ,read,begin=guard.USB_BASE,end=guard.USB_BASE+0x2FFF)
        h.u.hook_add(UC_HOOK_MEM_WRITE,write,begin=guard.USB_BASE,end=guard.USB_BASE+0x2FFF)
        def completed(u,p,n,d):
            if u.reg_read(UC_ARM_REG_R0)!=self.native.usb_endpoint or self.native.in_flight is None or self.cancel_pending:return
            payload=bytes(u.mem_read(*self.native.in_flight));assert b''.join(self.tx_fifo)==payload
            self.native.usb_completed.append(payload);self.native.in_flight=None;self.tx_fifo.clear()
        h.u.hook_add(UC_HOOK_CODE,completed,begin=0x080268DE,end=0x080268DE)
        for pc in (0x080646D0,0x0804293E,0x0802C7AC,0x08042690,0x0802AB36,0x08040C22,0x0805268E,0x080268D0,
                   0x0804301A,0x080531A6,0x080525B2,0x080525B6,0x0805261C,0x08068A2C,0x08042584,0x0804259A):
            h.u.hook_add(UC_HOOK_CODE,lambda u,p,n,d:self.irq_visits.append(p),begin=pc,end=pc)
        h.u.ctl_remove_cache(0x08010000,0x08080000)
    def daint(self):
        result=0
        for n in range(6):
            mask=self.regs.get(0x810,0)|((self.regs.get(0x834,0)>>n&1)<<7)
            if self.flags[0x908+n*0x20]&mask:result|=1<<n
            if self.flags[0xB08+n*0x20]&self.regs.get(0x814,0):result|=1<<(16+n)
        return result
    def gint(self):
        d=self.daint()&self.regs[0x81C]
        return self.external|(16 if self.events else 0)|(1<<18 if d&0xFFFF else 0)|(1<<19 if d>>16 else 0)
    def run_irq(self):
        h=self.h
        old=h.u.reg_read(UC_ARM_REG_IPSR);h.u.reg_write(UC_ARM_REG_IPSR,16)
        try:result=h.call(0x080646D0)
        finally:h.u.reg_write(UC_ARM_REG_IPSR,old)
        return result
    def bus(self):
        if self.auto_barrier and self.disable_requested:self.ack_disable();self.flags[guard.IN_INT]=self.regs[guard.IN_INT]
        if self.native.in_flight is not None and not self.cancel_pending:
            self.flags[guard.IN_INT]|=0x80;self.run_irq()
            self.flags[guard.IN_INT]&=~0x80;self.flags[guard.IN_INT]|=1
            self.regs[guard.IN_CTL]&=~guard.EPENA;self.run_irq()
        return [self.native.drain_uart(n) for n in range(2)]
    def ack_disable(self,ack=True):
        super().ack_disable(ack);self.flags[guard.IN_INT]=self.regs[guard.IN_INT]
    def reset_irq(self):self.external|=1<<12;return self.run_irq()
    def enumerate_irq(self):self.external|=1<<13;return self.run_irq()
    def setup(self,packet):
        assert len(packet)==8;self.events.append((6<<17)|(8<<4));self.fifo_words.extend(int.from_bytes(packet[n:n+4],'little') for n in (0,4))
        self.run_irq();self.flags[0xB08]|=8;return self.run_irq()
    def address(self,value=7):return self.setup(bytes([0,5,value,0,0,0,0,0]))
    def configure(self,value=1):return self.setup(bytes([0,9,value,0,0,0,0,0]))
