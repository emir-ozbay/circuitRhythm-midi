"""USB suspend/wakeup ownership under synthetic MMIO and native callbacks."""
import unittest
import test_midi_usb_factory as prior
import midi_usb_power_prototype as power
import midi_usb_session_prototype as session
import midi_usb_msc_prototype as msc
from midi_usb_power_test_support import UsbPowerFixture
base=prior.base


class UsbPowerTests(unittest.TestCase):
    setUpClass=classmethod(prior.UsbFactoryTests.setUpClass.__func__)
    for name in ('setUp','word','read','store','call','setup_playback','setup_recovery','setup_sysex_router',
                 'sysex_descriptor','install_nested_calls','setup_notice','setup_request','seed_notes','stall','release',
                 'capture_shorts','attach_native_note_receiver','setup_ledger','setup_life','setup_session','setup_control',
                 'setup_composite','setup_msc','setup_storage','setup_factory','send','fill_pending','finish_reply'):
        locals()[name]=getattr(prior.UsbFactoryTests,name)
    sysex_packets=staticmethod(prior.UsbFactoryTests.sysex_packets)
    bytes_as_packets=staticmethod(prior.UsbFactoryTests.bytes_as_packets)
    def setup_power(self):self.setup_factory();self.pw=UsbPowerFixture(self)

    def test_suspend_waits_for_shared_barrier_before_clock_stop(self):
        self.setup_power();self.assertEqual(self.pw.suspend(),0)
        self.assertEqual(self.pw.status()['pending'],1);self.assertEqual(self.pw.clock_stops,[])
        self.assertEqual(self.u.mem_read(self.ib.ctrl+0x274,1),b'\x03')
        self.pw.pump();self.assertEqual(self.pw.status()['asleep'],1)
        self.assertEqual(self.u.mem_read(self.ib.ctrl+0x274,2),b'\x04\x03')
        self.assertEqual(len(self.pw.clock_stops),1);self.pw.check()

    def test_wakeup_ungates_and_rebuilds_configured_midi_and_msc(self):
        self.setup_power();self.pw.suspend();self.pw.pump();self.assertEqual(self.pw.wake(),0)
        self.assertEqual(self.pw.status()['asleep'],0);self.assertFalse(self.ss.regs[0xE00]&1)
        self.pw.pump();self.assertEqual(self.ss.status()['phase'],session.OPEN)
        self.assertEqual(self.mc.status()['phase'],msc.OPEN)
        self.sd.command();self.sd.complete_tx();self.assertEqual(self.sd.sent,[self.sd.media]);self.pw.check()

    def test_active_read_is_cancelled_before_suspend_clock_stop(self):
        self.setup_power();self.sd.command();self.pw.suspend()
        self.assertEqual(self.sd.status()['tx_active'],1);self.assertEqual(self.pw.clock_stops,[])
        self.pw.pump();self.assertEqual(self.sd.status()['cancel_tx'],1)
        self.assertEqual(self.sd.sent,[]);self.assertEqual(self.pw.status()['asleep'],1);self.pw.check()

    def test_early_wakeup_cancels_pending_sleep_without_clock_stop(self):
        self.setup_power();self.pw.suspend();self.pw.wake();self.pw.pump()
        self.assertEqual(self.pw.clock_stops,[]);self.assertEqual(self.ss.status()['phase'],session.OPEN)
        self.assertEqual(self.pw.status()['pending'],0);self.pw.check()

    def test_reset_while_asleep_does_not_reopen_old_configuration(self):
        self.setup_power();self.pw.suspend();self.pw.pump();self.cc.reset();self.pw.pump()
        self.assertEqual(self.pw.status()['asleep'],0);self.assertEqual(self.ss.status()['phase'],session.SEALED)
        self.cc.enumerate();self.cc.address();self.cc.configure(1);self.pw.pump()
        self.assertEqual(self.ss.status()['phase'],session.OPEN);self.pw.check()

    def test_coalesced_wake_and_suspend_keeps_wake_priority(self):
        self.setup_power();self.ss.poke(0x808,1);self.ib.external|=power.WAKE|power.SUSPEND
        self.assertEqual(self.ib.run(),0);self.pw.pump()
        self.assertEqual(self.pw.clock_stops,[]);self.assertEqual(self.pw.status()['pending'],0)
        self.assertEqual(self.ss.status()['phase'],session.OPEN);self.pw.check()

    def test_repeated_suspend_is_idempotent_and_defers_factory_while_asleep(self):
        self.setup_power();self.pw.suspend();self.pw.pump();before=self.pw.status()
        self.pw.suspend();self.pw.pump();self.assertEqual(self.pw.status(),before)
        self.assertTrue(self.pw.sleeping_reads)
        self.assertEqual(self.ss.regs[0x18],power.WAKE|power.RESET)
        self.fx.request(1);self.pw.pump();self.assertEqual(self.fx.status()['pending'],1)
        self.assertEqual(self.u.mem_read(self.ib.root,1),b'\x02')
        self.pw.wake();self.pw.pump();self.assertEqual(self.fx.status()['applied'],1)
        self.assertEqual(self.pw.status()['pending'],0);self.pw.check()

    def test_admitted_midi_debt_prevents_clock_stop(self):
        self.setup_power();self.fill_pending();self.pw.suspend()
        for _ in range(8):
            self.pw.service()
            if self.mc.status()['phase']==msc.WAIT_DISABLE:self.mc.ack()
            if self.mc.status()['phase']==msc.WAIT_FLUSH:self.mc.finish_flush()
        self.assertEqual(self.pw.clock_stops,[]);self.assertEqual(self.pw.status()['pending'],1)
        self.assertNotEqual(self.ss.status()['phase'],session.SEALED);self.pw.check()

    def test_missing_msc_disable_ack_prevents_clock_stop(self):
        self.setup_power();self.pw.suspend();self.pw.service()
        self.assertEqual(self.mc.status()['phase'],msc.WAIT_DISABLE)
        for _ in range(4):self.pw.service()
        self.assertEqual(self.pw.clock_stops,[]);self.assertEqual(self.pw.status()['asleep'],0)
        self.pw.pump();self.assertEqual(self.pw.status()['asleep'],1);self.pw.check()

    def test_midi_only_resumes_query_without_arming_msc(self):
        self.setup_power();self.fx.request(1);self.pw.pump();self.fx.enumerate()
        self.pw.suspend();self.pw.pump();self.assertEqual(self.pw.status()['asleep'],1)
        self.pw.wake();self.pw.pump()
        self.assertEqual(self.mc.status()['phase'],msc.SEALED);self.assertEqual(self.mc.status()['rx_active'],0)
        self.ib.rx_data(self.inquiries);self.ib.rx_complete();self.ib.run();self.rx.poll();self.finish_reply()
        self.assertEqual(b''.join(self.native.usb_completed),b''.join(self.replies));self.pw.check()

    def test_unprotected_native_suspend_stops_clock_with_live_reader_negative(self):
        self.setup_power();self.sd.command();self.pw.strict_clock=False
        self.call(self.pw.labels['pw_suspend_native'],self.ib.handle)
        self.assertEqual(self.sd.status()['tx_active'],1);self.assertEqual(self.ss.status()['phase'],session.OPEN)
        self.assertTrue(self.ss.regs[0xE00]&1);self.assertEqual(len(self.pw.clock_stops),1);self.pw.check()

    def test_wakeup_inside_native_state_save_cannot_stop_clock_afterwards(self):
        self.setup_power();self.pw.suspend()
        def wake(u,p,n,d):self.ib.external|=power.WAKE
        self.u.hook_add(base.UC_HOOK_CODE,wake,begin=0x080427AA,end=0x080427AA)
        injected,results=self.install_nested_calls(0x080427AA,[(0x0804293E,(self.ib.handle,))])
        self.ss.record_nested_trampoline();self.pw.pump()
        self.assertEqual(len(injected),1);self.assertEqual(results(),[0])
        self.assertEqual(self.pw.clock_stops,[]);self.assertEqual(self.ss.status()['phase'],session.OPEN)
        self.assertEqual(self.pw.status()['pending'],0);self.pw.check()

    def test_coalesced_reset_and_suspend_waits_for_host_reconfiguration(self):
        self.setup_power();self.ss.poke(0x808,1);self.ib.external|=power.RESET|power.SUSPEND
        self.assertEqual(self.ib.run(),0);self.pw.pump()
        self.assertEqual(self.pw.clock_stops,[]);self.assertEqual(self.ss.status()['phase'],session.SEALED)
        self.cc.enumerate();self.cc.address();self.cc.configure(1);self.pw.pump()
        self.assertEqual(self.ss.status()['phase'],session.OPEN);self.pw.check()

    def test_deep_sleep_dma_and_lpm_remain_explicit_unsupported(self):
        for off in (16,32):
            self.setUp();self.setup_power();self.word(self.ib.handle+off,1)
            self.assertEqual(self.pw.suspend(),1);self.assertEqual(self.ss.status()['phase'],session.BROKEN)
            self.assertEqual(self.pw.clock_stops,[])
        self.setUp();self.setup_power();self.ib.external=1<<27;self.ss.poke(0x18,power.POWER_GINT|(1<<27))
        self.assertEqual(self.ib.run(),1);self.assertEqual(self.ss.status()['phase'],session.BROKEN)
        self.assertEqual(self.pw.clock_stops,[])

    def test_din_off_and_project_ram_survive_suspend_wakeup(self):
        self.setup_power();before=self.u.mem_read(0x20010000,0x29484)
        self.output.note(0,60,0,on=False);self.output.drain(0)
        self.pw.suspend();self.pw.pump();self.pw.wake();self.pw.pump()
        self.assertEqual([self.output.pop(p) for p in (1,2)],[bytes([0x80,60,0])]*2)
        self.assertEqual(self.u.mem_read(0x20010000,0x29484),before);self.pw.check()

    def test_generation_wrap_freezes_without_clock_stop(self):
        self.setup_power();self.word(power.STATE_BASE+power.GENERATION,0xFFFFFFFF)
        self.assertEqual(self.pw.suspend(),1);self.assertEqual(self.ss.status()['phase'],session.BROKEN)
        self.assertEqual(self.pw.status()['errors'],1);self.assertEqual(self.pw.clock_stops,[])


if __name__=='__main__':unittest.main()
