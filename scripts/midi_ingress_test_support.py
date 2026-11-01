"""Real stock byte parser, dispatch registry and USB software receive FIFO.

All objects live in synthetic RAM. No UART/USB peripheral, DMA, ISR, task wakeup
or host device is accessed. USB tests start at already received packet bytes.
"""
import struct
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1


class MidiIngressFixture:
    def __init__(self, h, midi):
        self.h, self.midi = h, midi
        self.parser = 0x20002000
        # Execute the real constructor, including allocator,16-byte short ring,
        # both message descriptors and SysEx windows. No timer or driver stub.
        h.call(0x0804042C, self.parser)
        self.short_desc = h.read(self.parser + 8)
        self.short_fifo = h.read(self.parser + 0x0C)
        assert h.u.mem_read(self.short_fifo + 4, 2) == bytes([16, 0])
        assert h.u.mem_read(self.short_fifo + 0x0A, 1) == bytes([3])

        # Registry24B68 synchronously calls52274(port, bytes, decoder).
        registry = 0x200008E0
        h.u.mem_write(registry + 4, b'\x01')
        h.word(registry + 8, 0x08052275)
        h.word(registry + 0x14, midi.decoder)
        h.u.mem_write(midi.decoder + 0x1C, b'\x09')

        self.usb_service = 0x20006DC0
        self.usb_port, ports, parsers = 0x20002500, 0x20002400, 0x20002480
        self.usb_desc, self.usb_data = 0x20002600, 0x20002700
        self.usb_fifo, usb_ring = 0x20002800, 0x20002900
        self.enqueue_desc, self.enqueue_data = 0x20002A00, 0x20002B00
        h.word(ports, self.usb_port)
        h.word(ports + 4, 0)
        h.word(parsers, self.parser)
        for off, ptr in ((4, ports), (0x0C, parsers), (0x10, self.usb_desc)):
            h.word(self.usb_service + off, ptr)
        h.word(self.usb_port + 0x18, self.usb_fifo)
        # Already armed: the empty-queue path must not call USB rearm269AC.
        h.u.mem_write(self.usb_port + 0x1C, b'\x01')
        self.descriptor(self.usb_desc, self.usb_data, 64)
        # USB driver's ring capacity is a synthetic boundary choice, not a
        # claim about the boot-created driver allocation.
        self.ring(self.usb_fifo, usb_ring, 192, 64)

    def descriptor(self, address, data, size):
        self.h.u.mem_write(address, struct.pack('<H2xI', size, data))

    def ring(self, address, data, capacity, item_size):
        self.h.u.mem_write(address, struct.pack('<I4H', data, capacity, 0, 0, item_size))

    def din(self, data, port=1):
        for value in data:
            self.h.call(0x08029C1A, self.parser, port, value)

    def usb(self, packets):
        assert len(packets) % 4 == 0 and 0 < len(packets) <= 64
        self.h.u.mem_write(self.enqueue_data, bytes(packets))
        self.descriptor(self.enqueue_desc, self.enqueue_data, len(packets))
        assert self.h.call(0x08025AEC, self.usb_fifo, self.enqueue_desc) == 1
        self.h.call(0x08029AC8)


