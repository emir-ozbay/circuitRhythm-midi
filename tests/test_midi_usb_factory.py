"""Native factory+class lists over synthetic hardware initialization boundary."""
import unittest
import test_midi_usb_storage as prior
import midi_usb_factory_prototype as factory
import midi_usb_msc_prototype as msc
from midi_usb_factory_test_support import UsbFactoryFixture

base=prior.base


class UsbFactoryTests(unittest.TestCase):
    setUpClass=classmethod(prior.UsbStorageTests.setUpClass.__func__)
    for name in ('setUp','word','read','store','call','setup_playback','setup_recovery','setup_sysex_router',
                 'sysex_descriptor','install_nested_calls','setup_notice','setup_request','seed_notes','stall','release',
                 'capture_shorts','attach_native_note_receiver','setup_ledger','setup_life','setup_session','setup_control',
                 'setup_composite','setup_msc','setup_storage','send','fill_pending','finish_reply'):
        locals()[name]=getattr(prior.UsbStorageTests,name)
    sysex_packets=staticmethod(prior.UsbStorageTests.sysex_packets)
    bytes_as_packets=staticmethod(prior.UsbStorageTests.bytes_as_packets)

    def setup_factory(self):self.setup_storage();self.fx=UsbFactoryFixture(self)

    def test_switch_to_midi_only_waits_for_barrier_then_runs_native_factory(self):
        self.setup_factory();self.assertEqual(self.fx.request(1),0)
        self.assertEqual(self.u.mem_read(self.ib.root,1),b'\x02')
        self.assertFalse(any(n=='list_clear' for n,_ in self.fx.events))
        self.fx.pump();self.assertEqual(self.fx.status()['applied'],1)
        self.assertEqual(self.u.mem_read(self.ib.root,1),b'\x01')
        self.assertEqual(self.read(self.ib.root+12),0)
        self.assertEqual(self.u.mem_read(self.ib.ctrl+0x274,1),b'\x01')
        self.assertTrue(any(n=='stop' for n,_ in self.fx.events));self.fx.check()

    def test_midi_only_can_enumerate_and_answer_query_without_arming_msc(self):
        self.setup_factory();self.fx.request(1);self.fx.pump();self.fx.enumerate()
        self.assertEqual(self.mc.status()['phase'],msc.SEALED)
        self.assertEqual(self.mc.status()['rx_active'],0)
        data=self.fx.descriptor();self.assertEqual(len(data),94);self.assertEqual(data[4],2)
        self.ib.rx_data(self.inquiries);self.ib.rx_complete();self.ib.run();self.rx.poll();self.finish_reply()
        self.assertEqual(b''.join(self.native.usb_completed),b''.join(self.replies));self.fx.check()

    def test_midi_only_to_composite_can_enumerate_and_read_storage(self):
        self.setup_factory();self.fx.request(1);self.fx.pump();self.fx.enumerate()
        self.fx.request(0x101);self.fx.pump();self.fx.enumerate()
        data=self.fx.descriptor();self.assertEqual(len(data),125);self.assertEqual(data[4],3)
        self.assertEqual(self.mc.status()['rx_active'],1)
        self.sd.command();self.sd.complete_tx();self.assertEqual(self.sd.sent,[self.sd.media]);self.fx.check()

    def test_read_transfer_is_cancelled_before_class_list_changes(self):
        self.setup_factory();self.sd.command();before=self.u.mem_read(self.ib.root,32)
        self.fx.request(1);self.mc.service()
        self.assertEqual(self.u.mem_read(self.ib.root,32),before)
        self.assertEqual(self.sd.status()['tx_active'],1)
        self.assertFalse(any(n=='list_clear' for n,_ in self.fx.events))
        self.fx.pump();self.assertEqual(self.sd.status()['cancel_tx'],1)
        self.assertEqual(self.fx.status()['applied'],1);self.assertEqual(self.sd.sent,[]);self.fx.check()

    def test_upper_stack_halfword_is_ignored_like_native_factory(self):
        self.setup_factory();self.fx.request(0xABCD0001);self.fx.pump()
        self.assertEqual(self.fx.status()['applied'],1);self.fx.check()

    def test_unsupported_msc_only_request_is_rejected_without_mutation(self):
        self.setup_factory();before=self.u.mem_read(self.ib.root,32)
        self.assertEqual(self.fx.request(0x100),1)
        self.assertEqual(self.u.mem_read(self.ib.root,32),before)
        self.assertEqual(self.fx.status()['pending'],0);self.fx.check()

    def test_unprotected_native_factory_clears_list_before_reader_retirement_negative(self):
        self.setup_factory();self.sd.command()
        self.call(self.fx.labels['fx_native_factory'],1)
        self.assertEqual(self.u.mem_read(self.ib.root,1),b'\x01')
        self.assertEqual(self.sd.status()['tx_active'],1)
        self.assertNotEqual(self.mc.status()['phase'],msc.SEALED)
        self.assertFalse(any(n=='msc_deinit' for n,_ in self.xc.events));self.fx.check()

    def test_latest_queued_mode_wins_without_partial_list_mutation(self):
        self.setup_factory();before=self.u.mem_read(self.ib.root,32)
        self.fx.request(1);self.fx.request(0x301)
        self.assertEqual(self.u.mem_read(self.ib.root,32),before)
        self.fx.pump();self.assertEqual(self.fx.status()['applied'],0x301)
        self.assertEqual(self.fx.status()['switches'],1)
        self.assertEqual(self.call(0x08043286),2);self.fx.check()

    def test_new_factory_request_during_native_rebuild_is_not_lost(self):
        self.setup_factory();self.fx.request(1)
        injected,results=self.install_nested_calls(0x08040A40,[(0x080432A8,(0x201,))])
        self.ss.record_nested_trampoline();self.fx.pump()
        self.assertEqual(len(injected),1);self.assertEqual(results(),[0])
        self.assertEqual(self.fx.status()['applied'],0x201)
        self.assertEqual(self.fx.status()['switches'],2);self.fx.check()

    def test_native_wrapper_2cb18_queues_the_factory_request(self):
        self.setup_factory();self.call(0x08043264,1)
        self.assertEqual(self.call(0x0802CB18),0)
        self.assertEqual(self.fx.status()['desired'],0x101);self.fx.pump();self.fx.check()

    def test_all_stock_storage_modes_can_rebuild_a_composite_descriptor(self):
        self.setup_factory()
        for argument,mode in ((0x101,1),(0x201,3),(0x301,2)):
            self.fx.request(argument);self.fx.pump();self.fx.enumerate()
            self.assertEqual(self.call(0x08043286),mode)
            self.assertEqual(self.fx.descriptor()[4],3)
            self.assertEqual(self.mc.status()['rx_active'],1)
        self.fx.check()

    def test_din_off_and_project_ram_survive_both_class_list_transitions(self):
        self.setup_factory();before=self.u.mem_read(0x20010000,0x29484)
        self.output.note(0,60,0,on=False);self.output.drain(0)
        self.fx.request(1);self.fx.pump();self.fx.enumerate()
        self.fx.request(0x101);self.fx.pump();self.fx.enumerate()
        self.assertEqual([self.output.pop(p) for p in (1,2)],[bytes([0x80,60,0])]*2)
        self.assertEqual(self.u.mem_read(0x20010000,0x29484),before);self.fx.check()

    def test_accepted_midi_debt_keeps_old_factory_list_owned(self):
        self.setup_factory();self.fill_pending();before=self.u.mem_read(self.ib.root,32)
        self.fx.request(1)
        for _ in range(8):
            self.mc.service()
            if self.mc.status()['phase']==msc.WAIT_DISABLE:self.mc.ack()
            if self.mc.status()['phase']==msc.WAIT_FLUSH:self.mc.finish_flush()
        self.assertEqual(self.u.mem_read(self.ib.root,32),before)
        self.assertEqual(self.fx.status()['pending'],1)
        self.assertFalse(any(n=='list_clear' for n,_ in self.fx.events));self.fx.check()

    def test_factory_main_service_rejects_irq_context(self):
        from unicorn.arm_const import UC_ARM_REG_IPSR
        self.setup_factory();self.fx.request(1);before=self.fx.status()
        self.u.reg_write(UC_ARM_REG_IPSR,16)
        try:self.assertEqual(self.mc.service(),1)
        finally:self.u.reg_write(UC_ARM_REG_IPSR,0)
        self.assertEqual(self.fx.status(),before);self.fx.pump();self.fx.check()

    def test_external_usb_reset_during_factory_is_processed_after_rebuild(self):
        import midi_usb_control_prototype as control
        self.setup_factory();self.fx.request(1);before=self.cc.status()['requests']
        injected,results=self.install_nested_calls(0x080427FC,[(self.cc.labels['cc_request'],(control.RESET_EVENT,))])
        self.ss.record_nested_trampoline();self.fx.pump()
        self.assertEqual(len(injected),1);self.assertEqual(results(),[0])
        self.assertEqual(self.cc.status()['requests'],before+1)
        self.assertEqual(self.cc.status()['flags'],0)
        self.assertEqual(self.fx.status()['applied'],1);self.fx.check()

    def test_wrong_native_handle_binding_cannot_start_factory(self):
        self.setup_factory();before=self.u.mem_read(self.ib.root,32)
        self.word(self.ib.ctrl+0x298,0x20008400)
        self.assertEqual(self.fx.request(1),1)
        self.assertEqual(self.u.mem_read(self.ib.root,32),before)
        self.word(self.ib.ctrl+0x298,self.ib.handle);self.fx.check()


if __name__=='__main__':unittest.main()
