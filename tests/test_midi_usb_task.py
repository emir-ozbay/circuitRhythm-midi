"""Native main-loop reachability, worker yield and bounded service ownership."""
import unittest
import test_midi_usb_power as prior
import midi_usb_task_prototype as task
import midi_usb_power_prototype as power
import midi_usb_session_prototype as session
import midi_usb_msc_prototype as msc
import midi_usb_ledger_prototype as ledger
from midi_usb_task_test_support import UsbTaskFixture
base=prior.base


class UsbTaskTests(unittest.TestCase):
    setUpClass=classmethod(prior.UsbPowerTests.setUpClass.__func__)
    for name in ('setUp','word','read','store','call','setup_playback','setup_recovery','setup_sysex_router',
                 'sysex_descriptor','install_nested_calls','setup_notice','setup_request','seed_notes','stall','release',
                 'capture_shorts','attach_native_note_receiver','setup_ledger','setup_life','setup_session','setup_control',
                 'setup_composite','setup_msc','setup_storage','setup_factory','setup_power','send','fill_pending','finish_reply'):
        locals()[name]=getattr(prior.UsbPowerTests,name)
    sysex_packets=staticmethod(prior.UsbPowerTests.sysex_packets)
    bytes_as_packets=staticmethod(prior.UsbPowerTests.bytes_as_packets)
    def setup_task(self,overlay=True):self.setup_power();self.ut=UsbTaskFixture(self,overlay=overlay)

    def test_native_main_order_reaches_one_task_service_per_pass(self):
        self.setup_task();saved=[self.u.reg_read(r) for r in base.SAVED]
        self.ut.frame();self.assertEqual(self.ut.events[:4],['output','input','msc_slot','task'])
        self.assertEqual(self.ut.status()['frames'],1)
        self.assertEqual([self.u.reg_read(r) for r in base.SAVED],saved);self.ut.check()

    def test_suspend_and_wake_complete_from_native_main_without_manual_service(self):
        self.setup_task();self.pw.suspend();self.ut.frames()
        self.assertEqual(self.pw.status()['asleep'],1);self.pw.wake();self.ut.frames()
        self.assertEqual(self.ss.status()['phase'],session.OPEN);self.ut.check()

    def test_native_main_services_inquiry_retry_and_wire_completion(self):
        self.setup_task();self.ut.inquiry();self.ut.frames()
        self.assertEqual(b''.join(self.native.usb_completed),b''.join(self.replies))
        self.assertEqual(self.q.status()['active'],0);self.ut.check()

    def test_read_and_csw_run_through_native_main_worker_and_irqs(self):
        self.setup_task();self.ut.queue_read();self.ut.frames(80)
        self.assertEqual(self.sd.sent[0],self.sd.media);self.assertEqual(self.sd.sent[1][:4],b'USBS')
        self.assertIn('worker',self.ut.events);self.assertIn('worker_loop',self.ut.events)
        self.assertIn('drain_yield',self.ut.events);self.ut.check()

    def test_without_main_hook_power_request_never_advances_negative(self):
        self.setup_task(overlay=False);self.pw.suspend();self.ut.frames()
        self.assertEqual(self.pw.status()['pending'],1);self.assertEqual(self.pw.status()['asleep'],0)
        self.assertEqual(self.ut.status()['frames'],0);self.ut.check()

    def test_without_main_hook_owned_inquiry_has_no_retry_service_negative(self):
        self.setup_task(overlay=False);self.ut.inquiry();self.ut.frames()
        self.assertEqual(self.q.status()['active'],1);self.assertEqual(self.native.usb_completed,[])
        self.assertEqual(self.ut.status()['frames'],0);self.ut.check()

    def test_suspend_cancels_read_from_main_then_wake_allows_another_read(self):
        self.setup_task();self.ut.queue_read();self.ut.frame(hardware=False)
        self.assertEqual(self.sd.status()['tx_active'],1);self.pw.suspend();self.ut.frames()
        self.assertEqual(self.pw.status()['asleep'],1);self.assertEqual(self.sd.sent,[])
        self.pw.wake();self.ut.frames();self.ut.queue_read();self.ut.frames(80)
        self.assertEqual(self.sd.sent[0],self.sd.media);self.ut.check()

    def test_missing_ack_keeps_main_alive_without_closing_reader(self):
        self.setup_task();self.ut.hw_ack=False;self.pw.suspend();self.ut.frames()
        self.assertEqual(self.pw.status()['asleep'],0);self.assertEqual(self.ut.status()['frames'],16)
        self.assertEqual(self.mc.status()['phase'],msc.WAIT_DISABLE)
        self.ut.hw_ack=True;self.ut.frames();self.assertEqual(self.pw.status()['asleep'],1);self.ut.check()

    def test_worker_nested_task_service_cannot_reenter_or_release_read(self):
        self.setup_task()
        injected,results=self.install_nested_calls(0x0802C328,[(self.ut.labels['ut_main'],())])
        self.ss.record_nested_trampoline();self.ut.queue_read();self.ut.frame(hardware=False)
        self.assertEqual(len(injected),1);self.assertEqual(results(),[1])
        self.assertEqual(self.ut.status()['rejects'],1);self.assertEqual(self.sd.status()['tx_active'],1)
        self.assertEqual(self.sd.status()['done'],0);self.ut.frames(80);self.ut.check()

    def test_suspend_irq_inside_worker_waits_for_outer_reader_return(self):
        self.setup_task()
        def suspend(u,p,n,d):self.ss.poke(0x808,1);self.ib.external|=power.SUSPEND
        self.u.hook_add(base.UC_HOOK_CODE,suspend,begin=0x0802C328,end=0x0802C328)
        injected,results=self.install_nested_calls(0x0802C328,[(0x0804293E,(self.ib.handle,)),(self.ut.labels['ut_main'],())])
        self.ss.record_nested_trampoline();self.ut.queue_read();self.ut.frame(hardware=False)
        self.assertEqual(len(injected),1);self.assertEqual(results(),[0,1])
        self.assertEqual(self.pw.clock_stops,[]);self.ut.frames()
        self.assertEqual(self.pw.status()['asleep'],1);self.assertEqual(self.sd.sent,[]);self.ut.check()

    def test_irq_or_masked_task_entry_performs_no_service(self):
        from unicorn.arm_const import UC_ARM_REG_IPSR,UC_ARM_REG_PRIMASK
        self.setup_task()
        for reg,value in ((UC_ARM_REG_IPSR,16),(UC_ARM_REG_PRIMASK,1)):
            self.u.reg_write(reg,value)
            try:self.assertEqual(self.call(self.ut.labels['ut_main']),1)
            finally:self.u.reg_write(reg,0)
        self.assertEqual(self.ut.status()['frames'],0);self.ut.check()

    def test_ordinary_inquiry_pressure_progresses_without_manual_retry_pump(self):
        self.setup_task();self.ut.hw_tx=False;self.ut.inquiry();self.ut.frames(4)
        self.assertIsNotNone(self.native.in_flight)
        self.ut.hw_tx=True;self.ut.frames(24)
        self.assertEqual(b''.join(self.native.usb_completed),b''.join(self.replies))
        self.assertEqual(self.q.status()['active'],0);self.ut.check()

    def test_pending_inquiry_debt_before_suspend_still_deadlocks_negative(self):
        self.setup_task();self.assertEqual(self.q.submit(self.sysex_descriptor()),0)
        self.send(self.inquiries*ledger.MAX_PENDING)
        self.assertEqual(self.rx.status()['pending'],ledger.MAX_PENDING)
        self.pw.suspend();self.ut.frames(32)
        # Correct native reachability does not repair this ownership protocol:
        # frozen cl_poll cannot transfer retained ledger debts, while ss_quiet
        # refuses closure until those debts/queued TX readers disappear.
        self.assertEqual(self.ut.status()['frames'],32)
        self.assertEqual(self.rx.status()['pending'],ledger.MAX_PENDING)
        self.assertEqual(self.pw.status()['pending'],1);self.assertEqual(self.pw.status()['asleep'],0)
        self.pw.wake();self.ut.frames(32)
        self.assertEqual(self.ut.status()['frames'],64);self.assertEqual(self.pw.status()['pending'],1)
        self.assertEqual(self.rx.status()['pending'],ledger.MAX_PENDING)
        self.assertEqual(self.pw.clock_stops,[]);self.ut.check()


if __name__=='__main__':unittest.main()
