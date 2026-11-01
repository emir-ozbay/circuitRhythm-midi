"""Ordered USB admission: compare native musical event order under TX pressure."""
import hashlib
import itertools
import random
import tempfile
import unittest

import test_midi_usb_inquiry as prior
import midi_usb_inquiry_prototype as rx
import midi_sysex_retry_prototype as retry
from midi_usb_inquiry_test_support import UsbInquiryFixture

base = prior.base


class UsbOrderTests(unittest.TestCase):
    setUpClass = classmethod(prior.UsbInquiryTests.setUpClass.__func__)
    for name in ('setUp', 'word', 'read', 'store', 'call', 'setup_playback',
                 'setup_recovery', 'setup_sysex_router', 'sysex_descriptor',
                 'install_nested_calls', 'setup_notice', 'setup_request',
                 'seed_notes', 'stall', 'release'):
        locals()[name] = getattr(prior.UsbInquiryTests, name)
    sysex_packets = staticmethod(prior.UsbInquiryTests.sysex_packets)

    def setup_ordered(self, native=False, overlay=True, mode=1):
        self.setup_request(native=native)
        self.rx = UsbInquiryFixture(self, overlay=overlay, ordered=True)
        self.u.mem_write(base.seq.SEQ_STATE_ADDR+4, bytes([mode]))
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
        # Legacy scan flags are unused, even when nonzero. No hidden second
        # dispatch path may depend on them in the ordered variant.
        self.u.mem_write(rx.STATE_BASE+rx.SEEN, b'\xA5'*64)

    def capture_shorts(self, real_receiver=False):
        messages = []
        pc = 0x0800EC04
        self.u.mem_write(pc, bytes.fromhex('7047'))
        self.word(0x200008E8, pc|1)
        self.u.mem_write(0x200008E4, bytes([2 if real_receiver else 1]))
        if real_receiver:
            self.word(0x200008EC, 0x08052275)
            self.word(0x200008F8, self.ingress.midi.decoder)
        def capture(u,a,n,d):
            ptr = u.reg_read(base.UC_ARM_REG_R1)
            status = u.mem_read(ptr, 1)[0]
            size = 1 if status >= 0xF8 else 2 if status >> 4 in (12, 13) or status in (0xF1, 0xF3) else 3
            messages.append(bytes(u.mem_read(ptr, size)))
        self.u.hook_add(base.UC_HOOK_CODE, capture, begin=pc, end=pc)
        return messages

    def attach_native_note_receiver(self):
        # Complete the existing playback graph using the same native receiver
        # and adapters as MidiRecordFixture, without overwriting its players.
        decoder, receiver = self.ingress.midi.decoder, self.ingress.midi.receiver
        self.u.mem_write(decoder+4, bytes(reversed(range(8))))
        self.word(receiver, 0x080665E4)
        self.word(receiver+0x24, 0x20007500)
        self.word(0x20007500, 0x080694D0)
        self.word(0x20007504, 0x20007520)
        self.word(0x20007520, 0x08069510)
        self.word(0x20007524, self.playback.router)
        self.u.mem_write(0x20007528, b'\x10')

    @staticmethod
    def bytes_as_packets(data):
        return b''.join(bytes([15, value, 0, 0]) for value in data)

    def send(self, packets):
        for n in range(0, len(packets), 64):
            self.rx.enqueue(packets[n:n+64]); self.rx.poll()

    def check_ordered(self):
        self.rx.check()
        self.assertEqual(self.u.mem_read(rx.STATE_BASE+rx.SEEN, 64), b'\xA5'*64)
        self.assertLessEqual(self.rx.status()['pending'], rx.MAX_PENDING)
        self.assertNotIn('ui_scan_realtime', self.rx.labels)

    def test_inquiry_note_on_stop_keeps_native_order_before_tx_drain(self):
        for mode in (0, 1):
            self.setUp(); self.setup_ordered(mode=mode); self.stall()
            self.attach_native_note_receiver()
            messages = self.capture_shorts(real_receiver=True)
            self.word(self.call(0x0803FD26, self.transport.transport, 0), 1)
            self.call(0x0803FE00, self.transport.transport)
            raw = bytes(self.u.mem_read(0x20010000, 0x29484))
            self.send(self.inquiries+bytes([9, 0x97, 60, 96, 15, 0xFC, 0, 0]))
            self.assertEqual(messages, [bytes([0x97, 60, 96]), b'\xFC'])
            self.assertEqual(self.transport.running(), 0)
            self.assertEqual(self.call(self.labels['c_midi_inputs_idle']), 0)
            self.send(bytes([8, 0x87, 60, 0]))
            self.assertEqual(self.call(self.labels['c_midi_inputs_idle']), 1)
            self.assertEqual(self.rx.status()['pending'], 1)
            before = list(messages)
            self.release(); self.rx.settle()
            self.assertEqual(messages, before)  # no delayed Note On after Stop
            self.assertEqual(self.output.delivered[0].count(self.replies[0]), 1)
            self.assertEqual(bytes(self.u.mem_read(0x20010000, 0x29484)), raw)
            self.check_ordered()

    def test_legitimate_note_after_stop_is_preserved_not_suppressed(self):
        self.setup_ordered(); self.stall()
        messages = self.capture_shorts()
        self.send(self.inquiries+bytes([15, 0xFC, 0, 0, 9, 0x97, 60, 96, 8, 0x87, 60, 0]))
        self.assertEqual(messages, [b'\xFC', bytes([0x97, 60, 96]), bytes([0x87, 60, 0])])
        self.release(); self.rx.settle(); self.check_ordered()

    def test_running_status_and_realtime_inside_partial_note_match_stock(self):
        packets = b''.join(self.sysex_packets(rx.INQUIRY))+self.bytes_as_packets(bytes([0x97, 60, 0xFC, 96, 61, 0xF8, 0, 60, 0]))
        traces = []
        for overlay in (False, True):
            self.setUp(); self.setup_ordered(overlay=overlay); self.stall()
            messages = self.capture_shorts()
            self.send(packets)
            traces.append(messages)
            if overlay:
                self.release(); self.rx.settle(); self.check_ordered()
        self.assertEqual(traces[0], [b'\xFC', bytes([0x97, 60, 96]), b'\xF8',
                                     bytes([0x97, 61, 0]), bytes([0x97, 60, 0])])
        self.assertEqual(traces[1], traces[0])

    def test_permuted_short_messages_inquiry_positions_and_buffer_splits(self):
        note, off, stop = bytes([9, 0x97, 60, 96]), bytes([8, 0x87, 60, 0]), bytes([15, 0xFC, 0, 0])
        for sequence in itertools.permutations((note, off, stop)):
            for position in range(4):
                source = list(sequence); source.insert(position, b'\x04\xF0\x7E\x7F\x07\x06\x01\xF7')
                packets = b''.join(source)
                for split in range(4, len(packets), 4):
                    self.setUp(); self.setup_ordered(); self.stall()
                    messages = self.capture_shorts()
                    self.send(packets[:split]); self.send(packets[split:])
                    self.assertEqual(messages, [p[1:2] if p[1] >= 0xF8 else p[1:] for p in sequence])
                    before = list(messages)
                    self.release(); self.rx.settle()
                    self.assertEqual(messages, before); self.check_ordered()

    def test_full_obligation_count_does_not_block_channel_or_transport_bytes(self):
        self.setup_ordered(); self.stall(); messages = self.capture_shorts()
        self.send(self.inquiries*rx.MAX_PENDING)
        self.assertEqual(self.rx.status()['pending'], rx.MAX_PENDING)
        self.send(bytes([9, 0x97, 60, 96, 15, 0xF8, 0, 0, 15, 0xFC, 0, 0, 8, 0x87, 60, 0]))
        self.assertEqual(messages, [bytes([0x97, 60, 96]), b'\xF8', b'\xFC', bytes([0x87, 60, 0])])
        self.assertEqual(self.rx.status()['pending'], rx.MAX_PENDING)
        self.release(); self.rx.settle()
        self.assertEqual(self.output.delivered[0].count(self.replies[0]), rx.MAX_PENDING)
        self.check_ordered()

    def test_capacity_barrier_restores_exact_cursor_without_reorder_or_request_loss(self):
        for prefix in (b'', bytes([9, 0x97, 60, 96])):
            self.setUp(); self.setup_ordered(); self.stall(); messages = self.capture_shorts()
            self.send(self.inquiries*rx.MAX_PENDING)
            packets = prefix+self.inquiries+bytes([15, 0xFC, 0, 0])
            self.send(packets)
            held = self.rx.status()
            before = bytes(self.u.mem_read(rx.STATE_BASE+rx.BUFFER, 64))
            self.assertEqual(messages, [bytes([0x97, 60, 96])] if prefix else [])
            for _ in range(5):
                self.rx.poll()
            self.assertEqual(self.rx.status(), held)
            self.assertEqual(self.u.mem_read(rx.STATE_BASE+rx.BUFFER, 64), before)
            self.assertEqual(self.u.mem_read(self.ingress.parser, 1), b'\x00')  # F0 not parsed
            self.release(); self.rx.settle()
            self.assertEqual(messages, ([bytes([0x97, 60, 96])] if prefix else [])+[b'\xFC'])
            self.assertEqual(self.output.delivered[0].count(self.replies[0]), rx.MAX_PENDING+1)
            self.check_ordered()

    def test_capacity_barrier_in_middle_of_packet_and_seeded_partial_sysex(self):
        for partial in (False, True):
            self.setUp(); self.setup_ordered(); self.stall(); messages = self.capture_shorts()
            self.send(self.inquiries*rx.MAX_PENDING)
            if partial:
                # Native parser already contains an inquiry prefix, e.g. an
                # externally seeded synthetic lifecycle. Guard before final F7.
                for value in rx.INQUIRY[:-1]:
                    self.call(0x080404BC, self.ingress.parser, value)
                packets = bytes([5, 0xF7, 0, 0, 15, 0xFC, 0, 0])
            else:
                packets = bytes([4, 0xF8, 0xF0, 0x7E, 4, 0x7F, 6, 1, 5, 0xF7, 0, 0, 15, 0xFC, 0, 0])
            self.send(packets)
            self.assertEqual(messages, [] if partial else [b'\xF8'])
            self.release(); self.rx.settle()
            self.assertEqual(messages, ([] if partial else [b'\xF8'])+[b'\xFC'])
            self.assertEqual(self.output.delivered[0].count(self.replies[0]), rx.MAX_PENDING+1)
            self.check_ordered()

    def test_two_inquiries_do_not_delay_realtime_in_the_next_usb_buffer(self):
        self.setup_ordered(); self.stall()
        self.send(self.inquiries*2)
        self.assertEqual(self.rx.status()['pending'], 2)
        self.assertEqual(self.rx.status()['length'], 0)
        self.send(bytes([15, 0xF8, 0, 0, 15, 0xFC, 0, 0]))
        self.assertEqual(self.read(self.transport.engine+0x5C), 1)
        self.assertEqual(self.rx.status()['pending'], 2)
        self.release(); self.rx.settle()
        self.assertEqual(self.output.delivered[0].count(self.replies[0]), 2)
        self.check_ordered()

    def test_capacity_still_can_delay_queued_realtime_negative_control(self):
        self.setup_ordered(); self.stall()
        self.send(self.inquiries*rx.MAX_PENDING)
        self.send(self.inquiries)
        self.rx.enqueue(bytes([15, 0xF8, 0, 0, 15, 0xFC, 0, 0]))
        for _ in range(5):
            self.rx.poll()
        self.assertEqual(self.read(self.transport.engine+0x5C), 0)
        self.assertGreater(self.call(0x0802A37E, self.ingress.usb_fifo), 0)
        self.release(); self.rx.settle()
        self.assertEqual(self.read(self.transport.engine+0x5C), 1)
        self.check_ordered()

    def test_main_context_reentry_invalid_count_and_variant_identity_reject(self):
        self.setup_ordered(); self.stall()
        injected, results = self.install_nested_calls(self.rx.labels['ui_try_reply'], [(rx.NATIVE_POLL, ())])
        self.send(self.inquiries)
        self.assertEqual(len(injected), 1); self.assertEqual(results(), [1])
        before = bytes(self.u.mem_read(rx.STATE_BASE, rx.STATE_SIZE))
        for reg in (base.UC_ARM_REG_PRIMASK, base.UC_ARM_REG_IPSR):
            self.u.reg_write(reg, 1 if reg == base.UC_ARM_REG_PRIMASK else 16)
            self.assertEqual(self.rx.poll(), 1)
            self.assertEqual(bytes(self.u.mem_read(rx.STATE_BASE, rx.STATE_SIZE)), before)
            self.u.reg_write(reg, 0)
        for offset, value in ((0, rx.MAGIC), (rx.PENDING, rx.MAX_PENDING+1), (rx.PENDING, 0xFFFFFFFF)):
            original = self.read(rx.STATE_BASE+offset)
            self.word(rx.STATE_BASE+offset, value)
            invalid = bytes(self.u.mem_read(rx.STATE_BASE, rx.STATE_SIZE))
            self.assertEqual(self.rx.poll(), 1)
            self.assertEqual(bytes(self.u.mem_read(rx.STATE_BASE, rx.STATE_SIZE)), invalid)
            self.word(rx.STATE_BASE+offset, original)
        self.release(); self.rx.settle(); self.check_ordered()

    def test_native_driver_stall_exact_count_payload_and_one_attempt_per_poll(self):
        self.setup_ordered(native=True)
        first = b'\xF0'+bytes(n % 128 for n in range(358))+b'\xF7'
        self.assertEqual(self.q.submit(self.sysex_descriptor(first)), 0)
        self.q.poll(); self.q.poll()
        self.assertEqual(self.native.usb_full(), 1)
        self.assertEqual([self.native.uart_full(n) for n in range(2)], [1, 1])
        self.send(self.inquiries*rx.MAX_PENDING)
        self.assertEqual(len(self.attempts), 1)
        self.assertEqual(self.rx.status()['pending'], rx.MAX_PENDING)
        wires = [bytearray(), bytearray()]
        for _ in range(200):
            self.q.poll()
            before = len(self.attempts); self.rx.poll()
            self.assertLessEqual(len(self.attempts)-before, 1)
            if self.native.in_flight is not None:
                self.native.release_usb_endpoint()
            for n in range(2):
                wires[n].extend(self.native.drain_uart(n))
            if not self.q.status()['active'] and not self.rx.status()['pending']:
                break
        else:
            self.fail('native driver drain did not finish')
        self.assertEqual([bytes(w) for w in wires], [first]*2)
        self.assertEqual(b''.join(self.native.usb_completed),
                         b''.join(self.sysex_packets(first)+self.replies*rx.MAX_PENDING))
        self.check_ordered()

    def test_native_64_voice_stop_preserves_closures_project_and_pending_count(self):
        for mode in (0, 1):
            self.setUp(); self.setup_ordered(mode=mode); self.seed_notes(64)
            raw = bytes(self.u.mem_read(0x20010000, 0x29484)); self.stall()
            self.send(self.inquiries*2+bytes([15, 0xF8, 0, 0, 15, 0xFC, 0, 0]))
            self.assertEqual(self.transport.running(), 0)
            self.release()
            for _ in range(40):
                self.q.poll(); self.rx.poll()
            for messages in self.output.delivered:
                self.assertEqual(sum(p[0] == 8 for p in messages), 64)
                self.assertEqual(sum(p[1] == 0xFC for p in messages), 1)
                self.assertEqual(sum(p[1] == 0xF8 for p in messages), 1)
            self.assertEqual(self.rx.status()['pending'], 2)  # no quarantine reset
            self.assertEqual(bytes(self.u.mem_read(0x20010000, 0x29484)), raw)
            self.check_ordered()

    def test_legacy_codegen_and_audit(self):
        from audit_midi_usb_inquiry_prototype import audit
        self.assertEqual(hashlib.sha256(rx.arm_code()[0]).hexdigest(),
                         'b1b24f86615963f3a4cc08366c51a4bade7604cc53b880412877aa54edfe0b0b')
        with tempfile.TemporaryDirectory() as out:
            result = audit(out, ordered=True)
        self.assertEqual(result['max_reply_attempts_per_pass'], 1)
        self.assertEqual(result['pending_inquiry_tokens'], rx.MAX_PENDING)
        self.assertEqual(result['forced_irq_mask_instructions'], 0)

    def test_differential_native_order_for_random_channels_realtime_and_sysex(self):
        rng = random.Random(5706)
        for case in range(24):
            stream, inquiry_count = bytearray(), 0
            for _ in range(32):
                kind = rng.randrange(7)
                if kind == 0 and inquiry_count < 4:
                    stream.extend(rx.INQUIRY); inquiry_count += 1
                elif kind == 1:
                    stream.append(rng.randrange(0xF8, 0x100))
                elif kind == 2:
                    stream.extend([0xF0, 0x7D, rng.randrange(128), 0xF7])
                elif kind == 3:
                    stream.extend([rng.choice([0xC0, 0xD0]) | rng.randrange(16), rng.randrange(128)])
                elif kind == 4:
                    stream.extend([0x90 | rng.randrange(16), rng.randrange(128), rng.randrange(0xF8, 0x100),
                                   rng.randrange(128), rng.randrange(128), 0])  # running status zero-velocity
                else:
                    stream.extend([rng.choice([0x80, 0x90, 0xA0, 0xB0, 0xE0]) | rng.randrange(16),
                                   rng.randrange(128), rng.randrange(128)])
            packets = self.bytes_as_packets(stream)
            traces = []
            for overlay in (False, True):
                self.setUp(); self.setup_ordered(overlay=overlay); self.stall()
                messages = self.capture_shorts()
                # Vary USB record boundaries independently of message boundaries.
                cursor = 0
                while cursor < len(packets):
                    chunk = 4*(1+(case+cursor//4) % 16)
                    self.send(packets[cursor:cursor+chunk]); cursor += chunk
                traces.append(list(messages))
                if overlay:
                    self.assertEqual(self.rx.status()['pending'], inquiry_count)
                    self.release(); self.rx.settle()
                    self.assertEqual(messages, traces[-1])
                    self.assertEqual(self.output.delivered[0].count(self.replies[0]), inquiry_count)
                    self.check_ordered()
            self.assertEqual(traces[0], traces[1], case)


if __name__ == '__main__':
    unittest.main()
