"""Upper formatter reservation experiment; native input retry remains open."""
import hashlib
import tempfile
import unittest

import test_midi_sysex_notification as prior
import midi_sysex_retry_prototype as retry
from midi_sysex_retry_test_support import SysexRetryFixture

base = prior.base


class SysexRequestTests(unittest.TestCase):
    setUpClass = classmethod(prior.SysexNotificationTests.setUpClass.__func__)
    setUp = prior.SysexNotificationTests.setUp
    word = prior.SysexNotificationTests.word
    read = prior.SysexNotificationTests.read
    store = prior.SysexNotificationTests.store
    call = prior.SysexNotificationTests.call
    setup_playback = prior.SysexNotificationTests.setup_playback
    setup_recovery = prior.SysexNotificationTests.setup_recovery
    setup_sysex_router = prior.SysexNotificationTests.setup_sysex_router
    sysex_descriptor = prior.SysexNotificationTests.sysex_descriptor
    sysex_packets = staticmethod(prior.SysexNotificationTests.sysex_packets)
    install_nested_calls = prior.SysexNotificationTests.install_nested_calls
    setup_notice = prior.SysexNotificationTests.setup_notice

    def setup_request(self, enabled=True, native=False):
        self.setup_notice(native=native, overlay=False)
        self.q = SysexRetryFixture(self, notifications=True, reservations=enabled)
        self.q.capture_native_callers()
        self.q.install_producer_guards()
        if enabled:
            self.q.install_request_guards()
        self.controller, self.settings, self.buffer = 0x20007100, 0x20007200, 0x20007300
        self.u.mem_write(self.controller, bytes(32))
        self.word(self.controller+0x14, self.buffer)
        self.u.mem_write(self.controller+0x19, b'\x17')
        self.u.mem_write(self.settings, bytes(n % 32 for n in range(128)))
        self.u.mem_write(self.buffer-4, b'UBEG')
        self.u.mem_write(self.buffer+360, b'UEND')
        self.u.mem_write(self.buffer, b'\xCC'*360)

    def upper_args(self, entry, context=0xAABB):
        arg2 = self.settings if entry in (0x08032120, 0x080321F4) else 0x123456 if entry == 0x08032154 else 5
        if entry == 0x080321BC:
            return (self.controller, 1, arg2, 1, self.buffer, 0x0800EB21, context)
        return (self.controller, 1, arg2, self.buffer, 0x0800EB21, context)

    def upper(self, entry, context=0xAABB, mask=1):
        args = list(self.upper_args(entry, context))
        args[1] = mask
        for n, value in enumerate(args[4:]):
            self.word(0x20040000+n*4, value)
        return self.call(entry, *args[:4])

    def check(self):
        self.assertEqual(self.u.mem_read(self.buffer-4, 4), b'UBEG')
        self.assertEqual(self.u.mem_read(self.buffer+360, 4), b'UEND')
        self.q.check_canaries()

    def nested_upper_stub(self, entry):
        from thumb_asm import Asm, push, pop, sub_sp_imm, add_sp_imm, movw, movt, str_sp, bl
        address = 0x08071C00
        a = Asm(address)
        a.emit(push, [3], lr=True)
        a.emit(sub_sp_imm, 16)
        args = self.upper_args(entry, 0xCCDD)
        for n, value in enumerate(args[4:]):
            a.imm32(0, value)
            a.emit(str_sp, 0, n*4)
        for n, value in enumerate(args[:4]):
            a.imm32(n, value)
        a.emit(bl, entry)
        a.emit(add_sp_imm, 16)
        a.emit(pop, [3], pc=True)
        code = a.assemble()[0]
        assert address+len(code) < retry.CODE_BASE
        self.u.mem_write(address, code)
        return address

    def test_five_real_upper_formatters_preserve_payload_return_and_stack_arguments(self):
        for entry in retry.REQUEST_GATES:
            outcomes = []
            for enabled in (False, True):
                self.setUp()
                self.setup_request(enabled)
                self.assertEqual(self.upper(entry), 0)
                captured = self.q.captured[-1]
                outcomes.append((captured['payload'], captured['mask']))
                self.q.settle()
                self.assertEqual([e[:3] for e in self.events], [(0, 0, 0xAABB)])
                self.assertEqual(self.output.delivered, [self.sysex_packets(captured['payload']), [], []])
                if enabled:
                    self.assertEqual(self.read(retry.STATE_BASE+retry.REQUEST), 0)
                self.check()
            self.assertEqual(outcomes[0], outcomes[1], hex(entry))

    def test_full_slot_rejects_before_source_mutation_and_allows_caller_retry(self):
        for entry in retry.REQUEST_GATES:
            self.setUp()
            self.setup_request()
            self.assertEqual(self.q.submit(self.sysex_descriptor()), 0)
            before = bytes(self.u.mem_read(self.buffer, 360))
            owner = bytes(self.u.mem_read(retry.NATIVE_OWNER, 8))
            self.assertEqual(self.upper(entry), 1)
            self.assertEqual(self.call(entry, 0xFFFFFFFF, 1, 0xFFFFFFFF, 0xFFFFFFFF), 1)
            self.assertEqual(bytes(self.u.mem_read(self.buffer, 360)), before)
            self.assertEqual(bytes(self.u.mem_read(retry.NATIVE_OWNER, 8)), owner)
            self.assertEqual(self.q.captured, [])
            self.q.settle()
            self.assertEqual(self.upper(entry), 0)
            self.q.settle()
            self.assertEqual(len(self.events), 1)
            self.check()

    def test_legacy_lower_guard_rejects_after_upper_source_was_already_mutated(self):
        self.setup_request(enabled=False)
        self.assertEqual(self.q.submit(self.sysex_descriptor()), 0)
        before = bytes(self.u.mem_read(self.buffer, 360))
        self.assertEqual(self.upper(0x08032120), 1)
        self.assertNotEqual(bytes(self.u.mem_read(self.buffer, 360)), before)
        self.q.settle()
        self.check()

    def test_disabled_upper_response_releases_reservation_without_notification(self):
        for entry in retry.REQUEST_GATES:
            self.setUp()
            self.setup_request()
            self.u.mem_write(self.controller+0x19, b'\x00')
            self.assertEqual(self.upper(entry), 1)
            self.assertEqual(self.q.status()['active'], 0)
            self.assertEqual(self.read(retry.STATE_BASE+retry.REQUEST), 0)
            self.assertEqual(self.events, [])
            self.check()

    def test_nested_upper_formatter_cannot_take_reserved_capacity(self):
        for enabled in (False, True):
            self.setUp()
            self.setup_request(enabled)
            target = self.nested_upper_stub(0x08032188)
            injected, results = self.install_nested_calls(0x08046A54, [(target, ())])
            self.assertEqual(self.upper(0x08032120), 0 if enabled else 1)
            self.assertEqual(results(), [1 if enabled else 0])
            self.assertEqual(len(injected), 1)
            self.q.settle()
            self.assertEqual([e[:3] for e in self.events], [(0, 0, 0xAABB if enabled else 0xCCDD)])
            if enabled:
                self.assertEqual(self.q.captured[0]['payload'][6], 9)
                self.assertEqual(self.read(retry.STATE_BASE+retry.REQUEST), 0)
            else:
                self.assertEqual(self.q.captured[0]['payload'][6], 8)
            self.check()

    def test_direct_submit_producer_and_service_cannot_steal_reservation(self):
        self.setup_request()
        desc = self.sysex_descriptor()
        target = self.nested_upper_stub(0x08032154)
        injected, results = self.install_nested_calls(0x08046A54, [
            (self.q.labels['sr_submit'], (self.output.router, 7, desc)),
            (self.q.labels['sr_service'], (self.output.router,)),
            (0x0804691A, (7, desc, 0x0800EB25, 0xCCDD)),
            (0x0802CBB8, (0x40, self.settings, 2)),
            (target, ()),
        ])
        self.assertEqual(self.upper(0x08032120), 0)
        self.assertEqual(results(), [1, 0, 1, 1, 1])
        self.assertEqual(len(injected), 1)
        self.assertEqual(len(self.q.captured), 1)  # capture hooks native router, not direct API
        self.assertEqual(self.q.captured[0]['payload'][6], 9)
        self.q.settle()
        self.assertEqual([e[:3] for e in self.events], [(0, 0, 0xAABB)])
        self.check()

    def test_masked_handler_context_and_unknown_router_reject_before_formatter(self):
        for kind in ('primask', 'ipsr', 'router', 'token'):
            self.setUp()
            self.setup_request()
            before = bytes(self.u.mem_read(self.buffer, 360))
            if kind == 'primask':
                self.u.reg_write(base.UC_ARM_REG_PRIMASK, 1)
            elif kind == 'ipsr':
                self.u.reg_write(base.UC_ARM_REG_IPSR, 16)
            elif kind == 'router':
                self.word(0x20006F04, 0)
            else:
                self.word(retry.STATE_BASE+retry.REQUEST, 0xFFFFFFFF)
            self.io_masks.clear()
            self.assertEqual(self.upper(0x08032120), 1)
            self.assertEqual(bytes(self.u.mem_read(self.buffer, 360)), before)
            self.assertEqual(self.io_masks, [])
            self.assertEqual(self.q.captured, [])
            self.u.reg_write(base.UC_ARM_REG_PRIMASK, 0)
            self.u.reg_write(base.UC_ARM_REG_IPSR, 0)
            self.check()

    def test_selected_fault_rejects_before_formatter_and_mask_is_preserved(self):
        self.setup_request()
        self.call(self.recovery.labels['rp_fault'], self.recovery.entries[0])
        before = bytes(self.u.mem_read(self.buffer, 360))
        self.assertEqual(self.upper(0x08032120), 1)
        self.assertEqual(bytes(self.u.mem_read(self.buffer, 360)), before)
        self.assertEqual(self.events, [])
        # Fault on unselected port0 does not block a healthy port1 request.
        args = list(self.upper_args(0x08032120))
        args[1] = 2
        for n, value in enumerate(args[4:]):
            self.word(0x20040000+n*4, value)
        self.assertEqual(self.call(0x08032120, *args[:4]), 0)
        self.q.settle()
        self.assertEqual(self.q.captured[-1]['mask'], 2)
        self.assertEqual(self.output.delivered[0], [bytes.fromhex('0ffc0000')])  # fault recovery Stop
        self.assertTrue(self.output.delivered[1])
        self.assertEqual(self.output.delivered[2], [])
        self.check()

    def test_native_usb_din_stall_keeps_failed_request_retryable(self):
        self.setup_request(native=True)
        raw_project = bytes(self.u.mem_read(0x20010000, 0x29484))
        self.assertEqual(self.upper(0x080321F4, mask=7), 0)
        first = self.q.captured[-1]['payload']
        self.q.poll()
        self.q.poll()  # first pass binds, second pass fills native driver buffers
        self.assertEqual(self.native.usb_full(), 1)
        #120B message exceeds the63-byte effective UART ring.
        self.assertEqual([self.native.uart_full(n) for n in range(2)], [1, 1])
        before = bytes(self.u.mem_read(self.buffer, 360))
        self.assertEqual(self.upper(0x08032120, 0xCCDD, mask=7), 1)
        self.assertEqual(bytes(self.u.mem_read(self.buffer, 360)), before)
        wire = [bytearray(), bytearray()]
        def settle_native():
            for _ in range(128):
                self.q.poll()
                if self.native.in_flight is not None:
                    self.native.release_usb_endpoint()
                for n in range(2):
                    wire[n].extend(self.native.drain_uart(n))
                if not self.q.status()['active']:
                    return
            self.fail('native request did not settle')
        settle_native()
        self.assertEqual(self.upper(0x08032120, 0xCCDD, mask=7), 0)
        second = self.q.captured[-1]['payload']
        settle_native()
        self.assertEqual([bytes(w) for w in wire], [first+second]*2)
        self.assertEqual(b''.join(self.native.usb_completed),
                         b''.join(self.sysex_packets(first)+self.sysex_packets(second)))
        self.assertEqual([e[:3] for e in self.events], [(0, 0, 0xAABB), (0, 0, 0xCCDD)])
        self.assertEqual(bytes(self.u.mem_read(0x20010000, 0x29484)), raw_project)
        self.check()

    def test_native_usb_and_din_dispatch_still_discard_busy_inquiry_response(self):
        # Required negative control: safe early formatter rejection alone does
        # not make the native void receive dispatcher retain a consumed request.
        inquiry = bytes.fromhex('f07e7f0601f7')
        for usb in (False, True):
            self.setUp()
            self.setup_request()
            self.word(0x20000900, retry.NATIVE_EVENT_VTABLE)
            self.u.mem_write(0x20000904, b'\x01')
            self.word(0x20000908, 0x08026F0D)
            self.word(0x20000914, 0)
            self.assertEqual(self.q.submit(self.sysex_descriptor()), 0)
            attempts = []
            self.u.hook_add(base.UC_HOOK_CODE, lambda u,a,n,d: attempts.append(a),
                            begin=0x08026F0C, end=0x08026F0C)
            if usb:
                self.ingress.usb(b''.join(self.sysex_packets(inquiry)))
                self.assertEqual(self.call(0x0802A37E, self.ingress.usb_fifo), 0)
            else:
                self.ingress.din(inquiry)
            self.assertEqual(len(attempts), 1)
            self.assertEqual(self.q.captured, [])
            self.assertEqual(self.u.mem_read(self.ingress.parser, 1), b'\x00')
            self.q.settle()
            self.assertEqual(len(attempts), 1)
            expected = self.sysex_packets(bytes.fromhex('f000202901f7'))
            self.assertEqual(self.output.delivered, [expected]*3)
            # Positive control: an explicit upstream resend after drain DOES
            # produce the17B identity reply. The parser does not retry itself.
            if usb:
                self.ingress.usb(b''.join(self.sysex_packets(inquiry)))
            else:
                self.ingress.din(inquiry)
            self.assertEqual(len(attempts), 2)
            self.assertEqual(len(self.q.captured), 1)
            reply = bytes.fromhex('f07e0006020020290163000001012c4af7')
            self.assertEqual(self.q.captured[-1]['payload'], reply)
            self.q.settle()
            selected = 0 if usb else 1
            self.assertEqual(self.output.delivered,
                             [expected+(self.sysex_packets(reply) if n == selected else []) for n in range(3)])
            self.check()

    def test_previous_variants_hashes_and_reservation_bounds_audit(self):
        from audit_midi_sysex_retry_prototype import audit
        self.assertEqual(hashlib.sha256(retry.arm_code()[0]).hexdigest(),
                         'ae8d859e129a72bb02e6e6916ac7ca6a256b30dc6699ff612eacc84ae617b266')
        self.assertEqual(hashlib.sha256(retry.arm_code(notifications=True)[0]).hexdigest(),
                         'c541d9d2c207f8230c75466b52342698e464a2077a7afa426c3bbaee9fb4fbe0')
        with self.assertRaises(ValueError):
            retry.arm_code(reservations=True)
        with tempfile.TemporaryDirectory() as out:
            report = audit(out, notifications=True, reservations=True)
        self.assertEqual(len(report['emulator_producer_overlays']), 17)
        self.assertEqual(report['combined_synthetic_ram_bytes'], 1260)


if __name__ == '__main__':
    unittest.main()
