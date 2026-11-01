"""Committed RX window is serviced in musical order, even at inquiry capacity."""
import hashlib
import random
import struct
import tempfile
import unittest

import test_midi_usb_order as prior
import midi_usb_ledger_prototype as ledger
import midi_usb_inquiry_prototype as rx
from midi_usb_ledger_test_support import UsbLedgerFixture

base = prior.base


class UsbLedgerTests(unittest.TestCase):
    setUpClass = classmethod(prior.UsbOrderTests.setUpClass.__func__)
    for name in ('setUp', 'word', 'read', 'store', 'call', 'setup_playback',
                 'setup_recovery', 'setup_sysex_router', 'sysex_descriptor',
                 'install_nested_calls', 'setup_notice', 'setup_request',
                 'seed_notes', 'stall', 'release', 'capture_shorts', 'attach_native_note_receiver'):
        locals()[name] = getattr(prior.UsbOrderTests, name)
    sysex_packets = staticmethod(prior.UsbOrderTests.sysex_packets)
    bytes_as_packets = staticmethod(prior.UsbOrderTests.bytes_as_packets)

    def setup_ledger(self, native=False, mode=1, overlay=True):
        self.setup_request(native=native)
        self.rx = UsbLedgerFixture(self, overlay=overlay)
        self.u.mem_write(base.seq.SEQ_STATE_ADDR+4, bytes([mode]))
        self.inquiries = b''.join(self.sysex_packets(rx.INQUIRY))
        self.replies = self.sysex_packets(rx.REPLY)
        self.first = bytes.fromhex('f000202901f7')
        self.word(0x20000900, 0x08069460)
        self.u.mem_write(0x20000904, b'\x01'); self.word(0x20000908, 0x08026F0D); self.word(0x20000914, 0)
        self.attempts, self.pops = [], []
        for pc, target in ((self.rx.labels['ul_try_reply'], self.attempts), (0x080269F0, self.pops)):
            self.u.hook_add(base.UC_HOOK_CODE, lambda u,a,n,d,t=target: t.append(a), begin=pc, end=pc)

    def send(self, packets):
        for n in range(0, len(packets), 64):
            self.rx.enqueue(packets[n:n+64]); self.rx.poll()

    def fill_pending(self):
        self.stall(); self.send(self.inquiries*ledger.MAX_PENDING)
        self.assertEqual(self.rx.status()['pending'], ledger.MAX_PENDING)
        self.assertEqual(self.rx.status()['queued'], 0)

    def test_full_capacity_query_then_note_stop_and_next_buffer_realtime_are_ordered(self):
        for mode in (0, 1):
            self.setUp(); self.setup_ledger(mode=mode); self.fill_pending()
            self.attach_native_note_receiver(); messages = self.capture_shorts(real_receiver=True)
            self.word(self.call(0x0803FD26, self.transport.transport, 0), 1)
            self.call(0x0803FE00, self.transport.transport)
            raw = bytes(self.u.mem_read(0x20010000, 0x29484))
            self.rx.enqueue(self.inquiries+bytes([9, 0x97, 60, 96, 15, 0xFC, 0, 0]))
            self.rx.enqueue(bytes([15, 0xF8, 0, 0, 8, 0x87, 60, 0]))
            self.rx.poll()
            self.assertEqual(messages, [bytes([0x97, 60, 96]), b'\xFC', b'\xF8', bytes([0x87, 60, 0])])
            self.assertEqual(self.transport.running(), 0)
            self.assertEqual(self.call(self.labels['c_midi_inputs_idle']), 1)
            self.assertEqual(self.rx.status()['owed'], 1)
            self.assertEqual(self.rx.status()['pending'], ledger.MAX_PENDING)
            read = self.rx.ring()['read']
            for _ in range(10):
                self.rx.poll()
            self.assertEqual(len(messages), 4)
            self.assertEqual(self.rx.ring()['read'], read)  # unacked owner is retained
            self.release(); self.rx.settle()
            self.assertEqual(len(messages), 4)
            self.assertEqual(self.output.delivered[0].count(self.replies[0]), ledger.MAX_PENDING+1)
            self.assertEqual(bytes(self.u.mem_read(0x20010000, 0x29484)), raw)
            self.rx.check()

    def test_almost_full_committed_rx_window_services_clock_stop_and_retains_all_replies(self):
        self.setup_ledger(); self.fill_pending(); messages = self.capture_shorts()
        for packet in (self.inquiries*8, self.inquiries*8,
                       self.inquiries*5+bytes([15, 0xF8, 0, 0, 15, 0xFC, 0, 0])):
            self.rx.enqueue(packet)
        self.assertEqual(self.rx.ring()['queued'], 182)
        self.rx.poll()
        self.assertEqual(messages, [b'\xF8', b'\xFC'])
        self.assertEqual(self.rx.status()['owed'], 21)
        self.assertEqual(self.rx.ring()['queued'], 182)
        for _ in range(4):
            self.rx.poll()
        self.assertEqual(messages, [b'\xF8', b'\xFC'])
        self.release(); self.rx.settle()
        self.assertEqual(self.output.delivered[0].count(self.replies[0]), 29)
        self.rx.check()

    def test_split_query_every_boundary_and_ring_wrap(self):
        for split in range(1, 6):
            self.setUp(); self.setup_ledger(); self.fill_pending()
            packets = self.bytes_as_packets(rx.INQUIRY)
            self.send(packets[:split*4])
            self.send(packets[split*4:]+bytes([15, 0xF8, 0, 0]))
            self.assertEqual(self.rx.status()['owed'], 1)
            self.assertEqual(self.read(self.transport.engine+0x5C), 1)
            self.release(); self.rx.settle()
            self.assertEqual(self.output.delivered[0].count(self.replies[0]), 9)
            # Native enqueue/pop wraps the192B ring repeatedly, no index reset.
            for _ in range(24):
                self.send(self.inquiries); self.rx.settle()
            self.assertEqual(self.output.delivered[0].count(self.replies[0]), 33)
            self.rx.check()

    def test_marker_transfer_does_not_replay_parser_or_break_partial_running_status(self):
        self.setup_ledger(); self.fill_pending(); messages = self.capture_shorts()
        self.send(self.inquiries+self.bytes_as_packets(bytes([0x97, 60])))
        self.assertEqual(self.rx.status()['owed'], 1)
        self.assertEqual(messages, [])
        self.release(); self.rx.settle()
        self.send(self.bytes_as_packets(bytes([96, 0xF8, 61, 0, 0xFC])))
        self.assertEqual(messages, [bytes([0x97, 60, 96]), b'\xF8', bytes([0x97, 61, 0]), b'\xFC'])
        self.rx.settle(); self.rx.check()

    def test_partial_native_producer_publication_is_not_parsed_or_acked(self):
        self.setup_ledger(); self.fill_pending()
        packet = self.inquiries
        source = 0x20007700
        self.u.mem_write(source, struct.pack('<H', len(packet))+packet)
        fifo = self.ingress.usb_fifo
        for n in range(len(packet)+2):
            self.assertEqual(self.call(0x0802A404, fifo, source+n, 1), 1)
            self.rx.poll()
            if n < len(packet)+1:
                self.assertEqual(self.rx.status()['scanned'], 0)
                self.assertEqual(self.rx.status()['owed'], 0)
                self.assertEqual(self.rx.ring()['read'], self.read(ledger.STATE_BASE+ledger.EXPECTED_READ))
                self.assertEqual(self.rx.status()['fault'], 0)
        self.assertEqual(self.rx.status()['owed'], 1)
        self.release(); self.rx.settle()
        self.assertEqual(self.output.delivered[0].count(self.replies[0]), 9)
        self.rx.check()

    def test_producer_append_during_parser_is_deferred_to_next_snapshot(self):
        self.setup_ledger(); self.fill_pending(); messages = self.capture_shorts()
        self.rx.enqueue(self.inquiries+bytes([9, 0x97, 60, 96]))
        self.u.mem_write(self.ingress.enqueue_data, bytes([15, 0xF8, 0, 0]))
        self.ingress.descriptor(self.ingress.enqueue_desc, self.ingress.enqueue_data, 4)
        injected, results = self.install_nested_calls(self.rx.labels['ul_byte'], [
            (0x08025AEC, (self.ingress.usb_fifo, self.ingress.enqueue_desc)), (rx.NATIVE_POLL, ())])
        self.rx.poll()
        self.assertEqual(results(), [1, 1]); self.assertEqual(len(injected), 1)
        self.assertEqual(messages, [bytes([0x97, 60, 96])])
        self.rx.poll()
        self.assertEqual(messages, [bytes([0x97, 60, 96]), b'\xF8'])
        self.release(); self.rx.settle(); self.rx.check()

    def test_fresh_forged_private_marker_rejects_before_any_record_callback(self):
        self.setup_ledger(); messages = self.capture_shorts()
        self.rx.enqueue(bytes([15, 0xF8, 0, 0, ledger.OWED, 0xF7, 0, 0]))
        before = bytes(self.u.mem_read(self.rx.ring()['data'], self.rx.ring()['capacity']))
        self.assertEqual(self.rx.poll(), 1)
        self.assertEqual(messages, [])
        self.assertEqual(self.rx.status()['fault'], 1)
        self.assertEqual(self.rx.status()['scanned'], 0)
        self.assertEqual(self.u.mem_read(self.rx.ring()['data'], self.rx.ring()['capacity']), before)
        self.rx.check()

    def test_provenance_boundary_reader_mismatch_and_invalid_context_fail_closed(self):
        self.setup_ledger(); self.rx.enqueue(self.inquiries)
        for off, value in ((0, rx.ORDERED_MAGIC), (ledger.PENDING, 9),
                           (ledger.SCANNED, 0xFFFFFFFF), (ledger.EXPECTED_READ, 1)):
            original = self.read(ledger.STATE_BASE+off)
            self.word(ledger.STATE_BASE+off, value)
            state = bytes(self.u.mem_read(ledger.STATE_BASE, ledger.STATE_SIZE))
            self.assertEqual(self.rx.poll(), 1)
            self.assertEqual(self.u.mem_read(ledger.STATE_BASE, ledger.STATE_SIZE), state)
            self.word(ledger.STATE_BASE+off, original)
        for reg in (base.UC_ARM_REG_PRIMASK, base.UC_ARM_REG_IPSR):
            self.u.reg_write(reg, 1 if reg == base.UC_ARM_REG_PRIMASK else 16)
            self.assertEqual(self.rx.poll(), 1); self.u.reg_write(reg, 0)
        self.rx.settle(); self.rx.check()

    def test_legacy_and_ordered_code_hashes_are_unchanged(self):
        self.assertEqual(hashlib.sha256(rx.arm_code()[0]).hexdigest(),
                         'b1b24f86615963f3a4cc08366c51a4bade7604cc53b880412877aa54edfe0b0b')
        self.assertEqual(hashlib.sha256(rx.arm_code(ordered=True)[0]).hexdigest(),
                         'f90f6c6291511fc4e63591c34a2f48050f04de5dea1c073ea3468689a6d5b119')

    def test_only_processed_header_bytes_change_in_native_rx_storage(self):
        self.setup_ledger(); self.fill_pending()
        self.rx.enqueue(self.inquiries+bytes([9, 0x97, 60, 96]))
        self.rx.enqueue(bytes([15, 0xF8, 0, 0, 15, 0xFC, 0, 0]))
        ring = self.rx.ring(); records = self.rx.records()
        before = bytes(self.u.mem_read(ring['data'], ring['capacity']))
        headers = {ring['data']+(ring['read']+r['offset']+2+p) % ring['capacity']
                   for r in records for p in range(0, r['size'], 4)}
        writes = []
        self.u.hook_add(base.UC_HOOK_MEM_WRITE, lambda u,k,a,n,v,d: writes.append((a,n,v)),
                        begin=ring['data'], end=ring['data']+ring['capacity']-1)
        self.rx.poll()
        self.assertTrue(writes)
        self.assertTrue(all(a in headers and n == 1 and v in (0, ledger.OWED) for a,n,v in writes))
        after = bytes(self.u.mem_read(ring['data'], ring['capacity']))
        self.assertTrue(all(before[n] == after[n] for n in range(ring['capacity'])
                            if ring['data']+n not in headers))
        self.release(); self.rx.settle(); self.rx.check()

    def test_fifo_capacity_backpressures_new_input_without_losing_admitted_requests(self):
        self.setup_ledger(); self.fill_pending(); messages = self.capture_shorts()
        self.rx.enqueue(self.inquiries*8); self.rx.enqueue(self.inquiries*8)
        self.rx.enqueue(self.inquiries*5+bytes([15, 0xF8, 0, 0, 15, 0xFC, 0, 0]))
        before = self.rx.ring()
        self.u.mem_write(self.ingress.enqueue_data, self.inquiries)
        self.ingress.descriptor(self.ingress.enqueue_desc, self.ingress.enqueue_data, len(self.inquiries))
        self.assertEqual(self.call(0x08025AEC, self.ingress.usb_fifo, self.ingress.enqueue_desc), 0)
        self.assertEqual(self.rx.ring(), before)  # refused record was never admitted
        self.rx.poll(); self.assertEqual(messages, [b'\xF8', b'\xFC'])
        self.release(); self.rx.settle()
        self.assertEqual(self.output.delivered[0].count(self.replies[0]), 29)
        self.rx.check()

    def test_native_driver_stall_preserves_all_reply_and_din_bytes(self):
        self.setup_ledger(native=True)
        first = b'\xF0'+bytes(n % 128 for n in range(358))+b'\xF7'
        self.assertEqual(self.q.submit(self.sysex_descriptor(first)), 0)
        self.q.poll(); self.q.poll()
        self.assertEqual(self.native.usb_full(), 1)
        self.send(self.inquiries*8)
        self.rx.enqueue(self.inquiries*8); self.rx.enqueue(self.inquiries*8)
        self.rx.poll()
        self.assertEqual(self.rx.status()['owed'], 16)
        wires = [bytearray(), bytearray()]
        for _ in range(256):
            self.q.poll(); a, p = len(self.attempts), len(self.pops); self.rx.poll()
            self.assertLessEqual(len(self.attempts)-a, 1); self.assertLessEqual(len(self.pops)-p, 1)
            if self.native.in_flight is not None:
                self.native.release_usb_endpoint()
            for n in range(2):
                wires[n].extend(self.native.drain_uart(n))
            if not self.q.status()['active'] and not self.rx.status()['pending'] and not self.rx.status()['queued']:
                break
        else:
            self.fail('native USB/DIN driver drain did not finish')
        self.assertEqual([bytes(w) for w in wires], [first]*2)
        self.assertEqual(b''.join(self.native.usb_completed), b''.join(self.sysex_packets(first)+self.replies*24))
        self.rx.check()

    def test_64_voice_stop_keeps_closures_and_unacknowledged_inquiry_owners(self):
        for mode in (0, 1):
            self.setUp(); self.setup_ledger(mode=mode); self.seed_notes(64); self.fill_pending()
            raw = bytes(self.u.mem_read(0x20010000, 0x29484))
            self.rx.enqueue(self.inquiries+bytes([15, 0xF8, 0, 0, 15, 0xFC, 0, 0]))
            self.rx.poll(); self.assertEqual(self.transport.running(), 0)
            self.release()
            for _ in range(40):
                self.q.poll(); self.rx.poll()
            for messages in self.output.delivered:
                self.assertEqual(sum(p[0] == 8 for p in messages), 64)
                self.assertEqual(sum(p[1] == 0xFC for p in messages), 1)
                self.assertEqual(sum(p[1] == 0xF8 for p in messages), 1)
            self.assertEqual(self.rx.status()['pending']+self.rx.status()['owed'], 9)
            self.assertEqual(self.u.mem_read(0x20010000, 0x29484), raw)
            self.rx.check()

    def test_differential_fresh_and_previously_processed_musical_order(self):
        rng = random.Random(57063)
        for case in range(16):
            stream = bytearray()
            for _ in range(8):
                stream.extend(rx.INQUIRY)
                stream.extend([0x90|rng.randrange(16), rng.randrange(128),
                               rng.choice([0xF8, 0xFC]), rng.randrange(128)])
                stream.extend([rng.randrange(128), 0])  # running-status Off
            packets = self.bytes_as_packets(stream)
            traces = []
            for overlay in (False, True):
                self.setUp(); self.setup_ledger(overlay=overlay); self.fill_pending() if overlay else self.stall()
                messages = self.capture_shorts()
                # Keep each window within the native finite ring; drain inquiry
                # obligations between windows, with repeat peeks before drain.
                for off in range(0, len(packets), 64):
                    self.rx.enqueue(packets[off:off+64]); self.rx.poll()
                    if overlay:
                        before = list(messages)
                        self.rx.poll(); self.assertEqual(messages, before)
                        self.release(); self.rx.settle()
                traces.append(messages)
                if overlay:
                    self.rx.check()
            self.assertEqual(traces[0], traces[1], case)

    def test_supported_ring_bounds_reject_invalid_ram_and_capacity(self):
        self.setup_ledger(); fifo = self.ingress.usb_fifo
        original = bytes(self.u.mem_read(fifo, 12))
        for capacity, data in ((5, 0x20002900), (ledger.MAX_RING+1, 0x20002900),
                               (192, 0x40000000), (192, 0x2004F650)):
            self.u.mem_write(fifo, struct.pack('<I4H', data, capacity, 0, 0, 64))
            self.assertEqual(self.rx.poll(), 1)
            self.assertEqual(self.rx.status()['pending'], 0)
        self.u.mem_write(fifo, original); self.rx.check()

    def test_largest_supported_committed_window_has_a_finite_instruction_budget(self):
        self.setup_ledger()
        self.ingress.ring(self.ingress.usb_fifo, 0x20008000, ledger.MAX_RING, 64)
        self.fill_pending(); messages = self.capture_shorts()
        for _ in range((ledger.MAX_RING-1)//66-1):
            self.rx.enqueue(self.inquiries*8)
        self.rx.enqueue(self.inquiries*7+bytes([15, 0xF8, 0, 0, 15, 0xFC, 0, 0]))
        # The general fixture's100k limit is for small individual calls. This
        # maximum-capacity stress call has an explicit500k budget, measured
        # rather than pretending it proves native cycles or real task latency.
        count = [0]
        hook = self.u.hook_add(base.UC_HOOK_CODE, lambda u,a,n,d: count.__setitem__(0, count[0]+1))
        saved = [self.u.reg_read(r) for r in base.SAVED]
        self.u.reg_write(base.UC_ARM_REG_SP, 0x20040000)
        self.u.reg_write(base.UC_ARM_REG_LR, base.STOP|1)
        self.u.emu_start(rx.NATIVE_POLL|1, base.STOP, count=500000)
        self.u.hook_del(hook)
        self.assertEqual(self.u.reg_read(base.UC_ARM_REG_PC), base.STOP)
        self.assertEqual(self.u.reg_read(base.UC_ARM_REG_SP), 0x20040000)
        self.assertEqual([self.u.reg_read(r) for r in base.SAVED], saved)
        self.assertLess(count[0], 500000)
        type(self).maximum_window_instructions = count[0]
        self.assertEqual(messages, [b'\xF8', b'\xFC'])
        self.assertEqual(self.rx.status()['owed'], ((ledger.MAX_RING-1)//66)*8-1)
        self.rx.check()

    def test_native_item_size_is_a_byte_and_padding_is_not_a_rejection_condition(self):
        self.setup_ledger()
        self.u.mem_write(self.ingress.usb_fifo+11, b'\xA5')
        self.send(self.inquiries); self.rx.settle()
        self.assertEqual(self.output.delivered[0], self.replies)
        self.assertEqual(self.rx.status()['fault'], 0)
        self.rx.check()

    def test_local_cfg_abi_and_ownership_manifest_audit(self):
        from audit_midi_usb_ledger_prototype import audit
        with tempfile.TemporaryDirectory() as out:
            report = audit(out)
        self.assertEqual(report['combined_synthetic_ram_bytes'], 1432)
        self.assertEqual(report['max_native_rx_pops_per_pass'], 1)
        self.assertEqual(report['max_reply_attempts_per_pass'], 1)
        self.assertEqual(report['forced_irq_mask_instructions'], 0)
        self.assertEqual(max(f['max_local_stack_bytes'] for f in report['functions'].values()), 32)


if __name__ == '__main__':
    unittest.main()
