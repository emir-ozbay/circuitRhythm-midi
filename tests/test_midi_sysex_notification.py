"""Optional owned ADMISSION notification, not physical completion or release GO."""
import tempfile
import unittest

import test_midi_sysex_retry_prototype as prior
import midi_sysex_retry_prototype as retry
from midi_sysex_retry_test_support import SysexRetryFixture, CALLERS, caller_args
from trace_midi_sysex_notification import trace

base = prior.base


class SysexNotificationTests(unittest.TestCase):
    setUpClass = classmethod(prior.SysexRetryTests.setUpClass.__func__)
    setUp = prior.SysexRetryTests.setUp
    word = prior.SysexRetryTests.word
    read = prior.SysexRetryTests.read
    store = prior.SysexRetryTests.store
    call = prior.SysexRetryTests.call
    setup_playback = prior.SysexRetryTests.setup_playback
    setup_recovery = prior.SysexRetryTests.setup_recovery
    setup_sysex_router = prior.SysexRetryTests.setup_sysex_router
    sysex_descriptor = prior.SysexRetryTests.sysex_descriptor
    sysex_packets = staticmethod(prior.SysexRetryTests.sysex_packets)
    install_nested_calls = prior.SysexRetryTests.install_nested_calls

    def setup_notice(self, enabled=True, native=False, overlay=True):
        self.setup_recovery(native=native)
        self.setup_sysex_router()
        self.word(self.output.router+0x20, retry.NATIVE_EVENT)
        self.u.mem_write(retry.NATIVE_EVENT, bytes(32))
        self.word(retry.NATIVE_EVENT, retry.NATIVE_EVENT_VTABLE)
        self.q = SysexRetryFixture(self, notifications=enabled)
        if overlay:
            self.q.capture_native_callers()
            self.q.install_producer_guards()
        self.events = []
        for index, pc in enumerate((0x0800EB20, 0x0800EB24, 0x0800EB28)):
            self.u.mem_write(pc, bytes.fromhex('00bf7047'))
            # Hook must not reenter u.emu_start; pending read is direct below.
            def capture(u, a, n, d, index=index):
                pending = []
                for port in self.output.ports:
                    counters = self.read(port+0x10)
                    pending.append(bytes(u.mem_read(counters, 2)) != bytes(u.mem_read(counters+2, 2)))
                self.events.append((index, u.reg_read(base.UC_ARM_REG_R0),
                                    u.reg_read(base.UC_ARM_REG_R1), u.reg_read(base.UC_ARM_REG_R2), pending))
            self.u.hook_add(base.UC_HOOK_CODE, capture, begin=pc+2, end=pc+2)

    def send(self, callback=0x0800EB21, context=0xAABB, mask=7, desc=None):
        return self.call(0x0804691A, mask, desc or self.sysex_descriptor(), callback, context)

    def test_stock_scatter_load_and_synchronous_accept_notification(self):
        with tempfile.TemporaryDirectory() as out:
            report = trace(out)
        self.assertEqual(report['vtable'], ['0x802d44d', '0x8024b69'])
        self.setup_notice(overlay=False)
        self.assertEqual(self.send(), 0)
        self.assertEqual(len(self.events), 1)
        self.assertEqual(self.events[0][:4], (0, 0, 0xAABB, 0x0800EB21))
        self.assertEqual(self.events[0][4], [True]*3)
        for _ in range(4):
            self.call(0x080297DE, self.output.router)
        self.assertEqual(len(self.events), 1)
        self.assertEqual(self.u.mem_read(self.output.router+0x19, 1), b'\x01')

    def test_optional_extension_preserves_baseline_code_and_snapshot_bounds(self):
        import hashlib
        self.assertEqual(hashlib.sha256(retry.arm_code()[0]).hexdigest(),
                         'ae8d859e129a72bb02e6e6916ac7ca6a256b30dc6699ff612eacc84ae617b266')
        with self.assertRaises(ValueError):
            retry.arm_code(state=0x2004F660-retry.STATE_SIZE, notifications=True)
        self.setup_notice()
        self.assertEqual(self.send(), 0)
        self.q.settle()
        self.assertEqual([e[:4] for e in self.events], [(0, 0, 0xAABB, 0x0800EB21)])
        self.assertEqual(self.u.mem_read(retry.STATE_BASE+retry.NOTICE, 1), b'\x03')
        self.q.check_canaries()

    def test_legacy_queue_negative_control_omits_native_admission_notification(self):
        self.setup_notice(enabled=False)
        self.assertEqual(self.send(), 0)
        self.q.settle()
        self.assertEqual(self.events, [])
        self.assertTrue(all(self.output.delivered))
        self.q.check_canaries()

    def test_all_twelve_caller_payloads_and_returns_match_legacy_queue(self):
        for entry, site, lifetime, behavior in CALLERS:
            outcomes = []
            for enabled in (False, True):
                self.setUp()
                self.setup_notice(enabled=enabled)
                args = caller_args(self, entry)
                value = self.call(entry, *args)
                captured = self.q.captured[-1]
                outcomes.append((value, captured['mask'], captured['payload']))
                self.q.settle()
                self.assertEqual(self.output.delivered,
                                 [self.sysex_packets(captured['payload']) if captured['mask'] & (1 << p) else []
                                  for p in range(3)])
                self.assertEqual(len(self.events), int(enabled and entry == 0x0804691A))
                self.q.check_canaries()
            self.assertEqual(outcomes[0], outcomes[1], hex(entry))

    def test_snapshot_owner_and_listener_registry_survive_later_mutation(self):
        self.setup_notice()
        self.assertEqual(self.send(), 0)
        # Emulated unrelated writes after admission cannot redirect the owned
        # event. This is not proof of all production writers/IRQ ordering.
        self.word(retry.NATIVE_OWNER, 0x0800EB25)
        self.word(retry.NATIVE_OWNER+4, 0xCCDD)
        self.u.mem_write(retry.NATIVE_EVENT+4, b'\x00')
        self.word(retry.NATIVE_EVENT+8, 0)
        self.q.settle()
        self.assertEqual([e[:3] for e in self.events], [(0, 0, 0xAABB)])
        self.q.check_canaries()

    def test_partial_admission_waits_and_notifies_once_before_payload_drain(self):
        self.setup_notice()
        self.u.mem_write(self.output.drivers[1]+4, b'\x00')
        self.assertEqual(self.send(), 0)
        for _ in range(4):
            self.q.poll()
        self.assertEqual(self.events, [])
        self.assertEqual(self.q.status()['waiting'], 2)
        self.u.mem_write(self.output.drivers[1]+4, b'\x01')
        self.q.service()
        self.assertEqual(len(self.events), 1)
        self.assertTrue(self.events[0][4][1])
        self.assertEqual(self.q.status()['active'], 1)
        self.assertEqual(self.send(0x0800EB25, 0xCCDD), 1)
        self.q.settle()
        self.assertEqual(len(self.events), 1)
        self.assertEqual(self.send(0x0800EB25, 0xCCDD), 0)
        self.q.settle()
        self.assertEqual([e[:3] for e in self.events], [(0, 0, 0xAABB), (1, 0, 0xCCDD)])
        self.q.check_canaries()

    def test_native_multicast_context_order_null_owner_and_empty_event(self):
        for listeners, callback in ((0, 0), (1, 0), (3, 0x0800EB21)):
            # Direct submissions preserve a native registry built BEFORE the
            # snapshot, including other listeners and an absent owner function.
            self.setUp()
            self.setup_notice()
            self.u.mem_write(retry.NATIVE_EVENT+4, bytes([listeners]))
            self.word(retry.NATIVE_EVENT+8, retry.NATIVE_OWNER_ADAPTER)
            self.word(retry.NATIVE_OWNER, callback)
            self.word(retry.NATIVE_OWNER+4, 0xAABB)
            for n in (1, 2):
                self.word(retry.NATIVE_EVENT+8+n*4, 0x0800EB21+n*4)
                self.word(retry.NATIVE_EVENT+0x14+n*4, 0x100+n)
            self.assertEqual(self.q.submit(self.sysex_descriptor()), 0)
            self.q.settle()
            self.assertEqual(len(self.events), 0 if listeners < 3 else 3)
            if listeners == 3:
                self.assertEqual([e[:3] for e in self.events],
                                 [(0, 0, 0xAABB), (1, 0, self.output.router), (2, 0, self.output.router)])
                self.assertEqual([e[3] for e in self.events[1:]], [0x101, 0x102])
            self.q.check_canaries()

    def test_callback_reentry_cannot_reuse_slot_or_replay_notification(self):
        self.setup_notice()
        self.assertEqual(self.send(), 0)
        desc = self.sysex_descriptor(b'\xF0\x02\xF7', True)
        injected, results = self.install_nested_calls(self.q.labels['owned_callback_call'], [
            *[(self.recovery.labels['rp_poll'], (port,)) for port in self.output.ports],
            (0x0804691A, (7, desc, 0x0800EB25, 0xCCDD)),
            (self.q.labels['sr_service'], (self.output.router,)),
            (self.q.labels['sr_submit'], (self.output.router, 7, desc)),
        ])
        self.q.settle()
        self.assertEqual(len(injected), 1)
        self.assertEqual(results()[-3:], [1, 0, 1])
        self.assertEqual([e[:3] for e in self.events], [(0, 0, 0xAABB)])
        self.assertEqual(self.events[0][4], [False]*3)  # readers ended inside callback window
        self.assertEqual(self.read(retry.NATIVE_OWNER+4), 0xAABB)
        self.assertEqual(self.u.reg_read(base.UC_ARM_REG_PRIMASK), 0)
        self.q.check_canaries()

    def test_invalid_event_and_fault_do_not_report_admission_success(self):
        for kind in ('pointer', 'vtable', 'count', 'fault'):
            self.setUp()
            self.setup_notice()
            if kind == 'pointer':
                self.word(self.output.router+0x20, 0xFFFFFFFF)
            elif kind == 'vtable':
                self.word(retry.NATIVE_EVENT, 0)
            elif kind == 'count':
                self.u.mem_write(retry.NATIVE_EVENT+4, b'\x04')
            else:
                self.u.mem_write(self.output.drivers[1]+4, b'\x00')
            self.assertEqual(self.send(), 0 if kind == 'fault' else 1)
            if kind == 'fault':
                self.q.poll()
                self.call(self.recovery.labels['rp_fault'], self.recovery.entries[1])
            for _ in range(4):
                self.q.poll()
            self.assertEqual(self.events, [])
            self.assertEqual(self.q.status()['active'], int(kind == 'fault'))
            self.q.check_canaries()

    def test_native_stalled_drivers_notify_at_admission_and_preserve_bytes(self):
        self.setup_notice(native=True)
        raw_project = bytes(self.u.mem_read(0x20010000, 0x29484))
        data = b'\xF0'+bytes(n % 128 for n in range(358))+b'\xF7'
        self.assertEqual(self.send(desc=self.sysex_descriptor(data)), 0)
        self.q.service()
        self.assertEqual([e[:3] for e in self.events], [(0, 0, 0xAABB)])
        self.q.poll()
        self.assertEqual(self.native.usb_full(), 1)
        self.assertEqual([self.native.uart_full(n) for n in range(2)], [1, 1])
        self.assertEqual(self.native.usb_completed, [])
        for _ in range(4):
            self.q.poll()
        self.assertEqual(len(self.events), 1)
        self.assertEqual(self.send(0x0800EB25, 0xCCDD), 1)
        wire = [bytearray(), bytearray()]
        for _ in range(128):
            self.q.poll()
            if self.native.in_flight is not None:
                self.native.release_usb_endpoint()
            for n in range(2):
                wire[n].extend(self.native.drain_uart(n))
            if not self.q.status()['active']:
                break
        else:
            self.fail('native SysEx did not settle')
        self.assertEqual([bytes(w) for w in wire], [data]*2)
        self.assertEqual(b''.join(self.native.usb_completed), b''.join(self.sysex_packets(data)))
        self.assertEqual(len(self.events), 1)
        self.assertEqual(bytes(self.u.mem_read(0x20010000, 0x29484)), raw_project)
        self.q.check_canaries()

    def test_private_event_corruption_and_local_code_audit(self):
        from audit_midi_sysex_retry_prototype import audit
        for offset, data in ((retry.EVENT, b'\x00'*4), (retry.EVENT+4, b'\x04'),
                             (retry.NOTICE, b'\x02')):
            self.setUp()
            self.setup_notice()
            self.assertEqual(self.send(), 0)
            self.u.mem_write(retry.STATE_BASE+offset, data)
            self.io_masks.clear()
            self.q.service()
            self.assertEqual(self.events, [])
            self.assertEqual(self.io_masks, [])
            self.assertTrue(self.q.status()['errors'] & retry.BAD_STATE)
            self.q.check_canaries()
        with tempfile.TemporaryDirectory() as out:
            report = audit(out, notifications=True)
        self.assertEqual(report['combined_synthetic_ram_bytes'], 1256)
        self.assertEqual(report['owned_admission_notification'], True)
        self.assertLessEqual(report['max_forced_mask_instructions'], 24)


if __name__ == '__main__':
    unittest.main()
