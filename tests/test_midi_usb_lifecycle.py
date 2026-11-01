"""Native RX reset/pop/producer gates and explicit active-TX disconnect limit."""
import hashlib
import unittest

import test_midi_usb_ledger as prior
import midi_usb_lifecycle_prototype as life
import midi_usb_ledger_prototype as ledger
import midi_usb_inquiry_prototype as rx
from midi_usb_lifecycle_test_support import UsbLifecycleFixture

base = prior.base


class UsbLifecycleTests(unittest.TestCase):
    setUpClass = classmethod(prior.UsbLedgerTests.setUpClass.__func__)
    for name in ('setUp', 'word', 'read', 'store', 'call', 'setup_playback',
                 'setup_recovery', 'setup_sysex_router', 'sysex_descriptor',
                 'install_nested_calls', 'setup_notice', 'setup_request',
                 'seed_notes', 'stall', 'release', 'capture_shorts', 'attach_native_note_receiver',
                 'setup_ledger', 'send', 'fill_pending'):
        locals()[name] = getattr(prior.UsbLedgerTests, name)
    sysex_packets = staticmethod(prior.UsbLedgerTests.sysex_packets)
    bytes_as_packets = staticmethod(prior.UsbLedgerTests.bytes_as_packets)

    def setup_life(self, native=False, mode=1):
        self.setup_ledger(native=native, mode=mode)
        self.lc = UsbLifecycleFixture(self)

    def test_registered_native_pop_paths_cannot_consume_private_headers(self):
        self.setup_life(); self.fill_pending(); self.send(self.inquiries)
        state = bytes(self.u.mem_read(ledger.STATE_BASE, ledger.STATE_SIZE))
        source = bytes(self.u.mem_read(self.rx.ring()['data'], self.rx.ring()['capacity']))
        for pc, args in ((0x080269F0, (self.ingress.usb_port, self.ingress.usb_desc)),
                         (0x08025B1A, (self.ingress.usb_fifo, self.ingress.usb_desc)),
                         (0x0802A470, (self.ingress.usb_fifo, self.ingress.usb_data, 1)),
                         (0x0802A426, (self.ingress.usb_fifo, self.ingress.usb_data))):
            self.assertEqual(self.call(pc, *args), 0)
            self.assertEqual(self.u.mem_read(ledger.STATE_BASE, ledger.STATE_SIZE), state)
            self.assertEqual(self.u.mem_read(self.rx.ring()['data'], self.rx.ring()['capacity']), source)
        self.release(); self.rx.settle(); self.lc.check()

    def test_busy_reset_and_reconstruction_leave_owners_and_bindings_unchanged(self):
        self.setup_life(); self.fill_pending(); self.send(self.inquiries)
        region = bytes(self.u.mem_read(self.ingress.usb_fifo, 12))
        parser = bytes(self.u.mem_read(self.ingress.parser, 44))
        before = self.rx.status()
        for pc, args, result in ((0x0802A374, (self.ingress.usb_fifo,), 1),
                                  (0x08025ACC, (self.ingress.usb_fifo, 192), 0),
                                  (0x08026828, (self.ingress.usb_port, 0, 1, 2), 0),
                                  (0x080405D4, (self.ingress.parser,), 1),
                                  (0x08040604, (self.ingress.parser, 1), 1),
                                  (0x080405F8, (self.ingress.parser, 0, 0, 1), 1)):
            self.assertEqual(self.call(pc, *args), result, hex(pc))
            self.assertEqual(self.u.mem_read(self.ingress.usb_fifo, 12), region)
            self.assertEqual(self.u.mem_read(self.ingress.parser, 44), parser)
        self.assertEqual(self.lc.reset(), 1)
        self.assertEqual(self.rx.status(), before)
        self.release(); self.rx.settle(); self.lc.check()

    def test_quiescent_reset_closes_producer_then_resumes_with_new_epoch(self):
        self.setup_life()
        self.send(self.inquiries); self.rx.settle()
        self.assertNotEqual(self.rx.ring()['read'], 0)
        raw = bytes(self.u.mem_read(0x20010000, 0x29484))
        self.assertEqual(self.lc.reset(), 0)
        self.assertEqual(self.rx.ring()['read'], 0)
        self.assertEqual(self.rx.ring()['write'], 0)
        self.assertEqual(self.rx.status()['scanned'], 0)
        self.assertEqual(self.lc.status()['phase'], life.CLOSED)
        self.assertEqual(self.lc.status()['epoch'], 2)
        self.assertEqual(self.lc.offer(self.inquiries), 0)
        self.assertEqual(self.rx.poll(), 1)
        self.assertEqual(self.lc.resume(), 0)
        self.send(self.inquiries); self.rx.settle()
        self.assertEqual(self.output.delivered[0], self.replies*2)
        self.assertEqual(self.u.mem_read(0x20010000, 0x29484), raw)
        self.lc.check()

    def test_partial_parser_and_held_note_refuse_reset(self):
        for data in (bytes([0xF0, 0x7E]), bytes([0x97, 60])):
            self.setUp(); self.setup_life(); self.send(self.bytes_as_packets(data))
            parser = bytes(self.u.mem_read(self.ingress.parser, 44))
            self.assertEqual(self.lc.reset(), 1)
            self.assertEqual(self.u.mem_read(self.ingress.parser, 44), parser)
            self.lc.check()
        self.setUp(); self.setup_life(); self.attach_native_note_receiver()
        self.send(bytes([9, 0x97, 60, 96])); self.assertEqual(self.lc.reset(), 1)
        self.send(bytes([8, 0x87, 60, 0])); self.rx.settle()
        self.assertEqual(self.lc.reset(), 0); self.lc.check()

    def test_rebind_identity_mismatch_freezes_without_reading_fresh_data(self):
        self.setup_life(); self.fill_pending(); self.send(self.inquiries)
        old = self.read(self.ingress.usb_fifo)
        self.word(self.ingress.usb_fifo, 0x20008000)
        before = bytes(self.u.mem_read(0x20008000, 192))
        self.assertEqual(self.rx.poll(), 1)
        self.assertEqual(self.lc.status()['phase'], life.FROZEN)
        self.assertEqual(self.lc.status()['errors'], life.BINDING_ERROR)
        self.assertEqual(self.u.mem_read(0x20008000, 192), before)
        self.assertEqual(self.lc.reset(), 1)
        self.word(self.ingress.usb_fifo, old)
        self.assertEqual(self.lc.resume(), 1)  # freeze cannot silently become a new session

    def test_disconnect_rx_ownership_freezes_and_idle_disconnect_can_reset(self):
        self.setup_life(); self.fill_pending(); self.send(self.inquiries)
        before = self.rx.status(); self.lc.configured(0)
        self.assertEqual(self.rx.poll(), 1)
        self.assertEqual(self.lc.status()['phase'], life.FROZEN)
        self.assertEqual(self.rx.status(), before)
        self.assertEqual(self.lc.offer(bytes([15, 0xF8, 0, 0])), 0)
        self.assertEqual(self.lc.reset(), 1)
        self.lc.configured(3); self.assertEqual(self.lc.resume(), 1)
        self.setUp(); self.setup_life(); self.lc.configured(0)
        self.assertEqual(self.rx.poll(), 1); self.assertEqual(self.lc.reset(), 0)
        self.assertEqual(self.lc.resume(), 1)
        self.lc.configured(3); self.assertEqual(self.lc.resume(), 0)
        self.send(self.inquiries); self.rx.settle(); self.lc.check()

    def test_mid_producer_reset_is_rejected_and_publication_completes_once(self):
        self.setup_life()
        # Native2A404 is entered after producer ownership is published.
        injected, results = self.install_nested_calls(0x0802A404, [(self.lc.labels['cl_reset'], ())])
        self.assertEqual(self.lc.offer(self.inquiries), 1)
        self.assertEqual(results(), [1]); self.assertEqual(len(injected), 1)
        self.assertEqual(self.lc.status()['publishing'], 0)
        self.rx.settle(); self.assertEqual(self.output.delivered[0], self.replies); self.lc.check()

    def test_native_calls_on_unregistered_objects_keep_stock_behavior(self):
        self.setup_life()
        foreign = self.read(self.output.ports[0]+4)
        self.assertEqual(self.call(0x0802A374, foreign), 0)
        self.assertEqual(self.call(0x08025B1A, self.ingress.short_fifo, self.ingress.usb_desc), 0)
        self.lc.check()

    def test_active_tx_disconnect_is_not_claimed_fixed_by_rx_guard(self):
        self.setup_life(native=True)
        self.send(self.inquiries)
        self.q.poll(); self.q.poll()
        self.assertEqual(self.q.status()['active'], 0)  # reader drain is not endpoint completion
        self.assertEqual(self.rx.status()['pending'], 0)
        self.assertIsNotNone(self.native.in_flight)
        self.lc.configured(0); self.assertEqual(self.rx.poll(), 1)
        self.assertEqual(self.lc.reset(), 1)
        # Deliberate negative: RX-only guard does not own TX service/DMA epoch.
        # Reconnection can still drain an old reply through the native worker.
        self.lc.configured(3)
        for _ in range(20):
            self.q.poll()
            if self.native.in_flight is not None:
                self.native.release_usb_endpoint()
        self.assertEqual(b''.join(self.native.usb_completed), b''.join(self.replies))
        self.assertEqual(self.lc.status()['phase'], life.FROZEN)

    def test_previous_ledger_codegen_is_unchanged(self):
        self.assertEqual(hashlib.sha256(ledger.arm_code()[0]).hexdigest(),
                         'bd43c2b77b861c710e99fc3f81c23bc607ddf9858eab09b6335c7e5310f20fa8')

    def test_raw_producer_paths_cannot_bypass_the_publication_guard(self):
        self.setup_life()
        self.u.mem_write(self.ingress.enqueue_data, self.inquiries)
        before = self.rx.ring()
        self.assertEqual(self.call(0x0802A404, self.ingress.usb_fifo, self.ingress.enqueue_data, 8), 0)
        self.assertEqual(self.call(0x0802A3BE, self.ingress.usb_fifo, 0xF8), 0)
        self.assertEqual(self.rx.ring(), before)
        self.send(self.inquiries); self.rx.settle(); self.lc.check()

    def test_irq_and_masked_producer_preserve_context_and_publication_ownership(self):
        for reg, value in ((base.UC_ARM_REG_IPSR, 16), (base.UC_ARM_REG_PRIMASK, 1)):
            self.setUp(); self.setup_life()
            self.u.reg_write(reg, value)
            self.assertEqual(self.lc.offer(self.inquiries), 1)
            self.assertEqual(self.u.reg_read(reg), value)
            self.assertEqual(self.lc.status()['publishing'], 0)
            self.assertEqual(self.lc.reset(), 1)
            self.u.reg_write(reg, 0)
            self.rx.settle(); self.assertEqual(self.output.delivered[0], self.replies)
            self.lc.check()

    def test_reset_transaction_blocks_producer_and_nested_reset_before_native_clear(self):
        self.setup_life()
        self.u.mem_write(self.ingress.enqueue_data, self.inquiries)
        self.ingress.descriptor(self.ingress.enqueue_desc, self.ingress.enqueue_data, len(self.inquiries))
        pc = self.lc.labels['cl_trampoline_0802a374']
        injected, results = self.install_nested_calls(pc, [
            (0x08025AEC, (self.ingress.usb_fifo, self.ingress.enqueue_desc)),
            (0x0802A404, (self.ingress.usb_fifo, self.ingress.enqueue_data, 8)),
            (self.lc.labels['cl_reset'], ()), (rx.NATIVE_POLL, ())])
        self.assertEqual(self.lc.reset(), 0)
        self.assertEqual(results(), [0, 0, 1, 1]); self.assertEqual(len(injected), 1)
        self.assertEqual(self.rx.ring()['queued'], 0)
        self.assertEqual(self.lc.resume(), 0); self.lc.check()

    def test_foreign_consumer_during_real_parser_cannot_steal_read_ownership(self):
        self.setup_life()
        injected, results = self.install_nested_calls(self.rx.labels['ul_byte'], [
            (0x080269F0, (self.ingress.usb_port, self.ingress.usb_desc)),
            (0x08025B1A, (self.ingress.usb_fifo, self.ingress.usb_desc)),
            (0x0802A470, (self.ingress.usb_fifo, self.ingress.usb_data, 1)),
            (0x0802A426, (self.ingress.usb_fifo, self.ingress.usb_data))])
        self.send(self.inquiries); self.rx.settle()
        self.assertEqual(results(), [0]*4); self.assertEqual(len(injected), 1)
        self.assertEqual(self.output.delivered[0], self.replies); self.lc.check()

    def test_api_context_and_epoch_wrap_rejections_leave_registered_state_untouched(self):
        self.setup_life()
        for reg, value in ((base.UC_ARM_REG_IPSR, 16), (base.UC_ARM_REG_PRIMASK, 1)):
            self.u.reg_write(reg, value)
            before = bytes(self.u.mem_read(life.STATE_BASE, life.STATE_SIZE))
            self.assertEqual(self.lc.reset(), 1); self.assertEqual(self.lc.resume(), 1)
            self.assertEqual(self.u.mem_read(life.STATE_BASE, life.STATE_SIZE), before)
            self.u.reg_write(reg, 0)
        self.word(life.STATE_BASE+life.EPOCH, 0xFFFFFFFF)
        before = bytes(self.u.mem_read(life.STATE_BASE, life.STATE_SIZE))
        self.assertEqual(self.lc.reset(), 1)
        self.assertEqual(self.u.mem_read(life.STATE_BASE, life.STATE_SIZE), before)
        self.lc.check()

    def test_stock_static_endpoint_constructor_prefix_builds_1057_byte_rx_ring(self):
        # Fresh synthetic RAM, native allocator and endpoint constructors only.
        # Stop before the unrelated static constructors at666BA; not full boot.
        self.call(0x0806668C, end=0x080666BA)
        port = 0x20005F94
        fifo = self.read(port+0x18)
        self.assertNotEqual(fifo, 0)
        self.assertEqual(int.from_bytes(self.u.mem_read(fifo+4, 2), 'little'), (64+2)*16+1)
        self.assertEqual(self.u.mem_read(fifo+10, 1), b'\x40')
        self.assertEqual(self.u.mem_read(port, 1), b'\x01')
        self.assertEqual(self.read(port+0x10), 0x20005CC8)
        self.assertNotEqual(self.read(port+0x14), 0)
        self.assertEqual(self.read(0x20005F70+0x18), 0)  # TX endpoint has no RX ring

    def test_native_disconnect_callback_keeps_rx_ring_bytes_and_indexes(self):
        self.setup_life(); self.fill_pending(); self.send(self.inquiries)
        wrapper, vt, ports = 0x20007B00, 0x20007B40, 0x20007B80
        self.word(wrapper, vt); self.word(wrapper+4, ports+8); self.word(wrapper+8, ports)
        self.word(ports, self.ingress.usb_port); self.word(ports+4, 0); self.word(ports+8, 0)
        self.word(vt+4, 0)
        self.u.mem_write(0x0802C90C, bytes.fromhex('00207047'))  # native hardware close boundary
        self.u.ctl_remove_cache(0x0802C90C, 0x0802C928)
        before = self.rx.status(); data = self.rx.ring()['data']
        raw = bytes(self.u.mem_read(data, self.rx.ring()['capacity']))
        self.call(0x0805261C, wrapper, self.read(life.STATE_BASE+life.CONTROLLER), 0)
        self.assertEqual(self.rx.status(), before)
        self.assertEqual(self.u.mem_read(data, self.rx.ring()['capacity']), raw)
        self.lc.configured(0); self.assertEqual(self.rx.poll(), 1)
        self.assertEqual(self.lc.status()['phase'], life.FROZEN)
        self.assertEqual(self.rx.status(), before)

    def test_closed_or_frozen_rx_completion_and_rearm_do_not_touch_native_port(self):
        self.setup_life()
        self.assertEqual(self.lc.reset(), 0)
        before = bytes(self.u.mem_read(self.ingress.usb_port, 36))
        for pc in (0x080269AC, 0x08026988):
            self.assertEqual(self.call(pc, self.ingress.usb_port, 8), 0)
        self.assertEqual(self.u.mem_read(self.ingress.usb_port, 36), before)
        self.assertEqual(self.lc.resume(), 0)
        self.lc.configured(0); self.assertEqual(self.rx.poll(), 1)
        for pc in (0x080269AC, 0x08026988):
            self.assertEqual(self.call(pc, self.ingress.usb_port, 8), 0)
        self.assertEqual(self.u.mem_read(self.ingress.usb_port, 36), before)

    def test_lifecycle_local_audit_and_pinned_native_trace(self):
        import tempfile
        from audit_midi_usb_lifecycle_prototype import audit
        from trace_midi_usb_lifecycle import trace
        with tempfile.TemporaryDirectory() as out:
            result = audit(out)
            contract = trace(out)
        self.assertEqual(result['combined_synthetic_ram_bytes'], 1496)
        self.assertFalse(result['masked_calls_or_loops'])
        self.assertEqual(len(result['emulator_overlays']), len(life.GATES)+1)
        self.assertEqual(contract['direct_refs']['0x80269f0'], ['0x8029b2a'])


if __name__ == '__main__':
    unittest.main()
