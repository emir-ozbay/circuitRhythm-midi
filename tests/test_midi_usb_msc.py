"""Active MSC CBW cancellation over native USB/BOT and synthetic MMIO."""
import unittest
import test_midi_usb_composite as prior
import midi_usb_msc_prototype as msc
import midi_usb_session_prototype as session
from midi_usb_msc_test_support import UsbMscFixture

base=prior.base


class UsbMscTests(unittest.TestCase):
    setUpClass=classmethod(prior.UsbCompositeTests.setUpClass.__func__)
    for name in ('setUp','word','read','store','call','setup_playback','setup_recovery',
                 'setup_sysex_router','sysex_descriptor','install_nested_calls','setup_notice','setup_request',
                 'seed_notes','stall','release','capture_shorts','attach_native_note_receiver','setup_ledger',
                 'setup_life','setup_session','setup_control','setup_composite','send','fill_pending','finish_reply'):
        locals()[name]=getattr(prior.UsbCompositeTests,name)
    sysex_packets=staticmethod(prior.UsbCompositeTests.sysex_packets)
    bytes_as_packets=staticmethod(prior.UsbCompositeTests.bytes_as_packets)

    def setup_msc(self): self.setup_composite(); self.mc=UsbMscFixture(self)

    def test_active_cbw_deconfigure_waits_ack_and_flush_before_native_teardown(self):
        self.setup_msc(); self.mc.configure(); before=self.u.mem_read(msc.CBW,31)
        self.assertEqual(self.cc.configure(0),0)
        self.assertEqual(self.mc.status()['phase'],msc.CLOSING)
        self.assertEqual(self.mc.events,[])
        self.assertEqual(self.mc.service(),1)
        self.assertEqual(self.mc.status()['phase'],msc.WAIT_DISABLE)
        self.assertEqual(self.mc.service(),1); self.assertEqual(self.mc.status()['rx_active'],1)
        self.assertEqual(self.mc.status()['teardowns'],0)
        self.mc.ack(); self.assertEqual(self.mc.service(),1)
        self.assertEqual(self.mc.status()['phase'],msc.WAIT_FLUSH)
        self.assertEqual(self.mc.service(),1); self.assertEqual(self.mc.status()['rx_active'],1)
        self.assertEqual(self.u.mem_read(msc.CBW,31),before)
        self.mc.finish_flush(); self.mc.pump()
        self.assertEqual(self.mc.status()['cancel_rx'],1)
        self.assertEqual(self.mc.status()['phase'],msc.SEALED)
        self.assertEqual(self.mc.status()['teardowns'],1)
        self.assertTrue(any(n=='msc_class_deinit' for n,_ in self.mc.events)); self.mc.check()

    def test_deconfigure_reconfigure_arms_one_new_cbw_then_midi_reply(self):
        self.setup_msc(); self.mc.configure(); ticket=self.mc.status()['ticket']
        self.cc.configure(0); self.mc.pump(); self.cc.configure(1); self.mc.pump()
        self.assertGreater(self.mc.status()['ticket'],ticket)
        self.assertEqual(self.mc.status()['submits'],2)
        self.assertEqual(self.mc.status()['phase'],msc.OPEN)
        self.ib.rx_data(self.inquiries); self.ib.rx_complete(); self.ib.run(); self.rx.poll(); self.finish_reply()
        self.assertEqual(b''.join(self.native.usb_completed),b''.join(self.replies)); self.mc.check()

    def test_native_bulk_only_reset_defers_rearm_until_common_barrier(self):
        self.setup_msc(); self.mc.configure(); count=self.mc.status()['submits']
        self.assertEqual(self.mc.reset_request(),0)
        self.assertEqual(self.mc.status()['submits'],count)
        self.assertEqual(self.mc.status()['op'],msc.BOT_RESET)
        self.mc.pump()
        self.assertEqual(self.mc.status()['submits'],count+1)
        self.assertEqual(self.mc.status()['phase'],msc.OPEN)
        self.assertEqual(self.ss.status()['phase'],session.OPEN)
        self.assertEqual(self.u.mem_read(msc.BOT+0x11,1),b'\x01')
        self.assertTrue(any(n=='native_bot_reset' for n,_ in self.mc.events)); self.mc.check()

    def test_native_msc_irq_does_not_publish_until_cpu_copy_finishes(self):
        self.setup_msc(); self.mc.configure(); cbw=b'USBC'+bytes(27)
        self.ib.rx_data(cbw,endpoint=2); self.ib.rx_complete(endpoint=2); self.ib.run()
        self.assertEqual(self.u.mem_read(msc.CBW,31),cbw)
        self.assertEqual(self.mc.status()['irq_done'],1)
        self.assertEqual(self.u.mem_read(0x20006124+28,1),b'\x01')
        self.assertEqual(self.mc.status()['rx_active'],0); self.mc.check()

    def test_old_cbw_completion_while_closing_never_reaches_bot_poll(self):
        self.setup_msc(); self.mc.configure(); self.cc.configure(0)
        cbw=b'USBC'+bytes(27); self.ib.rx_data(cbw,endpoint=2); self.ib.rx_complete(endpoint=2)
        self.ib.run(); self.mc.poll()
        self.assertFalse(any(n=='scsi_dispatch' for n,_ in self.mc.events))
        self.assertEqual(self.mc.status()['irq_done'],0)
        self.mc.pump(); self.assertEqual(self.mc.status()['phase'],msc.SEALED); self.mc.check()

    def test_executing_storage_command_is_retained_closed_without_resetting_bot(self):
        self.setup_msc(); self.mc.configure(); self.u.mem_write(msc.BOT+0x10,b'\x01')
        before=self.u.mem_read(msc.BOT,20); self.cc.configure(0)
        for _ in range(4): self.assertEqual(self.mc.service(),1)
        self.assertEqual(self.u.mem_read(msc.BOT,20),before)
        self.assertEqual(self.mc.status()['phase'],msc.CLOSING)
        self.assertEqual(self.mc.status()['blocked'],1); self.assertEqual(self.mc.status()['rx_active'],1)
        self.mc.poll(); self.assertFalse(any(n=='msc_class_deinit' for n,_ in self.mc.events)); self.mc.check()

    def test_missing_disable_ack_or_ahb_idle_never_releases_cbw_owner(self):
        self.setup_msc(); self.mc.configure(); self.cc.configure(0); self.mc.service()
        self.mc.ack(ack=False)
        for _ in range(3): self.assertEqual(self.mc.service(),1)
        self.assertEqual(self.mc.status()['phase'],msc.WAIT_DISABLE)
        self.assertEqual(self.mc.status()['rx_active'],1)
        self.mc.ack(); self.ss.poke(session.GRSTCTL,0)
        self.assertEqual(self.mc.service(),1); self.assertEqual(self.mc.status()['phase'],msc.WAIT_DISABLE)
        self.ss.poke(session.GRSTCTL,0x80000000); self.mc.pump()
        self.assertEqual(self.mc.status()['cancel_rx'],1); self.mc.check()

    def test_shared_rx_fifo_drains_without_global_flush_or_early_msc_ready(self):
        self.setup_msc(); self.mc.configure(); self.ss.arm_rx()
        self.ib.rx_data(b'USBC'+bytes(27),endpoint=2); self.ib.rx_complete(endpoint=2)
        self.ib.rx_data(self.inquiries); self.ib.rx_complete()
        self.ib.run(); self.assertEqual(self.mc.status()['rx_seen'],1)
        self.assertEqual(self.u.mem_read(0x20006124+28,1),b'\x00')
        self.ib.run(); self.assertEqual(self.mc.status()['irq_done'],1)
        self.assertEqual(self.ib.status()['rx_done'],1)
        self.assertNotIn('RX',self.ss.flushes); self.rx.poll(); self.finish_reply(); self.mc.check()

    def test_partial_cbw_and_pending_fifo_survive_until_drain_and_barrier(self):
        self.setup_msc(); self.mc.configure(); self.cc.configure(0)
        self.ib.rx_data(b'partial!',endpoint=2); self.mc.service(); self.mc.ack()
        self.assertEqual(self.mc.service(),1); self.assertEqual(self.mc.status()['phase'],msc.WAIT_DISABLE)
        self.ib.run(); self.assertEqual(self.u.mem_read(msc.CBW,8),b'partial!')
        self.assertEqual(self.mc.status()['irq_done'],0)
        self.mc.pump(); self.assertEqual(self.mc.status()['cancel_rx'],1)
        self.assertEqual(self.u.mem_read(msc.CBW,8),b'partial!'); self.mc.check()

    def test_din_off_queues_survive_msc_reset_and_reconfiguration(self):
        self.setup_msc(); self.mc.configure(); self.output.note(0,60,0,on=False); self.output.drain(0)
        self.mc.reset_request(); self.mc.pump()
        self.assertEqual([self.output.pending(p) for p in (1,2)],[1,1])
        self.cc.configure(0); self.mc.pump(); self.cc.configure(1); self.mc.pump()
        self.assertEqual([self.output.pop(p) for p in (1,2)],[bytes([0x80,60,0])]*2); self.mc.check()

    def test_accepted_midi_debt_stays_owned_while_msc_cancels(self):
        self.setup_msc(); self.mc.configure(); self.fill_pending(); before=self.rx.status()
        self.mc.reset_request()
        for _ in range(8):
            self.mc.service()
            if self.mc.status()['phase']==msc.WAIT_DISABLE: self.mc.ack()
            if self.mc.status()['phase']==msc.WAIT_FLUSH: self.mc.finish_flush()
        self.assertEqual(self.mc.status()['phase'],msc.SEALED)
        self.assertEqual(self.mc.status()['submits'],1)
        self.assertEqual(self.rx.status(),before); self.mc.check()

    def test_native_poll_runs_but_reset_inside_poll_blocks_scsi_dispatch(self):
        import midi_usb_control_prototype as control
        self.setup_msc(); self.mc.configure(); self.mc.poll()
        self.assertTrue(any(n=='msc_poll' for n,_ in self.mc.events))
        injected,results=self.install_nested_calls(0x08027638,[
            (self.cc.labels['cc_request'],(control.RESET_EVENT,)),(self.mc.labels['mc_service'],())])
        self.ss.record_nested_trampoline(); self.mc.poll()
        self.assertEqual(len(injected),1); self.assertEqual(results(),[0,1])
        self.assertFalse(any(n=='scsi_dispatch' for n,_ in self.mc.events))
        self.mc.pump(); self.mc.check()

    def test_new_reset_during_cbw_submit_retains_new_job_until_its_own_barrier(self):
        import midi_usb_control_prototype as control
        self.setup_msc(); self.mc.configure(); self.mc.reset_request()
        injected,results=self.install_nested_calls(0x08042FD8,[
            (self.cc.labels['cc_request'],(control.RESET_EVENT,))])
        self.ss.record_nested_trampoline(); self.mc.pump()
        self.assertEqual(len(injected),1); self.assertEqual(results(),[0])
        self.assertEqual(self.mc.status()['submits'],2)
        self.assertEqual(self.mc.status()['cancel_rx'],2)
        self.assertEqual(self.mc.status()['phase'],msc.SEALED)
        self.assertEqual(self.ss.status()['phase'],session.SEALED); self.mc.check()

    def test_late_old_completion_after_cancel_cannot_set_ready_before_reopen(self):
        self.setup_msc(); self.mc.configure(); self.cc.configure(0); self.mc.pump()
        self.ib.rx_complete(endpoint=2); self.ib.run()
        self.assertEqual(self.mc.status()['irq_done'],0)
        self.assertEqual(self.u.mem_read(0x20006124+28,1),b'\x00')
        self.cc.configure(1); self.mc.pump(); self.assertEqual(self.mc.status()['submits'],2); self.mc.check()

    def test_xfrc_after_broken_barrier_remains_indistinguishable_negative(self):
        self.setup_msc(); self.mc.configure(); self.cc.configure(0); self.mc.pump()
        self.cc.configure(1); self.mc.pump()
        # Deliberately violate the assumed hardware barrier. An untagged old
        # status cannot identify its originating job, even with a new epoch.
        self.ib.rx_complete(endpoint=2); self.ib.run()
        self.assertEqual(self.mc.status()['irq_done'],1)
        self.assertEqual(self.mc.status()['rx_active'],0); self.mc.check()

    def test_oversized_cbw_packets_drain_to_private_scratch_and_fail_closed(self):
        self.setup_msc(); self.mc.configure(); self.u.mem_write(msc.CBW+32,b'CBW!')
        for _ in range(2):
            self.ib.rx_data(bytes(range(64)),endpoint=2); self.ib.run()
            self.assertEqual(self.u.mem_read(msc.CBW+32,4),b'CBW!')
            self.assertEqual(self.mc.status()['phase'],msc.BROKEN)
            self.assertEqual(self.mc.status()['irq_done'],0)
        self.assertEqual(self.mc.service(),1); self.assertEqual(self.ib.fifo_words.__len__(),0)
        self.mc.check()

    def test_active_msc_in_endpoint_is_retained_closed(self):
        self.setup_msc(); self.mc.configure(); self.ss.poke(msc.IN_CTL,session.EPENA)
        self.cc.configure(0)
        for _ in range(3): self.mc.service()
        self.assertEqual(self.mc.status()['blocked'],1)
        self.assertEqual(self.mc.status()['cancel_rx'],0); self.mc.check()

    def test_native_bus_reset_then_ep0_enumeration_rebuilds_msc_once(self):
        self.setup_msc(); self.mc.configure(); self.cc.reset(); self.mc.pump()
        self.assertEqual(self.mc.status()['phase'],msc.SEALED)
        self.cc.enumerate(); self.cc.address(); self.cc.configure(1); self.mc.pump()
        self.assertEqual(self.mc.status()['phase'],msc.OPEN)
        self.assertEqual(self.mc.status()['submits'],2); self.mc.check()

    def test_ticket_wrap_fails_closed_even_though_native_parent_ignores_submit_error(self):
        self.setup_msc(); self.mc.configure(); self.cc.configure(0); self.mc.pump()
        self.word(msc.STATE_BASE+msc.NEXT,0xFFFFFFFF); self.cc.configure(1)
        for _ in range(8):
            self.mc.service()
            if self.mc.status()['phase']==msc.WAIT_FLUSH: self.mc.finish_flush()
            if self.ss.status()['phase']==session.WAIT_FLUSH: self.ss.finish_flush()
        self.assertEqual(self.mc.status()['phase'],msc.BROKEN)
        self.assertEqual(self.mc.status()['submits'],1)
        self.assertNotEqual(self.ss.status()['phase'],session.OPEN); self.mc.check()

    def test_irq_context_cannot_run_main_cancellation_service(self):
        from unicorn.arm_const import UC_ARM_REG_IPSR
        self.setup_msc(); self.mc.configure(); self.cc.configure(0); before=self.mc.status()
        self.u.reg_write(UC_ARM_REG_IPSR,16)
        try: self.assertEqual(self.mc.service(),1)
        finally: self.u.reg_write(UC_ARM_REG_IPSR,0)
        self.assertEqual(self.mc.status(),before); self.mc.pump(); self.mc.check()

    def test_new_external_reset_during_native_teardown_is_not_swallowed(self):
        import midi_usb_control_prototype as control
        self.setup_msc(); self.mc.configure(); self.cc.configure(0)
        before=self.cc.status()['requests']
        injected,results=self.install_nested_calls(0x08052628,[
            (self.cc.labels['cc_request'],(control.RESET_EVENT,))])
        self.ss.record_nested_trampoline(); self.mc.pump()
        self.assertEqual(len(injected),1); self.assertEqual(results(),[0])
        self.assertEqual(self.cc.status()['requests'],before+1)
        self.assertEqual(self.mc.status()['phase'],msc.SEALED); self.mc.check()


if __name__=='__main__': unittest.main()
