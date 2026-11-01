"""Owned retry ledger experiment; no production/router-callback acceptance."""
import unittest
import test_midi_recovery_prototype as prior
import midi_recovery_prototype as recovery
import midi_sysex_retry_prototype as retry
from midi_sysex_retry_test_support import SysexRetryFixture, CALLERS, caller_args

base = prior.base


class SysexRetryTests(unittest.TestCase):
    setUpClass = classmethod(prior.MidiRecoveryPrototypeTests.setUpClass.__func__)
    setUp = prior.MidiRecoveryPrototypeTests.setUp
    word = prior.MidiRecoveryPrototypeTests.word
    read = prior.MidiRecoveryPrototypeTests.read
    store = prior.MidiRecoveryPrototypeTests.store
    call = prior.MidiRecoveryPrototypeTests.call
    setup_playback = prior.MidiRecoveryPrototypeTests.setup_playback
    setup_recovery = prior.MidiRecoveryPrototypeTests.setup_recovery
    setup_sysex_router = prior.MidiRecoveryPrototypeTests.setup_sysex_router
    sysex_descriptor = prior.MidiRecoveryPrototypeTests.sysex_descriptor
    sysex_packets = staticmethod(prior.MidiRecoveryPrototypeTests.sysex_packets)
    install_nested_calls = prior.MidiRecoveryPrototypeTests.install_nested_calls

    def setup_retry(self, native=False):
        self.setup_recovery(native=native)
        self.setup_sysex_router()
        self.retry = SysexRetryFixture(self)

    def test_all_twelve_real_callers_return_or_discard_without_retry(self):
        for entry, site, lifetime, behavior in CALLERS:
            results = []
            for injected in (0, 1):
                with self.subTest(entry=hex(entry), result=injected):
                    self.setUp()
                    self.setup_retry()
                    args = caller_args(self, entry)
                    self.retry.capture_native_callers(forced_result=injected)
                    result = self.call(entry, *args)
                    self.assertEqual(len(self.retry.captured), 1)
                    self.assertEqual(self.retry.captured[0]['router'], self.output.router)
                    results.append(result)
                    self.retry.check_canaries()
            if behavior == 'discard':
                self.assertEqual(results[0], results[1], hex(entry))
            else:
                self.assertEqual(results, [0, 1], hex(entry))

    def test_all_caller_payloads_are_owned_before_stack_or_source_dies(self):
        for entry, site, lifetime, behavior in CALLERS:
            with self.subTest(entry=hex(entry), lifetime=lifetime):
                self.setUp()
                self.setup_retry()
                args = caller_args(self, entry)
                self.retry.capture_native_callers()
                for driver in self.output.drivers:
                    self.u.mem_write(driver+4, b'\x00')
                self.call(entry, *args)
                self.assertEqual(len(self.retry.captured), 1)
                captured = self.retry.captured[0]
                expected, mask = captured['payload'], captured['mask'] & 7
                self.assertEqual(self.retry.status()['waiting'], mask)
                self.assertEqual(self.u.mem_read(retry.STATE_BASE+retry.PAYLOAD, len(expected)), expected)
                if lifetime != 'flash':
                    self.u.mem_write(captured['pointer'], b'\xCC'*len(expected))
                self.u.mem_write(captured['descriptor'], b'\xDD'*8)
                self.u.mem_write(0x2003F000, b'\xA5'*0x1000)
                for _ in range(3):
                    self.retry.poll()
                self.assertEqual(self.retry.status()['waiting'], mask)
                for driver in self.output.drivers:
                    self.u.mem_write(driver+4, b'\x01')
                self.retry.settle()
                self.assertEqual(self.output.delivered, [self.sysex_packets(expected) if mask & (1 << n) else [] for n in range(3)])
                self.assertEqual(self.route_callbacks, [])  # no fabricated native callback
                self.retry.check_canaries()

    def test_partial_admission_retries_only_waiting_ports_and_never_duplicates(self):
        self.setup_retry()
        q = self.retry
        desc = self.sysex_descriptor()
        data = bytes(self.u.mem_read(desc+16, 6))
        self.u.mem_write(self.output.drivers[1]+4, b'\x00')
        self.assertEqual(q.submit(desc), 0)
        attempts = []
        self.u.hook_add(base.UC_HOOK_CODE, lambda u,a,n,d: attempts.append(u.reg_read(base.UC_ARM_REG_R0)),
                        begin=self.recovery.labels['rp_sysex_send'], end=self.recovery.labels['rp_sysex_send'])
        for _ in range(8):
            attempts.clear()
            q.poll()
            self.assertLessEqual(len(attempts), 3)
            self.assertEqual(len(attempts), len(set(attempts)))
        self.assertEqual(q.status()['waiting'], 2)
        self.assertEqual(q.status()['accepted'], 5)
        self.assertEqual(self.output.delivered, [self.sysex_packets(data), [], self.sysex_packets(data)])
        self.u.mem_write(self.output.drivers[1]+4, b'\x01')
        q.settle()
        self.assertEqual(self.output.delivered, [self.sysex_packets(data)]*3)
        self.assertEqual(q.status(), dict(active=0, waiting=0, accepted=7, failed=0, errors=0, busy=0))
        q.check_canaries()

    def test_full_slot_is_rejected_and_preserved_until_all_readers_finish(self):
        self.setup_retry()
        q = self.retry
        first, second = self.sysex_descriptor(), self.sysex_descriptor(b'\xF0\x02\xF7', True)
        self.assertEqual(q.submit(first), 0)
        q.service()
        for driver in self.output.drivers:
            self.u.mem_write(driver+5, b'\x01')
        before = bytes(self.u.mem_read(retry.STATE_BASE+retry.DESCRIPTOR, retry.STATE_SIZE-retry.DESCRIPTOR))
        for _ in range(8):
            self.assertEqual(q.submit(second), 1)
            q.poll()
        self.assertEqual(bytes(self.u.mem_read(retry.STATE_BASE+retry.DESCRIPTOR, retry.STATE_SIZE-retry.DESCRIPTOR)), before)
        self.assertEqual(q.status()['accepted'], 7)
        self.assertEqual(q.status()['active'], 1)
        self.assertEqual(q.status()['errors'], retry.REJECTED)
        for driver in self.output.drivers:
            self.u.mem_write(driver+5, b'\x00')
        q.settle()
        self.assertEqual(q.submit(second), 0)
        q.settle()
        self.assertEqual(self.output.delivered, [self.sysex_packets(b'\xF0\x00\x20\x29\x01\xF7')+self.sysex_packets(b'\xF0\x02\xF7')]*3)
        q.check_canaries()

    def test_faulted_admission_and_mid_transaction_fault_pin_obligation(self):
        self.setup_retry()
        q = self.retry
        desc = self.sysex_descriptor()
        self.u.mem_write(self.output.drivers[1]+4, b'\x00')
        self.assertEqual(q.submit(desc), 0)
        q.poll()
        self.call(self.recovery.labels['rp_fault'], self.recovery.entries[1])
        for _ in range(4):
            q.poll()
        self.assertEqual(q.status()['waiting'], 2)
        self.assertEqual(q.status()['failed'], 2)
        self.assertEqual(q.status()['accepted'], 5)
        self.assertEqual(q.status()['errors'], retry.PORT_FAULT)
        self.assertEqual(q.submit(desc), 1)
        q.check_canaries()
        # A fresh empty queue must not accept a new transaction for a faulted port.
        self.setUp()
        self.setup_retry()
        desc = self.sysex_descriptor()
        self.call(self.recovery.labels['rp_fault'], self.recovery.entries[0])
        self.assertEqual(self.retry.submit(desc, 1), 1)
        self.assertEqual(self.retry.status()['active'], 0)

    def test_nested_submit_and_service_preserve_payload_and_do_not_issue_io(self):
        for pc in (retry.NATIVE_COPY, 'port_send'):
            with self.subTest(boundary=pc):
                self.setUp()
                self.setup_retry()
                q = self.retry
                first, second = self.sysex_descriptor(), self.sysex_descriptor(b'\xF0\x02\xF7', True)
                if pc == 'port_send':
                    self.assertEqual(q.submit(first), 0)
                    pc = self.recovery.labels['rp_sysex_send']
                injected, results = self.install_nested_calls(pc, [
                    (q.labels['sr_submit'], (self.output.router, 7, second)),
                    (q.labels['sr_service'], (self.output.router,)),
                ])
                if pc == retry.NATIVE_COPY:
                    self.assertEqual(q.submit(first), 0)
                q.settle()
                self.assertEqual(injected, [pc])
                self.assertEqual(results(), [1, 0])
                self.assertEqual(q.status()['errors'], retry.REENTRANT)
                self.assertEqual(self.output.delivered, [self.sysex_packets(b'\xF0\x00\x20\x29\x01\xF7')]*3)
                self.assertEqual(set(self.io_masks), {0})
                q.check_canaries()

    def test_bad_inputs_metadata_and_masked_caller_fail_closed(self):
        self.setup_retry()
        q = self.retry
        for data in (b'', b'\xF0', b'\xF0'+b'\x00'*359+b'\xF7', b'\x01\xF7', b'\xF0\x01', b'\xF0\x80\xF7'):
            self.assertEqual(q.submit(self.sysex_descriptor(data)), 1)
            self.assertEqual(q.status()['active'], 0)
        desc = self.sysex_descriptor()
        self.assertEqual(q.submit(desc, 0), 1)
        self.u.reg_write(base.UC_ARM_REG_PRIMASK, 1)
        self.io_masks.clear()
        self.assertEqual(q.submit(desc), 1)
        self.assertEqual(q.service(), 0)
        self.assertEqual(self.io_masks, [])
        self.assertEqual(self.u.reg_read(base.UC_ARM_REG_PRIMASK), 1)
        self.u.reg_write(base.UC_ARM_REG_PRIMASK, 0)
        self.assertEqual(self.call(q.labels['sr_submit'], 0xFFFFFFFF, 7, 0xFFFFFFFF), 1)
        self.word(retry.STATE_BASE, 0)
        self.assertEqual(q.submit(0xFFFFFFFF), 1)
        self.word(retry.STATE_BASE, retry.MAGIC)
        for offset, data in [(retry.ACTIVE,b'\xFF'),(retry.WAITING,b'\xFF'),(retry.ACCEPTED,b'\x01'),
                             (retry.FAILED,b'\x80'),(retry.DESCRIPTOR,b'\xFF'*4),
                             (retry.DESCRIPTOR+4,(361).to_bytes(4,'little'))]:
            self.u.mem_write(retry.STATE_BASE+retry.ACTIVE, b'\x00')  # fixture reset, never runtime recovery
            self.assertEqual(q.submit(desc), 0)
            self.u.mem_write(retry.STATE_BASE+retry.ERRORS, b'\x00')
            self.u.mem_write(retry.STATE_BASE+offset, data)
            self.io_masks.clear()
            q.service()
            self.assertTrue(q.status()['errors'] & retry.BAD_STATE)
            self.assertEqual(self.io_masks, [])
        self.assertEqual(self.output.delivered, [[],[],[]])
        q.check_canaries()

    def test_native_usb_din_stall_owned_max_payload_and_safe_slot_reuse(self):
        self.setup_retry(native=True)
        q, p, native = self.retry, self.recovery, self.native
        wire = [bytearray(), bytearray()]
        raw_project = bytes(self.u.mem_read(0x20010000, 0x29484))
        previous = b'\xF0'+bytes(n % 128 for n in range(198))+b'\xF7'
        payload = b'\xF0'+bytes((n+1) % 128 for n in range(358))+b'\xF7'
        old_desc = self.sysex_descriptor(previous)
        desc = self.sysex_descriptor(payload, True)
        for port in range(3):
            self.assertEqual(p.sysex_send(port, old_desc), 1)
        p.poll()
        self.assertEqual(native.usb_full(), 1)
        self.assertEqual([native.uart_full(n) for n in range(2)], [1, 1])
        self.assertEqual(q.submit(desc), 0)
        self.u.mem_write(desc+16, b'\xDD'*len(payload))
        for _ in range(8):
            q.poll()
        self.assertEqual(q.status()['waiting'], 7)
        self.assertEqual(q.status()['accepted'], 0)
        added = False
        for _ in range(128):
            q.poll()
            if not q.status()['active'] and not added:
                # Copy ownership can end before wire completion. Native USB
                # staging owns its own bytes, checked by release_usb_endpoint.
                self.assertIsNotNone(native.in_flight)
                self.assertEqual(q.submit(self.sysex_descriptor(b'\xF0\x05\xF7')), 0)
                added = True
            if native.in_flight is not None:
                native.release_usb_endpoint()
            for n in range(2):
                wire[n].extend(native.drain_uart(n))
            if added and not q.status()['active'] and not any(p.pending(n) for n in range(3)):
                break
        else:
            self.fail('native queue transaction did not settle')
        expected = previous+payload+b'\xF0\x05\xF7'
        self.assertEqual([bytes(w) for w in wire], [expected]*2)
        packets = self.sysex_packets(previous)+self.sysex_packets(payload)+self.sysex_packets(b'\xF0\x05\xF7')
        self.assertEqual(b''.join(native.usb_completed), b''.join(packets))
        self.assertEqual(bytes(self.u.mem_read(0x20010000, 0x29484)), raw_project)
        self.assertEqual(set(self.io_masks), {0})
        q.check_canaries()

    def test_ignored_failure_still_loses_response_when_owned_slot_is_full(self):
        # Negative acceptance evidence: finite buffering alone is insufficient.
        for entry, site, lifetime, behavior in CALLERS:
            if behavior != 'discard':
                continue
            with self.subTest(entry=hex(entry)):
                self.setUp()
                self.setup_retry()
                q = self.retry
                desc = self.sysex_descriptor()
                first = bytes(self.u.mem_read(desc+16, 6))
                self.assertEqual(q.submit(desc), 0)
                args = caller_args(self, entry)
                q.capture_native_callers()
                self.call(entry, *args)
                self.assertEqual(len(q.captured), 1)
                self.assertTrue(q.status()['errors'] & retry.REJECTED)
                q.settle()
                self.assertEqual(self.output.delivered, [self.sysex_packets(first)]*3)
                q.check_canaries()

    def test_general_adapter_overwrites_callback_owner_before_queue_rejection(self):
        # Negative lifecycle evidence; NEVER claim the explicit API is a native
        # router replacement. The global callback belongs to the wrong request.
        self.setup_retry()
        q = self.retry
        desc = self.sysex_descriptor()
        q.capture_native_callers()
        callback_a, callback_b = 0x0800EB20, 0x0800EB24
        self.u.mem_write(callback_a, bytes.fromhex('11207047'))
        self.u.mem_write(callback_b, bytes.fromhex('22207047'))
        self.assertEqual(self.call(0x0804691A, 1, desc, callback_a|1, 0xAABB), 0)
        self.assertEqual(self.read(0x20006EE0), callback_a|1)
        self.assertEqual(self.call(0x0804691A, 1, desc, callback_b|1, 0xCCDD), 1)
        self.assertEqual(self.read(0x20006EE0), callback_b|1)
        args = []
        self.u.hook_add(base.UC_HOOK_CODE, lambda u,a,n,d: args.append(
            (u.reg_read(base.UC_ARM_REG_R0), u.reg_read(base.UC_ARM_REG_R1))),
            begin=callback_b, end=callback_b)
        self.assertEqual(self.call(0x080468EC, 1), 0x22)
        self.assertEqual(args, [(1, 0xCCDD)])
        q.settle()
        self.assertEqual(len(q.captured), 2)
        self.assertEqual(self.output.delivered, [self.sysex_packets(b'\xF0\x00\x20\x29\x01\xF7')]*1+[[],[]])
        q.check_canaries()

    def test_guarded_caller_entries_preserve_all_healthy_payloads_and_results(self):
        for entry, site, lifetime, behavior in CALLERS:
            outcomes = []
            for guarded in (False, True):
                with self.subTest(entry=hex(entry), guarded=guarded):
                    self.setUp()
                    self.setup_retry()
                    q = self.retry
                    if guarded:
                        q.install_producer_guards()
                    args = caller_args(self, entry)
                    q.capture_native_callers()
                    value = self.call(entry, *args)
                    self.assertEqual(len(q.captured), 1)
                    outcomes.append((value, q.captured[0]['payload'], q.captured[0]['mask']))
                    q.settle()
                    self.assertEqual(self.u.mem_read(retry.STATE_BASE+retry.PRODUCER_BUSY, 1), b'\x00')
                    q.check_canaries()
            self.assertEqual(outcomes[0], outcomes[1])

    def test_producer_guard_prevents_nested_formatter_source_overwrite(self):
        for guarded in (False, True):
            with self.subTest(guarded=guarded):
                self.setUp()
                self.setup_retry()
                q = self.retry
                if guarded:
                    q.install_producer_guards()
                q.capture_native_callers()
                self.u.mem_write(0x20006100, b'\x01\x02\x03\x04')
                injected, results = self.install_nested_calls(q.labels['submit_copy'], [
                    (0x0802CBB8, (0x41, 0x20006102, 2))])
                self.assertEqual(self.call(0x0802CBB8, 0x40, 0x20006100, 2), 0)
                self.assertEqual(results(), [1])
                self.assertEqual(len(injected), 1)
                self.assertEqual(len(q.captured), 1 if guarded else 2)
                first = q.captured[0]['payload']
                owned = bytes(self.u.mem_read(retry.STATE_BASE+retry.PAYLOAD, len(first)))
                if guarded:
                    self.assertEqual(owned, first)
                else:
                    self.assertNotEqual(owned, first)  # retained negative control
                    self.assertEqual(owned, q.captured[1]['payload'])
                q.settle()
                self.assertEqual(self.output.delivered, [self.sysex_packets(owned), [], []])
                q.check_canaries()

    def test_producer_guard_rejects_before_global_callback_owner_is_overwritten(self):
        self.setup_retry()
        q = self.retry
        q.install_producer_guards()
        q.capture_native_callers()
        desc = self.sysex_descriptor()
        self.assertEqual(self.call(0x0804691A, 1, desc, 0x0800EB21, 0xAABB), 0)
        before = bytes(self.u.mem_read(0x20006EE0, 8))
        self.assertEqual(self.call(0x0804691A, 1, desc, 0x0800EB25, 0xCCDD), 1)
        self.assertEqual(bytes(self.u.mem_read(0x20006EE0, 8)), before)
        self.assertEqual(len(q.captured), 1)
        self.assertEqual(q.status()['errors'], retry.REJECTED)
        q.settle()
        self.assertEqual(self.route_callbacks, [])  # native completion policy still open
        q.check_canaries()

    def test_irq_masked_producer_and_local_code_bounds_cfg_audit(self):
        import tempfile
        from audit_midi_sysex_retry_prototype import audit
        self.setup_retry()
        q = self.retry
        q.install_producer_guards()
        q.capture_native_callers()
        desc = self.sysex_descriptor()
        before = bytes(self.u.mem_read(0x20006EE0, 8))
        self.io_masks.clear()
        self.u.reg_write(base.UC_ARM_REG_PRIMASK, 1)
        self.assertEqual(self.call(0x0804691A, 1, desc, 0x0800EB21, 0xAA), 1)
        self.assertEqual(self.u.reg_read(base.UC_ARM_REG_PRIMASK), 1)
        self.assertEqual(self.io_masks, [])
        self.assertEqual(bytes(self.u.mem_read(0x20006EE0, 8)), before)
        self.u.reg_write(base.UC_ARM_REG_PRIMASK, 0)
        self.word(0x20006F04, 0)
        self.assertEqual(self.call(0x0804691A, 1, desc, 0x0800EB21, 0xAA), 1)
        self.assertEqual(bytes(self.u.mem_read(0x20006EE0, 8)), before)
        self.assertEqual(q.captured, [])
        q.check_canaries()
        with tempfile.TemporaryDirectory() as directory:
            report = audit(directory)
        self.assertEqual(report['max_admission_attempts_per_service'], 3)
        self.assertEqual(report['combined_synthetic_ram_bytes'], 1216)
        self.assertEqual(len(report['emulator_producer_overlays']), 12)
        self.assertLessEqual(report['max_forced_mask_instructions'], 16)
        for kwargs in ({'base': recovery.CODE_BASE}, {'base': 0x0807FFFC},
                       {'state': recovery.STATE_BASE}, {'state': 0x2004F660},
                       {'state': 0x20047801}, {'state': 0x40000000}):
            with self.subTest(bounds=kwargs), self.assertRaises(ValueError):
                retry.arm_code(**kwargs)


if __name__ == '__main__':
    unittest.main()
