"""Unified packaged-SYX USB MIDI TX/RX + Composite MSC + Suspend/Wake/Reset fixture.

Runs on the exact packaged candidate image (build/circuitrhythm-5706-phase1-recovery.syx)
without any prototype code overlays. Exercises in one shared lifecycle:
- Composite class list at *0x20006F20 (MIDI 0x080676F4 + MSC 0x08067730)
- Native USB MIDI TX (IN1 0x81) + both DIN UARTs with 64-note Off/Stop closure debt
- Native USB MIDI RX (OUT1 0x01 -> 080531CC -> 080526C8 -> 08026988 -> 0802691E -> 080269F0)
- Native USB MSC BOT/SCSI (OUT2 0x02 CBW -> 08027624 -> 0802F04A -> 080458D0 -> IN2 0x82 data + CSW)
- Native USB Suspend (GINTSTS bit11 -> 0802C7E6 -> 0804279E, PCGCCTL bit0, ctrl+0x274==4)
  and Wakeup (GINTSTS bit31 -> 0802C9F8 + 0802C802 -> 080427AE, ctrl+0x274==3)
- Mid-transfer USBRST / deconfigure / EP0 reconfigure with deferred composite init (08040B5A)
"""
import struct
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1
import midi_accepted_tx_patch as guard
from integrated_usb_irq_test_support import IntegratedUsbIrqFixture


