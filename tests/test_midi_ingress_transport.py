"""Stock ingress parser/FIFO to receiver ownership; no physical peripheral."""
import unittest
import test_phase1_safety as base
from midi_record_test_support import MidiRecordFixture
from midi_ingress_test_support import MidiIngressFixture, TransportControlFixture
from shared_project_test_support import SharedModeFixture


class MidiIngressTransportTests(unittest.TestCase):
    setUpClass = classmethod(base.SafetyTests.setUpClass.__func__)
    setUp = base.SafetyTests.setUp
    word = base.SafetyTests.word
    read = base.SafetyTests.read
    store = base.SafetyTests.store
    call = base.SafetyTests.call

    def setup_graph(self):
        self.midi = MidiRecordFixture(self, 0, router=0x2000C000)
        self.mode_ui = SharedModeFixture(self, ctrl=0x2000B000, view=0x2000B400, grid=0x2000B800)
        self.ingress = MidiIngressFixture(self, self.midi)

    def idle(self):
        return self.call(self.labels['c_midi_inputs_idle'])

    def test_din_byte_parser_dispatches_note_and_running_status_off(self):
        self.setup_graph()
        self.ingress.din([0x97, 48])
        self.assertEqual(self.idle(), 1)  # incomplete message has no owner
        self.ingress.din([96])
        self.assertEqual(self.idle(), 0)
        self.mode_ui.press()
        self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR+4, 1), b'\x00')
        self.mode_ui.release()
        self.ingress.din([48, 0])  # running status97, velocity zero -> Off
        self.assertEqual(self.idle(), 1)
        self.mode_ui.press()
        self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR+4, 1), b'\x01')

    def test_usb_software_packet_fifo_dispatches_note_and_matching_off(self):
        self.setup_graph()
        self.ingress.usb([0x09, 0x97, 127, 96])
        self.assertEqual(self.idle(), 0)
        self.mode_ui.press()
        self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR+4, 1), b'\x00')
        self.mode_ui.release()
        self.ingress.usb([0x08, 0x87, 127, 0])
        self.assertEqual(self.idle(), 1)
        self.mode_ui.press()
        self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR+4, 1), b'\x01')

    def test_din_realtime_runs_real_transport_store_and_start_position_reset(self):
        self.setup_graph()
        transport = TransportControlFixture(self, self.midi, self.mode_ui)
        self.ingress.din([0xFA])
        self.assertEqual(transport.running(), 1)
        self.assertEqual([(e[0], e[1]) for e in transport.events],
                         [('driver', 'reset'), ('engine', 'reset'), ('engine', 'continue')])
        for track, store in enumerate(transport.track_settings):
            pointer = self.call(0x0803FC58, store, 0)
            self.assertEqual(bytes(self.u.mem_read(pointer, 3)), bytes([31, 0, 0]), track)
        for track, store in enumerate(transport.positions):
            pointer = self.call(0x0803FC58, store, 0)
            self.assertEqual(bytes(self.u.mem_read(pointer, 12)), bytes(12), track)
        pointer = self.call(0x0803FC58, transport.tick, 0)
        self.assertEqual(self.read(pointer), 0)
        self.mode_ui.press()
        self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR+4, 1), b'\x00')
        self.mode_ui.release()
        self.ingress.din([0xFC])
        self.assertEqual(transport.running(), 0)
        self.assertEqual([(e[0], e[1]) for e in transport.events[-2:]],
                         [('engine', 'stop'), ('driver', 'stop')])
        self.mode_ui.press()
        self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR+4, 1), b'\x01')
        self.mode_ui.release()
        self.ingress.din([0xFB])
        self.assertEqual(transport.running(), 1)
        self.ingress.din([0xFC])
        self.assertEqual(transport.running(), 0)

    def test_running_status_survives_interleaved_real_clock_and_stop(self):
        for mode in (0, 1):
            with self.subTest(mode=mode):
                self.setUp()
                self.setup_graph()
                transport = TransportControlFixture(self, self.midi, self.mode_ui)
                self.u.mem_write(base.seq.SEQ_STATE_ADDR+4, bytes([mode]))
                self.ingress.din([0xFA, 0x97, 48, 0xF8])
                self.assertEqual(self.read(transport.engine+0x5C), 1)
                self.assertEqual(self.idle(), 1)  # final velocity not received
                self.ingress.din([96, 49, 0xF8, 96, 0xFC])
                self.assertEqual(self.read(transport.engine+0x5C), 2)
                self.assertEqual(transport.running(), 0)
                self.assertEqual(len([e for e in transport.events if e[:2] == ('clock', 'tick')]), 2)
                self.assertEqual(self.idle(), 0)  # Stop is not a Note Off
                self.mode_ui.press()
                self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR+4, 1), bytes([mode]))
                self.mode_ui.release()
                self.ingress.din([48, 0])
                self.assertEqual(self.idle(), 0)  # other note still held
                self.ingress.din([49, 0])
                self.assertEqual(self.idle(), 1)
                self.mode_ui.press()
                self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR+4, 1), bytes([1-mode]))

    def test_usb_realtime_runs_transport_and_clock_in_both_modes(self):
        for mode in (0, 1):
            with self.subTest(mode=mode):
                self.setUp()
                self.setup_graph()
                transport = TransportControlFixture(self, self.midi, self.mode_ui)
                self.u.mem_write(base.seq.SEQ_STATE_ADDR+4, bytes([mode]))
                self.ingress.usb([0x0F, 0xFA, 0, 0, 0x0F, 0xF8, 0, 0])
                self.assertEqual(transport.running(), 1)
                self.assertEqual(self.read(transport.engine+0x5C), 1)
                self.mode_ui.press()
                self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR+4, 1), bytes([mode]))
                self.mode_ui.release()
                self.ingress.usb([0x0F, 0xFC, 0, 0])
                self.assertEqual(transport.running(), 0)
                self.mode_ui.press()
                self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR+4, 1), bytes([1-mode]))
                self.mode_ui.release()
                self.ingress.usb([0x0F, 0xFB, 0, 0, 0x0F, 0xF8, 0, 0])
                self.assertEqual(transport.running(), 1)
                self.assertEqual(self.read(transport.engine+0x5C), 2)

    def test_external_transport_disabled_preserves_stock_ignore_behavior(self):
        self.setup_graph()
        transport = TransportControlFixture(self, self.midi, self.mode_ui)
        for bank in (0x40, 0xC0):
            self.word(transport.settings+bank+8, 0)
        self.ingress.din([0xFA, 0xFB, 0xF8, 0xFC])
        self.assertEqual(transport.running(), 0)
        self.assertEqual(self.read(transport.engine+0x5C), 0)
        self.assertEqual(transport.events, [])
        self.mode_ui.press()
        self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR+4, 1), b'\x01')

    def test_usb_fifo_wrap_and_multiple_messages_keep_matching_ownership(self):
        self.setup_graph()
        # Repeated real enqueue/dequeue wraps the192-byte USB and16-byte parser
        # rings. No manual read/write-index reset or mask clearing between calls.
        for note in range(128):
            self.ingress.usb([0x09, 0x97, note, 96])
            self.assertEqual(self.idle(), 0, note)
            self.ingress.usb([0x08, 0x87, note, 0])
            self.assertEqual(self.idle(), 1, note)


if __name__ == '__main__':
    unittest.main()
