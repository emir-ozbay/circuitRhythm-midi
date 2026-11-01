"""Native output/class-deinit over explicit bus configuration/close boundaries.

No recovery overlay. Native5261C/2C90C/42F92/52EDC run over a register model.
Configuration, cancellation and completion are not silicon or complete
EP0/reset IRQ evidence.
"""
from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_READ,UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R1
import midi_accepted_tx_patch as accepted
from thumb_asm import b_w
from integrated_reset_test_support import IntegratedResetFixture
from native_midi_driver_test_support import NativeMidiDriverFixture


class IntegratedUsbTxFixture:
    def __init__(self,h,out):
        self.h,self.out=h,out;self.native=NativeMidiDriverFixture(h,out)
        self.reset=IntegratedResetFixture(h,out)
        self.wrapper,self.tx_array,self.rx_array,self.handle=0x20008000,0x20008100,0x20008120,0x20008400
        self.closes=[];self.cancelled=[];self.rejects=[]
        self.cancel_pending=False;self.auto_barrier=True;self.writes=[];self.disable_requested=False
        self.allowed_flushes={0x60}
        _,tg=accepted.arm_code(0x2004F320,11)
        close_bytes=bytes(h.u.mem_read(accepted.CLOSE_SITE,4))
        self.guard_installed=close_bytes in (b_w(accepted.CLOSE_SITE,tg['tg_close_gate']),bytes.fromhex('2cf0f4bd'))
        assert self.guard_installed or close_bytes==accepted.CLOSE_BYTES
        h.word(self.wrapper,0x080676F4);h.word(self.wrapper+4,self.tx_array);h.word(self.wrapper+8,self.rx_array)
        h.word(self.tx_array,self.native.usb_endpoint);h.word(self.tx_array+4,0);h.word(self.rx_array,0)
        h.word(self.native.usb_controller+0x298,self.handle);h.word(self.handle,0x40040000)
        h.word(self.handle+0x10,0)
        h.u.mem_map(accepted.USB_BASE,0x3000)
        self.regs={accepted.IN_CTL:0x88040,accepted.IN_INT:0,accepted.GRSTCTL:0x80000000,
                   accepted.DAINTMSK:0xA000A,accepted.DEACHMSK:0xA000A,accepted.EMPMSK:0xA}
        for off,v in self.regs.items():h.word(accepted.USB_BASE+off,v)
        def read(u,access,address,size,value,data):
            off=address-accepted.USB_BASE
            if off in self.regs:u.mem_write(address,self.regs[off].to_bytes(4,'little'))
        def write(u,access,address,size,value,data):
            off=address-accepted.USB_BASE;self.writes.append((off,value));assert size==4
            if off==accepted.IN_INT:self.regs[off]&=~value
            else:
                self.regs[off]=value
                if off==accepted.IN_CTL and value&accepted.EPDIS:self.disable_requested=True
                if off==accepted.GRSTCTL:assert value in self.allowed_flushes,'Unexpected USB FIFO flush'
        h.u.hook_add(UC_HOOK_MEM_READ,read,begin=accepted.USB_BASE,end=accepted.USB_BASE+0x2FFF)
        h.u.hook_add(UC_HOOK_MEM_WRITE,write,begin=accepted.USB_BASE,end=accepted.USB_BASE+0x2FFF)
        def hw_submit(u,p,n,d):
            if u.reg_read(UC_ARM_REG_R1)==0x81:self.regs[accepted.IN_CTL]|=accepted.EPENA
        h.u.hook_add(UC_HOOK_CODE,hw_submit,begin=0x0802C9B8,end=0x0802C9B8)
        assert h.u.mem_read(0x08052EDC,4)==bytes.fromhex('70b44d78')
        def closed(u,p,n,d):
            self.closes.append(u.reg_read(UC_ARM_REG_R1))
            if self.native.in_flight is not None:
                job=self.native.in_flight
                if not self.cancel_pending:self.cancelled.append(bytes(u.mem_read(*job)))
                if self.guard_installed:self.cancel_pending=True
                else:self.native.in_flight=None
        h.u.hook_add(UC_HOOK_CODE,closed,begin=0x08052EDC,end=0x08052EDC)
        h.u.ctl_remove_cache(0x08010000,0x08080000)
    def disconnect_before_flush(self,no_credit=False):
        h=self.h
        applied=[]
        def configure(u,p,n,d):
            if not applied:
                applied.append(p)
                u.mem_write(self.native.usb_controller+0x274,b'\0')
                if no_credit:u.mem_write(self.native.usb_endpoint+0x1C,b'\0')
        # This hook runs before the trampoline's second visit to the flush.
        h.u.hook_add(UC_HOOK_CODE,configure,begin=0x0802B498,end=0x0802B498)
        return self.reset.inject_once(0x0802B498,[(0x0805261C,(self.wrapper,self.native.usb_controller,0))])
    def reconnect(self):
        self.h.u.mem_write(self.native.usb_controller+0x274,b'\x03')
        self.h.u.mem_write(self.native.usb_endpoint+0x1C,b'\x01')
        self.regs[accepted.IN_CTL]|=0x88040 # modeled host configuration/open
        for reg in (accepted.DAINTMSK,accepted.DEACHMSK):self.regs[reg]|=2
        self.reset.parent()
    def main(self):
        descriptor=self.h.read(self.out.drivers[0]+8)
        length=int.from_bytes(self.h.u.mem_read(descriptor,2),'little')
        return length,bytes(self.h.u.mem_read(self.h.read(descriptor+4),64))
    def bus(self):
        if self.auto_barrier:
            if self.disable_requested:self.ack_disable()
            if self.regs[accepted.GRSTCTL]&0x20:self.finish_flush()
        if self.native.in_flight is not None and not self.cancel_pending:
            self.regs[accepted.IN_CTL]&=~accepted.EPENA
            self.native.release_usb_endpoint()
        return [self.native.drain_uart(n) for n in range(2)]
    def ack_disable(self,ack=True):
        assert self.disable_requested
        self.regs[accepted.IN_CTL]&=~(accepted.EPENA|accepted.EPDIS)
        if ack:self.regs[accepted.IN_INT]|=2
        self.disable_requested=False
    def finish_flush(self):
        assert self.regs[accepted.GRSTCTL]&0x20
        self.regs[accepted.GRSTCTL]=0x80000000
        if self.cancel_pending:self.native.in_flight=None;self.cancel_pending=False
