"""Real pattern players, not calls directly into the MIDI output adapter."""
import unittest
from types import SimpleNamespace
import test_phase1_safety as base
from midi_output_test_support import MidiOutputFixture
from midi_ingress_test_support import MidiIngressFixture, TransportControlFixture
from shared_project_test_support import SharedModeFixture
from sequencer_playback_test_support import SequencerPlaybackFixture


class SequencerPlaybackTests(unittest.TestCase):
    setUpClass = classmethod(base.SafetyTests.setUpClass.__func__)
    setUp = base.SafetyTests.setUp
    word = base.SafetyTests.word
    read = base.SafetyTests.read
    store = base.SafetyTests.store
    call = base.SafetyTests.call

    def setup_playback(self, mode=0, full_transport=False):
        if full_transport:
            self.mode_ui = SharedModeFixture(self, ctrl=0x2000B000,
                                             view=0x2000B400, grid=0x2000B800)
            midi = SimpleNamespace(decoder=0x20004000, receiver=0x20004100, router=0x2000C000)
            self.word(midi.decoder, midi.receiver)
            self.transport = TransportControlFixture(self, midi, self.mode_ui)
            self.ingress = MidiIngressFixture(self, midi)
        else:
            self.transport = SimpleNamespace(engine=0x20001240, root=0x20001000)
        self.output = MidiOutputFixture(self, self.transport)
        self.playback = SequencerPlaybackFixture(
            self, self.output, getattr(self.transport, 'transport', None))
        self.u.mem_write(base.seq.SEQ_STATE_ADDR+4, bytes([mode]))

    def test_real_steps_and_timed_off_preserve_midi_while_sample_is_muted(self):
        for mode in (0, 1):
            for track in range(8):
                for pattern, step, note in ((0, 0, 12), (7, 31, 127), (0, 16, 0)):
                    with self.subTest(mode=mode, track=track, pattern=pattern, step=step, note=note):
                        self.setUp()
                        self.setup_playback(mode)
                        self.playback.step(track, step, note, pattern=pattern)
                        self.assertEqual(len(self.playback.active(track)), 1)
                        self.playback.expire_tick(track)
                        self.assertEqual(len(self.playback.active(track)), 1)
                        self.playback.expire_tick(track)
                        self.assertEqual(self.playback.active(track), [])
                        self.output.poll()
                        pitch = (note or 48)-12
                        expected = [bytes([9, 0x90|track, pitch, 96]),
                                    bytes([8, 0x80|track, pitch, 0])]
                        self.assertEqual(self.output.delivered, [expected]*3)
                        ons = [c for c in self.playback.sample_calls if c[0] == 'on']
                        self.assertEqual(len(ons), 1 if mode == 0 else 0)
                        p = self.playback.players[track]
                        self.assertEqual(self.u.mem_read(p-4, 4), b'PLY!')
                        self.assertEqual(self.u.mem_read(p+0x150, 4), b'END!')

    def test_ninth_distinct_pitch_steals_oldest_off_before_new_on(self):
        self.setup_playback(1)
        for n in range(9):
            self.playback.step(0, n, 48+n, gate=96)
            self.output.poll()
            self.assertEqual(len(self.playback.active(0)), min(n+1, 8))
        expected = [bytes([9, 0x90, 36+n, 96]) for n in range(8)]
        expected += [bytes([8, 0x80, 36, 0]), bytes([9, 0x90, 44, 96])]
        self.assertEqual(self.output.delivered, [expected]*3)
        self.playback.flush(0)
        self.assertEqual(self.playback.active(0), [])
        self.output.poll()
        self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR+base.seq.OFF_MIDI_TX_FAULT, 1), b'\x00')

    def test_all_thirty_two_native_step_reads_on_last_track_and_pattern(self):
        self.setup_playback(1)
        expected = []
        for step in range(32):
            self.playback.step(7, step, 48+step, pattern=7)
            self.playback.expire_tick(7)
            self.playback.expire_tick(7)
            self.output.poll()
            expected += [bytes([9, 0x97, 36+step, 96]), bytes([8, 0x87, 36+step, 0])]
        self.assertEqual(self.output.delivered, [expected]*3)
        self.assertEqual(self.playback.active(7), [])
        self.assertEqual([c for c in self.playback.sample_calls if c[0] == 'on'], [])
        # Independently inspect the true raw pattern's first/last tuples.
        raw_pattern = 0x20010000+7*0x5140+0x2E4+7*0xA28
        self.assertEqual(self.u.mem_read(raw_pattern, 8), bytes([48, 6, 1, 96, 7, 255, 0, 0]))
        self.assertEqual(self.u.mem_read(raw_pattern+31*8, 8), bytes([79, 6, 1, 96, 7, 255, 0, 0]))

    def test_same_pitch_retrigger_has_off_on_order_and_one_active_record(self):
        self.setup_playback(1)
        self.playback.step(0, 0, 60, gate=96)
        self.playback.step(0, 1, 60, gate=96)
        self.assertEqual(len(self.playback.active(0)), 1)
        self.output.poll()
        expected = [bytes([9, 0x90, 48, 96]), bytes([8, 0x80, 48, 0]),
                    bytes([9, 0x90, 48, 96])]
        self.assertEqual(self.output.delivered, [expected]*3)

    def test_eight_tracks_can_leave_sixty_four_outstanding_notes(self):
        self.setup_playback(1)
        for t in range(8):
            for n in range(8):
                self.playback.step(t, n, 48+n, gate=96)
                self.output.poll()
        self.assertEqual([len(self.playback.active(t)) for t in range(8)], [8]*8)
        for t in range(8):
            self.playback.flush(t)
        self.assertEqual([self.output.pending(p) for p in range(3)], [64]*3)
        self.output.poll()
        for messages in self.output.delivered:
            self.assertEqual(sum(m[0] == 9 for m in messages), 64)
            self.assertEqual(sum(m[0] == 8 for m in messages), 64)

    def test_native_stop_notification_can_overflow_after_sixty_four_note_offs(self):
        for mode in (0, 1):
            with self.subTest(mode=mode):
                self.setUp()
                self.setup_playback(mode, full_transport=True)
                self.playback.attach_stop_listeners()
                for t in range(8):
                    for n in range(8):
                        self.playback.step(t, n, 48+n, gate=96)
                        self.output.poll()
                running = self.call(0x0803FD26, self.transport.transport, 0)
                self.word(running, 1)
                self.call(0x0803FE00, self.transport.transport)
                raw = bytes(self.u.mem_read(0x20010000, 0x29484))
                # No producer loop invented here: actual33EAE updates the
                # transport store, notifies8 native players, then emits Stop.
                self.call(0x08033EAE, self.transport.root+0x0C, 0)
                self.assertEqual(self.transport.running(), 0)
                self.assertEqual([self.playback.active(t) for t in range(8)], [[]]*8)
                self.output.poll()
                for messages in self.output.delivered:
                    self.assertEqual(sum(m[0] == 8 for m in messages), 64)
                    self.assertEqual(sum(m[1] == 0xFC for m in messages), 0)
                self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR+base.seq.OFF_MIDI_TX_FAULT, 1), b'\x01')
                self.assertEqual(bytes(self.u.mem_read(0x20010000, 0x29484)), raw)
                self.mode_ui.press()
                self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR+4, 1), bytes([mode]))

    def test_sixty_three_note_offs_leave_exactly_one_slot_for_stop(self):
        self.setup_playback(1, full_transport=True)
        self.playback.attach_stop_listeners()
        for t in range(8):
            for n in range(7 if t == 7 else 8):
                self.playback.step(t, n, 48+n, gate=96)
                self.output.poll()
        self.word(self.call(0x0803FD26, self.transport.transport, 0), 1)
        self.call(0x0803FE00, self.transport.transport)
        self.call(0x08033EAE, self.transport.root+0x0C, 0)
        self.assertEqual([self.output.pending(p) for p in range(3)], [64]*3)
        self.output.poll()
        for messages in self.output.delivered:
            self.assertEqual(sum(m[0] == 8 for m in messages), 63)
            self.assertEqual(messages[-1], bytes([0x0F, 0xFC, 0, 0]))
        self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR+base.seq.OFF_MIDI_TX_FAULT, 1), b'\x00')

    def test_tied_same_pitch_does_not_retrigger_output_and_flush_sends_off(self):
        self.setup_playback(1)
        self.playback.step(0, 0, 60, tie=1)
        self.playback.step(0, 1, 60, tie=0)
        self.assertEqual(len(self.playback.active(0)), 1)
        self.output.poll()
        expected = [bytes([9, 0x90, 48, 96])]
        self.assertEqual(self.output.delivered, [expected]*3)
        self.playback.flush(0)
        self.output.poll()
        expected += [bytes([8, 0x80, 48, 0])]
        self.assertEqual(self.output.delivered, [expected]*3)

    def test_one_usb_clock_before_stop_can_lose_player_off_and_stop(self):
        self.setup_playback(1, full_transport=True)
        self.playback.attach_stop_listeners()
        for t in range(8):
            for n in range(8):
                self.playback.step(t, n, 48+n, gate=96)
                self.output.poll()
        self.word(self.call(0x0803FD26, self.transport.transport, 0), 1)
        self.call(0x0803FE00, self.transport.transport)
        # A single8-byte USB buffer, consumed by the real parser/dispatcher.
        # The USB yield hook cannot split Clock and Stop inside this buffer.
        self.ingress.usb([15, 0xF8, 0, 0, 15, 0xFC, 0, 0])
        self.output.poll()
        for messages in self.output.delivered:
            self.assertEqual(sum(m[0] == 9 for m in messages), 64)
            self.assertEqual(sum(m[0] == 8 for m in messages), 63)
            self.assertEqual(sum(m[1] == 0xF8 for m in messages), 1)
            self.assertEqual(sum(m[1] == 0xFC for m in messages), 0)
        self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR+base.seq.OFF_MIDI_TX_FAULT, 1), b'\x01')


if __name__ == '__main__':
    unittest.main()
