"""Joined synthetic controller + real short-message/receiver/recorder graph.

Not UART/USB hardware or a full boot. Controller ownership stores are separate
from receiver+74 masks; the guard must independently observe external ownership.
"""
import unittest
import test_phase1_safety as base
from midi_record_test_support import MidiRecordFixture
from shared_project_test_support import SharedModeFixture


class MidiModeOwnershipTests(unittest.TestCase):
    setUpClass = classmethod(base.SafetyTests.setUpClass.__func__)
    setUp = base.SafetyTests.setUp
    word = base.SafetyTests.word
    read = base.SafetyTests.read
    store = base.SafetyTests.store
    call = base.SafetyTests.call

    def idle(self):
        return self.call(self.labels['c_midi_inputs_idle'])

    def test_external_note_blocks_toggle_until_matching_off_all_tracks(self):
        for mode in (0, 1):
            for track in range(8):
                for note, off_status in ((0, 0x80), (127, 0x90)):
                    with self.subTest(mode=mode, track=track, note=note, off_status=off_status):
                        self.setUp()
                        midi = MidiRecordFixture(self, track)
                        mode_ui = SharedModeFixture(self, ctrl=0x2000B000, view=0x2000B400, grid=0x2000B800)
                        self.u.mem_write(base.seq.SEQ_STATE_ADDR + 4, bytes([mode]))
                        midi.send(0x90, note=note)
                        self.assertNotEqual(bytes(self.u.mem_read(midi.receiver + 0x74, 160)), bytes(160))
                        mode_ui.press()
                        self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR + 4, 1), bytes([mode]))
                        mode_ui.release()
                        self.word(midi.clock + 0x40, 24)
                        midi.send(off_status, note=note, velocity=0)
                        midi.finish()
                        self.assertEqual(bytes(self.u.mem_read(midi.receiver + 0x74, 160)), bytes(160))
                        mode_ui.press()
                        self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR + 4, 1), bytes([1-mode]))

    def test_stock_all_notes_off_drain_reopens_only_after_last_note(self):
        for track in range(8):
            with self.subTest(track=track):
                self.setUp()
                midi = MidiRecordFixture(self, track)
                mode_ui = SharedModeFixture(self, ctrl=0x2000B000, view=0x2000B400, grid=0x2000B800)
                for note in (0, 60, 127):
                    midi.send(0x90, note=note)
                self.assertEqual(self.idle(), 0)
                self.word(midi.clock + 0x40, 24)
                midi.send(0x80, note=60, velocity=0)
                self.assertEqual(self.idle(), 0)
                # Actual stock mask drain, not manual mask clearing. This is not
                # evidence that every transport Stop source reaches this helper.
                self.call(0x0803F7D8, midi.receiver, 16+track)
                self.assertEqual(bytes(self.u.mem_read(midi.receiver + 0x74, 160)), bytes(160))
                for filt in midi.filters:
                    self.assertEqual(bytes(self.u.mem_read(filt + 4, 40)), bytes(40))
                self.assertEqual(self.idle(), 1)
                mode_ui.press()
                self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR + 4, 1), b'\x01')

    def test_two_real_decoder_receivers_require_both_sources_to_release(self):
        midi = MidiRecordFixture(self, 0)
        receivers = [midi.receiver, 0x2000C000]
        decoder, message = 0x2000C200, 0x2000C300
        self.word(receivers[1], 0x080665E4)
        self.word(receivers[1]+0x24, self.read(midi.receiver+0x24))
        self.word(decoder, receivers[1])
        self.u.mem_write(decoder+4, bytes(reversed(range(8))))
        self.u.mem_write(decoder+0x1C, b'\x01')
        midi.send(0x90, note=48)
        self.u.mem_write(message, bytes([0x97, 49, 96]))
        self.call(0x0805AF94, decoder, message)
        self.assertEqual(self.idle(), 0)
        midi.send(0x80, note=48, velocity=0)
        self.assertEqual(self.idle(), 0)
        self.u.mem_write(message, bytes([0x87, 49, 0]))
        self.call(0x0805AF94, decoder, message)
        self.assertEqual(self.idle(), 1)
        state = base.seq.SEQ_STATE_ADDR
        self.assertEqual(self.read(state + base.seq.OFF_MIDI_RECEIVERS), receivers[0])
        self.assertEqual(self.read(state + base.seq.OFF_MIDI_RECEIVERS+4), receivers[1])

    def test_fifth_context_latches_guard_without_losing_note_delivery(self):
        midi = MidiRecordFixture(self, 0)
        sources = [(midi.decoder, midi.receiver)]
        for n in range(4):
            receiver, decoder = 0x2000C000+0x200*n, 0x2000D000+0x100*n
            self.word(receiver, 0x080665E4)
            self.word(receiver+0x24, self.read(midi.receiver+0x24))
            self.word(decoder, receiver)
            self.u.mem_write(decoder+4, bytes(reversed(range(8))))
            self.u.mem_write(decoder+0x1C, b'\x01')
            sources.append((decoder, receiver))
        message = 0x2000E000
        for n, (decoder, receiver) in enumerate(sources):
            self.u.mem_write(message, bytes([0x97, 48+n, 96]))
            self.call(0x0805AF94, decoder, message)
            self.assertNotEqual(bytes(self.u.mem_read(receiver+0x74, 160)), bytes(160))
        self.assertEqual(self.u.mem_read(midi.recorder+0x60, 2), bytes([64, 96]))
        for n, (decoder, receiver) in enumerate(sources):
            self.u.mem_write(message, bytes([0x87, 48+n, 0]))
            self.call(0x0805AF94, decoder, message)
            self.assertEqual(bytes(self.u.mem_read(receiver+0x74, 160)), bytes(160))
        state = base.seq.SEQ_STATE_ADDR
        self.assertEqual(self.u.mem_read(state+base.seq.OFF_MIDI_ACTIVE_CALLS, 1), b'\x00')
        self.assertEqual(self.u.mem_read(state+base.seq.OFF_MIDI_CONTEXT_FAULT, 1), b'\x01')
        self.assertEqual(self.idle(), 0)  # no unsafe recycling of the fifth context

    def test_direct_zero_velocity_replays_stock_flags_and_return_value(self):
        midi = MidiRecordFixture(self, 0)
        self.assertEqual(self.call(0x0803F5A8, midi.receiver, 16, 48, 96), 96)
        self.assertEqual(self.idle(), 0)
        self.assertEqual(self.call(0x0803F5A8, midi.receiver, 16, 48, 0), 0)
        self.assertEqual(bytes(self.u.mem_read(midi.receiver+0x74, 160)), bytes(160))
        self.assertEqual(self.idle(), 1)

    def test_observer_preserves_all_stock_volatile_register_results(self):
        for note in (0, 127):
            for velocity in (0, 96):
                with self.subTest(note=note, velocity=velocity):
                    outcomes = []
                    for stock_entry in (True, False):
                        self.setUp()
                        midi = MidiRecordFixture(self, 0)
                        if stock_entry:
                            # Controlled ABI reference only; production path is
                            # separately run with its packaged hook intact.
                            self.u.mem_write(base.seq.HOOK_MIDI_RECEIVE_ON, base.seq.EXPECTED_MIDI_RECEIVE_ON)
                        midi.send(0x90, note=note)
                        self.call(0x0803F5A8, midi.receiver, 16, note, velocity)
                        outcomes.append(tuple(self.u.reg_read(r) for r in base.REGS))
                    self.assertEqual(outcomes[1], outcomes[0])

    def test_mask_scan_covers_all_40_words_and_stops_before_state_boundary(self):
        state = base.seq.SEQ_STATE_ADDR
        receiver = state - 0x114
        self.u.mem_write(receiver, bytes(0x114))
        self.call(self.labels['c_midi_observe_begin'], receiver)
        self.call(self.labels['c_midi_observe_end'], state)
        magic = self.read(state)
        self.assertNotEqual(magic, 0)
        self.assertEqual(self.idle(), 1)  # adjacent magic is not a mask word
        for word in range(40):
            with self.subTest(word=word):
                address = receiver + 0x74 + 4*word
                self.word(address, 1 << 31)
                self.assertEqual(self.idle(), 0)
                self.assertEqual(self.read(address), 1 << 31)
                self.word(address, 0)
        self.assertEqual(self.read(state), magic)
        self.assertEqual(self.idle(), 1)

    def test_stock_callback_runs_once_with_busy_set_and_original_irq_mask(self):
        for primask in (0, 1):
            with self.subTest(primask=primask):
                self.setUp()
                midi = MidiRecordFixture(self, 0)
                observations = []
                def entered(u, address, size, data):
                    observations.append((
                        u.reg_read(base.UC_ARM_REG_PRIMASK),
                        u.mem_read(base.seq.SEQ_STATE_ADDR+base.seq.OFF_MIDI_ACTIVE_CALLS, 1)[0],
                        bytes(u.mem_read(midi.receiver+0x74, 160)),
                    ))
                target = self.labels['c_midi_receive_on_stock']
                self.u.hook_add(base.UC_HOOK_CODE, entered, begin=target, end=target)
                self.u.reg_write(base.UC_ARM_REG_PRIMASK, primask)
                midi.send(0x90)
                self.assertEqual(observations, [(primask, 1, bytes(160))])
                self.assertEqual(self.u.reg_read(base.UC_ARM_REG_PRIMASK), primask)
                self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR+base.seq.OFF_MIDI_ACTIVE_CALLS, 1), b'\x00')

    def test_context_overflow_and_damaged_pointers_fail_closed(self):
        state = base.seq.SEQ_STATE_ADDR
        pointers = [0x20006000 + 0x200*n for n in range(5)]
        for pointer in pointers:
            self.assertEqual(self.call(self.labels['c_midi_observe_begin'], pointer), state)
            self.call(self.labels['c_midi_observe_end'], state)
        self.assertEqual([self.read(state + base.seq.OFF_MIDI_RECEIVERS+4*n) for n in range(4)], pointers[:4])
        self.assertEqual(self.u.mem_read(state + base.seq.OFF_MIDI_CONTEXT_FAULT, 1), b'\x01')
        self.assertEqual(self.idle(), 0)
        self.assertEqual(self.u.mem_read(state + base.seq.OFF_MIDI_ACTIVE_CALLS, 1), b'\x00')
        for bad in (1, 0x08010000, 0x20006001, state, 0xFFFFFFFF):
            with self.subTest(bad=hex(bad)):
                self.setUp()
                self.word(state + base.seq.OFF_MIDI_RECEIVERS, bad)
                self.assertEqual(self.idle(), 0)

    def test_nested_bookkeeping_busy_and_saturation_do_not_open_a_window(self):
        state = base.seq.SEQ_STATE_ADDR
        receiver = 0x20006000
        for depth in (1, 2):
            self.call(self.labels['c_midi_observe_begin'], receiver)
            self.assertEqual(self.u.mem_read(state + base.seq.OFF_MIDI_ACTIVE_CALLS, 1), bytes([depth]))
            self.assertEqual(self.idle(), 0)
        self.call(self.labels['c_midi_observe_end'], state)
        self.assertEqual(self.idle(), 0)
        self.call(self.labels['c_midi_observe_end'], state)
        self.assertEqual(self.idle(), 1)
        self.call(self.labels['c_midi_observe_end'], state)  # duplicate cannot underflow
        self.assertEqual(self.idle(), 1)
        self.u.mem_write(state + base.seq.OFF_MIDI_ACTIVE_CALLS, b'\xff')
        self.call(self.labels['c_midi_observe_begin'], receiver)
        self.assertEqual(self.u.mem_read(state + base.seq.OFF_MIDI_ACTIVE_CALLS, 1), b'\xff')
        self.call(self.labels['c_midi_observe_end'], state)
        self.assertEqual(self.u.mem_read(state + base.seq.OFF_MIDI_CONTEXT_FAULT, 1), b'\x01')
        self.assertEqual(self.idle(), 0)

    def test_bookkeeping_restores_primask_and_invalid_heap_changes_no_state(self):
        state = base.seq.SEQ_STATE_ADDR
        for primask in (0, 1):
            self.u.reg_write(base.UC_ARM_REG_PRIMASK, primask)
            self.call(self.labels['c_midi_observe_begin'], 0x20006000)
            self.assertEqual(self.u.reg_read(base.UC_ARM_REG_PRIMASK), primask)
            self.call(self.labels['c_midi_observe_end'], state)
            self.assertEqual(self.u.reg_read(base.UC_ARM_REG_PRIMASK), primask)
        self.word(base.seq.HEAP_CUR_PTR, state+4)
        before = bytes(self.u.mem_read(state, 256))
        self.assertEqual(self.call(self.labels['c_midi_observe_begin'], 0x20006000), 0)
        self.call(self.labels['c_midi_observe_end'], state)
        self.assertEqual(self.idle(), 0)
        self.assertEqual(bytes(self.u.mem_read(state, 256)), before)

    def test_realtime_decoder_clock_stop_boundary_preserves_held_notes(self):
        midi = MidiRecordFixture(self, 0)
        receiver = midi.receiver
        # Actual derived receiver subobject vtables from3F454 constructor.
        self.word(receiver+0x0C, 0x08066654)
        self.word(receiver+0x10, 0x08066670)
        transport, vt = 0x2000C000, 0x2000C040
        self.word(receiver+0x30, transport)
        self.word(receiver+0x34, transport)
        self.word(transport, vt)
        boundaries = [0x0800E950 + 4*n for n in range(3)]
        events = []
        for n, address in enumerate(boundaries):
            self.word(vt+4*n, address|1)
            self.u.mem_write(address, bytes.fromhex('7047'))
            self.u.hook_add(base.UC_HOOK_CODE, lambda u,a,z,d: events.append(a), begin=address, end=address)
        self.u.mem_write(midi.decoder+0x1C, b'\x09')  # note and realtime delivery enabled
        midi.send(0x90)
        before = bytes(self.u.mem_read(receiver+0x74, 160))
        for mode in (0, 1):
            self.u.mem_write(base.seq.SEQ_STATE_ADDR+4, bytes([mode]))
            for status, target in ((0xF8, boundaries[0]), (0xFA, boundaries[0]),
                                   (0xFB, boundaries[1]), (0xFC, boundaries[2])):
                self.u.mem_write(midi.message, bytes([status, 0, 0]))
                before_count = len(events)
                self.call(0x0805AF94, midi.decoder, midi.message)
                self.assertEqual(len(events), before_count + 1)
                self.assertEqual(events[-1], target)
                self.assertEqual(bytes(self.u.mem_read(receiver+0x74, 160)), before)
                self.assertEqual(self.idle(), 0)
        midi.send(0x80, velocity=0)
        self.assertEqual(self.idle(), 1)


if __name__ == '__main__':
    unittest.main()
