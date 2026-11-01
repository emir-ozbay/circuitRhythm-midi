"""Real stock HAL submit/IRQ/native callback chain with CPU-FIFO MMIO model."""
import unittest
import test_midi_usb_session as prior
import midi_usb_irq_prototype as irq
import midi_usb_session_prototype as session
import midi_usb_lifecycle_prototype as life
import hashlib
from midi_usb_irq_test_support import UsbIrqFixture

base=prior.base


class UsbIrqTests(unittest.TestCase):
    setUpClass=classmethod(prior.UsbSessionTests.setUpClass.__func__)
    for name in ('setUp','word','read','store','call','setup_playback','setup_recovery',
                 'setup_sysex_router','sysex_descriptor','install_nested_calls',
                 'setup_notice','setup_request','seed_notes','stall','release',
                 'capture_shorts','attach_native_note_receiver','setup_ledger',
                 'setup_life','setup_session','send','fill_pending'):
        locals()[name]=getattr(prior.UsbSessionTests,name)
    sysex_packets=staticmethod(prior.UsbSessionTests.sysex_packets)
    bytes_as_packets=staticmethod(prior.UsbSessionTests.bytes_as_packets)

    def setup_irq(self):
        self.setup_session(); self.ib=UsbIrqFixture(self)

    def finish_reply(self):
        for _ in range(16):
            self.q.poll(); self.rx.poll()
            if self.native.in_flight is not None:
                self.ib.tx_empty(); self.assertEqual(self.ib.run(),0)
                self.ib.tx_complete(); self.assertEqual(self.ib.run(),0)
            if not self.q.status()['active'] and not self.rx.status()['pending'] and self.native.in_flight is None:
                return
        self.fail('Native IRQ reply did not drain')

    def test_native_tx_submit_fifo_and_callback_chain_needs_no_test_tag(self):
        self.setup_irq(); self.send(self.inquiries); self.finish_reply()
        self.assertEqual(b''.join(self.native.usb_completed),b''.join(self.replies))
        for pc in (0x0804301A,0x080531A6,0x0802C7AC,0x08042690,
                   0x0802AB36,0x08040C22,0x0805268E): self.assertIn(pc,self.ib.visits)
        self.assertEqual(self.ib.status()['tx_done'],1); self.ib.check()

    def test_native_rx_fifo_copy_then_callback_publishes_exactly_once(self):
        self.setup_irq(); self.ss.arm_rx()
        self.ib.rx_data(self.inquiries); self.assertEqual(self.ib.run(),0)
        self.assertEqual(self.rx.status()['queued'],0)
        self.assertEqual(self.ib.copy_words,len(self.inquiries)//4)
        self.ib.rx_complete(); self.assertEqual(self.ib.run(),0)
        self.assertEqual(self.ib.status()['rx_done'],1)
        self.rx.poll(); self.finish_reply()
        self.assertEqual(b''.join(self.native.usb_completed),b''.join(self.replies))
        for pc in (0x08042FD8,0x080531CC,0x0802C798,0x08042614,
                   0x0802AB42,0x08040C46,0x080526C8): self.assertIn(pc,self.ib.visits)
        self.ib.check()

    def test_coalesced_out_completion_waits_for_native_fifo_copy(self):
        self.setup_irq(); self.ss.arm_rx()
        self.ib.rx_data(self.inquiries); self.ib.rx_complete()
        self.assertEqual(self.ib.run(),0)
        self.assertEqual(self.ib.status()['rx_done'],1)
        self.rx.poll(); self.finish_reply()
        self.assertEqual(b''.join(self.native.usb_completed),b''.join(self.replies)); self.ib.check()

    def test_rx_pending_frame_retains_identity_across_two_fifo_irqs(self):
        self.setup_irq(); self.ss.arm_rx(); token=self.ss.status()['rx_ticket']
        self.ib.rx_data(self.inquiries[:4]); self.ib.rx_data(self.inquiries[4:]); self.ib.rx_complete()
        self.ib.run()
        self.assertEqual(self.ib.status()['rx_seen'],1)
        self.assertEqual(self.ib.status()['rx_done'],0)
        self.assertEqual(self.ss.status()['rx_ticket'],token)
        self.assertEqual(self.rx.status()['queued'],0)
        self.ib.run()
        self.assertEqual(self.ib.status()['rx_seen'],0); self.assertEqual(self.ib.status()['rx_done'],1)
        self.assertGreater(self.ss.status()['rx_ticket'],token)
        self.rx.poll(); self.finish_reply()
        self.assertEqual(b''.join(self.native.usb_completed),b''.join(self.replies)); self.ib.check()

    def test_simultaneous_rx_tx_completions_keep_separate_owners(self):
        self.setup_irq(); self.send(self.inquiries); self.q.poll(); self.q.poll()
        self.ss.arm_rx(); self.ib.tx_empty(); self.ib.run()
        self.ib.rx_data(self.inquiries); self.ib.rx_complete(); self.ib.tx_complete()
        self.ib.run()
        self.assertEqual(self.ib.status()['rx_done'],1); self.assertEqual(self.ib.status()['tx_done'],1)
        self.rx.poll(); self.finish_reply()
        self.assertEqual(b''.join(self.native.usb_completed),b''.join(self.replies)*2); self.ib.check()

    def test_direct_native_callbacks_outside_irq_do_not_release_or_publish(self):
        self.setup_irq(); self.ss.arm_rx(); self.send(self.inquiries); self.q.poll(); self.q.poll()
        before=self.ss.status(); rx_before=self.rx.status()
        self.assertEqual(self.call(0x08026988,self.ingress.usb_port,8),0)
        self.call(0x080268D0,self.native.usb_endpoint)
        self.assertEqual(self.ss.status(),before); self.assertEqual(self.rx.status(),rx_before)
        self.finish_reply(); self.ib.check()

    def test_nested_irq_is_refused_without_overwriting_frame(self):
        self.setup_irq(); self.ss.arm_rx()
        injected,results=self.install_nested_calls(self.ib.labels['ib_after_native_irq'],[
            (irq.NATIVE_IRQ,(self.ib.handle,))])
        self.ss.record_nested_trampoline()
        self.ib.rx_data(self.inquiries); self.ib.rx_complete(); self.ib.run()
        self.assertEqual(results(),[1]); self.assertEqual(len(injected),1)
        self.assertEqual(self.ib.status()['rx_done'],1)
        self.rx.poll(); self.finish_reply(); self.ib.check()

    def test_cancel_from_irq_is_refused_before_ownership_can_change(self):
        self.setup_irq(); self.ss.arm_rx()
        injected,results=self.install_nested_calls(0x080526C8,[
            (self.ss.labels['ss_begin'],())])
        self.ss.record_nested_trampoline()
        self.ib.rx_data(self.inquiries); self.ib.rx_complete(); self.ib.run()
        self.assertEqual(results(),[1]); self.assertEqual(len(injected),1)
        self.assertEqual(self.ss.status()['phase'],session.OPEN)
        self.rx.poll(); self.finish_reply(); self.ib.check()

    def test_irq_drains_old_cpu_fifo_while_session_closes_without_publishing(self):
        self.setup_irq(); self.ss.arm_rx(); self.ib.rx_data(self.inquiries)
        self.ib.rx_complete(); self.ss.begin(); self.ss.step()
        self.assertEqual(self.ib.run(),0)
        self.assertEqual(self.ib.status()['rx_done'],0); self.assertEqual(self.rx.status()['queued'],0)
        self.assertFalse(self.ib.events); self.assertFalse(self.ib.fifo_words)
        self.assertEqual(self.ss.step(),1); self.ss.finish_flush(); self.assertEqual(self.ss.step(),0)
        self.assertEqual(self.ss.resume(),0)
        self.ib.rx_data(self.inquiries); self.ib.rx_complete(); self.ib.run()
        self.rx.poll(); self.finish_reply()
        self.assertEqual(b''.join(self.native.usb_completed),b''.join(self.replies)); self.ib.check()

    def test_pending_rx_snapshot_is_discarded_after_cancel_epoch(self):
        self.setup_irq(); self.ss.arm_rx(); old=self.ss.status()['rx_ticket']
        self.ib.rx_data(self.inquiries[:4]); self.ib.rx_data(self.inquiries[4:]); self.ib.rx_complete()
        self.ib.run(); self.assertEqual(self.ib.status()['rx_seen'],1)
        self.ss.begin(); self.ss.step(); self.ib.run()
        self.ss.step(); self.ss.finish_flush(); self.ss.step(); self.ss.resume()
        self.ib.rx_data(self.inquiries); self.ib.rx_complete(); self.ib.run()
        self.assertEqual(self.read(irq.STATE_BASE+irq.CANCEL_RX),1)
        self.assertNotEqual(self.ss.status()['rx_ticket'],old)
        self.assertEqual(self.ib.status()['rx_done'],1)
        self.rx.poll(); self.finish_reply(); self.ib.check()

    def test_dma_and_control_reset_causes_are_explicitly_unsupported(self):
        self.setup_irq(); self.ss.arm_rx(); self.word(self.ib.handle+16,1)
        self.assertEqual(self.ib.run(),1); self.assertEqual(self.ss.status()['phase'],session.BROKEN)
        self.assertEqual(self.lc.status()['phase'],life.FROZEN); self.assertEqual(self.ib.status()['rx_done'],0)
        self.setUp(); self.setup_irq(); self.ss.arm_rx()
        self.ib.external=1<<12; self.ss.poke(0x18,irq.ALLOWED_GINT|(1<<12))
        self.assertEqual(self.ib.run(),1); self.assertEqual(self.ss.status()['phase'],session.BROKEN)
        self.assertEqual(self.ss.status()['rx_active'],1)  # old owner was not cleared

    def test_direct_native_disconnect_freezes_before_endpoint_close(self):
        self.setup_irq(); self.ss.arm_rx()
        self.call(0x0805261C,self.ib.wrapper,self.ib.ctrl,0)
        self.assertEqual(self.ss.status()['phase'],session.BROKEN)
        self.assertEqual(self.lc.status()['phase'],life.FROZEN)
        self.assertEqual(self.ss.status()['rx_active'],1)
        self.assertEqual(self.ss.resume(),1); self.ib.check()

    def test_other_endpoint_cpu_rx_copy_does_not_complete_midi_job(self):
        self.setup_irq(); self.ss.arm_rx()
        descriptor=self.ib.handle+0x1FC+3*0x1C; destination=0x2000A600
        self.word(descriptor+12,destination); self.word(descriptor+8,64)
        self.ib.rx_data(b'TEST',endpoint=3); self.ib.rx_complete(endpoint=3); self.ib.run()
        self.assertEqual(bytes(self.u.mem_read(destination,4)),b'TEST')
        self.assertEqual(self.ib.status()['rx_done'],0); self.assertEqual(self.rx.status()['queued'],0)
        self.assertEqual(self.ss.status()['rx_active'],1); self.ib.check()

    def test_snapshot_is_fixed_before_callback_and_ss_rearm(self):
        self.setup_irq(); self.ss.arm_rx(); token=self.ss.status()['rx_ticket']
        self.ib.rx_data(self.inquiries); self.ib.rx_complete(); self.ib.run()
        self.assertEqual(self.read(irq.STATE_BASE+irq.RX_TICKET),token)
        self.assertGreater(self.ss.status()['rx_ticket'],token)
        self.rx.poll(); self.finish_reply(); self.ib.check()

    def test_broken_barrier_old_untagged_hardware_flag_can_masquerade_as_new(self):
        self.setup_irq(); self.ss.arm_rx(); self.ss.close(); self.ss.resume()
        new=self.ss.status()['rx_ticket']
        # Required negative: actual native hardware XFRC has no generation.
        # A fabricated old XFRC after the assumed barrier looks like completion
        # of the newly armed job. IRQ snapshotting cannot disambiguate it.
        self.ib.rx_complete(); self.ib.run()
        self.assertEqual(self.ib.status()['rx_done'],1)
        self.assertGreater(self.ss.status()['rx_ticket'],new)
        self.assertEqual(self.rx.status()['queued'],0); self.ib.check()

    def test_foreign_handle_empty_irq_retains_native_path(self):
        self.setup_irq(); foreign=0x2000B000; self.word(foreign,self.ib.base)
        before=self.ib.status(); self.call(irq.NATIVE_IRQ,foreign)
        self.assertEqual(self.ib.status(),before); self.ib.check()

    def test_previous_session_codegen_is_unchanged(self):
        self.assertEqual(hashlib.sha256(session.arm_code()[0]).hexdigest(),
                         'fe091ec2e783a8eab3210405df7dcca0302dfea2e7056d20e69c06522cfcbf9d')

    def test_wrong_return_pc_cannot_claim_an_existing_irq_snapshot(self):
        self.setup_irq(); self.send(self.inquiries); self.q.poll(); self.q.poll()
        self.ss.arm_rx(); self.ib.tx_empty(); self.ib.run()
        injected,results=self.install_nested_calls(0x080526C8,[
            (0x08026988,(self.ingress.usb_port,8)),(0x080268D0,(self.native.usb_endpoint,))])
        self.ss.record_nested_trampoline()
        self.ib.rx_data(self.inquiries); self.ib.rx_complete(); self.ib.tx_complete(); self.ib.run()
        self.assertEqual(results(),[0,0]); self.assertEqual(len(injected),1)
        self.assertEqual(self.ib.status()['tx_done'],1); self.assertEqual(self.ib.status()['rx_done'],1)
        self.rx.poll(); self.finish_reply(); self.ib.check()

    def test_native_initialization_prefix_selects_cpu_fifo_and_hs_register_base(self):
        self.setup_irq(); controller=0x2000B000; self.u.mem_write(controller,b'\x01')
        self.call(0x0802C82A,controller,end=0x0802C862)
        handle=self.read(controller+0x298)
        self.assertEqual(handle,0x200054B4)
        self.assertEqual(self.read(handle),0x40040000)
        self.assertEqual(self.read(handle+16),0)
        self.assertEqual(self.read(handle+4),6)
        self.assertEqual(self.read(handle+0x400),controller)
        self.ib.check()  # partial prefix only; stopped before native hardware init


if __name__=='__main__': unittest.main()
