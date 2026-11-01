"""Main-loop poll order from real stock instructions; no OS/IRQ emulation."""
import unittest
import test_phase1_safety as base
from midi_record_test_support import MidiRecordFixture
from midi_ingress_test_support import MidiIngressFixture, TransportControlFixture
from midi_output_test_support import MidiOutputFixture
from midi_task_test_support import MidiTaskFixture
from shared_project_test_support import SharedModeFixture


class MidiTaskScheduleTests(unittest.TestCase):
    setUpClass = classmethod(base.SafetyTests.setUpClass.__func__)
    setUp = base.SafetyTests.setUp
    word = base.SafetyTests.word
    read = base.SafetyTests.read
    store = base.SafetyTests.store
    call = base.SafetyTests.call

    def setup_graph(self, native_backend=True):
        self.midi = MidiRecordFixture(self, 0, router=0x2000C000)
        self.ui = SharedModeFixture(self, ctrl=0x2000B000, view=0x2000B400, grid=0x2000B800)
        self.ingress = MidiIngressFixture(self, self.midi)
        self.transport = TransportControlFixture(self, self.midi, self.ui)
        self.output = MidiOutputFixture(self, self.transport)
        if native_backend:
            self.output.native_clock_backend()
        self.task = MidiTaskFixture(self, self.ingress, self.output)

    def test_stock_hook_control_reproduces_stop_loss_in_real_main_order(self):
        self.setup_graph()
        # Preserve the original counterexample by restoring only the new hook.
        self.u.mem_write(base.seq.HOOK_USB_RX_YIELD, base.seq.EXPECTED_USB_RX_YIELD)
        self.ingress.din([0xFA, 0xF8])
        self.output.poll()
        before = [len(p) for p in self.output.delivered]
        self.task.queue_usb(bytes([0x0F, 0xF8, 0, 0])*64 + bytes([0x0F, 0xFC, 0, 0]))
        self.assertEqual(self.task.usb_bytes_pending(), 270)
        self.task.step()
        self.assertEqual(self.transport.running(), 0)
        self.assertEqual(self.task.usb_bytes_pending(), 0)
        self.assertEqual([self.output.pending(n) for n in range(3)], [64]*3)
        self.task.step()
        for port in range(3):
            self.assertEqual(self.output.delivered[port][before[port]:],
                             [bytes([0x0F, 0xF8, 0, 0])]*64)
            self.assertEqual(self.output.pending(port), 0)

    def test_usb_burst_with_queue_headroom_keeps_stop_and_main_abi(self):
        self.setup_graph()
        self.ingress.din([0xFA, 0xF8])
        self.output.poll()
        before = [len(p) for p in self.output.delivered]
        self.task.queue_usb(bytes([0x0F, 0xF8, 0, 0])*63 + bytes([0x0F, 0xFC, 0, 0]))
        regs = [self.u.reg_read(r) for r in base.SAVED]
        for _ in range(4):
            self.task.step()
        self.assertEqual([self.u.reg_read(r) for r in base.SAVED], regs)
        self.assertEqual(self.transport.running(), 0)
        self.task.step()
        for port in range(3):
            self.assertEqual(self.output.delivered[port][before[port]:],
                             [bytes([0x0F, 0xF8, 0, 0])]*63 + [bytes([0x0F, 0xFC, 0, 0])])

    def test_yield_preserves_all_clock_and_stop_with_65_message_usb_burst(self):
        for mode in (0, 1):
            with self.subTest(mode=mode):
                self.setUp()
                self.setup_graph()
                self.u.mem_write(base.seq.SEQ_STATE_ADDR+4, bytes([mode]))
                self.ingress.din([0xFA, 0xF8])
                self.output.poll()
                before = [len(p) for p in self.output.delivered]
                self.task.queue_usb(bytes([0x0F, 0xF8, 0, 0])*64 + bytes([0x0F, 0xFC, 0, 0]))
                self.task.step()
                self.assertEqual(self.task.usb_bytes_pending(), 204)
                self.assertEqual(self.transport.running(), 1)  # Stop remains queued
                self.assertEqual([self.output.pending(n) for n in range(3)], [16]*3)
                for _ in range(4):
                    self.task.step()
                self.assertEqual(self.transport.running(), 0)
                self.task.step()
                for port in range(3):
                    self.assertEqual(self.output.delivered[port][before[port]:],
                                     [bytes([0x0F, 0xF8, 0, 0])]*64 + [bytes([0x0F, 0xFC, 0, 0])])

    def test_full_native_usb_rx_capacity_is_drained_without_starving_output(self):
        self.setup_graph()
        self.ingress.din([0xFA, 0xF8])
        self.output.poll()
        before = [len(p) for p in self.output.delivered]
        self.task.queue_usb(bytes([0x0F, 0xF8, 0, 0])*255 + bytes([0x0F, 0xFC, 0, 0]))
        self.assertEqual(self.task.usb_bytes_pending(), 1056)
        for _ in range(16):
            self.task.step()
            self.assertLessEqual(max(self.output.pending(n) for n in range(3)), 16)
        self.task.step()
        self.assertEqual(self.task.usb_bytes_pending(), 0)
        self.assertEqual(self.transport.running(), 0)
        for port in range(3):
            self.assertEqual(self.output.delivered[port][before[port]:],
                             [bytes([0x0F, 0xF8, 0, 0])]*255 + [bytes([0x0F, 0xFC, 0, 0])])

    def test_yield_branch_preserves_registers_stack_flags_and_primask(self):
        registers = base.REGS + base.SAVED + [base.UC_ARM_REG_R12,
                                             base.UC_ARM_REG_SP, base.UC_ARM_REG_LR]
        for cursor in (0, 60, 64, 68):
            for mask in (0, 1):
                with self.subTest(cursor=cursor, primask=mask):
                    results = []
                    for stock_entry in (True, False):
                        self.setUp()
                        if stock_entry:
                            self.u.mem_write(base.seq.HOOK_USB_RX_YIELD, base.seq.EXPECTED_USB_RX_YIELD)
                        descriptor = 0x20002600
                        self.word(descriptor+4, 0x20002700)
                        self.u.reg_write(base.UC_ARM_REG_R5, cursor)
                        self.u.reg_write(base.UC_ARM_REG_PRIMASK, mask)
                        self.u.reg_write(base.UC_ARM_REG_APSR, 0x10000000)
                        end = (0x08029B04 if stock_entry else 0x08029AF2) if cursor >= 64 else 0x08029B66
                        writes = []
                        self.u.hook_add(base.UC_HOOK_MEM_WRITE,
                                        lambda u,k,a,n,v,d: writes.append((a,n)))
                        self.call(0x08029B60, descriptor, 64, 0xA1A1A1A1, 0xB2B2B2B2, end=end)
                        self.assertEqual(writes, [])
                        self.assertEqual(self.u.reg_read(base.UC_ARM_REG_PRIMASK), mask)
                        results.append(([self.u.reg_read(r) for r in registers],
                                        self.u.reg_read(base.UC_ARM_REG_APSR)))
                    self.assertEqual(results[1], results[0])

    def test_din_task_consumes_one_byte_per_port_per_main_pass(self):
        self.setup_graph(native_backend=False)
        driver, ring_data, parser = 0x20003100, 0x20003200, 0x20003300
        self.call(0x0804042C, parser)
        self.word(self.task.din_ports, driver)
        self.word(self.task.din_ports+4, 0)
        self.word(self.read(self.ingress.usb_service+0x0C)+4, parser)
        self.u.mem_write(self.ingress.usb_service+1, b'\x01')
        self.ingress.ring(driver+0x18, ring_data, 65, 1)
        source = 0x20003400
        self.u.mem_write(source, bytes([0xF8])*64)
        self.assertEqual(self.call(0x0802A404, driver+0x18, source, 64), 64)
        for remaining in range(63, -1, -1):
            self.task.step()
            self.assertEqual(self.call(0x0802A37E, driver+0x18), remaining)
            self.assertEqual([self.output.pending(n) for n in range(3)], [1]*3)
        self.task.step()
        for port in range(3):
            self.assertEqual(self.output.delivered[port], [bytes([0x0F, 0xF8, 0, 0])]*64)

    def test_sustained_driver_full_still_exposes_unresolved_stop_loss(self):
        self.setup_graph()
        self.ingress.din([0xFA, 0xF8])
        self.output.poll()
        before = [len(p) for p in self.output.delivered]
        for driver in self.output.drivers:
            self.u.mem_write(driver+5, b'\x01')
        self.task.queue_usb(bytes([0x0F, 0xF8, 0, 0])*64 + bytes([0x0F, 0xFC, 0, 0]))
        for _ in range(5):
            self.task.step()
        self.assertEqual(self.transport.running(), 0)
        for driver in self.output.drivers:
            self.u.mem_write(driver+5, b'\x00')
        self.task.step()
        for port in range(3):
            self.assertEqual(self.output.delivered[port][before[port]:],
                             [bytes([0x0F, 0xF8, 0, 0])]*64)

    def test_sysex_parser_state_and_following_notes_survive_usb_yield(self):
        self.setup_graph()
        received = []
        target = 0x0800EC00
        self.u.mem_write(target, bytes.fromhex('7047'))  # final SysEx consumer only
        self.u.mem_write(0x20000904, b'\x01')
        self.word(0x20000908, target | 1)
        self.word(0x20000914, 0x20003600)
        def sysex_consumer(u, a, s, d):
            descriptor = u.reg_read(base.UC_ARM_REG_R1)
            payload, length = self.read(descriptor), self.read(descriptor+4)
            received.append(bytes(u.mem_read(payload, length)))
        self.u.hook_add(base.UC_HOOK_CODE, sysex_consumer, begin=target, end=target)
        message = bytes([0xF0]) + bytes(range(1, 95)) + bytes([0xF7])
        frames = b''.join(bytes([7 if n == 93 else 4]) + message[n:n+3]
                          for n in range(0, len(message), 3))
        self.task.queue_usb(frames)
        self.task.step()
        self.assertEqual(received, [])
        self.assertEqual(self.task.usb_bytes_pending(), 66)
        self.task.step()
        self.assertEqual(received, [message])
        self.task.queue_usb(bytes([9, 0x97, 60, 96, 8, 0x87, 60, 0]))
        self.task.step()
        self.assertEqual(received, [message])
        self.assertEqual(bytes(self.u.mem_read(self.midi.receiver+0x74, 160)), bytes(160))
        self.assertEqual(self.call(self.labels['c_midi_inputs_idle']), 1)


if __name__ == '__main__':
    unittest.main()
