"""Native synchronous file FIFO/wait/worker used by the pack sample loader."""
import unittest
import test_midi_usb_long_loop as prior
import midi_usb_session_prototype as session
import midi_usb_power_prototype as power
from midi_usb_file_queue_test_support import UsbFileQueueFixture
from midi_usb_long_loop_test_support import wav,swapped
base=prior.base


class UsbFileQueueTests(unittest.TestCase):
    setUpClass=classmethod(prior.UsbLongLoopTests.setUpClass.__func__)
    for name in ('setUp','word','read','store','call','setup_playback','setup_recovery','setup_sysex_router',
                 'sysex_descriptor','install_nested_calls','setup_notice','setup_request','seed_notes','stall','release',
                 'capture_shorts','attach_native_note_receiver','setup_ledger','setup_life','setup_session','setup_control',
                 'setup_composite','setup_msc','setup_storage','setup_factory','setup_power','setup_task','send',
                 'fill_pending','finish_reply','debt','expected','setup_staging','snapshot','start_payload','configure_host','assert_loop'):
        locals()[name]=getattr(prior.UsbLongLoopTests,name)
    sysex_packets=staticmethod(prior.UsbLongLoopTests.sysex_packets)
    bytes_as_packets=staticmethod(prior.UsbLongLoopTests.bytes_as_packets)
    def setup_loop(self,files=None):self.setup_staging();self.ll=UsbFileQueueFixture(self,files)
    def tearDown(self):
        if hasattr(self,'ll'):self.ll.record(self._testMethodName)

    def test_native_queue_full_loader_missing_files_both_modes(self):
        for mode in (0,1):
            self.setUp();self.setup_loop();self.u.mem_write(base.seq.SEQ_STATE_ADDR+4,bytes([mode]))
            self.assertEqual(self.ll.run(),1);self.assert_loop()
            self.assertEqual((self.ll.dispatches,self.ll.waits,self.ll.workers),(128,128,128))
            self.assertEqual({r for _,_,r,_ in self.ll.results},{5})
            if mode==0:self.ll.record(self._testMethodName+'-normal')

    def test_native_queue_valid_double_buffer_and_partial_last_chunk(self):
        payload=bytes(n%256 for n in range(4608));self.setup_loop({0:wav(payload),127:wav(payload)})
        before=bytes(self.u.mem_read(0x20010000,0x29484));self.assertEqual(self.ll.run(),1);self.assert_loop()
        self.assertEqual(b''.join(b for _,b in self.ll.writes),swapped(payload*2))
        self.assertEqual([len(b) for _,b in self.ll.writes],[2048,2048,512]*2)
        self.assertEqual(self.ll.dispatches,134);self.assertEqual(len(self.ll.dequeued),134)
        self.assertEqual(self.u.mem_read(0x20010000,0x29484),before)

    def test_native_file_queue_and_msc_read_data_csw_share_loop_without_main(self):
        self.setup_loop({63:wav(bytes(range(256))*2)});self.ut.queue_read()
        self.assertEqual(self.ll.run(after_slot=lambda n:self.ut.bus()),1);self.assert_loop()
        self.assertEqual([len(b) for b in self.sd.sent],[4096,13]);self.assertEqual(self.sd.sent[0],self.sd.media)
        self.assertEqual(self.ut.status()['frames'],0);self.assertEqual(self.ll.dispatches,129)

    def test_file_worker_nested_inside_msc_worker_retains_outer_reader(self):
        self.setup_loop({0:wav(bytes(range(256))*2)})
        injected,results=self.ll.inject(0x0802C328,[(0x08053E8C,(0,)),(self.ut.labels['ut_main'],())])
        self.ut.queue_read();self.ut.frame(hardware=False)
        self.assertEqual(len(injected),1);self.assertEqual(results(),[256,1])
        self.assertEqual(self.sd.status()['reads'],1);self.assertEqual(self.sd.status()['cancel_tx'],0)
        self.assertEqual(b''.join(b for _,b in self.ll.writes),swapped(bytes(range(256))*2))
        self.ut.frames(80);self.assertEqual(self.sd.sent[0],self.sd.media);self.ll.check()

    def test_reset_in_native_file_read_keeps_copied_request_until_worker_completion(self):
        self.setup_loop({0:wav(bytes(range(256))*2)});self.ut.queue_read();self.ut.frame(hardware=False);once=[]
        def reset(u,p,n,d):
            if not once:once.append(p);self.ib.external|=power.RESET
        self.u.hook_add(base.UC_HOOK_CODE,reset,begin=0x0802AE2E,end=0x0802AE2E)
        injected,results=self.ll.inject(0x0802AE2E,[(0x0804293E,(self.ib.handle,)),(self.ut.labels['ut_main'],())])
        self.assertEqual(self.ll.run(),1);self.assert_loop();self.assertEqual(len(injected),1)
        # File request ownership is distinct from the already-submitted MSC
        # TX. No MSC worker/drain is active here,so main service can run.
        self.assertEqual(results(),[0,0]);self.assertEqual(self.ut.status()['frames'],2)
        self.ut.frames(24)
        self.assertEqual(self.ss.status()['phase'],session.SEALED);self.assertEqual(self.sd.sent,[])
        self.configure_host();self.ut.queue_read();self.ut.frames(80)
        self.assertEqual(self.sd.sent[0],self.sd.media);self.ll.check()

    def test_suspend_in_file_worker_preserves_midi_debt_and_request_credit(self):
        self.setup_loop({0:wav(bytes(range(256))*2)});self.debt();once=[]
        def suspend(u,p,n,d):
            if not once:once.append(p);self.ss.poke(0x808,1);self.ib.external|=power.SUSPEND
        self.u.hook_add(base.UC_HOOK_CODE,suspend,begin=0x0802AE2E,end=0x0802AE2E)
        injected,results=self.ll.inject(0x0802AE2E,[(0x0804293E,(self.ib.handle,))])
        self.assertEqual(self.ll.run(),1);self.assert_loop();self.assertEqual(results(),[0])
        self.assertEqual(self.pw.status()['pending'],1);self.assertEqual(self.pw.status()['asleep'],0)
        self.ut.frames(16);self.assertEqual(self.pw.status()['asleep'],1)
        self.pw.wake();self.ut.frames(80);self.assertEqual(b''.join(self.native.usb_completed),self.expected());self.ll.check()

    def test_native_file_read_error_is_published_before_wait_returns(self):
        self.setup_loop({0:wav(bytes(range(256))*2)});self.ll.faults[0,0]=(3,0)
        descriptor=0x22002000
        self.word(descriptor,4);self.word(descriptor+4,0);self.word(descriptor+8,0xFE)
        self.word(0x20040000,0);self.word(0x20040004,0)
        self.assertEqual(self.call(0x0804603A,descriptor,0,0x20006AD8,64),3)
        self.assertEqual(self.ll.results,[(0,0,3,0)])
        self.assertEqual(self.read(self.ll.worker+0xC),3);self.assertEqual(self.ll.writes,[]);self.ll.check()

    def test_short_sample_data_read_is_not_zero_filled_negative(self):
        payload=bytes(range(256))*16;self.setup_loop({0:wav(payload)})
        self.ll.faults[0,44+2048]=(4,2)
        self.u.mem_write(0x20003F94,b'\xA5'*2048)
        self.assertEqual(self.call(0x08053E8C,0),2048)
        self.assertEqual(self.ll.results[-1],(0,2092,4,2))
        self.assertEqual(len(self.ll.writes),2);self.assertEqual(self.ll.writes[-1][1][2:],b'\xA5'*2046)
        self.assertNotEqual(b''.join(b for _,b in self.ll.writes),swapped(payload));self.ll.check()


if __name__=='__main__':unittest.main()
