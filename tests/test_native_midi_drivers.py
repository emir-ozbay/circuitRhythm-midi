"""Native formatting/availability; physical submit/IRQ/DMA remain boundaries."""
import unittest
import test_phase1_safety as base
import test_midi_output_transport as output_tests
from native_midi_driver_test_support import NativeMidiDriverFixture


class NativeMidiDriverTests(unittest.TestCase):
    setUpClass = classmethod(base.SafetyTests.setUpClass.__func__)
    setUp = base.SafetyTests.setUp
    word = base.SafetyTests.word
    read = base.SafetyTests.read
    store = base.SafetyTests.store
    call = base.SafetyTests.call
    setup_graph = output_tests.MidiOutputTransportTests.setup_graph

    def test_native_usb_frames_and_din_running_status_keep_clock_and_off(self):
        self.setup_graph()
        native = NativeMidiDriverFixture(self, self.output)
        self.output.note(0, 60)
        self.output.note(0, 61)
        self.ingress.din([0xF8])
        self.output.note(0, 60, velocity=0, on=False)
        self.output.note(0, 61, velocity=0, on=False)
        self.output.poll()
        expected_usb = bytes([9, 0x90, 60, 96, 9, 0x90, 61, 96,
                              15, 0xF8, 0, 0, 8, 0x80, 60, 0, 8, 0x80, 61, 0])
        self.assertEqual(native.usb_submissions, [expected_usb])
        self.assertEqual(native.usb_ready(), 1)
        self.assertEqual(native.usb_full(), 1)
        native.release_usb_endpoint()
        self.assertEqual(native.usb_full(), 0)
        expected_din = bytes([0x90, 60, 96, 61, 96, 0xF8, 0x80, 60, 0, 61, 0])
        for port in range(2):
            self.assertEqual(native.drain_uart(port), expected_din)

    def test_native_usb_busy_preserves_staging_until_release_then_drains_rest(self):
        self.setup_graph()
        native = NativeMidiDriverFixture(self, self.output)
        for _ in range(20):
            self.ingress.din([0xF8])
        self.output.poll()
        self.assertEqual([len(p) for p in native.usb_submissions], [64])
        self.assertEqual(self.output.pending(0), 4)
        self.output.poll()
        self.assertEqual([len(p) for p in native.usb_submissions], [64])
        self.assertEqual(self.output.pending(0), 4)
        native.release_usb_endpoint()
        self.output.poll()
        self.assertEqual([len(p) for p in native.usb_submissions], [64, 16])
        native.release_usb_endpoint()
        self.assertEqual(b''.join(native.usb_completed), bytes([15, 0xF8, 0, 0])*20)
        self.assertEqual(self.output.pending(0), 0)

    def test_native_usb_stall_overflow_latches_guard_after_actual_off_loss(self):
        for mode in (0, 1):
            with self.subTest(mode=mode):
                self.setUp()
                self.setup_graph()
                native = NativeMidiDriverFixture(self, self.output)
                self.u.mem_write(base.seq.SEQ_STATE_ADDR+4, bytes([mode]))
                self.output.note(0, 48)
                self.output.poll()
                native.release_usb_endpoint()
                for port in range(2):
                    native.drain_uart(port)
                # Real USB full is now derived from endpoint+1C==0, not a full
                # stub byte. Leave this transfer unreleased while filling FIFO.
                for _ in range(16):
                    self.ingress.din([0xF8])
                self.output.poll()
                for port in range(2):
                    native.drain_uart(port)
                self.assertEqual(native.usb_full(), 1)
                for _ in range(64):
                    self.ingress.din([0xF8])
                self.output.note(0, 48, velocity=0, on=False)
                self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR+base.seq.OFF_MIDI_TX_FAULT, 1), b'\x01')
                while self.output.pending(0):
                    native.release_usb_endpoint()
                    self.output.poll()
                    for port in range(2):
                        native.drain_uart(port)
                native.release_usb_endpoint()
                self.assertNotIn(bytes([8, 0x80, 48, 0]), b''.join(native.usb_completed))
                self.mode_ui.press()
                self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR+4, 1), bytes([mode]))

    def test_native_unconfigured_usb_does_not_falsely_latch_fifo_overflow(self):
        self.setup_graph(slots=2)
        native = NativeMidiDriverFixture(self, self.output)
        self.output.note(0, 48)
        self.output.note(0, 49)
        self.u.mem_write(native.usb_controller+0x274, b'\x00')
        self.assertEqual(native.usb_ready(), 0)
        self.output.poll()  # native401CA clears the unavailable port's queue
        self.assertEqual(self.output.pending(0), 0)
        self.assertEqual(native.usb_submissions, [])
        self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR+base.seq.OFF_MIDI_TX_FAULT, 1), b'\x00')
