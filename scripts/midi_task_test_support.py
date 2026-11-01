"""Real main-loop MIDI poll span25870..2587C, synthetic software RX queues.

USB RX header/size follow666A6..666B6/26828/2C71C (16 packets of64 bytes).
No USB/UART hardware or IRQ is run. The following27624 USB endpoint service
and RTOS scheduling are deliberately outside this span.
"""
import struct
from unicorn.arm_const import UC_ARM_REG_SP


class MidiTaskFixture:
    ENTRY, END = 0x08025870, 0x0802587C

    def __init__(self, h, ingress, output):
        self.h, self.ingress, self.output = h, ingress, output
        # Exact native ring header; storage placement is synthetic. Reusing the
        # real boot heap would count this graph twice and is not a boot proof.
        self.rx_buffer, self.rx_capacity = 0x2003E000, 16*(64+2)+1
        h.u.mem_write(ingress.usb_fifo, struct.pack('<I4H', self.rx_buffer,
                                                  self.rx_capacity, 0, 0, 64))
        h.u.mem_write(ingress.usb_port+2, struct.pack('<HH', 64, 16))
        h.u.mem_write(ingress.usb_service, b'\x01')
        self.din_ports = 0x20003000
        h.word(ingress.usb_service+8, self.din_ports)
        h.word(self.din_ports, 0)

    def queue_usb(self, packets):
        assert len(packets) % 4 == 0
        for offset in range(0, len(packets), 64):
            chunk = bytes(packets[offset:offset+64])
            self.h.u.mem_write(self.ingress.enqueue_data, chunk)
            self.ingress.descriptor(self.ingress.enqueue_desc, self.ingress.enqueue_data, len(chunk))
            assert self.h.call(0x08025AEC, self.ingress.usb_fifo, self.ingress.enqueue_desc) == 1

    def step(self):
        # Exercise actual application instructions: output poll THEN USB/DIN.
        self.h.call(self.ENTRY, end=self.END)
        assert self.h.u.reg_read(UC_ARM_REG_SP) == 0x20040000

    def usb_bytes_pending(self):
        return self.h.call(0x0802A37E, self.ingress.usb_fifo)
