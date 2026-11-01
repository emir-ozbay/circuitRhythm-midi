"""Native MAIN staging survives a rejected submit; no device I/O."""
import unittest
import test_midi_usb_carry as prior
import midi_usb_carry_prototype as carry
import midi_usb_session_prototype as session
import midi_usb_power_prototype as power
import midi_sysex_retry_prototype as retry
import midi_usb_ledger_prototype as ledger
from midi_usb_carry_test_support import UsbCarryFixture
base=prior.base


class UsbStagingTests(unittest.TestCase):
    setUpClass=classmethod(prior.UsbCarryTests.setUpClass.__func__)
    for name in ('setUp','word','read','store','call','setup_playback','setup_recovery','setup_sysex_router',
                 'sysex_descriptor','install_nested_calls','setup_notice','setup_request','seed_notes','stall','release',
                 'capture_shorts','attach_native_note_receiver','setup_ledger','setup_life','setup_session','setup_control',
                 'setup_composite','setup_msc','setup_storage','setup_factory','setup_power','setup_task','send',
                 'fill_pending','finish_reply','debt','expected'):
        locals()[name]=getattr(prior.UsbCarryTests,name)
    sysex_packets=staticmethod(prior.UsbCarryTests.sysex_packets)
    bytes_as_packets=staticmethod(prior.UsbCarryTests.bytes_as_packets)
    def setup_staging(self,enabled=True):self.setup_task();self.cy=UsbCarryFixture(self,staging=enabled)
    def snapshot(self):
        d=self.read(session.STATE_BASE+session.DRIVER);m=self.read(d+8);c=self.read(session.STATE_BASE+session.TX_COUNTER)
        n=int.from_bytes(self.u.mem_read(m,2),'little')
        return dict(length=n,data=bytes(self.u.mem_read(self.read(m+4),n)),
                    cursor=int.from_bytes(self.u.mem_read(c,2),'little'),
                    total=int.from_bytes(self.u.mem_read(c+2,2),'little'))
    def interrupt(self,pc,reset=False):
        captured=[]
        def signal(u,p,n,d):
            if not captured:
                captured.append(self.snapshot());self.ss.poke(0x808,1)
                self.ib.external|=power.RESET if reset else power.SUSPEND
        self.u.hook_add(base.UC_HOOK_CODE,signal,begin=pc,end=pc)
        injected,results=self.install_nested_calls(pc,[(0x0804293E,(self.ib.handle,))])
        self.ss.record_nested_trampoline();return captured,injected,results
    def start_payload(self,payload):
        self.assertEqual(self.q.submit(self.sysex_descriptor(payload)),0)
        # First main pass admits the immutable slot; the next native output
        # worker formats it. No direct driver/formatter call or RAM staging.
        self.ut.frame();self.assertEqual(self.q.status()['accepted'],7)
    def settle_sleep(self):
        self.ut.frames(16);self.assertEqual(self.pw.status()['asleep'],1)
        self.assertEqual(self.ss.status()['tx_active'],0)
    def wake_and_check(self,payload):
        self.pw.wake();self.ut.frames(96)
        self.assertEqual(b''.join(self.native.usb_completed),b''.join(self.sysex_packets(payload)))
        self.assertEqual([bytes(b) for b in self.cy.din_bytes],[payload,payload])
        self.assertEqual(self.q.status()['active'],0);self.assertEqual(self.cy.status()['active'],0);self.cy.check()

    def test_native_pre_submit_suspend_preserves_full_main_and_partial_owned_cursor(self):
        for mode in (0,1):
            self.setUp();self.setup_staging();self.u.mem_write(base.seq.SEQ_STATE_ADDR+4,bytes([mode]))
            payload=b'\xF0'+bytes(n%128 for n in range(358))+b'\xF7';self.start_payload(payload)
            captured,injected,results=self.interrupt(0x0802B498)
            self.ut.frame();self.assertEqual(results(),[0]);self.assertEqual(len(injected),1)
            self.assertEqual(captured[0]['length'],64);self.assertEqual(captured[0]['cursor'],48)
            self.assertEqual(self.native.usb_submissions,[]);self.settle_sleep()
            self.assertEqual(self.snapshot(),captured[0]);self.wake_and_check(payload)

    def test_without_staging_guard_native_rejected_submit_erases_prepared_bytes_negative(self):
        self.setup_staging(enabled=False);payload=b'\xF0'+bytes(range(58))+b'\xF7';self.start_payload(payload)
        captured,_,results=self.interrupt(0x0802B498);self.ut.frame();self.ut.frames(16)
        self.assertEqual(results(),[0]);self.assertEqual(captured[0]['length'],64)
        self.assertEqual(self.snapshot()['length'],0);self.assertEqual(self.snapshot()['cursor'],48)
        self.assertEqual(self.native.usb_submissions,[]);self.assertEqual(self.cy.status()['seals'],0);self.cy.check()

    def test_reset_before_actual_submit_keeps_bytes_until_host_reconfiguration(self):
        self.setup_staging();payload=b'\xF0'+bytes(range(58))+b'\xF7';self.start_payload(payload)
        captured,_,results=self.interrupt(self.cy.labels['cy_flush_submit'],reset=True)
        self.ut.frame();self.ut.frames(16);self.assertEqual(results(),[0])
        self.assertEqual(self.ss.status()['phase'],session.SEALED)
        self.assertEqual(self.snapshot(),captured[0]);self.assertEqual(self.native.usb_submissions,[])
        self.cc.enumerate();self.cc.address();self.cc.configure(1);self.ut.frames(64)
        self.assertEqual(b''.join(self.native.usb_completed),b''.join(self.sysex_packets(payload)));self.cy.check()

    def test_short_note_off_with_no_remaining_software_debt_is_carried(self):
        self.setup_staging();self.assertEqual(self.recovery.send(0,0x80,60,0),1)
        captured,_,results=self.interrupt(0x0802B498);self.ut.frame();self.assertEqual(results(),[0])
        self.assertEqual(captured[0]['length'],4);self.assertEqual(captured[0]['cursor'],0)
        self.settle_sleep();self.assertEqual(self.snapshot(),captured[0]);self.pw.wake();self.ut.frames(32)
        self.assertEqual(b''.join(self.native.usb_completed),bytes([8,0x80,60,0]));self.cy.check()

    def test_accepted_submit_before_suspend_is_not_classified_unsent_negative(self):
        self.setup_staging();payload=b'\xF0'+bytes(range(58))+b'\xF7';self.start_payload(payload)
        _,_,results=self.interrupt(self.cy.labels['cy_flush_after_submit']);self.ut.frame();self.ut.frames(16)
        self.assertEqual(results(),[0]);self.assertEqual(self.ss.status()['tx_active'],1)
        self.assertEqual(self.snapshot()['length'],0);self.assertEqual(len(self.native.usb_submissions),1)
        self.assertEqual(self.native.usb_completed,[]);self.assertEqual(self.cy.status()['seals'],0)
        self.assertEqual(self.pw.status()['asleep'],0);self.cy.check()

    def test_missing_ack_never_retires_or_changes_prepared_main(self):
        self.setup_staging();payload=b'\xF0'+bytes(range(58))+b'\xF7';self.start_payload(payload)
        captured,_,_=self.interrupt(0x0802B498);self.ut.hw_ack=False;self.ut.frame();self.ut.frames(16)
        self.assertEqual(self.pw.status()['asleep'],0);self.assertEqual(self.cy.status()['seals'],0)
        self.assertEqual(self.snapshot(),captured[0]);self.ut.hw_ack=True;self.settle_sleep()
        self.assertEqual(self.snapshot(),captured[0]);self.wake_and_check(payload)

    def test_repeated_sleep_before_retained_main_submit_keeps_original_cursor(self):
        self.setup_staging();payload=b'\xF0'+bytes(range(58))+b'\xF7';self.start_payload(payload)
        captured,_,_=self.interrupt(0x0802B498);self.ut.frame();self.settle_sleep();self.pw.wake()
        for _ in range(16):
            self.ut.frame()
            if self.ss.status()['phase']==session.OPEN:break
        self.assertEqual(self.ss.status()['phase'],session.OPEN)
        self.assertEqual(self.snapshot(),captured[0]);self.pw.suspend();self.settle_sleep()
        self.assertEqual(self.snapshot(),captured[0]);self.wake_and_check(payload)
        self.assertEqual(self.cy.status()['seals'],2)

    def test_completed_first_packet_is_not_replayed_when_partial_cursor_resumes(self):
        self.setup_staging();payload=b'\xF0'+bytes(n%128 for n in range(358))+b'\xF7';self.start_payload(payload)
        self.ut.frame();first=b''.join(self.native.usb_completed);self.assertEqual(len(first),64)
        state=self.snapshot();self.assertEqual(state['cursor'],48);self.assertEqual(state['length'],0)
        self.pw.suspend();self.settle_sleep();self.assertEqual(self.snapshot(),state);self.wake_and_check(payload)

    def test_partial_borrower_outside_owned_slot_remains_closed_negative(self):
        self.setup_staging();payload=b'\xF0'+bytes(range(58))+b'\xF7';self.start_payload(payload)
        self.interrupt(0x0802B498);self.ut.frame();p=self.read(session.STATE_BASE+session.TX_PORT)
        self.word(p+8,0x20004C00);self.ut.frames(16)
        self.assertEqual(self.pw.status()['asleep'],0);self.assertEqual(self.cy.status()['seals'],0)
        self.assertEqual(self.native.usb_submissions,[]);self.cy.check()

    def test_invalid_main_or_raw_mode_is_never_admitted_negative(self):
        for kind in ('unaligned','oversized','raw_length','raw_mode','foreign_main'):
            with self.subTest(kind=kind):
                self.setUp();self.setup_staging();payload=b'\xF0'+bytes(range(58))+b'\xF7';self.start_payload(payload)
                self.interrupt(0x0802B498);self.ut.frame();d=self.read(session.STATE_BASE+session.DRIVER);m=self.read(d+8)
                if kind=='unaligned':self.u.mem_write(m,b'\x03\x00')
                elif kind=='oversized':self.u.mem_write(m,b'\x44\x00')
                elif kind=='raw_length':self.u.mem_write(d+18,b'\x04\x00')
                elif kind=='raw_mode':self.u.mem_write(d+20,b'\x01')
                else:self.word(d+24,self.read(d+12))
                self.ut.frames(16);self.assertEqual(self.pw.status()['asleep'],0)
                self.assertEqual(self.cy.status()['seals'],0);self.assertEqual(self.native.usb_submissions,[]);self.cy.check()

    def test_staged_payload_and_owed_queries_do_not_replay_committed_clock_stop(self):
        self.setup_staging();payload=b'\xF0'+bytes(range(58))+b'\xF7'
        self.start_payload(payload);self.send(self.inquiries*ledger.MAX_PENDING);messages=self.capture_shorts()
        self.send(self.inquiries+bytes([15,0xF8,0,0,15,0xFC,0,0]));self.assertEqual(messages,[b'\xF8',b'\xFC'])
        self.interrupt(0x0802B498);self.ut.frame();self.settle_sleep();self.pw.wake();self.ut.frames(96)
        expected=b''.join(self.sysex_packets(payload)+self.replies*(ledger.MAX_PENDING+1))
        self.assertEqual(b''.join(self.native.usb_completed),expected);self.assertEqual(messages,[b'\xF8',b'\xFC'])
        self.assertEqual(self.rx.status()['pending'],0);self.cy.check()

    def test_default_carry_machine_code_remains_pinned(self):
        import hashlib
        self.assertEqual(hashlib.sha256(carry.arm_code()[0]).hexdigest(),
            'f703550dabc585a6bcdc1025a8cf9f93dc68d2bad1617096947d45db62709636')


if __name__=='__main__':unittest.main()
