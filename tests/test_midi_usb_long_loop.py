"""Full native pack-loader loop; modeled sample file/flash/UI boundaries."""
import unittest
import test_midi_usb_poll_callers as prior
import midi_usb_session_prototype as session
import midi_usb_power_prototype as power
import midi_usb_storage_prototype as storage
from midi_usb_long_loop_test_support import UsbLongLoopFixture,wav,swapped
base=prior.base


class UsbLongLoopTests(unittest.TestCase):
    setUpClass=classmethod(prior.UsbPollCallerTests.setUpClass.__func__)
    for name in ('setUp','word','read','store','call','setup_playback','setup_recovery','setup_sysex_router',
                 'sysex_descriptor','install_nested_calls','setup_notice','setup_request','seed_notes','stall','release',
                 'capture_shorts','attach_native_note_receiver','setup_ledger','setup_life','setup_session','setup_control',
                 'setup_composite','setup_msc','setup_storage','setup_factory','setup_power','setup_task','send',
                 'fill_pending','finish_reply','debt','expected','setup_staging','snapshot','start_payload','configure_host'):
        locals()[name]=getattr(prior.UsbPollCallerTests,name)
    sysex_packets=staticmethod(prior.UsbPollCallerTests.sysex_packets)
    bytes_as_packets=staticmethod(prior.UsbPollCallerTests.bytes_as_packets)
    def setup_loop(self,files=None):self.setup_staging();self.ll=UsbLongLoopFixture(self,files)
    def tearDown(self):
        if hasattr(self,'ll'):self.ll.record(self._testMethodName)
    def assert_loop(self):
        self.assertEqual(self.ll.polls,128);self.assertEqual(len(self.ll.watchdogs),128)
        self.assertEqual(set(self.ll.watchdogs),{0xAAAA});self.assertEqual(self.ll.completed,1)
        self.assertEqual(self.ll.slots,list(range(128)))
        self.assertEqual([r[0] for r in self.ll.reads if r[1]==0],list(range(128)))
        self.assertEqual([r[1:] for r in self.ll.progress if r[0]==16],[(0,128)]+[(n,128) for n in range(128)])
        self.assertEqual(len(self.ll.metadata),512);self.ll.check()

    def test_native_full_128_missing_sample_loop_both_modes_and_selected_pack(self):
        for mode in (0,1):
            self.setUp();self.setup_loop();self.u.mem_write(base.seq.SEQ_STATE_ADDR+4,bytes([mode]))
            self.assertEqual(self.ll.run(pack=0xFE),1);self.assert_loop()
            self.assertEqual(set(self.ll.metadata.values()),{0});self.assertEqual(self.ll.writes,[])
            self.assertEqual(self.ut.status()['frames'],0)
            if mode==0:self.ll.record(self._testMethodName+'-normal')

    def test_native_valid_sample_double_buffer_partial_tail_and_project_ram(self):
        first=bytes(n%256 for n in range(512));last=bytes((n*3)%256 for n in range(4608))
        self.setup_loop({0:wav(first),127:wav(last)});before=bytes(self.u.mem_read(0x20010000,0x29484))
        self.assertEqual(self.ll.run(),1);self.assert_loop()
        self.assertEqual(b''.join(b for _,b in self.ll.writes),swapped(first+last))
        self.assertEqual([len(b) for _,b in self.ll.writes],[512,2048,2048,512])
        self.assertEqual([p for _,o,p,n in self.ll.reads if o],[0x20004794,0x20004794,0x20003F94,0x20004794])
        self.assertEqual(self.ll.allocations,[0,127]);self.assertEqual(self.u.mem_read(0x20010000,0x29484),before)

    def test_native_loop_polls_read_data_and_csw_without_main_both_modes(self):
        for mode in (0,1):
            self.setUp();self.setup_loop({64:wav(bytes(range(256))*2)})
            self.u.mem_write(base.seq.SEQ_STATE_ADDR+4,bytes([mode]));self.ut.queue_read()
            self.assertEqual(self.ll.run(after_slot=lambda n:self.ut.bus()),1);self.assert_loop()
            self.assertEqual([len(b) for b in self.sd.sent],[4096,13]);self.assertEqual(self.sd.sent[0],self.sd.media)
            self.assertEqual(self.sd.sent[1][:4],b'USBS');self.assertEqual(self.sd.status()['reads'],1)
            self.assertEqual(self.ut.status()['frames'],0)
            if mode==0:self.ll.record(self._testMethodName+'-normal')

    def test_sample_loop_cannot_overwrite_active_usb_data_reader(self):
        payload=bytes(range(256))*10;self.setup_loop({0:wav(payload),127:wav(payload)})
        self.ut.queue_read();self.ut.frame(hardware=False);job=self.sd.job
        before=bytes(self.u.mem_read(storage.BUFFER,4096));status=self.sd.status().copy()
        self.assertEqual(self.ll.run(),1);self.assert_loop()
        self.assertEqual(self.sd.job,job);self.assertEqual(self.sd.status(),status)
        self.assertEqual(self.u.mem_read(storage.BUFFER,4096),before)
        self.ut.frames(80);self.assertEqual(self.sd.sent[0],self.sd.media);self.ll.check()

    def test_media_semaphore_held_suppresses_msc_during_full_loop(self):
        self.setup_loop();self.ut.queue_read();pointer=self.call(0x0802EF6A,4)
        self.assertEqual(pointer,0x20003F94);self.assertEqual(self.u.mem_read(0x20003F8C,1),b'\0')
        self.assertEqual(self.ll.run(),1);self.assert_loop();self.assertEqual(self.sd.status()['reads'],0)
        self.call(0x0802EF98);self.ut.frames(80);self.assertEqual(self.sd.sent[0],self.sd.media);self.ll.check()

    def test_full_loop_nested_in_native_worker_cannot_reenter_outer_msc_read(self):
        self.setup_loop();injected,results=self.ll.inject(0x0802C328,[(0x08053E24,(0,))])
        self.ut.queue_read();self.ut.frame(hardware=False)
        self.assertEqual(len(injected),1);self.assertEqual(results(),[1]);self.assert_loop()
        self.assertEqual(self.ll.native_polls,1);self.assertEqual(self.sd.status()['reads'],1)
        self.assertEqual(self.sd.status()['cancel_tx'],0)
        self.ut.frames(80);self.assertEqual(self.sd.sent[0],self.sd.media);self.ll.check()

    def test_suspend_mid_sample_load_defers_power_service_until_main(self):
        self.setup_loop({0:wav(bytes(range(256))*2)});self.debt();self.ut.queue_read();self.ut.frame(hardware=False)
        once=[]
        def suspend(u,p,n,d):
            if not once:once.append(p);self.ss.poke(0x808,1);self.ib.external|=power.SUSPEND
        self.u.hook_add(base.UC_HOOK_CODE,suspend,begin=0x0805401A,end=0x0805401A)
        injected,results=self.ll.inject(0x0805401A,[(0x0804293E,(self.ib.handle,))])
        self.assertEqual(self.ll.run(),1);self.assert_loop()
        self.assertEqual(results(),[0]);self.assertEqual(self.pw.status()['pending'],1)
        self.assertEqual(self.pw.status()['asleep'],0);self.assertEqual(self.pw.clock_stops,[])
        self.ut.frames(16);self.assertEqual(self.pw.status()['asleep'],1);self.assertEqual(self.sd.sent,[])
        self.pw.wake();self.ut.frames(80);self.assertEqual(b''.join(self.native.usb_completed),self.expected());self.ll.check()

    def test_reset_during_loop_seals_old_reader_then_new_read_after_reconfigure(self):
        self.setup_loop();self.ut.queue_read();self.ut.frame(hardware=False);once=[]
        def reset(u,p,n,d):
            if not once:once.append(p);self.ib.external|=power.RESET
        self.u.hook_add(base.UC_HOOK_CODE,reset,begin=0x08053E78,end=0x08053E78)
        injected,results=self.ll.inject(0x08053E78,[(0x0804293E,(self.ib.handle,))])
        self.assertEqual(self.ll.run(),1);self.assert_loop()
        self.assertEqual(results(),[0]);self.assertEqual(self.sd.sent,[])
        self.ut.frames(24);self.assertEqual(self.ss.status()['phase'],session.SEALED);self.assertEqual(self.sd.sent,[])
        self.configure_host();self.ut.queue_read();self.ut.frames(80)
        self.assertEqual(self.sd.sent[0],self.sd.media);self.assertEqual(self.sd.status()['reads'],2);self.ll.check()

    def test_full_loop_does_not_service_retained_midi_retry_negative(self):
        self.setup_loop();self.debt();self.assertEqual(self.ll.run(after_slot=lambda n:self.ut.bus()),1);self.assert_loop()
        self.assertEqual(self.ut.status()['frames'],0);self.assertEqual(self.native.usb_completed,[])
        self.assertEqual(self.q.status()['active'],1);self.ut.frames(80)
        self.assertEqual(b''.join(self.native.usb_completed),self.expected());self.ll.check()

    def test_native_rejected_pack_returns_before_any_slot_or_usb_poll(self):
        self.setup_loop();self.assertEqual(self.ll.run(pack=0xFF),0)
        self.assertEqual(self.ll.reads,[]);self.assertEqual(self.ll.progress,[]);self.assertEqual(self.ll.polls,0)
        self.assertEqual(self.ll.watchdogs,[]);self.ll.check()


if __name__=='__main__':unittest.main()
