"""Actual USB64-byte staging and DIN running-status formatters.

USB low-level submit2C9B8 and UART IRQ-enable2AC58 are hardware boundaries.
Endpoint availability is released through native5268E/268D0,injected as a
completion notification;actual IRQ dispatch and DMA/wire timing are not claimed.
"""
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3


class NativeMidiDriverFixture:
    def __init__(self, h, output):
        self.h, self.output = h, output
        self.usb_raw, self.usb_endpoint, self.usb_controller = 0x20003700, 0x20003800, 0x20003A00
        self.usb_submissions, self.usb_completed = [], []
        self.in_flight = None
        h.u.mem_write(0x0802C9B8, bytes.fromhex('7047'))
        h.u.mem_write(0x0802AC58, bytes.fromhex('7047'))
        h.u.mem_write(self.usb_controller+0x274, b'\x03')  # native configured state
        h.u.mem_write(self.usb_endpoint, b'\x81')
        h.u.mem_write(self.usb_endpoint+2, bytes([64, 0]))
        h.word(self.usb_endpoint+0x10, self.usb_controller)
        h.u.mem_write(self.usb_endpoint+0x1C, b'\x01\x01')  # available + capacity from26828
        h.call(0x0802B3AC, self.usb_raw, self.usb_endpoint)
        h.call(0x0802B408, output.drivers[0], self.usb_raw, 0)
        self.completion_wrapper=0x20003500
        h.word(self.completion_wrapper,0x20003520);h.word(self.completion_wrapper+4,0x20003540)
        h.word(0x20003520+0x14,0);h.word(0x20003540,self.usb_endpoint);h.word(0x20003544,0)
        def submit(u, pc, size, data):
            endpoint, pointer, length = (u.reg_read(r) for r in
                                         (UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3))
            u.reg_write(UC_ARM_REG_R0,0) # native4301A/2C9B8 success status
            if length:
                foreign=getattr(self,'foreign_usb_submit',None)
                if endpoint!=0x81 and foreign is not None:
                    foreign(endpoint,pointer,length)
                    return
                assert self.in_flight is None, 'overlapping USB transfers'
                assert endpoint == 0x81 and 0 < length <= 64
                self.in_flight = pointer, length
                self.usb_submissions.append(bytes(u.mem_read(pointer, length)))
        h.u.hook_add(UC_HOOK_CODE, submit, begin=0x0802C9B8, end=0x0802C9B8)

        self.uart_devices = [0x20003D00, 0x20003D40]
        self.uart_buffers = [0x20003E00, 0x20003F00]
        for index, (device, data) in enumerate(zip(self.uart_devices, self.uart_buffers)):
            raw = self.usb_raw + 8 + index*8
            h.u.mem_write(device+0x0C,
                          data.to_bytes(4, 'little') + bytes([65, 0, 0, 0, 0, 0, 1, 0]))
            h.call(0x0802B534, raw, device)
            h.call(0x0802B564, output.drivers[index+1], raw)

    def usb_ready(self):
        return self.h.call(0x0802B4D8, self.output.drivers[0])

    def usb_full(self):
        return self.h.call(0x0802B4B2, self.output.drivers[0])

    def release_usb_endpoint(self):
        assert self.in_flight is not None
        pointer, length = self.in_flight
        payload = bytes(self.h.u.mem_read(pointer, length))
        assert payload == self.usb_submissions[-1], 'in-flight USB buffer changed'
        self.usb_completed.append(payload)
        self.in_flight = None
        self.h.call(0x0805268E,self.completion_wrapper,self.usb_controller,1)

    def uart_full(self, index):
        return self.h.call(0x0802B5CA, self.output.drivers[index+1])

    def drain_uart(self, index):
        fifo = self.uart_devices[index]+0x0C
        count = self.h.call(0x0802A37E, fifo)
        assert count <= 64
        destination = 0x20003600
        assert self.h.call(0x0802A470, fifo, destination, count) == count
        return bytes(self.h.u.mem_read(destination, count))
