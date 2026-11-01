"""Retained USB inquiry and realtime bypass; explicit finite-buffer boundary."""
import hashlib
import tempfile
import unittest

import test_midi_sysex_request_reservation as prior
import test_midi_recovery_prototype as recovery_tests
import midi_usb_inquiry_prototype as rx
import midi_sysex_retry_prototype as retry
from midi_usb_inquiry_test_support import UsbInquiryFixture

base = prior.base


class UsbInquiryTests(unittest.TestCase):
    setUpClass = classmethod(prior.SysexRequestTests.setUpClass.__func__)
    for name in ('setUp', 'word', 'read', 'store', 'call', 'setup_playback',
                 'setup_recovery', 'setup_sysex_router', 'sysex_descriptor',
                 'install_nested_calls', 'setup_notice', 'setup_request'):
        locals()[name] = getattr(prior.SysexRequestTests, name)
    sysex_packets = staticmethod(prior.SysexRequestTests.sysex_packets)
    seed_notes = recovery_tests.MidiRecoveryPrototypeTests.seed_notes

    def setup_rx(self, native=False):
        self.setup_request(native=native)
        self.rx = UsbInquiryFixture(self)
        self.inquiries = b''.join(self.sysex_packets(rx.INQUIRY))
        self.replies = self.sysex_packets(rx.REPLY)
        self.first = bytes.fromhex('f000202901f7')
        self.word(0x20000900, retry.NATIVE_EVENT_VTABLE)
        self.u.mem_write(0x20000904, b'\x01')
        self.word(0x20000908, 0x08026F0D)
        self.word(0x20000914, 0)
        self.attempts = []
        self.u.hook_add(base.UC_HOOK_CODE, lambda u,a,n,d: self.attempts.append(a),
                        begin=self.rx.labels['ui_try_reply'], end=self.rx.labels['ui_try_reply'])

    def stall(self):
        self.assertEqual(self.q.submit(self.sysex_descriptor()), 0)
        for driver in self.output.drivers:
            self.u.mem_write(driver+5, b'\x01')  # ready, but downstream full

    def release(self):
        for driver in self.output.drivers:
            self.u.mem_write(driver+5, b'\x00')

    def test_busy_inquiry_is_retried_without_host_resend_exactly_once(self):
        self.setup_rx(); self.stall()
        self.rx.enqueue(self.inquiries); self.rx.poll()
        self.assertEqual(self.rx.status()['pending'], 1)
        self.assertEqual(self.call(0x0802A37E, self.ingress.usb_fifo), 0)
        for _ in range(8):
            self.q.poll(); self.rx.poll()
        self.assertEqual(len(self.attempts), 9)
        self.assertEqual(self.output.delivered, [[], [], []])
        self.release(); self.rx.settle()
        expected = self.sysex_packets(self.first)
        self.assertEqual(self.output.delivered, [expected+self.replies, expected, expected])
        for _ in range(5):
            self.q.poll(); self.rx.poll()
        self.assertEqual(self.output.delivered[0], expected+self.replies)
        self.rx.check()

    def test_retained_second_inquiry_and_clock_stop_bypass_are_not_replayed(self):
        self.setup_rx(); self.stall()
        self.word(self.call(0x0803FD26, self.transport.transport, 0), 1)
        self.call(0x0803FE00, self.transport.transport)
        packets = self.inquiries*2 + bytes([15, 0xF8, 0, 0, 15, 0xFC, 0, 0])
        self.rx.enqueue(packets); self.rx.poll()
        self.assertEqual(self.rx.status()['pending'], 1)
        self.assertEqual(self.rx.status()['length'], len(packets))
        self.assertEqual(self.read(self.transport.engine+0x5C), 1)
        before = self.rx.status()
        for _ in range(8):
            self.rx.poll()
        self.assertEqual(self.rx.status(), before)
        self.assertEqual(self.read(self.transport.engine+0x5C), 1)
        self.release(); self.rx.settle()
        self.assertEqual(self.read(self.transport.engine+0x5C), 1)
        self.assertEqual(self.output.delivered[0].count(self.replies[0]), 2)
        self.assertEqual(sum(p[1] == 0xFC for p in self.output.delivered[0]), 1)
        self.rx.check()

    def test_realtime_only_following_buffers_progress_while_reply_stalls(self):
        self.setup_rx(); self.stall()
        self.rx.enqueue(self.inquiries); self.rx.poll()
        for _ in range(12):
            self.rx.enqueue(bytes([15, 0xF8, 0, 0])); self.rx.poll()
        self.assertEqual(self.read(self.transport.engine+0x5C), 12)
        self.assertEqual(self.rx.status()['pending'], 1)
        self.assertEqual(self.rx.status()['length'], 0)
        self.release(); self.rx.settle(); self.rx.check()

    def test_split_inquiry_at_every_boundary_and_fifo_wrap(self):
        for split in range(1, 6):
            self.setUp(); self.setup_rx()
            # CIN F allows a single parser byte, as in the native implementation.
            packets = b''.join(bytes([15, b, 0, 0]) for b in rx.INQUIRY)
            for _ in range(12):
                self.rx.enqueue(packets[:split*4]); self.rx.poll()
                self.rx.enqueue(packets[split*4:]); self.rx.settle()
            self.assertEqual(self.output.delivered, [self.replies*12, [], []])
            self.rx.check()

    def test_realtime_inside_inquiry_and_padding_are_not_confused(self):
        self.setup_rx(); self.stall()
        # Native parser permits realtime between SysEx bytes, including inside
        # a three-byte CIN4 packet. Padding F8/FC is NOT a message.
        packets = bytes([4, 0xF0, 0x7E, 0xF8, 4, 0x7F, 6, 1,
                         5, 0xF7, 0xFC, 0xF8, 15, 0xF8, 0xFC, 0xFC])
        self.rx.enqueue(packets); self.rx.poll()
        self.assertEqual(self.read(self.transport.engine+0x5C), 2)
        self.assertEqual(self.rx.status()['pending'], 1)
        self.release(); self.rx.settle()
        self.assertEqual(self.output.delivered[0].count(self.replies[0]), 1)
        self.assertFalse(any(p[1] == 0xFC for p in self.output.delivered[0]))
        self.rx.check()

    def test_two_queued_buffers_are_not_popped_while_cursor_owns_nonrt_bytes(self):
        self.setup_rx(); self.stall()
        self.rx.enqueue(self.inquiries*2); self.rx.poll()
        retained = bytes(self.u.mem_read(rx.STATE_BASE+rx.BUFFER, 64))
        self.rx.enqueue(self.inquiries); self.rx.enqueue(self.inquiries)
        queued = self.call(0x0802A37E, self.ingress.usb_fifo)
        for _ in range(5):
            self.rx.poll()
        self.assertEqual(self.call(0x0802A37E, self.ingress.usb_fifo), queued)
        self.assertEqual(bytes(self.u.mem_read(rx.STATE_BASE+rx.BUFFER, 64)), retained)
        self.release(); self.rx.settle()
        self.assertEqual(self.output.delivered[0].count(self.replies[0]), 4)
        self.rx.check()

    def test_head_of_line_realtime_in_another_queued_buffer_remains_open(self):
        # Negative control: finite one-buffer bypass cannot promise realtime
        # service behind another retained non-RT buffer. Do NOT call this GO.
        self.setup_rx(); self.stall()
        self.rx.enqueue(self.inquiries*2); self.rx.poll()
        self.rx.enqueue(bytes([15, 0xF8, 0, 0, 15, 0xFC, 0, 0]))
        for _ in range(5):
            self.rx.poll()
        self.assertEqual(self.read(self.transport.engine+0x5C), 0)
        self.assertGreater(self.call(0x0802A37E, self.ingress.usb_fifo), 0)
        self.release(); self.rx.settle()
        self.assertEqual(self.read(self.transport.engine+0x5C), 1)
        self.rx.check()

    def test_reentry_masked_and_handler_calls_leave_cursor_and_token_unchanged(self):
        self.setup_rx(); self.stall()
        self.rx.enqueue(self.inquiries*2)
        injected, results = self.install_nested_calls(self.rx.labels['ui_try_reply'], [(rx.NATIVE_POLL, ())])
        self.rx.poll()
        self.assertEqual(results(), [1]); self.assertEqual(len(injected), 1)
        before = bytes(self.u.mem_read(rx.STATE_BASE, rx.STATE_SIZE))
        for reg in (base.UC_ARM_REG_PRIMASK, base.UC_ARM_REG_IPSR):
            self.u.reg_write(reg, 1 if reg == base.UC_ARM_REG_PRIMASK else 16)
            self.assertEqual(self.rx.poll(), 1)
            self.assertEqual(bytes(self.u.mem_read(rx.STATE_BASE, rx.STATE_SIZE)), before)
            self.u.reg_write(reg, 0)
        self.release(); self.rx.settle(); self.rx.check()

    def test_real_stop_with_64_voices_keeps_off_stop_and_project_bytes(self):
        for mode in (0, 1):
            self.setUp(); self.setup_rx()
            self.u.mem_write(base.seq.SEQ_STATE_ADDR+4, bytes([mode]))
            self.seed_notes(64)
            raw = bytes(self.u.mem_read(0x20010000, 0x29484))
            self.stall()
            self.rx.enqueue(self.inquiries*2+bytes([15, 0xF8, 0, 0, 15, 0xFC, 0, 0]))
            self.rx.poll()
            self.assertEqual(self.transport.running(), 0)
            self.release()
            # Recovery quarantine can pin the pending inquiry. Musical closure
            # MUST still drain; no clearing FAULT just to make SysEx pass.
            for _ in range(40):
                self.q.poll(); self.rx.poll()
            for messages in self.output.delivered:
                self.assertEqual(sum(p[0] == 8 for p in messages), 64)
                self.assertEqual(sum(p[1] == 0xFC for p in messages), 1)
                self.assertEqual(sum(p[1] == 0xF8 for p in messages), 1)
            self.assertEqual(self.rx.status()['pending'], 1)  # fault quarantine pins the inquiry
            self.assertEqual(bytes(self.u.mem_read(0x20010000, 0x29484)), raw)
            self.rx.check()

    def test_non_inquiry_sysex_uses_native_dispatch_and_channel_messages_survive(self):
        self.setup_rx()
        # Isolate the unknown SysEx listener; never invoke update/storage code.
        seen = []
        pc = 0x0800EC00
        self.u.mem_write(pc, bytes.fromhex('7047'))
        self.word(0x20000908, pc|1)
        def capture(u,a,n,d):
            desc = u.reg_read(base.UC_ARM_REG_R1)
            seen.append(bytes(u.mem_read(self.read(desc), self.read(desc+4))))
        self.u.hook_add(base.UC_HOOK_CODE, capture, begin=pc, end=pc)
        for payload in (b'\xF0\x7E\x7F\x06\x02\xF7', b'\xF0\x7E\x7F\x06\x01\x00\xF7'):
            self.rx.enqueue(b''.join(self.sysex_packets(payload))); self.rx.poll()
        self.assertEqual(len(seen), 2); self.assertEqual(self.attempts, [])
        # Playback fixture has no channel-note receiver. Observe the real
        # parser/short-dispatch boundary instead of inventing input ownership.
        shorts = []
        short_pc = 0x0800EC04
        self.u.mem_write(short_pc, bytes.fromhex('7047'))
        self.word(0x200008E8, short_pc|1)
        self.u.hook_add(base.UC_HOOK_CODE,
                        lambda u,a,n,d: shorts.append(bytes(u.mem_read(u.reg_read(base.UC_ARM_REG_R1), 3))),
                        begin=short_pc, end=short_pc)
        self.rx.enqueue(bytes([9, 0x97, 60, 96])); self.rx.poll()
        self.rx.enqueue(bytes([8, 0x87, 60, 0])); self.rx.poll()
        self.assertEqual(shorts, [bytes([0x97, 60, 96]), bytes([0x87, 60, 0])])
        self.rx.check()

    def test_max_buffer_and_unsupported_cable_fail_closed_without_overwrite(self):
        self.setup_rx(); self.stall()
        self.rx.enqueue(self.inquiries*8); self.rx.poll()
        self.release(); self.rx.settle()
        self.assertEqual(self.output.delivered[0].count(self.replies[0]), 8)
        self.rx.enqueue(bytes([0x1F, 0xF8, 0, 0])); self.rx.poll()
        self.assertEqual(self.rx.status()['fault'], 1)
        self.assertEqual(self.read(self.transport.engine+0x5C), 0)
        before = bytes(self.u.mem_read(rx.STATE_BASE, rx.STATE_SIZE))
        self.assertEqual(self.rx.poll(), 1)
        self.assertEqual(bytes(self.u.mem_read(rx.STATE_BASE, rx.STATE_SIZE)), before)
        self.rx.check()

    def test_previous_retry_variant_is_unchanged(self):
        self.assertEqual(hashlib.sha256(retry.arm_code(notifications=True, reservations=True)[0]).hexdigest(),
                         '321fca8a65d1ef9c99b0cf05ed1e7bd61ccf128ee06d8891ad0fe3e52b53141a')
        with self.assertRaises(ValueError):
            rx.arm_code(state=retry.STATE_BASE)

    def test_native_usb_din_driver_stall_and_exact_reply_bytes(self):
        self.setup_rx(native=True)
        first = b'\xF0'+bytes(n % 128 for n in range(358))+b'\xF7'
        self.assertEqual(self.q.submit(self.sysex_descriptor(first)), 0)
        self.q.poll(); self.q.poll()
        self.assertEqual(self.native.usb_full(), 1)
        self.assertEqual([self.native.uart_full(n) for n in range(2)], [1, 1])
        self.rx.enqueue(self.inquiries*2); self.rx.poll()
        self.assertEqual(self.rx.status()['pending'], 1)
        raw = bytes(self.u.mem_read(0x20010000, 0x29484))
        wire = [bytearray(), bytearray()]
        for _ in range(160):
            self.q.poll(); self.rx.poll()
            if self.native.in_flight is not None:
                self.native.release_usb_endpoint()
            for n in range(2):
                wire[n].extend(self.native.drain_uart(n))
            if not self.q.status()['active'] and not self.rx.status()['pending'] and not self.rx.status()['length']:
                break
        else:
            self.fail('native drivers and RX did not settle')
        self.assertEqual([bytes(w) for w in wire], [first]*2)
        self.assertEqual(b''.join(self.native.usb_completed),
                         b''.join(self.sysex_packets(first)+self.replies*2))
        self.assertEqual(bytes(self.u.mem_read(0x20010000, 0x29484)), raw)
        self.rx.check()

    def test_pending_token_does_not_borrow_parser_or_pop_destination(self):
        self.setup_rx(); self.stall()
        self.rx.enqueue(self.inquiries); self.rx.poll()
        descriptor = self.read(self.ingress.parser+36)
        self.u.mem_write(self.read(descriptor+4), b'\xCC'*6)
        self.u.mem_write(self.ingress.usb_data, b'\xDD'*64)
        self.u.mem_write(self.ingress.enqueue_data, b'\xEE'*64)
        self.release(); self.rx.settle()
        expected = self.sysex_packets(self.first)
        self.assertEqual(self.output.delivered, [expected+self.replies, expected, expected])
        self.rx.check()

    def test_relocated_state_and_code_bounds_reject_overlap(self):
        for kwargs in ({'base': 0x08072000}, {'base': 0x0807FFFC},
                       {'state': 0x20048000-rx.STATE_SIZE}, {'state': rx.STATE_BASE+1}):
            with self.assertRaises(ValueError):
                rx.arm_code(**kwargs)

    def test_local_cfg_abi_and_bounded_scans_audit(self):
        from audit_midi_usb_inquiry_prototype import audit
        with tempfile.TemporaryDirectory() as out:
            report = audit(out)
        self.assertEqual(report['combined_synthetic_ram_bytes'], 1432)
        self.assertEqual(report['forced_irq_mask_instructions'], 0)
        self.assertEqual(report['max_native_rx_pops_per_pass'], 1)
        self.assertEqual(max(f['max_local_stack_bytes'] for f in report['functions'].values()), 32)

    def test_realtime_bypass_can_reorder_a_deferred_note_on_negative_control(self):
        self.setup_rx(); self.stall()
        messages = []
        pc = 0x0800EC04
        self.u.mem_write(pc, bytes.fromhex('7047'))
        self.word(0x200008E8, pc|1)
        self.u.hook_add(base.UC_HOOK_CODE,
                        lambda u,a,n,d: messages.append(bytes(u.mem_read(u.reg_read(base.UC_ARM_REG_R1), 3))),
                        begin=pc, end=pc)
        self.rx.enqueue(self.inquiries+bytes([9, 0x97, 60, 96, 15, 0xFC, 0, 0]))
        self.rx.poll()
        # Native short pop copies the actual length1; the remaining two stack
        # bytes are unspecified and are not part of a realtime MIDI message.
        self.assertEqual([m[0] for m in messages], [0xFC])
        self.release(); self.rx.settle()
        self.assertEqual([m[0] for m in messages], [0xFC, 0x97])
        self.assertEqual(messages[1], bytes([0x97, 60, 96]))
        self.rx.check()


if __name__ == '__main__':
    unittest.main()
