"""Native MIDI output adapter/router/port FIFO in synthetic RAM.

The final drivers' ready/full/accept/flush methods are controlled boundaries;
no physical driver is called. Queues and output workers execute stock code.
"""
import struct
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_SP


class MidiOutputFixture:
    def __init__(self, h, transport, slots=64):
        self.h, self.transport, self.slots = h, transport, slots
        self.adapter, self.router, self.port_array = 0x20001A00, 0x20001B00, 0x20001B80
        self.ports = [0x20001D00 + n*0x20 for n in range(3)]
        self.drivers = [0x20001E00 + n*0x20 for n in range(3)]
        driver_vt = 0x20001F00
        self.descriptor, self.data = 0x20001F40, 0x20001F60
        self.delivered = [[] for _ in range(3)]
        # ldrb r0,[r0,#4]; bx lr. A controlled ready byte, no device access.
        h.u.mem_write(0x0800EB00, bytes.fromhex('00797047'))
        h.word(driver_vt + 0x0C, 0x0800EB01)
        h.u.mem_write(0x0800EB04, bytes.fromhex('40797047'))  # full byte+5
        h.word(driver_vt + 8, 0x0800EB05)
        for offset, address in ((0, 0x0800EB08), (4, 0x0800EB0C)):
            h.u.mem_write(address, bytes.fromhex('7047'))
            h.word(driver_vt + offset, address | 1)
        def delivered(u, pc, size, data):
            driver = u.reg_read(UC_ARM_REG_R0)
            packet = u.reg_read(UC_ARM_REG_R1)
            self.delivered[self.drivers.index(driver)].append(bytes(u.mem_read(packet, 4)))
        h.u.hook_add(UC_HOOK_CODE, delivered, begin=0x0800EB08, end=0x0800EB08)
        for n, (port, driver) in enumerate(zip(self.ports, self.drivers)):
            h.word(driver, driver_vt)
            h.u.mem_write(driver + 4, b'\x01')
            h.call(0x0804016C, port, driver, slots)
            h.word(self.port_array + 4*n, port)
        h.word(self.router + 0x14, self.port_array)
        h.u.mem_write(self.router + 0x18, b'\x03')
        h.word(0x20006F04, self.router)
        h.word(0x20000A7C, 0)  #468FA/2A666 output enable gate
        h.call(0x08031F08, self.adapter)
        h.u.mem_write(self.adapter + 0x18, b'\x09')  # notes and realtime output
        # Boot27D72 /27E32 pass these actual derived subobjects.
        h.word(transport.engine + 8, self.adapter + 8)
        h.word(transport.root + 0x18, self.adapter + 4)

    def pending(self, port):
        fifo = self.h.read(self.ports[port] + 4)
        return self.h.call(0x0802A37E, fifo) // 3

    def pop(self, port):
        self.h.u.mem_write(self.descriptor, struct.pack('<H2xI', 3, self.data))
        result = self.h.call(0x08040DEE, self.h.read(self.ports[port]+4), self.descriptor)
        return bytes(self.h.u.mem_read(self.data, 3)) if result else None

    def note(self, track, note, velocity=96, on=True):
        return self.h.call(0x08031F9C if on else 0x08031FC6,
                           self.adapter, 16+track, note, velocity)

    def drain(self, port):
        return self.h.call(0x080402B4, self.ports[port])

    def poll(self):
        return self.h.call(0x080297DE, self.router)

    def native_clock_backend(self):
        """Replace the remaining3328C backend stub with native constructors.

        Timer service and tempo output are explicit boundaries. External clock
        is seeded present/selected; elapsed real time and ISR delivery are not
        claimed. Original FIFO, output adapter and transport handlers stay real.
        """
        h, t = self.h, self.transport
        self.timer_events = []
        for address in (0x08046DDE, 0x08046E2A, 0x08030B60, 0x08046E44):
            h.u.mem_write(address, bytes.fromhex('7047'))
            def boundary(u, pc, size, data):
                regs = (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3)
                args = tuple(u.reg_read(r) for r in regs)
                extra = int.from_bytes(u.mem_read(u.reg_read(UC_ARM_REG_SP), 4), 'little')
                self.timer_events.append((pc, args, extra))
            h.u.hook_add(UC_HOOK_CODE, boundary, begin=address, end=address)
        def native_store():
            obj = h.next_store
            h.next_store += 0x200
            h.call(0x0803FB50, obj, 4, 8)
            return obj
        # Native constructors register listeners; the older no-listener
        # synthetic store helper cannot supply their listener allocation.
        t.settings, clock_params = native_store(), native_store()
        pointer = h.call(0x0803FD26, t.settings, 2)
        h.word(pointer, 1 << 4)
        h.call(0x0803FE00, t.settings)
        h.word(t.root + 0x1C, t.settings)
        h.call(0x0803223C, t.engine, self.adapter + 8, t.settings, clock_params)
        h.call(0x0803328C, t.backend, t.engine, t.settings)
        t.source = h.read(t.engine + 0x48)
        # Runtime condition: valid external clock present (bit1) and enabled.
        # This is a fixture input, not proof of the timer's source detection.
        h.u.mem_write(t.engine + 0x54, b'\x03')
