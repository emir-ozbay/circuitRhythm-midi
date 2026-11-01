"""Isolated Thumb recovery experiment; packaged candidate stays unchanged."""
import unittest
import test_phase1_safety as base
import test_sequencer_playback as playback_tests
import midi_recovery_prototype as recovery
from midi_recovery_prototype_test_support import MidiRecoveryPrototypeFixture
from native_midi_driver_test_support import NativeMidiDriverFixture


class MidiRecoveryPrototypeTests(unittest.TestCase):
    setUpClass = classmethod(base.SafetyTests.setUpClass.__func__)
    setUp = base.SafetyTests.setUp
    word = base.SafetyTests.word
    read = base.SafetyTests.read
    store = base.SafetyTests.store
    call = base.SafetyTests.call
    setup_playback = playback_tests.SequencerPlaybackTests.setup_playback

    def setup_recovery(self, mode=1, native=False, sysex=True):
        self.setup_playback(mode, full_transport=True)
        self.playback.attach_stop_listeners()
        self.native = NativeMidiDriverFixture(self, self.output) if native else None
        self.recovery = MidiRecoveryPrototypeFixture(self, self.output, sysex=sysex)
        self.io_masks = []
        for pc in (0x0800EB00, 0x0800EB04, 0x0800EB08, 0x0800EB0C,
                   0x0802C9B8, 0x0802AC58):
            self.u.hook_add(base.UC_HOOK_CODE,
                            lambda u,a,n,d: self.io_masks.append(u.reg_read(base.UC_ARM_REG_PRIMASK)),
                            begin=pc, end=pc)

    def seed_notes(self, count):
        for t in range(8):
            for n in range(7 if t == 7 and count == 63 else 8):
                self.playback.step(t, n, 48+n, gate=96)
                self.recovery.poll()
        self.word(self.call(0x0803FD26, self.transport.transport, 0), 1)
        self.call(0x0803FE00, self.transport.transport)

    def sysex_descriptor(self, data=b'\xF0\x00\x20\x29\x01\xF7', second=False):
        address = 0x20006000 if second else 0x20005000
        self.word(address, address+16)
        self.word(address+4, len(data))
        self.u.mem_write(address+16, data)
        return address

    def setup_sysex_router(self):
        self.router_descriptor, self.router_buffer = 0x20004B40, 0x20004C00
        router = self.output.router
        self.word(router, self.router_descriptor)
        self.word(router+4, self.router_buffer)
        self.word(self.router_descriptor, self.router_buffer)
        self.word(self.router_descriptor+4, 360)
        self.u.mem_write(self.router_buffer-4, b'STAR')
        self.u.mem_write(self.router_buffer+360, b'LAST')
        self.word(router+0x20, 0x20004B60)
        self.word(0x20004B60, 0x20004B70)
        self.word(0x20004B74, 0x0800EB11)
        self.u.mem_write(0x0800EB10, bytes.fromhex('00bf7047'))
        self.route_callbacks = []
        self.u.hook_add(base.UC_HOOK_CODE, lambda u,a,n,d: self.route_callbacks.append(
            (u.reg_read(base.UC_ARM_REG_R0), u.reg_read(base.UC_ARM_REG_R1))),
            begin=0x0800EB12, end=0x0800EB12)

    @staticmethod
    def sysex_packets(data):
        return [bytes([4+len(data[n:n+3]) if data[n:n+3][-1] == 0xF7 else 4])
                +data[n:n+3]+bytes(3-len(data[n:n+3])) for n in range(0, len(data), 3)]

    def install_nested_calls(self, pc, calls):
        from thumb_asm import Asm, b_w, bl, movw, movt, pop, push, raw, str_imm
        address, results = 0x08071000, 0x20004A80
        a = Asm(address)
        a.emit(push, list(range(13)), lr=True)
        a.emit(raw, bytes.fromhex('eff30084'))
        a.emit(push, [4, 5])
        for n, (target, args) in enumerate(calls):
            for reg, value in enumerate(args):
                a.emit(movw, reg, value & 0xFFFF)
                a.emit(movt, reg, value >> 16)
            a.emit(bl, target)
            a.emit(movw, 3, (results+n*4) & 0xFFFF)
            a.emit(movt, 3, (results+n*4) >> 16)
            a.emit(str_imm, 0, 3)
        a.emit(pop, [4, 5])
        a.emit(raw, bytes.fromhex('84f3008c'))
        a.emit(pop, list(range(13)), lr=True)
        a.emit(b_w, pc)
        self.u.mem_write(address, a.assemble()[0])
        injected = []
        def inject(u, addr, size, data):
            if injected:
                return
            self.assertEqual(u.reg_read(base.UC_ARM_REG_PRIMASK), 0)
            injected.append(addr)
            u.reg_write(base.UC_ARM_REG_PC, address|1)
        self.u.hook_add(base.UC_HOOK_CODE, inject, begin=pc, end=pc)
        return injected, lambda: [self.read(results+n*4) for n in range(len(calls))]

    def test_native_stop_and_single_buffer_clock_stop_recover_all_closures(self):
        for mode in (0, 1):
            for count, usb in ((63, False), (64, False), (64, True)):
                with self.subTest(mode=mode, count=count, usb=usb):
                    self.setUp()
                    self.setup_recovery(mode)
                    self.seed_notes(count)
                    raw = bytes(self.u.mem_read(0x20010000, 0x29484))
                    if usb:
                        self.ingress.usb([15, 0xF8, 0, 0, 15, 0xFC, 0, 0])
                    else:
                        self.call(0x08033EAE, self.transport.root+0x0C, 0)
                    rounds = self.recovery.settle()
                    self.assertLessEqual(rounds, 12)
                    for messages in self.output.delivered:
                        self.assertEqual(sum(m[0] == 9 for m in messages), count)
                        self.assertEqual(sum(m[0] == 8 for m in messages), count)
                        self.assertEqual(sum(m[1] == 0xFC for m in messages), 1)
                        self.assertEqual(messages[-1], bytes([15, 0xFC, 0, 0]))
                        self.assertEqual(sum(m[1] == 0xF8 for m in messages), int(usb))
                    self.assertEqual(bytes(self.u.mem_read(0x20010000, 0x29484)), raw)
                    self.assertTrue(self.io_masks)
                    self.assertEqual(set(self.io_masks), {0})
                    self.recovery.check_canaries()

    def test_stall_deduplicates_off_and_rejects_new_on_and_clock_until_recovery(self):
        self.setup_recovery()
        p = self.recovery
        p.send(0, 0x90, 48, 96)
        p.poll()
        self.u.mem_write(self.output.drivers[0]+5, b'\x01')
        for _ in range(64):
            self.assertEqual(p.send(0, 0xF8), 1)
        for _ in range(128):
            self.assertEqual(p.send(0, 0x80, 48), 1)
        self.assertEqual(p.pending_off(0), 1)
        self.assertEqual(p.send(0, 0x90, 49, 96), 0)
        self.assertEqual(p.send(0, 0xF8), 0)
        for _ in range(12):
            p.poll()
        self.assertEqual(p.pending_off(0), 1)
        self.assertEqual(self.output.pending(0), 64)
        self.u.mem_write(self.output.drivers[0]+5, b'\x00')
        p.settle()
        messages = self.output.delivered[0]
        self.assertEqual(messages[0], bytes([9, 0x90, 48, 96]))
        self.assertEqual(messages[-2:], [bytes([8, 0x80, 48, 0]), bytes([15, 0xFC, 0, 0])])
        self.assertEqual(sum(m[1] == 0xF8 for m in messages), 64)
        self.assertEqual(len(messages), 67)
        self.assertEqual([p.flags(n) for n in range(3)], [recovery.FAULT, 0, 0])
        self.assertEqual(p.send(0, 0x90, 50, 96), 0)  # quarantine is sticky
        p.check_canaries()

    def test_full_channel_note_domain_is_bounded_and_drains_without_overwrite(self):
        self.setup_recovery()
        p = self.recovery
        for _ in range(64):
            p.send(0, 0xF8)
        raw = bytes(self.u.mem_read(0x20010000, 0x29484))
        for channel in range(16):
            for note in range(128):
                self.assertEqual(p.send(0, 0x80|channel, note), 1)
        self.assertEqual(p.pending_off(0), 2048)
        for channel in range(16):
            # NoteOn velocity0 is also a closing obligation; repeated Offs coalesce.
            self.assertEqual(p.send(0, 0x90|channel, 127, 0), 1)
        self.assertEqual(p.pending_off(0), 2048)
        rounds = p.settle(rounds=512)
        self.assertLessEqual(rounds, 275)
        offs = [tuple(m[1:3]) for m in self.output.delivered[0] if m[0] == 8]
        self.assertEqual(len(offs), 2048)
        self.assertEqual(set(offs), {(0x80|c, n) for c in range(16) for n in range(128)})
        self.assertEqual(self.output.delivered[0][-1], bytes([15, 0xFC, 0, 0]))
        self.assertEqual(bytes(self.u.mem_read(0x20010000, 0x29484)), raw)
        self.assertEqual(self.u.mem_read(p.entries[0]+recovery.BITMAP, 256), bytes(256))
        p.check_canaries()

    def test_masked_caller_defers_without_io_and_service_preserves_primask(self):
        self.setup_recovery()
        p = self.recovery
        self.io_masks.clear()
        self.u.reg_write(base.UC_ARM_REG_PRIMASK, 1)
        self.assertEqual(p.send(0, 0x8F, 127), 1)
        self.assertEqual(p.send(0, 0x9F, 127, 96), 0)
        self.assertEqual(p.poll(0), 0)
        self.assertEqual(self.u.reg_read(base.UC_ARM_REG_PRIMASK), 1)
        self.assertEqual(self.io_masks, [])
        self.assertEqual(p.pending_off(0), 1)
        self.u.reg_write(base.UC_ARM_REG_PRIMASK, 0)
        p.settle()
        self.assertEqual(self.output.delivered[0], [bytes([8, 0x8F, 127, 0]), bytes([15, 0xFC, 0, 0])])
        self.assertEqual(set(self.io_masks), {0})
        self.assertEqual(self.u.reg_read(base.UC_ARM_REG_PRIMASK), 0)

    def test_unknown_port_bad_magic_and_invalid_note_fail_closed(self):
        self.setup_recovery()
        p = self.recovery
        state = bytes(self.u.mem_read(recovery.STATE_BASE, recovery.STATE_SIZE))
        for port in (0, 0xFFFFFFFF, 0x20050000, 0x20001D60):
            self.assertEqual(self.call(p.labels['rp_send'], port, p.message), 0)
            self.assertEqual(self.call(p.labels['rp_poll'], port), 0)
        self.word(recovery.STATE_BASE, 0)
        self.assertEqual(p.send(0, 0x80, 48), 0)
        self.assertEqual(p.poll(0), 0)
        self.word(recovery.STATE_BASE, recovery.MAGIC)
        self.assertEqual(bytes(self.u.mem_read(recovery.STATE_BASE, recovery.STATE_SIZE)), state)
        self.call(p.labels['rp_fault'], p.entries[0])
        self.assertEqual(p.send(0, 0x80, 128), 0)
        self.assertEqual(p.pending_off(0), 0)
        self.assertEqual(self.u.mem_read(p.entries[0]+recovery.BITMAP, 256), bytes(256))
        self.assertEqual(p.flags(0), recovery.FAULT|recovery.STOP_PENDING)
        p.check_canaries()

    def test_never_ready_port_stays_native_and_disconnect_retains_faulted_fifo(self):
        self.setup_recovery()
        p = self.recovery
        self.u.mem_write(self.output.drivers[0]+4, b'\x00')
        self.assertEqual(p.send(0, 0x90, 48, 96), 0)
        self.assertEqual(p.send(0, 0x80, 48), 0)
        p.poll()
        self.assertEqual(p.flags(0), 0)
        self.u.mem_write(self.output.drivers[0]+4, b'\x01')
        p.send(0, 0x90, 48, 96)
        p.poll()
        for _ in range(64):
            p.send(0, 0xF8)
        p.send(0, 0x80, 48)
        self.u.mem_write(self.output.drivers[0]+4, b'\x00')
        for _ in range(12):
            p.poll()
        self.assertEqual(self.output.pending(0), 64)
        self.assertEqual(p.pending_off(0), 1)
        self.u.mem_write(self.output.drivers[0]+4, b'\x01')
        p.settle()
        self.assertEqual(self.output.delivered[0][-2:], [bytes([8, 0x80, 48, 0]), bytes([15, 0xFC, 0, 0])])

    def test_healthy_messages_preserve_exact_bytes_and_release_velocity(self):
        self.setup_recovery()
        p = self.recovery
        for port in range(3):
            self.assertEqual(p.send(port, 0x9F, 127, 96), 1)
            self.assertEqual(p.send(port, 0xF8), 1)
            self.assertEqual(p.send(port, 0x8F, 127, 37), 1)
            self.assertEqual(p.send(port, 0xFC), 1)
        p.poll()
        expected = [bytes([9, 0x9F, 127, 96]), bytes([15, 0xF8, 0, 0]),
                    bytes([8, 0x8F, 127, 37]), bytes([15, 0xFC, 0, 0])]
        self.assertEqual(self.output.delivered, [expected]*3)
        self.assertEqual([p.flags(n) for n in range(3)], [0]*3)

    def test_damaged_count_cursor_and_cached_invalid_pointer_do_not_escape_arena(self):
        self.setup_recovery()
        p = self.recovery
        self.word(p.entries[0], 0xFFFFFFFF)
        self.assertEqual(self.call(p.labels['rp_send'], 0xFFFFFFFF, p.message), 0)
        self.word(p.entries[0], self.output.ports[0])
        self.call(p.labels['rp_fault'], p.entries[0])
        self.u.mem_write(p.entries[0]+recovery.COUNT, (2049).to_bytes(2, 'little'))
        self.u.mem_write(p.entries[0]+recovery.CURSOR, b'\xFF')
        before = bytes(self.u.mem_read(p.entries[0]+recovery.BITMAP, 256))
        self.assertEqual(p.send(0, 0x80, 127), 0)
        self.assertEqual(p.poll(0), 1)
        self.assertEqual(p.pending_off(0), 2049)
        self.assertEqual(self.u.mem_read(p.entries[0]+recovery.BITMAP, 256), before)
        self.assertEqual(self.output.delivered[0], [])
        p.check_canaries()

    def test_native_usb_stall_and_din_running_status_recover_real_player_offs(self):
        self.setup_recovery(native=True)
        p, native = self.recovery, self.native
        wire = [bytearray(), bytearray()]
        def progress():
            p.poll()
            if native.in_flight is not None:
                native.release_usb_endpoint()
            for n in range(2):
                wire[n].extend(native.drain_uart(n))
        for t in range(8):
            for n in range(8):
                self.playback.step(t, n, 48+n, gate=96)
                progress()
        for _ in range(4):
            progress()
        self.assertEqual([self.output.pending(n) for n in range(3)], [0]*3)
        self.word(self.call(0x0803FD26, self.transport.transport, 0), 1)
        self.call(0x0803FE00, self.transport.transport)
        for _ in range(16):
            self.ingress.din([0xF8])
        p.poll()  # leave the actual USB endpoint in flight
        for n in range(2):
            wire[n].extend(native.drain_uart(n))
        self.assertEqual(native.usb_full(), 1)
        for _ in range(64):
            self.ingress.din([0xF8])
        self.call(0x08033EAE, self.transport.root+0x0C, 0)
        for _ in range(3):
            p.poll()
        self.assertEqual(p.pending_off(0), 64)
        self.assertEqual(self.output.pending(0), 64)
        for rounds in range(128):
            progress()
            if not any(p.pending(n) for n in range(3)) and native.in_flight is None:
                break
        else:
            self.fail('native USB/DIN recovery did not complete')
        on = [bytes([9, 0x90|t, 36+n, 96]) for t in range(8) for n in range(8)]
        off = [bytes([8, 0x80|t, 36+n, 0]) for t in range(8) for n in range(8)]
        expected_usb = b''.join(on+[bytes([15, 0xF8, 0, 0])]*80+off+[bytes([15, 0xFC, 0, 0])])
        self.assertEqual(b''.join(native.usb_completed), expected_usb)
        expected_din = b''.join(bytes([0x90|t])+b''.join(bytes([36+n, 96]) for n in range(8)) for t in range(8))
        expected_din += b'\xF8'*80
        expected_din += b''.join(bytes([0x80|t])+b''.join(bytes([36+n, 0]) for n in range(8)) for t in range(8))
        expected_din += b'\xFC'
        self.assertEqual([bytes(w) for w in wire], [expected_din]*2)
        self.assertEqual(set(self.io_masks), {0})
        p.check_canaries()

    def install_nested_send_trampoline(self, stop_phase):
        # Model preemption at a native enqueue boundary. This preserves CPU
        # context but is not an NVIC/exception-stack/real IRQ timing proof.
        from thumb_asm import Asm, b_w, bl, movw, movt, pop, push, raw
        p = self.recovery
        trampoline = 0x08071000
        a = Asm(trampoline)
        a.emit(push, list(range(13)), lr=True)  #56B
        a.emit(raw, bytes.fromhex('eff30084'))  # MRS r4,APSR
        a.emit(push, [4, 5])  #64B frame; native calls remain aligned8
        messages = [(0x80, 49, 0), (0x90, 50, 96), (0xF8, 0, 0)]
        if not stop_phase:
            messages.insert(0, (0x80, 48, 0))  # duplicate of in-flight Off
        for n, message in enumerate(messages):
            address = 0x20004FE0+n*4
            self.u.mem_write(address, bytes(message))
            for reg, value in ((0, self.output.ports[0]), (1, address)):
                a.emit(movw, reg, value & 0xFFFF)
                a.emit(movt, reg, value >> 16)
            a.emit(bl, p.labels['rp_send'])
        a.emit(pop, [4, 5])
        a.emit(raw, bytes.fromhex('84f3008c'))  # MSR APSR_NZCVQG,r4
        a.emit(pop, list(range(13)), lr=True)
        a.emit(b_w, recovery.NATIVE_SEND)
        self.u.mem_write(trampoline, a.assemble()[0])
        injected = []
        def inject(u, pc, size, data):
            if injected or u.reg_read(base.UC_ARM_REG_R0) != self.output.ports[0]:
                return
            status = u.mem_read(u.reg_read(base.UC_ARM_REG_R1), 1)[0]
            if status != (0xFC if stop_phase else 0x80):
                return
            injected.append((status, u.mem_read(p.entries[0]+recovery.BUSY, 1)[0]))
            u.reg_write(base.UC_ARM_REG_PC, trampoline|1)
        self.u.hook_add(base.UC_HOOK_CODE, inject, begin=recovery.NATIVE_SEND, end=recovery.NATIVE_SEND)
        return injected

    def test_nested_off_during_off_or_stop_keeps_new_closing_obligation(self):
        for stop_phase in (False, True):
            with self.subTest(stop_phase=stop_phase):
                self.setUp()
                self.setup_recovery()
                p = self.recovery
                p.send(0, 0x90, 48, 96)
                p.send(0, 0x90, 49, 96)
                p.poll()
                for _ in range(64):
                    p.send(0, 0xF8)
                p.send(0, 0x80, 48)
                injected = self.install_nested_send_trampoline(stop_phase)
                p.settle()
                self.assertEqual(injected, [(0xFC if stop_phase else 0x80, 1)])
                messages = self.output.delivered[0]
                self.assertEqual(sum(m[0] == 9 for m in messages), 2)
                self.assertEqual([m for m in messages if m[0] == 8],
                                 [bytes([8, 0x80, 48, 0]), bytes([8, 0x80, 49, 0])])
                self.assertEqual(messages[-1], bytes([15, 0xFC, 0, 0]))
                self.assertEqual(sum(m[1] == 0xFC for m in messages), 2 if stop_phase else 1)
                self.assertEqual(self.u.mem_read(p.entries[0]+recovery.BUSY, 1), b'\x00')
                self.assertEqual(set(self.io_masks), {0})
                p.check_canaries()

    def test_capstone_cfg_stack_and_explicit_irq_mask_budget(self):
        import tempfile
        from audit_midi_recovery_prototype import audit
        with tempfile.TemporaryDirectory() as directory:
            report = audit(directory)
        self.assertFalse(report['production_integrated'])
        self.assertEqual(report['ram_bytes'], 832)
        self.assertTrue(all(v['exit_sp_deltas'] == [0] for v in report['functions'].values()))
        self.assertLessEqual(max(v['max_instructions_until_restore'] for v in report['forced_mask_paths']), 16)
        for kwargs in ({'base': 0x08010000}, {'base': 0x0807FFFC},
                       {'state': 0x40023C00}, {'state': 0x1FFF0000},
                       {'state': 0x2004F660}, {'state': 0x20047001}):
            with self.subTest(bounds=kwargs), self.assertRaises(ValueError):
                recovery.arm_code(**kwargs)

    def test_poll_enqueues_at_most_eight_offs_per_port_pass(self):
        self.setup_recovery()
        p = self.recovery
        self.call(p.labels['rp_fault'], p.entries[0])
        self.u.mem_write(p.entries[0]+recovery.BITMAP, b'\xFF'*256)
        self.u.mem_write(p.entries[0]+recovery.COUNT, (2048).to_bytes(2, 'little'))
        attempts = []
        self.u.hook_add(base.UC_HOOK_CODE, lambda u,a,n,d: attempts.append(a),
                        begin=recovery.NATIVE_SEND, end=recovery.NATIVE_SEND)
        p.poll(0)
        self.assertEqual(len(attempts), 8)
        self.assertEqual(p.pending_off(0), 2040)
        attempts.clear()
        p.poll(0)
        self.assertEqual(len(attempts), 8)
        self.assertEqual(p.pending_off(0), 2032)
        p.check_canaries()

    def test_sysex_healthy_bytes_match_native_and_descriptor_is_not_retained(self):
        for size in (2, 3, 4, 5, 6, 47, 48, 49, 360):
            data = b'\xF0'+bytes(n % 128 for n in range(size-2))+b'\xF7'
            outcomes = []
            for hooked in (False, True):
                with self.subTest(size=size, hooked=hooked):
                    self.setUp()
                    self.setup_recovery(sysex=hooked)
                    p = self.recovery
                    desc = self.sysex_descriptor(data)
                    for port in range(3):
                        self.assertEqual(p.sysex_send(port, desc), 1)
                        self.assertEqual(p.sysex_pending(port), 1)
                    # Only the payload is borrowed. Overwrite the stack-like
                    # descriptor immediately; native workers never read it.
                    self.u.mem_write(desc, b'\xFF'*8)
                    p.settle()
                    self.assertEqual(self.output.delivered, [self.sysex_packets(data)]*3)
                    outcomes.append(self.output.delivered)
                    p.check_canaries()
            self.assertEqual(outcomes[0], outcomes[1])

    def test_sysex_fault_masked_busy_and_invalid_context_reject_without_borrow(self):
        self.setup_recovery()
        p = self.recovery
        desc = self.sysex_descriptor()
        for port in range(3):
            before = bytes(self.u.mem_read(self.output.ports[port], 24))
            self.u.reg_write(base.UC_ARM_REG_PRIMASK, 1)
            self.io_masks.clear()
            self.assertEqual(p.sysex_send(port, desc), 0)
            self.assertEqual(self.u.reg_read(base.UC_ARM_REG_PRIMASK), 1)
            self.assertEqual(self.io_masks, [])
            self.u.reg_write(base.UC_ARM_REG_PRIMASK, 0)
            self.u.mem_write(p.entries[port]+recovery.BUSY, b'\x01')
            self.assertEqual(p.sysex_send(port, 0xFFFFFFFF), 0)
            self.assertEqual(p.sysex_pending(port), 1)
            self.u.mem_write(p.entries[port]+recovery.BUSY, b'\x00')
            self.call(p.labels['rp_fault'], p.entries[port])
            self.assertEqual(p.sysex_send(port, 0xFFFFFFFF), 0)
            self.assertEqual(p.sysex_pending(port), 0)  # no borrowed payload
            self.assertEqual(bytes(self.u.mem_read(self.output.ports[port], 24)), before)
        for port in (0, 0xFFFFFFFF, 0x20050000, 0x20001D60):
            self.assertEqual(self.call(p.labels['rp_sysex_send'], port, 0xFFFFFFFF), 0)
            self.assertEqual(self.call(p.labels['rp_sysex_pending'], port), 1)
        self.word(recovery.STATE_BASE, 0)
        self.assertEqual(p.sysex_send(0, 0xFFFFFFFF), 0)
        self.assertEqual(p.sysex_pending(0), 1)
        self.word(recovery.STATE_BASE, recovery.MAGIC)
        p.settle()
        self.assertEqual(self.output.delivered, [[bytes([15, 0xFC, 0, 0])]]*3)
        p.check_canaries()

    def test_sysex_stall_has_one_service_attempt_and_preserves_borrowed_payload(self):
        self.setup_recovery()
        p = self.recovery
        first, second = self.sysex_descriptor(), self.sysex_descriptor(b'\xF0\x02\xF7', True)
        attempts = []
        self.u.hook_add(base.UC_HOOK_CODE, lambda u,a,n,d: attempts.append(a),
                        begin=recovery.NATIVE_POLL, end=recovery.NATIVE_POLL)
        for port in range(3):
            self.assertEqual(p.sysex_send(port, first), 1)
            original = bytes(self.u.mem_read(self.output.ports[port]+8, 12))
            self.u.mem_write(self.output.drivers[port]+5, b'\x01')
            attempts.clear()
            self.assertEqual(p.sysex_send(port, second), 0)
            self.assertEqual(len(attempts), 1)
            self.assertEqual(bytes(self.u.mem_read(self.output.ports[port]+8, 12)), original)
            self.u.mem_write(self.output.drivers[port]+4, b'\x00')
            # Native4028C lies about payload ownership when disconnected.
            self.assertEqual(self.call(recovery.NATIVE_PENDING, self.output.ports[port]), 0)
            self.assertEqual(p.sysex_pending(port), 1)
            p.poll(port)
            self.assertEqual(p.sysex_send(port, second), 0)
            self.assertEqual(bytes(self.u.mem_read(self.output.ports[port]+8, 12)), original)
            self.u.mem_write(self.output.drivers[port]+4, b'\x01')
            self.u.mem_write(self.output.drivers[port]+5, b'\x00')
        # Demonstrate the lifetime contract: changing still-borrowed payload
        # changes output. Caller must keep it immutable until pending clears.
        self.u.mem_write(first+16+4, b'\x03')
        p.settle()
        expected = self.sysex_packets(b'\xF0\x00\x20\x29\x03\xF7')+[bytes([15, 0xFC, 0, 0])]
        self.assertEqual(self.output.delivered, [expected]*3)
        p.check_canaries()

    def test_sysex_existing_ready_transfer_finishes_before_rebind(self):
        self.setup_recovery()
        p = self.recovery
        data = b'\xF0\x02\xF7'
        first, second = self.sysex_descriptor(), self.sysex_descriptor(data, True)
        for port in range(3):
            self.assertEqual(p.sysex_send(port, first), 1)
            self.assertEqual(p.sysex_send(port, second), 1)
        p.settle()
        self.assertEqual(self.output.delivered,
                         [self.sysex_packets(b'\xF0\x00\x20\x29\x01\xF7')+self.sysex_packets(data)]*3)
        p.check_canaries()

    def test_unhooked_sysex_wait_stalls_with_full_driver_or_naive_busy_wrapper(self):
        # Keep bounded emulator execution of the old infinite-wait hypothesis.
        # The instruction limit is a test escape, not a firmware timeout.
        for busy in (False, True):
            with self.subTest(naive_busy_wrapper=busy):
                self.setUp()
                self.setup_recovery(sysex=False)
                p = self.recovery
                first, second = self.sysex_descriptor(), self.sysex_descriptor(b'\xF0\x02\xF7', True)
                self.assertEqual(p.sysex_send(0, first), 1)
                if busy:
                    self.u.mem_write(p.entries[0]+recovery.BUSY, b'\x01')
                else:
                    self.u.mem_write(self.output.drivers[0]+5, b'\x01')
                attempts = []
                self.u.hook_add(base.UC_HOOK_CODE, lambda u,a,n,d: attempts.append(a),
                                begin=p.labels['rp_poll'], end=p.labels['rp_poll'])
                with self.assertRaisesRegex(AssertionError, 'instruction budget exhausted'):
                    p.sysex_send(0, second)
                self.assertGreater(len(attempts), 16)
                self.assertEqual(self.read(self.output.ports[0]+8), first+16)
                self.assertEqual(self.output.delivered[0], [])
                p.check_canaries()

    def test_sysex_nested_send_off_and_poll_do_not_deadlock_or_commit_after_fault(self):
        for pc in (0x0800EB00, recovery.NATIVE_POLL):
            with self.subTest(preemption=hex(pc)):
                self.setUp()
                self.setup_recovery()
                p = self.recovery
                first, second = self.sysex_descriptor(), self.sysex_descriptor(b'\xF0\x02\xF7', True)
                if pc == recovery.NATIVE_POLL:
                    self.assertEqual(p.sysex_send(0, first), 1)
                port = self.output.ports[0]
                self.u.mem_write(p.message, b'\x80\x30\x00')
                self.u.mem_write(0x20004AE0, b'\x90\x31\x60\x00\xF8\x00\x00')
                injected, results = self.install_nested_calls(pc, [
                    (p.labels['rp_sysex_send'], (port, second)),
                    (p.labels['rp_sysex_pending'], (port,)),
                    (p.labels['rp_poll'], (port,)),
                    (p.labels['rp_send'], (port, p.message)),
                    (p.labels['rp_send'], (port, 0x20004AE0)),
                    (p.labels['rp_send'], (port, 0x20004AE4)),
                ])
                self.assertEqual(p.sysex_send(0, second), 0)
                self.assertEqual(injected, [pc])
                self.assertEqual(results(), [0, 1, 0, 1, 0, 0])
                self.assertEqual(p.pending_off(0), 1)
                p.settle()
                expected = self.sysex_packets(b'\xF0\x00\x20\x29\x01\xF7') if pc == recovery.NATIVE_POLL else []
                expected += [bytes([8, 0x80, 48, 0]), bytes([15, 0xFC, 0, 0])]
                self.assertEqual(self.output.delivered[0], expected)
                self.assertEqual(p.flags(0), recovery.FAULT)
                self.assertEqual(set(self.io_masks), {0})
                p.check_canaries()

    def test_sysex_router_native_copy_return_contract_and_bounded_stall(self):
        for hooked in (False, True):
            with self.subTest(hooked=hooked):
                self.setUp()
                self.setup_recovery(sysex=hooked)
                self.setup_sysex_router()
                p = self.recovery
                desc = self.sysex_descriptor()
                second = self.sysex_descriptor(b'\xF0\x02\xF7', True)
                self.assertEqual(self.call(recovery.NATIVE_ROUTER, self.output.router, 7, desc), 0)
                self.assertEqual(self.route_callbacks, [(0x20004B60, 0)])
                for port in self.output.ports:
                    self.assertEqual(self.read(port+8), self.router_buffer)
                original = bytes(self.u.mem_read(self.router_buffer, 360))
                self.u.mem_write(desc+16, b'\x55'*6)  # source copied before return
                if hooked:
                    for driver in self.output.drivers:
                        self.u.mem_write(driver+5, b'\x01')
                    # Unhooked stock would spin here; new router returns1
                    # before memcpy, even though all selected ports are ready.
                    self.assertEqual(self.call(recovery.NATIVE_ROUTER, self.output.router, 7, second), 1)
                    self.assertEqual(bytes(self.u.mem_read(self.router_buffer, 360)), original)
                    self.assertEqual(len(self.route_callbacks), 1)
                    for driver in self.output.drivers:
                        self.u.mem_write(driver+5, b'\x00')
                p.settle()
                self.assertEqual(self.output.delivered, [self.sysex_packets(b'\xF0\x00\x20\x29\x01\xF7')]*3)
                self.assertEqual(self.call(recovery.NATIVE_ROUTER, self.output.router, 7, second), 0)
                p.settle()
                self.assertTrue(all(m[-1] == bytes([7, 0xF0, 2, 0xF7]) for m in self.output.delivered))
                self.assertEqual(self.u.mem_read(self.router_buffer-4, 4), b'STAR')
                self.assertEqual(self.u.mem_read(self.router_buffer+360, 4), b'LAST')
                p.check_canaries()

    def test_sysex_router_nested_copy_callback_and_faulted_fanout(self):
        for pc in (0x08022CF0, 0x0800EB10):
            with self.subTest(preemption=hex(pc)):
                self.setUp()
                self.setup_recovery()
                self.setup_sysex_router()
                p = self.recovery
                first, second = self.sysex_descriptor(), self.sysex_descriptor(b'\xF0\x02\xF7', True)
                injected, results = self.install_nested_calls(pc, [
                    (recovery.NATIVE_ROUTER, (self.output.router, 7, second))])
                self.assertEqual(self.call(recovery.NATIVE_ROUTER, self.output.router, 7, first), 0)
                self.assertEqual(injected, [pc])
                self.assertEqual(results(), [1])
                p.settle()
                self.assertEqual(self.output.delivered, [self.sysex_packets(b'\xF0\x00\x20\x29\x01\xF7')]*3)
                self.assertEqual(self.u.mem_read(recovery.STATE_BASE+recovery.ROUTER_BUSY, 1), b'\x00')
                for port in range(3):
                    self.call(p.labels['rp_fault'], p.entries[port])
                self.assertEqual(self.call(recovery.NATIVE_ROUTER, self.output.router, 7, second), 1)
                p.settle()
                self.assertTrue(all(len(messages) == 3 for messages in self.output.delivered))
                self.assertEqual(len(self.route_callbacks), 1)
                p.check_canaries()

    def test_sysex_router_bounds_mask_and_disconnected_payload_ownership(self):
        self.setup_recovery()
        self.setup_sysex_router()
        p = self.recovery
        desc, second = self.sysex_descriptor(), self.sysex_descriptor(b'\xF0\x02\xF7', True)
        for length in (0, 1, 361, 65536, 0xFFFFFFFF):
            self.word(desc+4, length)
            self.assertEqual(self.call(recovery.NATIVE_ROUTER, self.output.router, 7, desc), 1)
            self.assertEqual(self.u.mem_read(recovery.STATE_BASE+recovery.ROUTER_BUSY, 1), b'\x00')
        self.word(desc+4, 6)
        self.u.reg_write(base.UC_ARM_REG_PRIMASK, 1)
        self.assertEqual(self.call(recovery.NATIVE_ROUTER, self.output.router, 7, desc), 1)
        self.assertEqual(self.u.reg_read(base.UC_ARM_REG_PRIMASK), 1)
        self.u.reg_write(base.UC_ARM_REG_PRIMASK, 0)
        # Only port0 selected, yet router must protect payload borrowed by ANY port.
        self.assertEqual(self.call(recovery.NATIVE_ROUTER, self.output.router, 1, desc), 0)
        original = bytes(self.u.mem_read(self.router_buffer, 360))
        self.u.mem_write(self.output.drivers[0]+4, b'\x00')
        self.assertEqual(self.call(recovery.NATIVE_PENDING, self.output.ports[0]), 0)
        self.assertEqual(self.call(recovery.NATIVE_ROUTER, self.output.router, 6, second), 1)
        self.assertEqual(bytes(self.u.mem_read(self.router_buffer, 360)), original)
        p.poll(0)
        self.u.mem_write(self.output.drivers[0]+4, b'\x01')
        p.settle()
        self.assertEqual(self.output.delivered[0], self.sysex_packets(b'\xF0\x00\x20\x29\x01\xF7')+[bytes([15, 0xFC, 0, 0])])
        self.assertEqual(self.output.delivered[1:], [[], []])
        p.check_canaries()

    def test_sysex_reentry_during_recovery_and_extended_router_capacity(self):
        self.setup_recovery()
        self.setup_sysex_router()
        p = self.recovery
        desc = self.sysex_descriptor()
        self.call(p.labels['rp_fault'], p.entries[0])
        p.send(0, 0x80, 48)
        injected, results = self.install_nested_calls(recovery.NATIVE_SEND, [
            (p.labels['rp_sysex_send'], (self.output.ports[0], desc)),
            (recovery.NATIVE_ROUTER, (self.output.router, 1, desc)),
        ])
        p.settle()
        self.assertEqual(injected, [recovery.NATIVE_SEND])
        self.assertEqual(results(), [0, 1])
        self.assertEqual(self.output.delivered[0], [bytes([8, 0x80, 48, 0]), bytes([15, 0xFC, 0, 0])])
        # Native extended mode uses router+8 capacity, not the old standard360.
        self.word(self.output.router+8, 0x20004B80)
        self.word(0x20004B80, self.router_buffer)
        self.word(0x20004B84, 6)
        self.u.mem_write(self.output.router+0x24, b'\x01')
        self.word(desc+4, 7)
        original = bytes(self.u.mem_read(self.router_buffer, 360))
        self.assertEqual(self.call(recovery.NATIVE_ROUTER, self.output.router, 6, desc), 1)
        self.assertEqual(bytes(self.u.mem_read(self.router_buffer, 360)), original)
        self.word(desc+4, 6)
        self.assertEqual(self.call(recovery.NATIVE_ROUTER, self.output.router, 6, desc), 0)
        p.settle()
        self.assertEqual(self.output.delivered[1:], [self.sysex_packets(b'\xF0\x00\x20\x29\x01\xF7')]*2)
        callbacks = len(self.route_callbacks)
        # Native aggregate failure does not mean zero recipients: port0 is
        # faulted, while ports1/2 accept. A blind caller retry can duplicate.
        self.assertEqual(self.call(recovery.NATIVE_ROUTER, self.output.router, 7, desc), 1)
        original = bytes(self.u.mem_read(self.router_buffer, 360))
        self.assertEqual(self.call(recovery.NATIVE_ROUTER, self.output.router, 7, desc), 1)
        self.assertEqual(bytes(self.u.mem_read(self.router_buffer, 360)), original)
        self.assertEqual(len(self.route_callbacks), callbacks)
        p.settle()
        self.assertEqual(self.output.delivered[1:], [self.sysex_packets(b'\xF0\x00\x20\x29\x01\xF7')*2]*2)
        p.check_canaries()

    def test_native_usb_din_sysex_stalls_and_fault_preserve_bytes_then_off_stop(self):
        self.setup_recovery(native=True)
        p, native = self.recovery, self.native
        wire = [bytearray(), bytearray()]
        def progress(release=True):
            p.poll()
            if release and native.in_flight is not None:
                native.release_usb_endpoint()
            if release:
                for n in range(2):
                    wire[n].extend(native.drain_uart(n))
        for port in range(3):
            p.send(port, 0x90, 48, 96)
        progress()
        data = b'\xF0'+bytes(n % 128 for n in range(198))+b'\xF7'
        desc = self.sysex_descriptor(data)
        second = self.sysex_descriptor(b'\xF0\x02\xF7', True)
        raw_project = bytes(self.u.mem_read(0x20010000, 0x29484))
        for port in range(3):
            self.assertEqual(p.sysex_send(port, desc), 1)
        progress(release=False)
        self.assertEqual(native.usb_full(), 1)
        self.assertEqual([native.uart_full(n) for n in range(2)], [1, 1])
        for port in range(3):
            self.assertEqual(p.sysex_send(port, second), 0)
            self.assertEqual(p.sysex_pending(port), 1)
            for _ in range(64):
                self.assertEqual(p.send(port, 0xF8), 1)
            self.assertEqual(p.send(port, 0x80, 48), 1)
            self.assertEqual(p.sysex_send(port, second), 0)
            self.assertEqual(p.send(port, 0x90, 49, 96), 0)
        for _ in range(3):
            progress(release=False)
        self.assertEqual([p.pending_off(n) for n in range(3)], [1]*3)
        for _ in range(128):
            progress()
            if not any(p.pending(n) for n in range(3)) and native.in_flight is None:
                break
        else:
            self.fail('native SysEx/Off/Stop did not settle')
        expected = [bytes([9, 0x90, 48, 96])]+self.sysex_packets(data)
        expected += [bytes([15, 0xF8, 0, 0])]*64+[bytes([8, 0x80, 48, 0]), bytes([15, 0xFC, 0, 0])]
        self.assertEqual(b''.join(native.usb_completed), b''.join(expected))
        self.assertEqual([bytes(w) for w in wire], [b'\x90\x30\x60'+data+b'\xF8'*64+b'\x80\x30\x00\xFC']*2)
        self.assertEqual(set(self.io_masks), {0})
        self.assertEqual(bytes(self.u.mem_read(0x20010000, 0x29484)), raw_project)
        p.check_canaries()

    def test_unhooked_native_sysex_api_can_bypass_experimental_quarantine(self):
        # Keep the previous negative control; explicitly omit new SysEx hooks.
        self.setup_recovery(sysex=False)
        p = self.recovery
        self.call(p.labels['rp_fault'], p.entries[0])
        payload, descriptor = 0x20004B00, 0x20004B20
        self.u.mem_write(payload, bytes([0xF0, 0, 0x20, 0x29, 1, 0xF7]))
        self.word(descriptor, payload)
        self.word(descriptor+4, 6)
        self.assertEqual(self.call(0x08040232, self.output.ports[0], descriptor), 1)
        p.settle()
        self.assertEqual(self.output.delivered[0][:2],
                         [bytes([4, 0xF0, 0, 0x20]), bytes([7, 0x29, 1, 0xF7])])
        self.assertEqual(p.flags(0), recovery.FAULT)


if __name__ == '__main__':
    unittest.main()
