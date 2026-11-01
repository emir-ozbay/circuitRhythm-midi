"""Native MIDI output FIFOs; physical port readiness is a controlled boundary."""
import unittest
import test_phase1_safety as base
from midi_record_test_support import MidiRecordFixture
from midi_ingress_test_support import MidiIngressFixture, TransportControlFixture
from midi_output_test_support import MidiOutputFixture
from shared_project_test_support import SharedModeFixture


class MidiOutputTransportTests(unittest.TestCase):
    setUpClass = classmethod(base.SafetyTests.setUpClass.__func__)
    setUp = base.SafetyTests.setUp
    word = base.SafetyTests.word
    read = base.SafetyTests.read
    store = base.SafetyTests.store
    call = base.SafetyTests.call

    def setup_graph(self, slots=64):
        self.midi = MidiRecordFixture(self, 0, router=0x2000C000)
        self.mode_ui = SharedModeFixture(self, ctrl=0x2000B000, view=0x2000B400, grid=0x2000B800)
        self.ingress = MidiIngressFixture(self, self.midi)
        self.transport = TransportControlFixture(self, self.midi, self.mode_ui)
        self.output = MidiOutputFixture(self, self.transport, slots=slots)

    def test_din_start_clock_stop_continue_reach_all_native_output_fifos(self):
        self.setup_graph()
        self.ingress.din([0xFA, 0xF8, 0xF8, 0xFC, 0xFB])
        for port in range(3):
            self.assertEqual(self.output.pending(port), 5)
            self.assertEqual([self.output.pop(port) for _ in range(5)],
                             [bytes([status, 0, 0]) for status in (0xFA, 0xF8, 0xF8, 0xFC, 0xFB)])
            self.assertIsNone(self.output.pop(port))

    def test_output_notes_clock_and_queued_bytes_survive_mode_toggle(self):
        self.setup_graph()
        self.output.note(7, 127)
        self.ingress.din([0xF8])
        self.output.note(7, 127, velocity=0, on=False)
        self.mode_ui.press()
        self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR+4, 1), b'\x01')
        for port in range(3):
            self.assertEqual([self.output.pop(port) for _ in range(3)],
                             [bytes([0x97, 127, 96]), bytes([0xF8, 0, 0]), bytes([0x87, 127, 0])])
        self.output.note(0, 0)
        self.output.note(0, 0, velocity=0, on=False)
        for port in range(3):
            self.assertEqual([self.output.pop(port) for _ in range(2)],
                             [bytes([0x90, 0, 96]), bytes([0x80, 0, 0])])

    def test_native_clock_backend_first_pulse_and_stop_reach_output_fifos(self):
        self.setup_graph()
        self.output.native_clock_backend()
        self.ingress.din([0xFA, 0xF8, 0xF8, 0xFC])
        self.assertEqual(self.transport.running(), 0)
        self.assertEqual(self.u.mem_read(self.transport.backend+0x10, 2), b'\x00\x00')
        for port in range(3):
            self.assertEqual([self.output.pop(port) for _ in range(4)],
                             [bytes([status, 0, 0]) for status in (0xFA, 0xF8, 0xF8, 0xFC)])
        self.assertTrue(self.output.timer_events)

    def test_real_output_worker_preserves_note_clock_off_packet_order(self):
        for mode in (0, 1):
            with self.subTest(mode=mode):
                self.setUp()
                self.setup_graph()
                self.output.native_clock_backend()
                self.u.mem_write(base.seq.SEQ_STATE_ADDR+4, bytes([mode]))
                self.ingress.usb([0x0F, 0xFA, 0, 0])
                self.output.note(3, 60)
                self.ingress.usb([0x0F, 0xF8, 0, 0])
                self.output.note(3, 60, velocity=0, on=False)
                self.ingress.usb([0x0F, 0xFC, 0, 0])
                expected = [bytes([0x0F, 0xFA, 0, 0]), bytes([9, 0x93, 60, 96]),
                            bytes([0x0F, 0xF8, 0, 0]), bytes([8, 0x83, 60, 0]),
                            bytes([0x0F, 0xFC, 0, 0])]
                for port in range(3):
                    self.output.drain(port)
                    self.assertEqual(self.output.delivered[port], expected)
                    self.assertEqual(self.output.pending(port), 0)
                    self.output.drain(port)
                    self.assertEqual(self.output.delivered[port], expected)

    def test_driver_backpressure_leaves_fifo_intact_until_worker_can_drain(self):
        self.setup_graph(slots=4)
        for driver in self.output.drivers:
            self.u.mem_write(driver+5, b'\x01')  # physical recipient full boundary
        self.output.note(0, 48)
        self.output.note(0, 48, velocity=0, on=False)
        for port, driver in enumerate(self.output.drivers):
            self.output.drain(port)
            self.assertEqual(self.output.pending(port), 2)
            self.assertEqual(self.output.delivered[port], [])
            self.u.mem_write(driver+5, b'\x00')
            self.output.drain(port)
            self.assertEqual(self.output.pending(port), 0)
            self.assertEqual(self.output.delivered[port],
                             [bytes([9, 0x90, 48, 96]), bytes([8, 0x80, 48, 0])])

    def test_inherited_full_stock_capacity_fifo_drops_off_without_overwrite(self):
        self.setup_graph()  # boot297A8 requests64 slots, not a reduced test queue
        stock = base.load_image()
        core_image = bytearray(self.image)
        hook = base.seq.HOOK_MIDI_TX_OVERFLOW-0x08010000
        # Explicitly account for the new fault observer, retaining byte checks
        # on the complete remaining output implementation. The live test below
        # keeps that observer enabled; it does not suppress the lost-Off probe.
        self.assertEqual(core_image[hook:hook+4],
                         base.seq.bl(base.seq.HOOK_MIDI_TX_OVERFLOW, self.labels['c_midi_tx_overflow']))
        core_image[hook:hook+4] = base.seq.EXPECTED_MIDI_TX_OVERFLOW
        for begin, end in ((0x08031F08, 0x0803223C), (0x0804016C, 0x0804042C),
                           (0x0802986A, 0x080298B4), (0x080468FA, 0x0804691A)):
            span = slice(begin-0x08010000, end-0x08010000)
            self.assertEqual(core_image[span], stock[span])
        self.output.note(0, 48)
        for port in range(3):
            self.output.drain(port)
        for _ in range(64):
            self.ingress.din([0xF8])
        snapshots = []
        for port in self.output.ports:
            fifo = self.read(port+4)
            snapshots.append((fifo, bytes(self.u.mem_read(fifo, 12)),
                              self.read(fifo), bytes(self.u.mem_read(self.read(fifo), 193))))
        diagnostics = []
        #23690 is a stock no-op (push r1-r3; add sp,12; bx lr), not a fatal
        # assertion. Observe it without modifying code or stopping execution.
        self.u.hook_add(base.UC_HOOK_CODE,
                        lambda u,a,s,d: diagnostics.append(u.reg_read(base.UC_ARM_REG_LR)),
                        begin=0x08023690, end=0x08023690)
        self.output.note(0, 48, velocity=0, on=False)
        self.assertEqual(diagnostics, [0x0804022D, 0x080298A5]*3)
        for fifo, header, buffer, content in snapshots:
            self.assertEqual(bytes(self.u.mem_read(fifo, 12)), header)
            self.assertEqual(bytes(self.u.mem_read(buffer, 193)), content)
        for port in range(3):
            self.assertEqual(self.output.pending(port), 64)
            self.output.drain(port)
            self.assertEqual(self.output.delivered[port],
                             [bytes([9, 0x90, 48, 96])] + [bytes([0x0F, 0xF8, 0, 0])]*64)
            self.assertNotIn(bytes([8, 0x80, 48, 0]), self.output.delivered[port])
            self.assertEqual(self.output.pending(port), 0)

    def test_native_adapter_all_tracks_and_ring_wrap_in_both_modes(self):
        self.setup_graph(slots=2)
        for mode in (0, 1):
            self.u.mem_write(base.seq.SEQ_STATE_ADDR+4, bytes([mode]))
            for track in range(8):
                for note in (0, 60, 127):
                    self.output.note(track, note)
                    self.output.note(track, note, velocity=0, on=False)
                    for port in range(3):
                        self.output.drain(port)
                        self.assertEqual(self.output.pending(port), 0)
                        self.assertEqual(self.output.delivered[port][-2:],
                                         [bytes([9, 0x90+track, note, 96]),
                                          bytes([8, 0x80+track, note, 0])])

    def test_native_stop_and_router_poll_keep_held_guard_until_matching_off(self):
        self.setup_graph()
        self.output.native_clock_backend()
        self.ingress.din([0x97, 48, 96, 0xFA, 0xF8, 0xFC])
        self.assertEqual(self.transport.running(), 0)
        self.output.poll()
        for port in range(3):
            self.assertEqual(self.output.pending(port), 0)
            self.assertEqual(self.output.delivered[port],
                             [bytes([0x0F, status, 0, 0]) for status in (0xFA, 0xF8, 0xFC)])
        self.mode_ui.press()
        self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR+4, 1), b'\x00')
        self.mode_ui.release()
        self.ingress.din([0x87, 48, 0])
        self.mode_ui.press()
        self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR+4, 1), b'\x01')


if __name__ == '__main__':
    unittest.main()
