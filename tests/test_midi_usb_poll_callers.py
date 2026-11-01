"""Native2DE90/43FA0 callback admission and reentry around owned USB readers."""
import unittest
import test_midi_usb_factory_debt as prior
import midi_usb_session_prototype as session
import midi_usb_msc_prototype as msc
import midi_usb_storage_prototype as storage
import midi_usb_power_prototype as power
from midi_usb_poll_callers_test_support import UsbPollCallerFixture
from unicorn.arm_const import UC_ARM_REG_IPSR,UC_ARM_REG_PRIMASK
base=prior.base


class UsbPollCallerTests(unittest.TestCase):
    setUpClass=classmethod(prior.UsbFactoryDebtTests.setUpClass.__func__)
    for name in ('setUp','word','read','store','call','setup_playback','setup_recovery','setup_sysex_router',
                 'sysex_descriptor','install_nested_calls','setup_notice','setup_request','seed_notes','stall','release',
                 'capture_shorts','attach_native_note_receiver','setup_ledger','setup_life','setup_session','setup_control',
                 'setup_composite','setup_msc','setup_storage','setup_factory','setup_power','setup_task','send',
                 'fill_pending','finish_reply','debt','expected','setup_staging','snapshot','start_payload','configure_host'):
        locals()[name]=getattr(prior.UsbFactoryDebtTests,name)
    sysex_packets=staticmethod(prior.UsbFactoryDebtTests.sysex_packets)
    bytes_as_packets=staticmethod(prior.UsbFactoryDebtTests.bytes_as_packets)
    def setup_callers(self):self.setup_staging();self.pc=UsbPollCallerFixture(self)
    def tearDown(self):
        if hasattr(self,'pc'):self.pc.record(self._testMethodName)

    def test_native_dispatch_adapter_callback_can_complete_read_in_both_modes(self):
        for mode in (0,1):
            self.setUp();self.setup_callers();self.u.mem_write(base.seq.SEQ_STATE_ADDR+4,bytes([mode]))
            self.ut.queue_read();self.assertEqual(self.pc.dispatch(),0)
            self.assertEqual(self.pc.events[:4],['dispatch','adapter','callback','bot_poll'])
            for _ in range(80):self.pc.poll();self.ut.bus()
            self.assertEqual(self.sd.sent[0],self.sd.media);self.assertEqual(self.sd.sent[1][:4],b'USBS')
            self.assertEqual(self.sd.status()['reads'],1);self.assertEqual(self.ut.status()['frames'],0);self.cy.check()
            if mode==0:self.pc.record(self._testMethodName+'-normal')

    def test_irq_or_masked_callback_cannot_consume_a_ready_cbw(self):
        self.setup_callers();self.ut.queue_read();before=self.pc.snapshot()
        for reg,value in ((UC_ARM_REG_IPSR,16),(UC_ARM_REG_PRIMASK,1)):
            self.u.reg_write(reg,value)
            try:self.assertEqual(self.pc.dispatch(),0)
            finally:self.u.reg_write(reg,0)
            self.assertEqual(self.pc.snapshot(),before)
        self.ut.frames(80);self.assertEqual(self.sd.sent[0],self.sd.media);self.cy.check()

    def test_worker_nested_callback_cannot_reenter_or_cancel_outer_read(self):
        self.setup_callers();injected,results=self.install_nested_calls(0x0802C328,
            [(0x08025652,(self.pc.callback,0)),(self.ut.labels['ut_main'],())])
        self.ss.record_nested_trampoline();self.ut.queue_read();self.ut.frame(hardware=False)
        self.assertEqual(len(injected),1);self.assertEqual(results(),[0,1])
        self.assertEqual(self.sd.status()['reads'],1);self.assertEqual(self.sd.status()['cancel_tx'],0)
        self.assertEqual(self.pc.events.count('bot_poll'),1)
        self.ut.frames(80);self.assertEqual(self.sd.sent[0],self.sd.media);self.cy.check()

    def test_suspend_from_worker_then_callback_does_not_release_worker_reader(self):
        self.setup_callers();once=[]
        def suspend(u,p,n,d):
            if not once:once.append(p);self.ss.poke(0x808,1);self.ib.external|=power.SUSPEND
        self.u.hook_add(base.UC_HOOK_CODE,suspend,begin=0x0802C328,end=0x0802C328)
        injected,results=self.install_nested_calls(0x0802C328,
            [(0x0804293E,(self.ib.handle,)),(0x08025652,(self.pc.callback,0)),(self.ut.labels['ut_main'],())])
        self.ss.record_nested_trampoline();self.ut.queue_read();self.ut.frame(hardware=False)
        self.assertEqual(len(injected),1);self.assertEqual(results(),[0,0,1])
        self.assertEqual(self.pw.clock_stops,[]);self.assertEqual(self.pc.events.count('bot_poll'),1)
        self.ut.frames(16);self.assertEqual(self.pw.status()['asleep'],1);self.assertEqual(self.sd.sent,[]);self.cy.check()

    def test_callback_during_active_data_tx_keeps_buffer_and_ticket_unchanged(self):
        self.setup_callers();self.ut.hw_tx=False;self.ut.queue_read();self.ut.frame()
        self.assertEqual(self.sd.status()['tx_active'],1);before=self.pc.snapshot()
        data=bytes(self.u.mem_read(storage.BUFFER,4096))
        for _ in range(16):self.assertEqual(self.pc.dispatch(),0)
        self.assertEqual(self.pc.snapshot(),before);self.assertEqual(self.u.mem_read(storage.BUFFER,4096),data)
        self.ut.hw_tx=True;self.ut.frames(80);self.assertEqual(self.sd.sent[0],self.sd.media);self.cy.check()

    def test_recursive_callback_after_native_poll_owner_publish_is_rejected(self):
        self.setup_callers();injected,results=self.install_nested_calls(0x0802EF5A,[(0x08025652,(self.pc.callback,0))])
        self.ss.record_nested_trampoline();self.ut.queue_read();self.ut.frame(hardware=False)
        self.assertEqual(len(injected),1);self.assertEqual(results(),[0])
        self.assertEqual(self.pc.events.count('bot_poll'),1);self.assertEqual(self.sd.status()['reads'],1)
        self.ut.frames(80);self.assertEqual(self.sd.sent[0],self.sd.media);self.cy.check()

    def test_suspend_between_poll_admission_and_native_body_cannot_bypass_barrier(self):
        self.setup_callers();pc=0x0802EF5A;once=[]
        def suspend(u,p,n,d):
            if not once:once.append(p);self.ss.poke(0x808,1);self.ib.external|=power.SUSPEND
        self.u.hook_add(base.UC_HOOK_CODE,suspend,begin=pc,end=pc)
        injected,results=self.install_nested_calls(pc,[(0x0804293E,(self.ib.handle,)),
            (0x08025652,(self.pc.callback,0)),(self.ut.labels['ut_main'],())])
        self.ss.record_nested_trampoline();self.ut.queue_read();self.ut.frame(hardware=False)
        self.assertEqual(len(injected),1);self.assertEqual(results(),[0,0,1])
        self.assertEqual(self.pw.clock_stops,[]);self.assertEqual(self.sd.status()['reads'],0)
        self.ut.frames(24);self.assertEqual(self.pw.status()['asleep'],1)
        self.assertEqual(self.sd.sent,[]);self.cy.check()

    def test_reset_from_worker_then_callback_keeps_reader_until_outer_return(self):
        self.setup_callers();pc=0x0802C328;once=[]
        def reset(u,p,n,d):
            if not once:once.append(p);self.ib.external|=power.RESET
        self.u.hook_add(base.UC_HOOK_CODE,reset,begin=pc,end=pc)
        injected,results=self.install_nested_calls(pc,[(0x0804293E,(self.ib.handle,)),
            (0x08025652,(self.pc.callback,0)),(self.ut.labels['ut_main'],())])
        self.ss.record_nested_trampoline();self.ut.queue_read();self.ut.frame(hardware=False)
        self.assertEqual(len(injected),1);self.assertEqual(results(),[0,0,1])
        self.assertEqual(self.sd.status()['reads'],1);self.assertEqual(self.pc.events.count('bot_poll'),1)
        self.ut.frames(24);self.assertEqual(self.ss.status()['phase'],session.SEALED)
        self.assertEqual(self.sd.sent,[]);self.configure_host();self.ut.queue_read();self.ut.frames(80)
        self.assertEqual(self.sd.sent[0],self.sd.media);self.cy.check()

    def test_callback_nested_inside_real_storage_completion_irq_cannot_poll_again(self):
        self.setup_callers();self.ut.queue_read();self.ut.frame(hardware=False)
        injected,results=self.install_nested_calls(0x080268D0,[(0x08025652,(self.pc.callback,0))])
        self.ss.record_nested_trampoline();before=self.pc.events.count('bot_poll')
        for _ in range(80):self.ut.bus()
        self.assertEqual(len(injected),1);self.assertEqual(results(),[0])
        self.assertEqual(self.pc.events.count('bot_poll'),before)
        self.assertEqual(self.sd.sent[0],self.sd.media);self.ut.frames(80)
        self.assertEqual(self.sd.sent[1][:4],b'USBS');self.assertEqual(self.sd.status()['reads'],1);self.cy.check()

    def test_asleep_callback_does_not_touch_mmio_or_discard_retained_midi_debt(self):
        self.setup_callers();self.debt();self.pw.suspend();self.ut.frames(16)
        self.assertEqual(self.pw.status()['asleep'],1);reads=list(self.pw.sleeping_reads)
        before=self.pc.snapshot();pending=self.rx.status()['pending']
        for _ in range(16):self.assertEqual(self.pc.dispatch(),0)
        self.assertEqual(self.pw.sleeping_reads,reads);self.assertEqual(self.pc.snapshot(),before)
        self.assertEqual(self.rx.status()['pending'],pending)
        self.pw.wake();self.ut.frames(64)
        self.assertEqual(b''.join(self.native.usb_completed),self.expected());self.cy.check()

    def test_callback_during_native_factory_cannot_reenter_class_rebuild(self):
        self.setup_callers();self.debt();self.fx.request(1)
        injected,results=self.install_nested_calls(0x08040A40,
            [(0x08025652,(self.pc.callback,0)),(self.ut.labels['ut_main'],())])
        self.ss.record_nested_trampoline();self.ut.frames(24)
        self.assertEqual(len(injected),1);self.assertEqual(results(),[0,1])
        self.assertEqual(self.fx.status()['switches'],1);self.assertEqual(self.fx.status()['applied'],1)
        self.assertEqual(self.pc.events.count('bot_poll'),0)
        self.configure_host();self.ut.frames(64)
        self.assertEqual(b''.join(self.native.usb_completed),self.expected());self.cy.check()

    def test_callback_only_does_not_replace_coordinated_main_service_negative(self):
        self.setup_callers();self.debt();self.pw.suspend()
        for _ in range(32):self.pc.poll();self.ut.bus()
        self.assertEqual(self.pw.status()['pending'],1);self.assertEqual(self.pw.status()['asleep'],0)
        self.assertEqual(self.ut.status()['frames'],0);self.assertEqual(self.native.usb_completed,[])
        self.assertEqual(self.q.status()['active'],1)
        self.ut.frames(16);self.assertEqual(self.pw.status()['asleep'],1)
        self.pw.wake();self.ut.frames(64)
        self.assertEqual(b''.join(self.native.usb_completed),self.expected());self.cy.check()

    def test_other_native_direct_poll_callsite_has_same_leaf_context_guards(self):
        self.setup_callers();self.ut.queue_read();before=self.pc.snapshot()
        for reg,value in ((UC_ARM_REG_IPSR,16),(UC_ARM_REG_PRIMASK,1)):
            self.u.reg_write(reg,value)
            try:self.assertEqual(self.call(0x08053E78,end=0x08053E7C),0)
            finally:self.u.reg_write(reg,0)
            self.assertEqual(self.pc.snapshot(),before)
        self.call(0x08053E78,end=0x08053E7C);self.assertEqual(self.sd.status()['reads'],1)
        self.ut.frames(80);self.assertEqual(self.sd.sent[0],self.sd.media);self.cy.check()


if __name__=='__main__':unittest.main()
