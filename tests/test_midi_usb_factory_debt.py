"""Native USB factory with retained MIDI MAIN/slot/ledger ownership."""
import unittest
import hashlib
import test_midi_usb_staging as prior
import midi_usb_session_prototype as session
import midi_usb_msc_prototype as msc
import midi_usb_carry_prototype as carry
import midi_usb_ledger_prototype as ledger
import midi_usb_power_prototype as power
from midi_usb_factory_debt_test_support import inject_second
base=prior.base


class UsbFactoryDebtTests(unittest.TestCase):
    setUpClass=classmethod(prior.UsbStagingTests.setUpClass.__func__)
    for name in ('setUp','word','read','store','call','setup_playback','setup_recovery','setup_sysex_router',
                 'sysex_descriptor','install_nested_calls','setup_notice','setup_request','seed_notes','stall','release',
                 'capture_shorts','attach_native_note_receiver','setup_ledger','setup_life','setup_session','setup_control',
                 'setup_composite','setup_msc','setup_storage','setup_factory','setup_power','setup_task','send',
                 'fill_pending','finish_reply','debt','expected','setup_staging','snapshot','start_payload'):
        locals()[name]=getattr(prior.UsbStagingTests,name)
    sysex_packets=staticmethod(prior.UsbStagingTests.sysex_packets)
    bytes_as_packets=staticmethod(prior.UsbStagingTests.bytes_as_packets)
    def configure_host(self):
        self.cc.reset();self.ut.frames(12)
        self.cc.enumerate();self.cc.address();self.cc.configure(1);self.ut.frames(12)
        self.assertEqual(self.ss.status()['phase'],session.OPEN)
    def queue_before_submit(self,argument,entry=0x080432A8,args=None):
        captured=[];pc=0x0802B498
        def snapshot(u,p,n,d):
            if not captured:captured.append(self.snapshot())
        self.u.hook_add(base.UC_HOOK_CODE,snapshot,begin=pc,end=pc)
        injected,results=self.install_nested_calls(pc,[(entry,(argument,) if args is None else args)])
        self.ss.record_nested_trampoline();self.ut.frame()
        self.assertEqual(results(),[0]);self.assertEqual(len(injected),1)
        self.assertEqual(self.native.usb_submissions,[])
        return captured[0]
    def change_before_submit(self,argument,entry=0x080432A8,args=None):
        state=self.queue_before_submit(argument,entry,args)
        self.ut.frames(16);self.assertEqual(self.fx.status()['applied'],argument)
        self.assertEqual(self.ss.status()['phase'],session.SEALED)
        self.assertEqual(self.snapshot(),state);return state
    def check_output(self,payload,queries=0):
        self.ut.frames(80)
        self.assertEqual(b''.join(self.native.usb_completed),b''.join(self.sysex_packets(payload)+self.replies*queries))
        self.assertEqual([bytes(b) for b in self.cy.din_bytes],[payload,payload])
        self.assertEqual(self.q.status()['active'],0);self.assertEqual(self.rx.status()['pending'],0)
        self.assertEqual(self.cy.status()['active'],0);self.cy.check()
        if hasattr(type(self),'evidence'):
            type(self).evidence.append(dict(test=self._testMethodName,mode=self.u.mem_read(base.seq.SEQ_STATE_ADDR+4,1)[0],
                applied=self.fx.status()['applied'],switches=self.fx.status()['switches'],descriptor_bytes=len(self.fx.descriptor()),
                payload_bytes=len(payload),query_replies=queries,usb_bytes=sum(map(len,self.native.usb_completed)),
                usb_sha256=hashlib.sha256(b''.join(self.native.usb_completed)).hexdigest(),
                din_bytes=[len(b) for b in self.cy.din_bytes],exact_usb_and_din=True,
                native_factory_calls=sum(n=='native_factory' for n,_ in self.fx.events),
                pending_queries=self.rx.status()['pending'],slot_active=self.q.status()['active']))

    def test_staged_partial_sysex_survives_composite_to_midi_only_factory(self):
        for mode in (0,1):
            self.setUp();self.setup_staging();self.u.mem_write(base.seq.SEQ_STATE_ADDR+4,bytes([mode]))
            payload=b'\xF0'+bytes(n%128 for n in range(358))+b'\xF7'
            self.start_payload(payload);before=self.u.mem_read(0x20010000,0x29484)
            state=self.change_before_submit(1);self.assertEqual(state['length'],64);self.assertEqual(state['cursor'],48)
            self.assertEqual(len(self.fx.descriptor()),94);self.assertEqual(self.fx.descriptor()[4],2)
            self.configure_host();self.check_output(payload)
            self.assertEqual(self.mc.status()['phase'],msc.SEALED);self.assertEqual(self.mc.status()['rx_active'],0)
            self.assertEqual(self.u.mem_read(0x20010000,0x29484),before)

    def test_staged_partial_sysex_survives_midi_only_to_composite_then_read(self):
        self.setup_staging();self.fx.request(1);self.ut.frames(16);self.configure_host()
        payload=b'\xF0'+bytes(range(58))+b'\xF7';self.start_payload(payload)
        self.change_before_submit(0x101)
        self.assertEqual(len(self.fx.descriptor()),125);self.assertEqual(self.fx.descriptor()[4],3)
        self.configure_host();self.check_output(payload)
        self.assertEqual(self.mc.status()['phase'],msc.OPEN);self.assertEqual(self.mc.status()['rx_active'],1)
        self.ut.queue_read();self.ut.frames(80)
        self.assertEqual(self.sd.sent[0],self.sd.media);self.assertEqual(self.sd.sent[1][:4],b'USBS');self.cy.check()

    def test_staged_payload_and_accepted_query_debt_survive_factory(self):
        self.setup_staging();payload=b'\xF0'+bytes(range(58))+b'\xF7';self.start_payload(payload)
        self.send(self.inquiries*ledger.MAX_PENDING);messages=self.capture_shorts()
        self.send(self.inquiries+bytes([15,0xF8,0,0,15,0xFC,0,0]))
        self.assertEqual(messages,[b'\xF8',b'\xFC']);self.change_before_submit(1)
        self.assertEqual(self.rx.status()['pending'],ledger.MAX_PENDING)
        self.configure_host();self.check_output(payload,ledger.MAX_PENDING+1)
        self.assertEqual(messages,[b'\xF8',b'\xFC'])

    def test_missing_ack_keeps_old_class_list_and_retained_main_owned(self):
        self.setup_staging();payload=b'\xF0'+bytes(range(58))+b'\xF7';self.start_payload(payload)
        before=self.u.mem_read(self.ib.root,32);self.ut.hw_ack=False
        state=self.queue_before_submit(1);self.ut.frames(16)
        self.assertEqual(self.snapshot(),state);self.assertEqual(self.u.mem_read(self.ib.root,32),before)
        self.assertEqual(self.fx.status()['switches'],0)
        self.assertFalse(any(n=='list_clear' for n,_ in self.fx.events))
        self.ut.hw_ack=True;self.ut.frames(16);self.assertEqual(self.fx.status()['applied'],1)
        self.configure_host();self.check_output(payload)

    def test_active_msc_read_is_cancelled_before_factory_with_staged_midi(self):
        self.setup_staging();self.ut.hw_tx=False;self.ut.queue_read()
        payload=b'\xF0'+bytes(range(58))+b'\xF7';self.start_payload(payload)
        self.assertEqual(self.sd.status()['tx_active'],1);self.change_before_submit(1)
        self.assertEqual(self.sd.status()['cancel_tx'],1);self.assertEqual(self.sd.sent,[])
        self.ut.hw_tx=True;self.configure_host();self.check_output(payload)

    def test_accepted_midi_tx_is_not_reclassified_as_unsent_for_factory_negative(self):
        self.setup_staging();self.ut.hw_tx=False
        payload=b'\xF0'+bytes(range(58))+b'\xF7';self.start_payload(payload);self.ut.frame()
        self.assertEqual(self.ss.status()['tx_active'],1);before=self.u.mem_read(self.ib.root,32)
        self.fx.request(1);self.ut.frames(32)
        self.assertEqual(self.fx.status()['switches'],0);self.assertEqual(self.u.mem_read(self.ib.root,32),before)
        self.assertEqual(self.native.usb_completed,[]);self.assertEqual(self.cy.status()['seals'],0);self.cy.check()

    def test_without_staging_variant_factory_still_blocks_after_native_data_loss_negative(self):
        self.setup_staging(enabled=False);payload=b'\xF0'+bytes(range(58))+b'\xF7';self.start_payload(payload)
        before=self.u.mem_read(self.ib.root,32);state=self.queue_before_submit(1);self.ut.frames(16)
        self.assertEqual(state['length'],64);self.assertEqual(self.snapshot()['length'],0)
        self.assertEqual(self.snapshot()['cursor'],48);self.assertEqual(self.fx.status()['pending'],1)
        self.assertEqual(self.fx.status()['switches'],0);self.assertEqual(self.u.mem_read(self.ib.root,32),before)
        self.cy.check()

    def test_new_factory_request_during_rebuild_retains_same_staged_payload(self):
        self.setup_staging();payload=b'\xF0'+bytes(range(58))+b'\xF7';self.start_payload(payload)
        self.ut.hw_ack=False;state=self.queue_before_submit(1);self.ut.frames(8)
        injected,results=inject_second(self,0x08040A40,[(0x080432A8,(0x201,))])
        self.ut.hw_ack=True;self.ut.frames(24)
        self.assertEqual(len(injected),1);self.assertEqual(results(),[0])
        self.assertEqual(self.fx.status()['applied'],0x201);self.assertEqual(self.fx.status()['switches'],2)
        self.assertEqual(self.snapshot(),state);self.configure_host();self.check_output(payload)

    def test_native_reset_irq_during_factory_cannot_resume_an_old_generation(self):
        self.setup_staging();payload=b'\xF0'+bytes(range(58))+b'\xF7';self.start_payload(payload)
        self.ut.hw_ack=False;state=self.queue_before_submit(1);self.ut.frames(8)
        once=[];pc=0x080427FC
        def signal(u,p,n,d):
            if not once:once.append(p);self.ib.external|=power.RESET
        self.u.hook_add(base.UC_HOOK_CODE,signal,begin=pc,end=pc)
        injected,results=inject_second(self,pc,[(0x0804293E,(self.ib.handle,))])
        self.ut.hw_ack=True;self.ut.frames(24)
        self.assertEqual(len(injected),1);self.assertEqual(results(),[0])
        self.assertEqual(self.ss.status()['phase'],session.SEALED);self.assertEqual(self.snapshot(),state)
        self.assertEqual(self.native.usb_submissions,[])
        self.configure_host();self.check_output(payload)

    def test_three_storage_mode_rebuilds_before_enumeration_do_not_rewind_cursor(self):
        self.setup_staging();payload=b'\xF0'+bytes(range(58))+b'\xF7';self.start_payload(payload)
        state=self.change_before_submit(1)
        for argument,mode in ((0x101,1),(0x201,3),(0x301,2)):
            self.fx.request(argument);self.ut.frames(16)
            self.assertEqual(self.fx.status()['applied'],argument);self.assertEqual(self.call(0x08043286),mode)
            self.assertEqual(self.snapshot(),state);self.assertEqual(self.native.usb_submissions,[])
        self.configure_host();self.check_output(payload)

    def test_native_settings_callback_selects_both_factory_modes_with_retained_main(self):
        for flag,argument in ((0,1),(1,0x101)):
            self.setUp();self.setup_staging();payload=b'\xF0'+bytes(range(58))+b'\xF7';self.start_payload(payload)
            # Synthetic view/store matching35814 ->3FC58(slot2). The actual
            # settings callback and bit17 branch run; full Packs UI is not run.
            view,store,data=0x20003200,0x20003220,0x20003260
            self.assertFalse(any(self.u.mem_read(view,0x80)))
            self.word(view+4,store);self.word(store+12,data);self.word(data+8,flag<<17)
            self.change_before_submit(argument,entry=0x08035814,args=(view,))
            self.configure_host();self.check_output(payload)

    def test_native_boot_wrapper_rebuilds_current_storage_mode_with_retained_main(self):
        self.setup_staging();payload=b'\xF0'+bytes(range(58))+b'\xF7';self.start_payload(payload)
        self.call(0x08043264,3)
        self.change_before_submit(0x301,entry=0x0802CB18,args=())
        self.configure_host();self.check_output(payload)

    def test_staged_note_off_survives_factory_with_no_borrowed_sysex_owner(self):
        self.setup_staging();self.assertEqual(self.recovery.send(0,0x80,60,0),1)
        state=self.change_before_submit(1);self.assertEqual(state['length'],4)
        self.configure_host();self.ut.frames(24)
        self.assertEqual(b''.join(self.native.usb_completed),bytes([8,0x80,60,0]));self.cy.check()


if __name__=='__main__':unittest.main()
