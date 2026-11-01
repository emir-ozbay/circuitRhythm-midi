"""Carry unsubmitted logical debt across the full hardware cancellation barrier."""
import unittest
import test_midi_usb_task as prior
import midi_usb_ledger_prototype as ledger
import midi_usb_session_prototype as session
import midi_usb_lifecycle_prototype as life
import midi_sysex_retry_prototype as retry
import midi_usb_carry_prototype as carry
import midi_usb_power_prototype as power
import midi_recovery_prototype as recovery
from midi_usb_carry_test_support import UsbCarryFixture
base=prior.base


class UsbCarryTests(unittest.TestCase):
    setUpClass=classmethod(prior.UsbTaskTests.setUpClass.__func__)
    for name in ('setUp','word','read','store','call','setup_playback','setup_recovery','setup_sysex_router',
                 'sysex_descriptor','install_nested_calls','setup_notice','setup_request','seed_notes','stall','release',
                 'capture_shorts','attach_native_note_receiver','setup_ledger','setup_life','setup_session','setup_control',
                 'setup_composite','setup_msc','setup_storage','setup_factory','setup_power','setup_task','send','fill_pending','finish_reply'):
        locals()[name]=getattr(prior.UsbTaskTests,name)
    sysex_packets=staticmethod(prior.UsbTaskTests.sysex_packets)
    bytes_as_packets=staticmethod(prior.UsbTaskTests.bytes_as_packets)
    def setup_carry(self):self.setup_task();self.cy=UsbCarryFixture(self)
    def debt(self,payload=None):
        if payload is None:payload=self.first
        self.assertEqual(self.q.submit(self.sysex_descriptor(payload)),0)
        self.send(self.inquiries*ledger.MAX_PENDING)
        self.assertEqual(self.rx.status()['pending'],ledger.MAX_PENDING)
    def expected(self,payload=None):
        return b''.join(self.sysex_packets(payload or self.first)+self.replies*ledger.MAX_PENDING)

    def test_previous_sleep_debt_counterexample_recovers_without_manual_pump(self):
        for mode in (0,1):
            self.setUp();self.setup_carry();self.u.mem_write(base.seq.SEQ_STATE_ADDR+4,bytes([mode]))
            self.debt();self.pw.suspend();self.ut.frames(16)
            self.assertEqual(self.pw.status()['asleep'],1);self.assertEqual(self.cy.status()['seals'],1)
            self.assertEqual(self.rx.status()['pending'],ledger.MAX_PENDING)
            self.pw.wake();self.ut.frames(48)
            self.assertEqual(b''.join(self.native.usb_completed),self.expected())
            self.assertEqual(self.rx.status()['pending'],0);self.assertEqual(self.pw.status()['pending'],0)
            self.assertEqual(self.cy.status()['active'],0);self.cy.check()

    def test_reset_preserves_unsubmitted_debt_until_host_reconfiguration(self):
        self.setup_carry();self.debt();self.cc.reset();self.ut.frames(16)
        self.assertEqual(self.ss.status()['phase'],session.SEALED)
        self.assertEqual(self.native.usb_completed,[])
        self.cc.enumerate();self.cc.address();self.cc.configure(1);self.ut.frames(48)
        self.assertEqual(b''.join(self.native.usb_completed),self.expected())
        self.assertEqual(self.rx.status()['pending'],0);self.cy.check()

    def test_missing_ack_keeps_debt_owned_and_buffers_unchanged(self):
        self.setup_carry();self.debt();before=self.u.mem_read(retry.STATE_BASE+retry.PAYLOAD,len(self.first))
        self.ut.hw_ack=False;self.pw.suspend();self.ut.frames(16)
        self.assertEqual(self.pw.status()['asleep'],0);self.assertEqual(self.cy.status()['seals'],0)
        self.assertEqual(self.u.mem_read(retry.STATE_BASE+retry.PAYLOAD,len(self.first)),before)
        self.ut.hw_ack=True;self.ut.frames(16);self.assertEqual(self.pw.status()['asleep'],1);self.cy.check()

    def test_inflight_tx_remains_strict_and_is_not_assumed_unsent_negative(self):
        self.setup_carry();self.ut.hw_tx=False;self.ut.inquiry();self.ut.frames(4)
        self.assertIsNotNone(self.native.in_flight);self.debt();self.pw.suspend();self.ut.frames(32)
        self.assertEqual(self.cy.status()['seals'],0);self.assertEqual(self.pw.status()['asleep'],0)
        self.assertEqual(self.ss.status()['tx_active'],1);self.cy.check()

    def test_full_owned_payload_survives_sleep_and_drains_across_packets_once(self):
        self.setup_carry();payload=b'\xF0'+bytes(n%128 for n in range(358))+b'\xF7'
        self.debt(payload);self.pw.suspend();self.ut.frames(16)
        self.assertEqual(self.pw.status()['asleep'],1)
        self.assertEqual(self.u.mem_read(retry.STATE_BASE+retry.PAYLOAD,len(payload)),payload)
        self.pw.wake();self.ut.frames(96)
        self.assertEqual(b''.join(self.native.usb_completed),self.expected(payload))
        self.assertEqual([bytes(b) for b in self.cy.din_bytes],[payload,payload])
        self.assertEqual(self.q.status()['active'],0);self.assertEqual(self.rx.status()['pending'],0);self.cy.check()

    def test_committed_clock_stop_after_debt_is_not_lost_or_replayed(self):
        self.setup_carry();self.debt();messages=self.capture_shorts()
        packets=bytes([15,0xF8,0,0,15,0xFC,0,0])
        self.rx.enqueue(packets)  # admitted, but not yet parsed when closure starts
        self.pw.suspend();self.ut.frames(16);self.assertEqual(messages,[])
        self.pw.wake();self.ut.frames(64)
        self.assertEqual(messages,[b'\xF8',b'\xFC'])
        self.assertEqual(self.rx.status()['pending'],0);self.cy.check()

    def test_repeated_sleep_before_any_tx_preserves_the_same_debt(self):
        self.setup_carry();self.debt();self.pw.suspend();self.ut.frames(16)
        self.pw.wake()
        for _ in range(16):
            self.ut.frame()
            if self.ss.status()['phase']==session.OPEN:break
        # One native frame resumes; before the next output poll can stage bytes,
        # close again and carry precisely the same logical ownership.
        self.assertEqual(self.ss.status()['phase'],session.OPEN)
        self.pw.suspend();self.ut.frames(16);self.assertEqual(self.pw.status()['asleep'],1)
        self.pw.wake();self.ut.frames(64)
        self.assertEqual(b''.join(self.native.usb_completed),self.expected())
        self.assertEqual(self.cy.status()['seals'],2);self.cy.check()

    def test_reset_during_hal_retirement_does_not_erase_new_request(self):
        self.setup_carry();self.debt()
        self.pw.suspend()
        reset_once=[]
        def reset(u,p,n,d):
            if not reset_once:reset_once.append(p);self.ib.external|=power.RESET
        p=self.cy.labels['cy_seal_commit']
        self.u.hook_add(base.UC_HOOK_CODE,reset,begin=p,end=p)
        injected,results=self.install_nested_calls(p,[(0x0804293E,(self.ib.handle,)),(self.ss.labels['ss_step'],())])
        self.ss.record_nested_trampoline();self.ut.frames(16)
        self.assertEqual(len(injected),1);self.assertEqual(results(),[0,1])
        self.assertEqual(self.rx.status()['pending'],ledger.MAX_PENDING)
        self.cc.enumerate();self.cc.address();self.cc.configure(1);self.ut.frames(64)
        self.assertEqual(b''.join(self.native.usb_completed),self.expected());self.cy.check()

    def test_partial_native_staging_is_not_treated_as_unsent_negative(self):
        self.setup_carry();self.debt()
        driver=self.read(session.STATE_BASE+session.DRIVER)
        self.u.mem_write(driver+18,b'\x04\x00')
        self.pw.suspend();self.ut.frames(16)
        self.assertEqual(self.cy.status()['seals'],0);self.assertEqual(self.pw.status()['asleep'],0)
        self.u.mem_write(driver+18,b'\x00\x00');self.cy.check()

    def test_resume_cannot_be_called_outside_the_owned_session_callsite(self):
        self.setup_carry();self.debt();self.pw.suspend();self.ut.frames(16)
        self.assertEqual(self.lc.status()['phase'],life.CLOSED)
        self.assertEqual(self.call(self.cy.labels['cy_resume']),1)
        self.assertEqual(self.lc.status()['phase'],life.CLOSED);self.cy.check()

    def test_wrapped_owed_record_preserves_provenance_and_never_replays_clock_stop(self):
        import struct
        self.setup_carry();ring=self.rx.ring();pos=ring['capacity']-6
        self.u.mem_write(self.ingress.usb_fifo+6,struct.pack('<HH',pos,pos))
        self.word(ledger.STATE_BASE+ledger.EXPECTED_READ,pos)
        self.debt();messages=self.capture_shorts()
        self.send(self.inquiries+bytes([15,0xF8,0,0,15,0xFC,0,0]))
        self.assertEqual(messages,[b'\xF8',b'\xFC'])
        scanned=self.read(ledger.STATE_BASE+ledger.SCANNED);self.assertGreater(scanned,0)
        data=self.u.mem_read(ring['data'],ring['capacity'])
        self.pw.suspend();self.ut.frames(16)
        self.assertEqual(self.pw.status()['asleep'],1)
        self.assertEqual(self.u.mem_read(ring['data'],ring['capacity']),data)
        self.assertEqual(self.read(ledger.STATE_BASE+ledger.SCANNED),scanned)
        self.pw.wake();self.ut.frames(80)
        self.assertEqual(messages,[b'\xF8',b'\xFC'])
        expected=b''.join(self.sysex_packets(self.first)+self.replies*(ledger.MAX_PENDING+1))
        self.assertEqual(b''.join(self.native.usb_completed),expected)
        self.assertEqual(self.read(ledger.STATE_BASE+ledger.SCANNED),0);self.cy.check()

    def test_queued_note_off_is_preserved_alongside_query_debt(self):
        self.setup_carry();self.debt();self.assertEqual(self.recovery.send(0,0x80,60,0),1)
        self.pw.suspend();self.ut.frames(16);self.assertEqual(self.pw.status()['asleep'],1)
        self.pw.wake();self.ut.frames(64)
        wire=b''.join(self.native.usb_completed);packets=[wire[i:i+4] for i in range(0,len(wire),4)]
        off=bytes([8,0x80,60,0]);self.assertEqual(packets.count(off),1)
        self.assertEqual(b''.join(p for p in packets if p!=off),self.expected());self.cy.check()

    def test_partial_parser_remains_closed_without_discarding_it_negative(self):
        self.setup_carry();self.debt();self.u.mem_write(self.ingress.parser,b'\x01')
        self.pw.suspend();self.ut.frames(16)
        self.assertEqual(self.cy.status()['seals'],0);self.assertEqual(self.pw.status()['asleep'],0)
        self.assertEqual(self.u.mem_read(self.ingress.parser,1),b'\x01');self.cy.check()

    def test_reset_at_resume_commit_cannot_open_an_obsolete_generation(self):
        self.setup_carry();self.debt();self.pw.suspend();self.ut.frames(16);self.pw.wake()
        once=[];p=self.cy.labels['cy_resume_commit']
        def reset(u,p,n,d):
            if not once:once.append(p);self.ib.external|=power.RESET
        self.u.hook_add(base.UC_HOOK_CODE,reset,begin=p,end=p)
        injected,results=self.install_nested_calls(p,[(0x0804293E,(self.ib.handle,))])
        self.ss.record_nested_trampoline();self.ut.frames(16)
        self.assertEqual(len(injected),1);self.assertEqual(results(),[0])
        self.assertEqual(self.native.usb_completed,[]);self.assertEqual(self.ss.status()['phase'],session.SEALED)
        self.cc.enumerate();self.cc.address();self.cc.configure(1);self.ut.frames(64)
        self.assertEqual(b''.join(self.native.usb_completed),self.expected());self.cy.check()

    def test_genuine_existing_port_fault_is_never_cleared_by_carry(self):
        self.setup_carry();self.assertEqual(self.recovery.send(0,0x80,60,0),1)
        self.lc.configured(0);self.recovery.poll(0)
        self.assertTrue(self.recovery.flags(0)&recovery.FAULT)
        self.lc.configured(3);self.assertEqual(self.q.submit(self.sysex_descriptor()),1)
        self.send(self.inquiries*ledger.MAX_PENDING);self.pw.suspend();self.ut.frames(16)
        self.assertTrue(self.recovery.flags(0)&recovery.FAULT)
        self.assertEqual(self.rx.status()['pending'],ledger.MAX_PENDING)
        self.assertEqual(self.cy.status()['seals'],0);self.assertEqual(self.pw.status()['asleep'],0);self.cy.check()


if __name__=='__main__':unittest.main()
