"""Native646D0/4293E + HAL/FIFO/completion/reset/EP0 over synthetic MMIO."""
import unittest
import test_integrated_accepted_tx as prior
import midi_accepted_tx_patch as guard
import midi_recovery_patch as fixed
from integrated_usb_irq_test_support import IntegratedUsbIrqFixture
base=prior.base


class IntegratedUsbIrqTests(unittest.TestCase):
    setUpClass=classmethod(prior.AcceptedTxTests.setUpClass.__func__)
    instruction_budget=500000
    for name in ('setUp','word','read','store','call','output','entry','settle','pump','stream','on','stage','state','submit_closures'):
        locals()[name]=getattr(prior.AcceptedTxTests,name)
    def usb(self):self.output();self.tx=IntegratedUsbIrqFixture(self,self.out)
    def reconfigure(self):self.tx.enumerate_irq();self.tx.address();self.tx.configure()
    expected=b'\x09\x90\x30\x60\x08\x80\x30\0\x0F\xFC\0\0'

    def test_native_vector_hal_fifo_completion_chain_in_both_modes(self):
        for mode in (0,1):
            self.setUp();self.usb();self.u.mem_write(base.seq.SEQ_STATE_ADDR+4,bytes([mode]))
            self.on();self.out.note(0,48,0,on=False);self.out.send(0,[0xFC,0,0]);self.out.poll();self.tx.bus()
            self.assertEqual(self.stream(),self.expected);self.assertEqual(self.state(guard.JOB),guard.IDLE)
            for pc in (0x080646D0,0x0804293E,0x0804301A,0x080531A6,0x0802C7AC,0x08042690,0x0802AB36,0x08040C22,0x0805268E):
                self.assertIn(pc,self.tx.irq_visits)

    def test_native_reset_address_configuration_replays_closures(self):
        for mode in (0,1):
            self.setUp();self.usb();self.u.mem_write(base.seq.SEQ_STATE_ADDR+4,bytes([mode]));self.submit_closures()
            self.tx.reset_irq();self.assertEqual(self.state(guard.PHASE),guard.REQUEST)
            self.reconfigure();self.assertNotEqual(self.state(guard.INIT_CLASS),0)
            self.assertEqual(self.tx.irq_visits.count(0x080525B6),0)
            self.pump();self.assertEqual(self.stream(),self.expected)
            self.assertEqual(self.tx.irq_visits.count(0x080525B6),1);self.tx.reset.check_rx()

    def test_coalesced_reset_and_xfrc_cannot_release_old_journal(self):
        self.usb();self.submit_closures();self.tx.flags[guard.IN_INT]|=0x80;self.tx.run_irq()
        self.tx.flags[guard.IN_INT]&=~0x80;self.tx.flags[guard.IN_INT]|=1;self.tx.external|=1<<12
        self.tx.run_irq();self.assertEqual(self.state(guard.JOB),guard.ACTIVE)
        self.assertEqual(self.stream(),b'\x09\x90\x30\x60')
        self.reconfigure();self.pump();self.assertEqual(self.stream(),self.expected)

    def test_no_host_configuration_keeps_replay_frozen(self):
        self.usb();self.submit_closures();self.tx.reset_irq();self.pump()
        self.assertEqual(self.state(guard.WAIT_CONFIG),1);self.assertEqual(self.state(guard.PHASE),guard.REPLAY)
        self.assertEqual(self.stream(),b'\x09\x90\x30\x60');self.assertEqual(self.tx.irq_visits.count(0x080525B6),0)
        self.reconfigure();self.pump();self.assertEqual(self.stream(),self.expected)

    def test_class_constructor_cannot_run_before_disable_ack(self):
        self.usb();job,payload=self.submit_closures();self.tx.reset_irq();self.reconfigure();self.tx.auto_barrier=False
        for _ in range(16):self.out.poll();self.tx.bus()
        self.assertEqual(self.state(guard.PHASE),guard.WAIT_ACK);self.assertEqual(self.tx.irq_visits.count(0x080525B6),0)
        self.assertEqual(self.u.mem_read(*job),payload);self.assertEqual(self.out.send(0,[0x90,49,96]),0)
        self.tx.ack_disable();self.tx.auto_barrier=True;self.pump();self.assertEqual(self.stream(),self.expected)

    def test_class_constructor_cannot_run_before_flush_completion(self):
        self.usb();self.submit_closures();self.tx.reset_irq();self.reconfigure();self.tx.hold_flush=True
        for _ in range(16):self.out.poll();self.tx.bus()
        self.assertEqual(self.state(guard.PHASE),guard.WAIT_FLUSH);self.assertEqual(self.tx.irq_visits.count(0x080525B6),0)
        self.assertEqual(self.tx.main()[0],0);self.tx.hold_flush=False;self.pump();self.assertEqual(self.stream(),self.expected)

    def test_native_deconfigure_then_configure_waits_for_retirement(self):
        self.usb();self.submit_closures();self.tx.configure(0);self.tx.configure(1)
        self.assertIn(0x0805261C,self.tx.irq_visits);self.assertNotEqual(self.state(guard.PHASE),guard.OPEN)
        self.assertEqual(self.tx.irq_visits.count(0x080525B6),0)
        self.pump();self.assertEqual(self.stream(),self.expected);self.assertEqual(self.tx.irq_visits.count(0x080525B6),1)

    def test_reset_inside_deferred_constructor_invalidates_old_request(self):
        self.usb();self.submit_closures();self.tx.reset_irq();self.reconfigure();_,tg=guard.arm_code(fixed.STATE_BASE,fixed.FLUSH_BUSY)
        fired=[]
        def reset(u,p,n,d):
            if not fired:fired.append(p);self.tx.external|=1<<12
        self.u.hook_add(base.UC_HOOK_CODE,reset,begin=tg['tg_native_init'],end=tg['tg_native_init'])
        self.tx.reset.inject_once(tg['tg_native_init'],[(guard.IRQ_SITE,(self.tx.handle,))])
        self.pump();self.assertEqual(len(fired),1);self.assertEqual(self.state(guard.WAIT_CONFIG),1)
        self.assertEqual(self.state(guard.INIT_CLASS),0);self.assertEqual(self.state(guard.INIT_BUSY),0)
        self.assertEqual(self.stream(),b'\x09\x90\x30\x60')
        self.reconfigure();self.pump();self.assertEqual(self.stream(),self.expected)

    def test_nested_irq_does_not_overwrite_outer_snapshot(self):
        self.usb();self.submit_closures();self.tx.flags[guard.IN_INT]|=0x80
        injected,results=self.tx.reset.inject_once(0x08042942,[(guard.IRQ_SITE,(self.tx.handle,))])
        self.tx.run_irq();self.assertEqual(len(injected),1);self.assertEqual(results(),[1])
        self.assertEqual(self.state(guard.IRQ_ACTIVE),0);self.tx.flags[guard.IN_INT]&=~0x80;self.tx.bus()
        self.assertEqual(self.stream(),self.expected)

    def test_duplicate_irq_without_new_cause_does_not_complete_new_job(self):
        self.usb();self.on();self.out.note(0,48,0,on=False);self.out.poll();self.tx.bus()
        self.assertEqual(self.out.send(0,[0x80,49,0]),1);self.out.poll()
        self.assertEqual(self.state(guard.JOB),guard.ACTIVE)
        self.tx.run_irq();self.assertEqual(self.state(guard.JOB),guard.ACTIVE)
        self.tx.bus();self.assertEqual(self.state(guard.JOB),guard.IDLE)

    def test_64_note_reset_replay_keeps_full_stream(self):
        for mode in (0,1):
            self.setUp();self.usb();self.u.mem_write(base.seq.SEQ_STATE_ADDR+4,bytes([mode]))
            for note in range(64):self.out.note(0,note);self.out.poll();self.tx.bus()
            for note in range(64):self.out.send(0,[0x80,note,0])
            self.out.send(0,[0xFC,0,0]);self.out.poll();self.tx.reset_irq();self.reconfigure();self.pump()
            expected=b''.join(bytes([9,0x90,n,96]) for n in range(64))+b''.join(bytes([8,0x80,n,0]) for n in range(64))+b'\x0F\xFC\0\0'
            self.assertEqual(self.stream(),expected)

    def test_rx_ring_and_din_closures_survive_native_class_reinit(self):
        self.usb();self.on();self.out.note(0,48,0,on=False);self.out.send(0,[0xFC,0,0]);self.out.poll()
        self.tx.reset_irq();self.reconfigure();din=[bytearray(),bytearray()]
        for _ in range(128):
            self.out.poll()
            for n,data in enumerate(self.tx.bus()):din[n].extend(data)
        self.tx.reset.check_rx();self.assertEqual(self.stream(),self.expected)
        self.assertEqual([bytes(b) for b in din],[b'\x80\x30\0']*2)

    def test_reset_without_active_job_does_not_replay_old_packet(self):
        self.usb();self.on();self.tx.reset_irq();self.reconfigure();self.pump()
        self.assertEqual(self.stream(),b'\x09\x90\x30\x60')
        self.assertEqual(self.out.send(0,[0x90,49,96]),1)

    def test_register_contract_violation_can_still_forge_old_xfrc(self):
        self.usb();self.submit_closures();self.tx.reset_irq();self.reconfigure();self.pump()
        self.assertEqual(self.out.send(0,[0x80,49,0]),1);self.out.poll();self.out.poll()
        self.assertEqual(self.state(guard.JOB),guard.ACTIVE)
        self.tx.flags[guard.IN_INT]|=0x80;self.tx.run_irq();self.tx.flags[guard.IN_INT]&=~0x80
        # A fabricated old hardware XFRC after the assumed barrier has no tag.
        self.tx.flags[guard.IN_INT]|=1;self.tx.run_irq();self.assertEqual(self.state(guard.JOB),guard.IDLE)

    def test_reset_arriving_after_irq_entry_is_seen_at_native_reset_branch(self):
        self.usb();self.submit_closures();self.tx.flags[guard.IN_INT]|=0x80;seen=[]
        def late(u,p,n,d):
            if not seen:seen.append(p);self.tx.external|=1<<12
        self.u.hook_add(base.UC_HOOK_CODE,late,begin=0x08042D16,end=0x08042D16)
        self.tx.run_irq();self.assertEqual(self.state(guard.GEN),1);self.assertEqual(self.state(guard.PHASE),guard.REQUEST)
        self.reconfigure();self.pump();self.assertEqual(self.stream(),self.expected)

    def test_reset_during_ep0_init_queue_invalidates_that_configuration(self):
        self.usb();self.submit_closures();self.tx.reset_irq();self.tx.enumerate_irq();self.tx.address()
        _,tg=guard.arm_code(fixed.STATE_BASE,fixed.FLUSH_BUSY);seen=[]
        def late(u,p,n,d):
            if not seen:seen.append(p);self.tx.external|=1<<12
        self.u.hook_add(base.UC_HOOK_CODE,late,begin=tg['init_queue'],end=tg['init_queue'])
        self.tx.configure();self.pump()
        self.assertEqual(self.state(guard.GEN),2);self.assertEqual(self.state(guard.INIT_CLASS),0)
        self.assertEqual(self.state(guard.WAIT_CONFIG),1);self.assertEqual(self.stream(),b'\x09\x90\x30\x60')
        self.reconfigure();self.pump();self.assertEqual(self.stream(),self.expected)

    def test_deferred_native_compound_list_preserves_constructor_order(self):
        self.usb();self.submit_closures();foreign,vt,tx,rx=0x2000A200,0x2000A240,0x2000A280,0x2000A290
        self.word(foreign,vt);self.word(foreign+4,tx);self.word(foreign+8,rx)
        self.word(tx,0);self.word(rx,0);self.word(vt,0x080427D3) # native ret0 parent boundary;no storage claims
        self.word(self.tx.root+12,foreign);self.word(self.tx.root+16,0);order=[]
        self.u.hook_add(base.UC_HOOK_CODE,lambda u,p,n,d:order.append(u.reg_read(base.UC_ARM_REG_R0)),begin=0x080525B6,end=0x080525B6)
        self.tx.reset_irq();self.reconfigure();self.assertEqual(order,[])
        self.pump();self.assertEqual(order,[self.tx.wrapper,foreign]);self.assertEqual(self.stream(),self.expected)


if __name__=='__main__':unittest.main()
