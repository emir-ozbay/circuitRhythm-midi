"""Native EP0 SET_CONFIGURATION and deferred MIDI endpoint reconstruction."""
import unittest
import test_midi_usb_irq as prior
import midi_usb_control_prototype as control
import midi_usb_session_prototype as session
import midi_usb_lifecycle_prototype as life
import midi_usb_irq_prototype as irq
import hashlib
from midi_usb_irq_test_support import UsbIrqFixture
from midi_usb_control_test_support import UsbControlFixture

base=prior.base


class UsbControlTests(unittest.TestCase):
    setUpClass=classmethod(prior.UsbIrqTests.setUpClass.__func__)
    for name in ('setUp','word','read','store','call','setup_playback','setup_recovery',
                 'setup_sysex_router','sysex_descriptor','install_nested_calls',
                 'setup_notice','setup_request','seed_notes','stall','release',
                 'capture_shorts','attach_native_note_receiver','setup_ledger',
                 'setup_life','setup_session','send','fill_pending','finish_reply'):
        locals()[name]=getattr(prior.UsbIrqTests,name)
    sysex_packets=staticmethod(prior.UsbIrqTests.sysex_packets)
    bytes_as_packets=staticmethod(prior.UsbIrqTests.bytes_as_packets)

    def setup_control(self):
        self.setup_session(); self.ib=UsbIrqFixture(self,control=True); self.cc=UsbControlFixture(self)

    def test_native_reset_irq_closes_then_native_ep0_configuration_reopens(self):
        self.setup_control(); self.ss.arm_rx()
        self.assertEqual(self.cc.reset(),0)
        self.assertEqual(self.cc.status()['reset'],1)
        self.assertEqual(self.ss.status()['phase'],session.CLOSING)
        self.cc.pump(); self.assertEqual(self.ss.status()['phase'],session.SEALED)
        # Native setup path expects addressed state after SET_ADDRESS. Address
        # assignment is outside this test; configuration itself is native.
        self.lc.configured(2); self.assertEqual(self.cc.configure(1),0)
        self.assertEqual(self.u.mem_read(self.ib.ctrl+0x274,1),b'\x03')
        self.assertEqual(self.cc.constructors,[])
        self.cc.pump(); self.assertEqual(self.ss.status()['phase'],session.OPEN)
        self.assertEqual(len(self.cc.constructors),1)
        self.assertEqual(self.cc.bootstrap,[session.SEALED])
        self.ib.rx_data(self.inquiries); self.ib.rx_complete(); self.ib.run()
        self.rx.poll(); self.finish_reply()
        self.assertEqual(b''.join(self.native.usb_completed),b''.join(self.replies)); self.cc.check()

    def test_native_ep0_deconfigure_reconfigure_cancels_old_tx(self):
        self.setup_control(); self.send(self.inquiries); self.q.poll(); self.q.poll()
        self.assertIsNotNone(self.native.in_flight)
        self.assertEqual(self.cc.configure(0),0)
        self.assertEqual(self.cc.status()['deinit'],1)
        self.cc.pump(); self.assertEqual(self.ss.status()['phase'],session.SEALED)
        self.assertEqual(self.native.usb_completed,[])
        self.assertEqual(self.cc.configure(1),0); self.cc.pump()
        self.assertEqual(self.ss.status()['phase'],session.OPEN)
        self.assertEqual(self.ss.status()['cancel_tx'],1)
        self.send(self.inquiries); self.finish_reply()
        self.assertEqual(b''.join(self.native.usb_completed),b''.join(self.replies)); self.cc.check()

    def test_reset_enumeration_native_ep0_setup_sequence_preserves_configured_resume(self):
        self.setup_control(); self.ss.arm_rx(); self.cc.reset(); self.cc.pump()
        self.assertEqual(self.cc.enumerate(),0)
        self.assertEqual(self.u.mem_read(self.ib.ctrl+0x274,1),b'\x01')
        self.assertEqual(self.cc.address(),0)
        self.assertEqual(self.u.mem_read(self.ib.ctrl+0x274,1),b'\x02')
        self.cc.configure(1); self.cc.pump()
        self.assertEqual(self.ss.status()['phase'],session.OPEN)
        self.assertEqual(self.cc.status()['restarts'],1); self.cc.check()

    def test_coalesced_reset_and_completion_never_admits_old_reply(self):
        self.setup_control(); self.ss.arm_rx(); self.send(self.inquiries); self.q.poll(); self.q.poll()
        self.ib.rx_data(self.inquiries); self.ib.rx_complete(); self.ib.tx_complete()
        self.assertEqual(self.cc.reset(),0)
        self.assertEqual(self.ib.status()['tx_done'],0); self.assertEqual(self.ib.status()['rx_done'],0)
        while self.ib.events: self.ib.run()
        self.cc.pump(); self.assertEqual(self.native.usb_completed,[])
        self.assertEqual(self.rx.status()['queued'],0); self.cc.check()

    def test_constructor_never_runs_before_ack_flush_and_software_quiescence(self):
        self.setup_control(); self.ss.arm_rx()
        self.lc.configured(2); self.cc.configure(1)
        self.assertEqual(self.cc.service(),1)
        self.assertEqual(self.cc.constructors,[])
        self.assertEqual(self.cc.service(),1); self.assertEqual(self.cc.constructors,[])
        for ctl in tuple(self.ss.disable_requested): self.ss.ack_disable(ctl)
        self.cc.service(); self.assertEqual(self.cc.constructors,[])
        self.cc.service(); self.assertEqual(self.cc.constructors,[])
        self.ss.finish_flush(); self.assertEqual(self.cc.service(),0)
        self.assertEqual(len(self.cc.constructors),1); self.cc.check()

    def test_deferred_constructor_does_not_globally_flush_rx(self):
        self.setup_control(); self.cc.configure(0); self.cc.pump()
        self.ss.flushes.clear()
        self.cc.configure(1); self.cc.pump()
        self.assertEqual(self.ss.flushes,[1])  # native IN flush only; no global RX
        self.cc.check()

    def test_pending_constructor_is_idempotent_and_invalid_configuration_rejected(self):
        self.setup_control(); self.lc.configured(2); self.cc.configure(1)
        requests=self.cc.status()['requests']
        self.assertEqual(self.call(0x080525B2,self.ib.wrapper,self.ib.ctrl,1),0)
        self.assertEqual(self.cc.status()['requests'],requests)
        self.assertEqual(self.call(0x080525B2,self.ib.wrapper,self.ib.ctrl,2),1)
        self.cc.pump(); self.assertEqual(len(self.cc.constructors),1); self.cc.check()

    def test_reset_invalidates_queued_configuration_until_new_host_request(self):
        self.setup_control(); self.lc.configured(2); self.cc.configure(1)
        self.assertTrue(self.cc.status()['flags']&control.PENDING)
        self.cc.reset(); self.assertFalse(self.cc.status()['flags']&control.PENDING)
        self.cc.pump(); self.assertEqual(self.cc.constructors,[])
        self.assertEqual(self.ss.status()['phase'],session.SEALED)
        self.lc.configured(2); self.cc.configure(1); self.cc.pump()
        self.assertEqual(len(self.cc.constructors),1); self.cc.check()

    def test_shared_payload_or_rx_debt_freezes_without_silent_clear(self):
        self.setup_control(); self.send(self.inquiries)
        payload=bytes(self.u.mem_read(0x20047800,428)); self.cc.reset()
        for _ in range(3): self.assertEqual(self.cc.service(),1)
        self.assertEqual(self.u.mem_read(0x20047800,428),payload)
        self.assertEqual(self.cc.constructors,[])
        self.assertEqual(self.ss.status()['phase'],session.CLOSING)
        self.setUp(); self.setup_control(); self.fill_pending(); before=self.rx.status()
        self.cc.reset(); self.assertEqual(self.cc.service(),1)
        self.assertEqual(self.rx.status(),before); self.cc.check()

    def test_held_note_ownership_prevents_cleanup(self):
        self.setup_control(); self.attach_native_note_receiver()
        self.send(bytes([9,0x97,60,96])); self.cc.reset()
        self.assertEqual(self.cc.service(),1)
        self.assertEqual(self.call(self.labels['c_midi_inputs_idle']),0)
        self.assertEqual(self.cc.constructors,[]); self.cc.check()

    def test_bootstrap_release_is_distinct_from_runtime_completion(self):
        self.setup_control(); self.send(self.inquiries); self.q.poll(); self.q.poll()
        before=self.ss.status(); self.call(0x080268D0,self.native.usb_endpoint)
        self.assertEqual(self.ss.status(),before)
        self.cc.configure(0); self.cc.pump(); self.cc.configure(1); self.cc.pump()
        self.assertEqual(self.cc.bootstrap,[session.SEALED])
        self.assertEqual(self.ib.status()['tx_done'],0)
        self.assertEqual(self.u.mem_read(self.native.usb_endpoint+28,1),b'\x01'); self.cc.check()

    def test_new_reset_during_init_is_retained(self):
        self.setup_control(); self.lc.configured(2); self.cc.configure(1)
        injected,results=self.install_nested_calls(0x080525B6,[
            (self.cc.labels['cc_request'],(control.RESET_EVENT,))])
        self.ss.record_nested_trampoline()
        for _ in range(3):
            self.cc.service()
            if self.ss.status()['phase']==session.WAIT_DISABLE:
                for ctl in tuple(self.ss.disable_requested): self.ss.ack_disable(ctl)
            if self.ss.status()['phase']==session.WAIT_FLUSH: self.ss.finish_flush()
        self.assertEqual(len(injected),1); self.assertEqual(results(),[0])
        self.assertEqual(self.ss.status()['phase'],session.CLOSING)
        self.assertFalse(self.cc.status()['flags']&control.PENDING)
        self.cc.pump(); self.assertEqual(self.ss.status()['phase'],session.SEALED); self.cc.check()

    def test_sof_cannot_bypass_completion_owned_mtu_packet(self):
        self.setup_control(); self.ss.arm_rx(); self.assertEqual(self.ss.rx_jobs[-1].size,64)
        self.ib.rx_data(self.inquiries); self.ib.run()
        self.ib.external|=1<<3; self.assertEqual(self.ib.run(),0)
        self.assertEqual(self.rx.status()['queued'],0)
        self.ib.rx_complete(); self.ib.run()
        self.rx.poll(); self.finish_reply()
        self.assertEqual(b''.join(self.native.usb_completed),b''.join(self.replies)); self.cc.check()

    def test_default_irq_codegen_is_unchanged(self):
        self.assertEqual(hashlib.sha256(irq.arm_code()[0]).hexdigest(),
                         'ef45bacef7a218db2a8f2e4798a9bf60e899dbf1b7ffad044df037c3ff5b55d4')

    def test_control_service_rejects_irq_masked_and_recursive_contexts(self):
        self.setup_control(); self.cc.reset()
        for register in (base.UC_ARM_REG_IPSR,base.UC_ARM_REG_PRIMASK):
            self.u.reg_write(register,1); self.assertEqual(self.cc.service(),1)
            self.u.reg_write(register,0)
        self.word(control.STATE_BASE+control.BUSY,1); self.assertEqual(self.cc.service(),1)
        self.word(control.STATE_BASE+control.BUSY,0); self.cc.pump(); self.cc.check()

    def test_reset_arriving_before_final_commit_is_not_lost(self):
        self.setup_control(); self.cc.reset()
        injected,results=self.install_nested_calls(self.cc.labels['service_closed'],[
            (self.cc.labels['cc_request'],(control.RESET_EVENT,))])
        self.ss.record_nested_trampoline()
        self.cc.service()
        for ctl in tuple(self.ss.disable_requested): self.ss.ack_disable(ctl)
        self.cc.service(); self.ss.finish_flush(); self.assertEqual(self.cc.service(),1)
        self.assertEqual(results(),[0]); self.assertEqual(len(injected),1)
        self.assertEqual(self.ss.status()['phase'],session.CLOSING)
        self.assertTrue(self.cc.status()['flags'])
        self.cc.pump(); self.assertEqual(self.ss.status()['phase'],session.SEALED); self.cc.check()

    def test_packet_capacity_pause_does_not_create_a_phantom_rx_job(self):
        self.setup_control(); self.ss.arm_rx(); packets=bytes([15,0xF8,0,0])*16
        for _ in range(2):
            self.ib.rx_data(packets); self.ib.rx_complete(); self.ib.run()
        self.assertEqual(self.rx.status()['queued'],132)
        self.assertEqual(self.cc.status()['rx_paused'],1)
        self.assertEqual(self.ss.status()['rx_active'],0)
        jobs=len(self.ss.rx_jobs); self.assertEqual(self.cc.service(),1)
        self.assertEqual(len(self.ss.rx_jobs),jobs)
        self.rx.poll(); self.assertEqual(self.cc.service(),0)
        self.assertEqual(self.cc.status()['rx_paused'],0)
        self.assertEqual(self.ss.status()['rx_active'],1)
        self.assertEqual(self.ss.rx_jobs[-1].size,64); self.cc.check()

    def test_event_generation_wrap_fails_closed_without_reusing_payload(self):
        self.setup_control(); self.ss.arm_rx(); self.word(control.STATE_BASE+control.REQUESTS,0xFFFFFFFF)
        self.assertEqual(self.cc.reset(),1)
        self.assertEqual(self.ss.status()['phase'],session.BROKEN)
        self.assertEqual(self.ss.status()['rx_active'],1)
        self.assertEqual(self.cc.constructors,[]); self.cc.check()

    def test_direct_native_disconnect_can_reconfigure_after_main_barrier(self):
        self.setup_control(); self.ss.arm_rx()
        self.call(0x0805261C,self.ib.wrapper,self.ib.ctrl,0)
        self.cc.pump(); self.assertEqual(self.ss.status()['phase'],session.SEALED)
        self.assertEqual(self.call(0x080525B2,self.ib.wrapper,self.ib.ctrl,1),0)
        self.cc.pump(); self.assertEqual(self.ss.status()['phase'],session.OPEN)
        self.assertEqual(self.cc.status()['deinit'],1); self.cc.check()

    def test_old_hardware_xfrc_after_broken_barrier_remains_a_negative(self):
        self.setup_control(); self.ss.arm_rx(); self.cc.configure(0); self.cc.pump()
        self.cc.configure(1); self.cc.pump(); token=self.ss.status()['rx_ticket']
        self.ib.rx_complete(); self.ib.run()
        self.assertGreater(self.ss.status()['rx_ticket'],token)
        self.assertEqual(self.ib.status()['rx_done'],1)  # status still has no hardware generation
        self.cc.check()

    def test_suspend_and_dma_remain_explicit_unsupported_paths(self):
        self.setup_control(); self.ss.arm_rx(); self.ib.external=1<<11
        self.ss.poke(0x18,control.CONTROL_GINT|(1<<11))
        self.assertEqual(self.ib.run(),1); self.assertEqual(self.ss.status()['phase'],session.BROKEN)
        self.setUp(); self.setup_control(); self.word(self.ib.handle+16,1)
        self.assertEqual(self.ib.run(),1); self.assertEqual(self.ss.status()['phase'],session.BROKEN)

    def test_resume_wait_does_not_repeat_native_constructor_callbacks(self):
        self.setup_control(); self.lc.configured(2); self.cc.configure(1)
        inserted=[]
        def pending(u,pc,size,data):
            if not inserted:
                inserted.append(pc); self.ib.flags[session.IN_INT]=1
        self.u.hook_add(base.UC_HOOK_CODE,pending,begin=self.cc.labels['service_resume'],end=self.cc.labels['service_resume'])
        self.cc.service(); self.cc.service(); self.ss.finish_flush()
        self.assertEqual(self.cc.service(),1)
        self.assertEqual(self.cc.status()['init_done'],1)
        self.assertEqual(self.cc.service(),1); self.assertEqual(len(self.cc.constructors),1)
        self.ib.flags[session.IN_INT]=0
        self.assertEqual(self.cc.service(),0); self.assertEqual(len(self.cc.constructors),1)
        self.assertEqual(self.ss.status()['phase'],session.OPEN); self.cc.check()


if __name__=='__main__': unittest.main()
