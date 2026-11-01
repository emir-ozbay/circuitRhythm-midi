"""Regression evidence for the second audit; real stock store-read ABI."""
import unittest
import test_phase1_safety as base


class ReauditABI(unittest.TestCase):
    # Current stock MIDI/recorder and ABI regressions; no storage hook bypass.

    setUpClass = classmethod(base.SafetyTests.setUpClass.__func__)
    setUp = base.SafetyTests.setUp
    word = base.SafetyTests.word
    read = base.SafetyTests.read
    store = base.SafetyTests.store
    call = base.SafetyTests.call


    def test_real_constructors_bind_recorders_to_project_storage(self):
        from project_alias_test_support import ProjectAliasFixture, STORE_LEN, TRACK_STRIDE, PATTERN_OFFSET
        f = ProjectAliasFixture(self)
        self.assertEqual(self.read(f.p + 0x14), f.raw)
        self.assertEqual(self.read(f.span), TRACK_STRIDE)
        self.assertEqual(self.read(f.span + 4), 8)
        self.assertEqual(len(set(f.recorders)), 8)
        for track, patterns in enumerate(f.patterns):
            self.assertEqual(patterns, f.raw + PATTERN_OFFSET + track * TRACK_STRIDE)
            self.assertGreaterEqual(patterns, f.raw)
            self.assertLessEqual(patterns + TRACK_STRIDE, f.raw + STORE_LEN)
        self.assertEqual(self.read(f.raw + STORE_LEN), f.raw)


    def test_midi_extreme_notes_preserve_recorder_boundary(self):
        from midi_record_test_support import MidiRecordFixture
        for note in (0, 127):
            with self.subTest(note=note):
                self.setUp()
                f = MidiRecordFixture(self, 7)
                self.u.mem_write(f.recorder + 0x294, b'\xa5' * 16)
                f.send(0x90, note=note)
                self.word(f.clock + 0x40, 24)
                f.send(0x80, note=note, velocity=0)
                f.finish()
                off = 7 * 0xA28 + 31 * 8
                data = bytes(self.u.mem_read(f.patterns, 8 * 0xA28))
                self.assertEqual(data[off], note + 12)
                self.assertEqual(data[:off] + data[off + 8:], bytes(len(data) - 8))
                self.assertEqual(self.u.mem_read(f.recorder + 0x294, 16), b'\xa5' * 16)

    def test_stock_note_ownership_keeps_other_source_until_release(self):
        filt, callback, vt = 0x20004000, 0x20004100, 0x20004200
        on, off = 0x0800E900, 0x0800E904
        self.word(callback, vt)
        self.word(vt, on | 1); self.word(vt + 4, off | 1)
        self.u.mem_write(on, bytes.fromhex('704700007047'))
        events = []
        self.u.hook_add(base.UC_HOOK_CODE, lambda u,a,z,d: events.append(a), begin=on, end=off)
        self.call(0x08054F10, filt, callback)
        self.call(0x08054F30, filt, 60, 96, 0)
        self.call(0x08054F30, filt, 60, 96, 0)  # duplicate from same source
        self.assertEqual(events, [on])
        self.call(0x08054F30, filt, 60, 96, 1)  # other source retriggers
        self.assertEqual(events, [on, off, on])
        self.call(0x08054FA8, filt, 60, 0)
        self.assertEqual(events, [on, off, on])
        self.call(0x08054FA8, filt, 60, 1)
        self.assertEqual(events, [on, off, on, off])
        self.call(0x08054FA8, filt, 60, 1)
        self.assertEqual(events, [on, off, on, off])
        self.assertEqual(bytes(self.u.mem_read(filt + 4, 40)), bytes(40))

    def test_midi_decoder_through_ownership_filters_to_pattern(self):
        from midi_record_test_support import MidiRecordFixture
        for track in range(8):
            for seq_enabled in (0, 1):
                for off_status in (0x80, 0x90):
                    with self.subTest(track=track, seq_enabled=seq_enabled, off_status=off_status):
                        self.setUp()
                        f = MidiRecordFixture(self, track)
                        self.u.mem_write(base.seq.SEQ_STATE_ADDR + 4, bytes([seq_enabled]))
                        f.send(0x90)
                        self.assertEqual(self.u.mem_read(f.recorder + 0x60, 2), bytes([60, 96]))
                        self.word(f.clock + 0x40, 24)
                        f.send(off_status, velocity=0)
                        f.finish()
                        data = bytes(self.u.mem_read(f.patterns, 8 * 0xA28))
                        off = 7 * 0xA28 + 31 * 8
                        self.assertEqual(data[off], 60)
                        self.assertGreater(data[off + 1], 0)
                        self.assertEqual(data[off + 3], 96)
                        self.assertEqual(data[:off] + data[off + 8:], bytes(len(data) - 8))
                        for filt in f.filters:
                            self.assertEqual(bytes(self.u.mem_read(filt + 4, 40)), bytes(40))
                        self.assertEqual(bytes(self.u.mem_read(f.receiver + 0x74, 160)), bytes(160))
                        self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR + base.seq.OFF_PROJECT_DIRTY, 1), b'\x00')
                        self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR + base.seq.OFF_SAVE_EDITED, 1), b'\x00')

    def test_midi_channel_and_note_translation_to_router_boundary(self):
        # Real decoder -> receiver -> note adapter -> track adapter. Only the
        # terminal router recipient is observed, not replaced with a recorder.
        decoder, receiver, adapter, offset_adapter = 0x20004000, 0x20004100, 0x20004300, 0x20004320
        router, vt, message = 0x20004400, 0x20004420, 0x20004700
        on, off = 0x0800E900, 0x0800E904
        self.word(decoder, receiver)
        self.u.mem_write(decoder + 4, bytes(reversed(range(8))))
        self.u.mem_write(decoder + 0x1C, b'\x01')
        self.word(receiver, 0x080665E4)
        self.word(receiver + 0x24, adapter)
        self.word(adapter, 0x080694D0)
        self.word(adapter + 4, offset_adapter)
        self.word(offset_adapter, 0x08069510)
        self.word(offset_adapter + 4, router)
        self.u.mem_write(offset_adapter + 8, b'\x10')
        self.word(router, vt)
        self.word(vt, on | 1)
        self.word(vt + 4, off | 1)
        self.u.mem_write(on, bytes.fromhex('704700007047'))
        events = []
        self.u.hook_add(base.UC_HOOK_CODE,
            lambda u,a,z,d: events.append((a, tuple(u.reg_read(r) for r in base.REGS))),
            begin=on, end=off)
        for track in range(8):
            for zero_off in (False, True):
                channel = 7 - track
                self.u.mem_write(message, bytes([0x90 | channel, 48, 96]))
                self.call(0x0805AF94, decoder, message)
                self.assertEqual(events[-1], (on, (router, 60, 96, 16 + track)))
                self.u.mem_write(message, bytes([(0x90 if zero_off else 0x80) | channel, 48, 0]))
                self.call(0x0805AF94, decoder, message)
                self.assertEqual(events[-1], (off, (router, 60, 16 + track, 0)))
                self.assertEqual(bytes(self.u.mem_read(receiver + 0x74, 8 * 20)), bytes(8 * 20))
        count = len(events)
        self.u.mem_write(message, bytes([0x98, 48, 96]))  # no matching channel
        self.call(0x0805AF94, decoder, message)
        self.assertEqual(len(events), count)
        self.u.mem_write(decoder + 0x1C, b'\x00')
        self.u.mem_write(message, bytes([0x97, 48, 96]))
        self.call(0x0805AF94, decoder, message)
        self.assertEqual(len(events), count)

    def test_record_group_routes_tracks_and_checks_all_three_gates(self):
        import struct
        group, recorder, patterns = 0x20004500, 0x20007000, 0x20010000
        for track in range(8):
            for flags in ((1, 1, 0), (0, 1, 0), (1, 0, 0), (1, 1, 1)):
                with self.subTest(track=track, flags=flags):
                    self.setUp()
                    self.word(group, 0x08068CE4)
                    self.word(group + 8, self.store(struct.pack('<3I', *flags)))
                    self.word(group + 0x0C + track * 4, recorder)
                    self.word(recorder, 0x08067864)
                    self.word(recorder + 0x50, patterns)
                    self.word(recorder + 0x14, self.store(bytes([1, 0, 0, 0])))
                    self.word(recorder + 0x20, self.store(bytes(4)))
                    self.word(recorder + 0x5C, self.store(bytes(8)))
                    self.word(recorder + 0x0C, self.store(struct.pack('<3I', 7, 31, 0)))
                    self.word(recorder + 0x10, self.store(struct.pack('<2I', 7, 31)))
                    clock = self.store(bytes(4))
                    self.word(recorder + 0x1C, clock)
                    self.call(0x08036A80, group, 60, 96, 16 + track)
                    enabled = flags == (1, 1, 0)
                    self.assertEqual(self.u.mem_read(recorder + 0x60, 2), bytes([60, 96]) if enabled else bytes(2))
                    self.word(clock + 0x40, 24)
                    self.call(0x08036AC4, group, 60, 16 + track)
                    self.word(0x20040000, 0)
                    self.call(0x08048D2A, recorder, 7, 31, 24)
                    data = bytes(self.u.mem_read(patterns, 8 * 0xA28))
                    if enabled:
                        off = 7 * 0xA28 + 31 * 8
                        self.assertEqual(data[off], 60)
                        self.assertEqual(data[off + 3], 96)
                        self.assertGreater(data[off + 1], 0)
                        self.assertEqual(data[:off] + data[off + 8:], bytes(len(data) - 8))
                    else:
                        self.assertEqual(data, bytes(len(data)))
                    self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR + base.seq.OFF_PROJECT_DIRTY, 1), bytes(1))

    def test_recorder_callbacks_through_pending_to_pattern(self):
        # Real recorder vtable and Note On/Off/flush code. This starts at the
        # recorder interface, not at UART/USB ingress or the MIDI dispatcher.
        import struct
        recorder, patterns = 0x20004000, 0x20010000
        self.word(recorder, 0x08067864)
        self.word(recorder + 0x50, patterns)
        self.word(recorder + 0x14, self.store(bytes([1, 0, 0, 0])))
        self.word(recorder + 0x20, self.store(bytes(4)))
        self.word(recorder + 0x5C, self.store(bytes(8)))
        for pattern in (0, 7):
            for step in (0, 31):
                with self.subTest(pattern=pattern, step=step):
                    self.u.mem_write(patterns, bytes(8 * 0xA28))
                    self.u.mem_write(recorder + 0x60, bytes(0x240))
                    self.word(recorder + 0x0C, self.store(struct.pack('<3I', pattern, step, 0)))
                    self.word(recorder + 0x10, self.store(struct.pack('<2I', pattern, step)))
                    clock = self.store(bytes(4))
                    self.word(recorder + 0x1C, clock)
                    self.u.mem_write(base.seq.SEQ_STATE_ADDR + base.seq.OFF_PROJECT_DIRTY, b'\x00')
                    self.u.mem_write(base.seq.SEQ_STATE_ADDR + base.seq.OFF_SAVE_EDITED, b'\x00')
                    self.call(0x080492A8, recorder, 60, 96)
                    self.assertEqual(self.u.mem_read(recorder + 0x60, 2), bytes([60, 96]))
                    self.assertEqual(bytes(self.u.mem_read(patterns, 8 * 0xA28)), bytes(8 * 0xA28))
                    self.word(clock + 0x40, 24)
                    self.call(0x0804933E, recorder, 60)
                    self.assertEqual(bytes(self.u.mem_read(patterns, 8 * 0xA28)), bytes(8 * 0xA28))
                    self.word(0x20040000, 0)  # flush fifth argument: timing offset
                    self.call(0x08048D2A, recorder, pattern, step, 24)
                    data = bytes(self.u.mem_read(patterns, 8 * 0xA28))
                    off = pattern * 0xA28 + step * 8
                    self.assertEqual(data[off], 60)
                    self.assertEqual(data[off + 3], 96)
                    self.assertGreater(data[off + 1], 0)
                    self.assertEqual(data[:off] + data[off + 8:], bytes(len(data) - 8))
                    self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR + base.seq.OFF_PROJECT_DIRTY, 1), b'\x00')
                    self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR + base.seq.OFF_SAVE_EDITED, 1), b'\x00')
                    self.u.mem_write(base.seq.SEQ_STATE_ADDR + base.seq.OFF_PROJECT_DIRTY, b'\x00')
                    self.call(0x0804933E, recorder, 60)
                    self.call(0x08048D2A, recorder, pattern, step, 24)
                    self.assertEqual(bytes(self.u.mem_read(patterns, len(data))), data)
                    self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR + base.seq.OFF_PROJECT_DIRTY, 1), b'\x00')

    def test_stock_direct_record_nonselected_pattern_preserves_canaries(self):
        player, patterns = 0x20004000, 0x20010000
        self.word(player + 0x50, patterns)
        for pattern in (0, 7):
            self.word(player + 0x14, self.store(bytes([1 if pattern == 0 else 0, 0, 0, 0])))
            for step in (0, 31):
                self.u.mem_write(patterns, bytes(8 * 0xA28))
                pending = 1 | (step << 1) | (pattern << 6) | (96 << 9) | (3 << 27)
                self.word(player + 0x64 + 60*4, pending)
                self.u.mem_write(base.seq.SEQ_STATE_ADDR + base.seq.OFF_PROJECT_DIRTY, b'\x00')
                self.u.mem_write(base.seq.SEQ_STATE_ADDR + base.seq.OFF_SAVE_EDITED, b'\x00')
                result = self.call(0x08048E70, player, 60, 24)
                self.assertEqual(result, 0)  # nonselected pattern, no store notify needed
                data = bytes(self.u.mem_read(patterns, 8 * 0xA28))
                off = pattern*0xA28 + step*8
                self.assertEqual(data[off], 60)
                self.assertGreater(data[off+1], 0)
                self.assertEqual(data[off+2:off+5], bytes([8, 96, 7]))
                self.assertEqual(data[:off] + data[off+8:], bytes(len(data)-8))
                self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR + base.seq.OFF_PROJECT_DIRTY, 1), b'\x00')
                self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR + base.seq.OFF_SAVE_EDITED, 1), b'\x00')
                # Consumed pending record: another call must not write/mark dirty.
                self.u.mem_write(base.seq.SEQ_STATE_ADDR + base.seq.OFF_PROJECT_DIRTY, b'\x00')
                self.call(0x08048E70, player, 60, 24)
                self.assertEqual(bytes(self.u.mem_read(patterns, len(data))), data)
                self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR + base.seq.OFF_PROJECT_DIRTY, 1), b'\x00')

    def test_stock_direct_delay_nonselected_pattern_preserves_canaries(self):
        player, patterns = 0x20004000, 0x20010000
        self.word(player + 0x50, patterns)
        self.word(player + 0x14, self.store(bytes(4)))
        self.call(0x0804909C, player, 7, 31, 42)
        data = bytes(self.u.mem_read(patterns, 8*0xA28))
        off = 7*0xA28 + 31*8 + 5
        self.assertEqual(data[off], 42)
        self.assertEqual(data[:off] + data[off+1:], bytes(len(data)-1))
        self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR + base.seq.OFF_PROJECT_DIRTY, 1), b'\x00')

    def test_record_selected_pattern_updates_stores_and_preserves_canaries(self):
        from verify_phase1_candidate import EmulatorHarness
        h = EmulatorHarness(self.image, self.labels)
        env = h.setup_step_view_environment(active_pattern=7)
        recorder = 0x20004500
        h.word(recorder + 0x50, env['patterns'])
        h.word(recorder + 0x14, h.readword(0x20001000 + 0x28))
        h.word(recorder + 0x54, env['st1'])
        h.word(recorder + 0x58, env['st2'])
        h.word(recorder + 0x64 + 60*4, 1 | (31<<1) | (7<<6) | (96<<9) | (3<<27))
        before = bytes(h.u.mem_read(env['patterns'], 8*0xA28))
        self.assertEqual(h.call(0x08048E70, recorder, 60, 24), 1)
        h.call(base.seq.STOCK_NOTIFY_STORE, env['st1'])
        h.call(base.seq.STOCK_NOTIFY_STORE, env['st2'])
        after = bytes(h.u.mem_read(env['patterns'], 8*0xA28))
        off = 7*0xA28 + 31*8
        self.assertEqual(after[off], 60)
        self.assertEqual(after[off+3], 96)
        self.assertEqual(after[:off] + after[off+8:], before[:off] + before[off+8:])
        self.assertEqual(h.u.mem_read(base.seq.SEQ_STATE_ADDR + base.seq.OFF_PROJECT_DIRTY, 1), b'\x00')

    def test_parameter_commit_preserved_across_same_project_mode_switch(self):
        from verify_phase1_candidate import EmulatorHarness
        from shared_project_test_support import SharedModeFixture
        for setter, store_name, offset, value in (
            (0x080549B0, 'st1', 3, 99), (0x080549D8, 'st1', 2, 5),
            (0x08054A04, 'st1', 4, 3), (0x08054A30, 'st1', 5, 80),
            (0x08054A5C, 'st2', 0, 72), (0x08054A84, 'st2', 1, 12),
            (0x08054AB0, 'st2', 6, 1),
        ):
            for step in (0, 31):
                with self.subTest(setter=hex(setter), step=step):
                    h = EmulatorHarness(self.image, self.labels)
                    env = h.setup_step_view_environment(active_pattern=7)
                    f = SharedModeFixture(h)
                    h.call(setter, env[store_name], step, value)
                    h.call(base.seq.STOCK_NOTIFY_STORE, env[store_name])
                    self.assertEqual(h.u.mem_read(env['patterns'] + 7*0xA28 + 8*step + offset, 1), bytes([value]))
                    before = bytes(h.u.mem_read(env['patterns'], 8*0xA28))
                    f.press()
                    self.assertEqual(h.u.mem_read(base.seq.SEQ_STATE_ADDR + 4, 1), b'\x01')
                    self.assertEqual(bytes(h.u.mem_read(env['patterns'], len(before))), before)

    def test_nonmutation_commit_notification_preserves_private_state_and_abi(self):
        listener, store = 0x20004000, 0x20006000
        # Unknown source takes the stock no-op return, without dereferencing stores.
        self.call(0x08048208, listener, store, 0)
        self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR + base.seq.OFF_PROJECT_DIRTY, 1), b'\x00')

    def test_stock_knob_delivery_in_both_runtime_modes(self):
        ctrl, view, vt = 0x20004000, 0x20005000, 0x20006000
        self.word(ctrl + 0x8C, self.store(bytes(4)))
        self.word(ctrl + 0x78, view); self.word(view, vt)
        callback = 0x0800E900
        self.word(vt + 0x10, callback | 1)
        self.u.mem_write(callback, bytes.fromhex('7047'))
        events = []
        self.u.hook_add(base.UC_HOOK_CODE, lambda u,a,z,d: events.append(tuple(u.reg_read(r) for r in base.REGS[:3])), begin=callback, end=callback)
        for mode in (0, 1):
            self.u.mem_write(base.seq.SEQ_STATE_ADDR + 4, bytes([mode]))
            for knob in range(8):
                for delta in (0, 1, 0xFFFFFFFF):
                    self.call(0x0803DDE0, ctrl, knob, delta)
                    self.assertEqual(events[-1], (view, knob, delta))
        self.assertEqual(len(events), 48)


    def test_allocator_rejects_integer_wrap(self):
        for size in (0xFFFFFFFC, 0xFFFFFFFF):
            cur = self.read(base.seq.HEAP_CUR_PTR)
            self.assertEqual(self.call(base.seq.STOCK_ALLOCATOR_ADDR, size), 0xFFFFFFFF)
            self.assertEqual(self.read(base.seq.HEAP_CUR_PTR), cur)


if __name__ == '__main__':
    unittest.main()