class TransportControlFixture:
    """Actual external Start/Continue/Stop and pattern reset/store writes.

Synthetic clock controller fields follow33578/boot294CC. Only the downstream
sequencer engine and clock-source driver are boundary stubs. Store listeners
are empty; this does not emulate scheduler, timer IRQ or output queues.
"""
    def __init__(self, h, midi, mode_ui):
        self.h, self.midi = h, midi
        self.root, self.action = 0x20001000, 0x20001200
        self.engine, self.backend, self.source_driver = 0x20001240, 0x20001300, 0x20001400
        self.pattern_reader = 0x20001800
        self.events = []
        h.word(self.root + 0x0C, 0x08066B80)
        h.call(0x08047004, self.action, self.root + 0x0C, 0)
        h.word(midi.receiver + 0x0C, 0x08066654)
        h.word(midi.receiver + 0x10, 0x08066670)
        h.word(midi.receiver + 0x30, self.action)
        for off, ptr in ((0x10, self.engine), (0x14, self.backend),
                         (0x18, self.source_driver), (0x20, self.pattern_reader)):
            h.word(self.root + off, ptr)

        # The full8-track raw span10000..39484 cannot overlap the MIDI router.
        assert not 0x20010000 <= midi.router < 0x20039484
        h.u.mem_write(0x20010000, bytes(0x29484))
        for track in range(8):
            for pattern in range(8):
                # Reader4709E: low byte=end, high byte=start; rate/direction0.
                h.u.mem_write(0x20010000 + track*0x5140 + pattern*0xA28 + 0x3E4,
                              bytes([31, 0, 0, 0]))
        h.word(self.pattern_reader, 0x20010000)

        # Keep all transport store buffers above raw data and below test stack.
        h.next_store = 0x2003A000
        self.settings = h.store(struct.pack('<3I', 0, 0, 1 << 4))
        self.transport = h.store(bytes(16))
        self.source = h.store(struct.pack('<I', 1))
        h.word(self.engine + 0x48, self.source)
        h.word(self.engine, 0x08068EFC)  # final3223C ctor table: Clock32BB6
        h.word(self.engine + 0x0C, self.settings)
        h.word(midi.receiver + 0x34, self.engine)
        self.clock_sink, clock_vt = 0x20001600, 0x20001640
        h.word(self.engine + 8, self.clock_sink)
        h.word(self.clock_sink, clock_vt)
        h.word(clock_vt, 0x0800EA21)
        h.u.mem_write(0x0800EA20, bytes.fromhex('7047'))
        def clock_boundary(u, address, size, data):
            self.events.append(('clock', 'tick', u.reg_read(UC_ARM_REG_R0),
                                u.reg_read(UC_ARM_REG_R1)))
        h.u.hook_add(UC_HOOK_CODE, clock_boundary, begin=0x0800EA20, end=0x0800EA20)
        h.word(self.root + 0x1C, self.settings)
        h.word(self.root + 0x28, self.transport)
        h.word(mode_ui.ctrl + 0x18, self.transport)
        mode_ui.transport = self.transport
        h.word(self.root + 0x24, h.store(bytes(64)))
        h.word(self.root + 0x2C, h.store(bytes(4)))
        self.positions, self.track_settings = [], []
        for track in range(8):
            pos = h.store(struct.pack('<3I', 0, 17, 100))
            setting = h.store(bytes(12))
            self.positions.append(pos)
            self.track_settings.append(setting)
            h.word(self.root + 0x30 + 4*track, pos)
            h.word(self.root + 0x50 + 4*track, setting)
        self.tick = h.store(struct.pack('<I', 1234))
        h.word(self.root + 0x90, self.tick)
        h.word(self.root + 0x9C, h.store(bytes(64)))
        h.word(self.root + 0xA0, h.store(bytes(8)))
        ready = h.store(struct.pack('<I', 1))
        h.u.mem_write(self.root + 0xE4, bytes(h.u.mem_read(ready, 24)))
        assert h.next_store <= 0x2003E000

        for group, obj, vtable in (('engine', self.backend, 0x20001500),
                                    ('driver', self.source_driver, 0x20001540)):
            h.word(obj, vtable)
            for n, method in enumerate(('reset', 'continue', 'stop')):
                address = 0x0800EA00 + (0 if group == 'engine' else 0x10) + 4*n
                h.word(vtable + 4*n, address | 1)
                h.u.mem_write(address, bytes.fromhex('7047'))
                def boundary(u, address, size, data, group=group, method=method):
                    self.events.append((group, method, u.reg_read(UC_ARM_REG_R0),
                                        u.reg_read(UC_ARM_REG_R1)))
                h.u.hook_add(UC_HOOK_CODE, boundary, begin=address, end=address)

    def running(self):
        pointer = self.h.call(0x0803FC58, self.transport, 0)
        return self.h.u.mem_read(pointer, 1)[0]