class UnifiedUsbLifecycleFixture(IntegratedUsbIrqFixture):
    def __init__(self, h, out):
        super().__init__(h, out)
        # Map FIFO2 (0x40043000) for MSC IN2 (0x82) CPU FIFO writes and 0x40023000 for SCSI buffers.
        h.u.mem_map(guard.USB_BASE + 0x3000, 0x1000)
        h.u.mem_map(0x40023000, 0x3000)
        self.allowed_flushes.add(0xA0)  # TX FIFO 2 flush during MSC IN2 open/close
        for reg, val in ((0x18, (1 << 3) | (1 << 4) | (1 << 11) | (1 << 12) | (1 << 13) | (1 << 18) | (1 << 19) | (1 << 31)),
                         (0x808, 0), (0x81C, 0x10003 | (1 << 2) | (1 << 17) | (1 << 18)), (0x834, 0xB | (1 << 2)),
                         (0x940, 0x8000), (0x958, 64), (0xB20, 0x8000), (0xB40, 0x8000), (0xE00, 0)):
            self.regs[reg] = val
            h.word(guard.USB_BASE + reg, val)
        for off in (0x3C, 0x58, 0x74, 0x1FC, 0x218, 0x234):
            h.word(self.handle + off + 8, 64)
            h.u.mem_write(self.handle + off + 3, b'\x02')
        h.word(self.handle + 0x20, 0)  # low_power_enable = 0

        # Place MIDI RX ring FIFO and staging buffers at 0x20006300..0x20006600 so
        # 0x20006100 and 0x20006124 remain dedicated to stock MSC ROM endpoint tables.
        self.reset.fifo = 0x20006300
        self.reset.buffer = 0x20006400
        self.rx_stage_buf = 0x20006580
        self.rx_desc = 0x200065D0
        self.rx_pop_buf = 0x200065E0
        h.word(self.reset.port + 0x14, self.rx_stage_buf)
        h.u.mem_write(self.reset.port + 0x0C, b'\x00')
        h.word(self.reset.port + 0x18, self.reset.fifo)
        h.u.mem_write(self.reset.port + 0x1C, b'\x01\x01')
        self.enable_midi_rx_ring()

        # Construct MSC endpoints 0x82 (0x20006100) and 0x02 (0x20006124) via stock 08026828
        # and wire composite class list at self.root (MIDI at root+8, MSC at root+12).
        self.msc = 0x2000A180
        self.storage = 0x2000A300
        self.msc_tx_port = 0x20006100
        self.msc_rx_port = 0x20006124
        h.word(self.msc, 0x08067730)
        h.word(self.msc + 4, 0x08069784)  # ROM array -> [0x20006100, 0]
        h.word(self.msc + 8, 0x0806978C)  # ROM array -> [0x20006124, 0]
        for off, val in ((0, 2), (4, self.native.usb_controller), (8, self.wrapper), (12, self.msc), (16, 0)):
            h.word(self.root + off, val)
        for address, endpoint in ((self.msc_tx_port, 0x82), (self.msc_rx_port, 2)):
            h.word(0x20040000, 0)
            h.word(0x20040004, 64)
            h.call(0x08026828, address, self.native.usb_controller, endpoint, 2)
        h.word(0x20006E68, self.msc_tx_port)
        h.word(0x20006E6C, self.msc_rx_port)
        h.u.mem_write(0x20003F8C, b'\x01\x01\x00')
        # Stock storage ops table with ROM ret0 (080427D3) for Init/IsReady and ROM Inquiry data (08068BC0).
        ops = (0x080427D3, 0x080650D5, 0x080427D3, 0x080650E9, 0x080427D3, 0x08065195, 0x08065251, 0x08065255, 0x08068BC0)
        h.u.mem_write(self.storage, struct.pack('<9I', *ops))
        h.word(0x200038AC, self.storage)

        self.msc_tx_fifo = []
        self.msc_in_flight = None
        self.msc_completed = []
        self.msc_cancelled = []
        self.clock_events = []
        self.native.foreign_usb_submit = self.submit_msc

        def fifo2_write(u, access, address, size, value, data):
            self.msc_tx_fifo.append(value.to_bytes(4, 'little'))
        h.u.hook_add(UC_HOOK_MEM_WRITE, fifo2_write, begin=guard.USB_BASE + 0x3000, end=guard.USB_BASE + 0x3003)

        def pcgcctl_write(u, access, address, size, value, data):
            self.regs[0xE00] = value
            self.clock_events.append(('stop' if value & 1 else 'start', value))
        h.u.hook_add(UC_HOOK_MEM_WRITE, pcgcctl_write, begin=guard.USB_BASE + 0xE00, end=guard.USB_BASE + 0xE03)

        def grstctl_write(u, access, address, size, value, data):
            if value & 0x20 and ((value >> 6) & 31) in (2, 16):
                self.msc_tx_fifo.clear()
                if self.msc_in_flight is not None:
                    self.msc_cancelled.append(self.msc_in_flight[2])
                    self.msc_in_flight = None
        h.u.hook_add(UC_HOOK_MEM_WRITE, grstctl_write, begin=guard.USB_BASE + guard.GRSTCTL, end=guard.USB_BASE + guard.GRSTCTL + 3)

        def msc_done(u, p, n, d):
            if u.reg_read(UC_ARM_REG_R0) != self.msc_tx_port or self.msc_in_flight is None:
                return
            pointer, length, expected = self.msc_in_flight
            assert b''.join(self.msc_tx_fifo)[:length] == expected
            self.msc_completed.append(expected)
            self.msc_in_flight = None
            self.msc_tx_fifo.clear()
        h.u.hook_add(UC_HOOK_CODE, msc_done, begin=0x080268DE, end=0x080268DE)

        for pc in (0x0802C798, 0x08042614, 0x0802AB42, 0x08040C46, 0x080526C8, 0x08026988,
                   0x0802691E, 0x080269AC, 0x080269F0, 0x080661DC, 0x080661EE, 0x0802F00C,
                   0x0802EFC8, 0x08027624, 0x0802F04A, 0x080458D0, 0x0802F014, 0x0802F112,
                   0x0802C7E6, 0x0804279E, 0x0802C802, 0x080427AE, 0x0802C9F8):
            h.u.hook_add(UC_HOOK_CODE, lambda u, p, n, d: self.irq_visits.append(p), begin=pc, end=pc)
        h.u.ctl_remove_cache(0x08010000, 0x08080000)

    def enable_midi_rx_ring(self):
        self.h.u.mem_write(self.reset.fifo, struct.pack('<I4H', self.reset.buffer, 260, 0, 0, 64))
        self.h.u.mem_write(self.reset.buffer, b'\xA5' * 260)
        self.h.u.mem_write(self.reset.port + 0x0C, b'\x00')

    def arm_midi_rx(self):
        return self.h.call(0x08029AB0)

    def arm_msc_bot(self):
        self.h.call(0x0802F00C)
        return self.h.call(0x0802EFC8, self.native.usb_controller)

    def submit_msc(self, endpoint, pointer, length):
        assert endpoint == 0x82 and self.msc_in_flight is None
        self.msc_in_flight = (pointer, length, bytes(self.h.u.mem_read(pointer, length)))
        self.msc_tx_fifo.clear()
        self.regs[0x940] |= guard.EPENA

    def rx_data(self, packet, endpoint=1):
        assert 0 < len(packet) <= 64
        self.events.append((2 << 17) | (len(packet) << 4) | endpoint)
        padded = packet + bytes(-len(packet) % 4)
        self.fifo_words.extend(int.from_bytes(padded[n:n + 4], 'little') for n in range(0, len(padded), 4))

    def rx_complete(self, endpoint=1):
        self.flags[0xB08 + endpoint * 0x20] |= 1
        reg = 0xB00 + endpoint * 0x20
        self.regs[reg] = self.regs.get(reg, 0) & ~guard.EPENA

    def send_usb_midi_rx(self, packets):
        assert 0 < len(packets) <= 64 and len(packets) % 4 == 0
        self.rx_data(packets, endpoint=1)
        self.run_irq()
        self.rx_complete(endpoint=1)
        return self.run_irq()

    def drain_usb_midi_rx(self):
        out = bytearray()
        while True:
            self.h.word(self.rx_desc, 64)
            self.h.word(self.rx_desc + 4, self.rx_pop_buf)
            if not self.h.call(0x080269F0, self.reset.port, self.rx_desc):
                break
            n = int.from_bytes(self.h.u.mem_read(self.rx_desc, 2), 'little')
            assert 0 < n <= 64 and n % 4 == 0
            out.extend(self.h.u.mem_read(self.rx_pop_buf, n))
        return bytes(out)

    def bus_msc(self):
        if self.msc_in_flight is not None:
            self.flags[0x948] |= 0x80
            self.run_irq()
            self.flags[0x948] &= ~0x80
            self.flags[0x948] |= 1
            self.regs[0x940] &= ~guard.EPENA
            self.run_irq()

    def msc_poll(self):
        return self.h.call(0x08027624)

    def msc_inquiry(self, tag=0x12345678):
        cbw = struct.pack('<4sIIBBB', b'USBC', tag, 36, 0x80, 0, 6) + bytes([0x12, 0, 0, 0, 36, 0]) + bytes(10)
        assert len(cbw) == 31
        before = len(self.msc_completed)
        self.rx_data(cbw, endpoint=2)
        self.rx_complete(endpoint=2)
        self.run_irq()
        self.msc_poll()
        self.bus_msc()
        self.msc_poll()
        self.bus_msc()
        self.msc_poll()
        packets = self.msc_completed[before:]
        assert len(packets) == 2 and len(packets[0]) == 36 and len(packets[1]) == 13
        sig, csw_tag, residue, status = struct.unpack('<4sIIB', packets[1])
        assert sig == b'USBS' and csw_tag == tag and residue == 0 and status == 0
        return packets[0], packets[1]

    def msc_test_unit_ready(self, tag=0x87654321):
        cbw = struct.pack('<4sIIBBB', b'USBC', tag, 0, 0x00, 0, 6) + bytes(16)
        assert len(cbw) == 31
        before = len(self.msc_completed)
        self.rx_data(cbw, endpoint=2)
        self.rx_complete(endpoint=2)
        self.run_irq()
        self.msc_poll()
        self.bus_msc()
        self.msc_poll()
        packets = self.msc_completed[before:]
        assert len(packets) == 1 and len(packets[0]) == 13
        sig, csw_tag, residue, status = struct.unpack('<4sIIB', packets[0])
        assert sig == b'USBS' and csw_tag == tag and residue == 0 and status == 0
        return packets[0]

    def suspend_irq(self):
        self.regs[0x808] = 1
        self.h.word(guard.USB_BASE + 0x808, 1)
        self.external |= 1 << 11
        return self.run_irq()

    def wakeup_irq(self):
        self.regs[0x808] = 0
        self.h.word(guard.USB_BASE + 0x808, 0)
        self.regs[0xE00] &= ~1
        self.h.word(guard.USB_BASE + 0xE00, self.regs[0xE00])
        self.external |= 1 << 31
        return self.run_irq()
