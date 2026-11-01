"""Native accepted-MAIN journal/retirement/replay,explicit MMIO contract."""
import unittest
import test_integrated_usb_tx as prior
import midi_accepted_tx_patch as guard
import midi_recovery_prototype as core
base=prior.base


class AcceptedTxTests(unittest.TestCase):
    setUpClass=classmethod(prior.IntegratedUsbTxTests.setUpClass.__func__)
    instruction_budget=500000
    for name in ('setUp','word','read','store','call','output','entry','settle','usb','pump','stream','on','stage'):
        locals()[name]=getattr(prior.IntegratedUsbTxTests,name)
    def state(self,offset):return self.read(guard.STATE_BASE+offset)
    def submit_closures(self):
        self.on();self.out.note(0,48,0,on=False);self.out.send(0,[0xFC,0,0]);self.out.poll()
        self.assertEqual(self.state(guard.JOB),guard.ACTIVE)
        return self.tx.native.in_flight,bytes(self.u.mem_read(*self.tx.native.in_flight))
    def close(self):
        self.u.mem_write(self.tx.native.usb_controller+0x274,b'\0')
        self.call(guard.CLOSE_SITE,self.tx.wrapper,self.tx.native.usb_controller,0)
    def done(self):return self.call(0x0805268E,self.tx.native.completion_wrapper,self.tx.native.usb_controller,1)

    def test_accepted_cancel_before_after_closures_in_both_modes(self):
        for mode in (0,1):
            self.setUp();self.usb();self.u.mem_write(base.seq.SEQ_STATE_ADDR+4,bytes([mode]))
            self.submit_closures();self.close();self.tx.reconnect();self.pump()
            self.assertEqual(self.stream(),b'\x09\x90\x30\x60\x08\x80\x30\0\x0F\xFC\0\0')
            self.assertEqual(self.state(guard.PHASE),guard.OPEN);self.assertEqual(self.state(guard.JOB),guard.IDLE)

    def test_missing_disable_ack_keeps_reader_and_shadow_frozen(self):
        self.usb();job,payload=self.submit_closures();self.tx.auto_barrier=False;self.close();self.tx.reconnect()
        for _ in range(32):self.out.poll();self.tx.bus()
        self.assertEqual(self.state(guard.PHASE),guard.WAIT_ACK)
        self.assertEqual(self.tx.native.in_flight,job);self.assertEqual(self.u.mem_read(*job),payload)
        self.assertEqual(self.u.mem_read(guard.STATE_BASE+guard.SHADOW,8),payload)
        self.assertEqual(self.out.send(0,[0x90,49,96]),0)
        self.u.mem_write(0x20009000,b'\x09\x90\x31\x60')
        self.assertEqual(self.call(0x0802B460,self.out.drivers[0],0x20009000),0)
        self.done();self.assertEqual(self.state(guard.JOB),guard.ACTIVE)
        self.assertEqual(self.u.mem_read(*job),payload)

    def test_missing_flush_does_not_release_old_main(self):
        self.usb();job,payload=self.submit_closures();self.tx.auto_barrier=False;self.close();self.tx.reconnect()
        self.out.poll();self.tx.ack_disable();self.out.poll()
        self.assertEqual(self.state(guard.PHASE),guard.WAIT_FLUSH)
        for _ in range(16):self.out.poll()
        self.assertEqual(self.tx.native.in_flight,job);self.assertEqual(self.u.mem_read(*job),payload)
        self.assertEqual(self.tx.main()[0],0)
        self.tx.finish_flush();self.tx.auto_barrier=True;self.pump()
        self.assertEqual(self.stream(),b'\x09\x90\x30\x60\x08\x80\x30\0\x0F\xFC\0\0')

    def test_completed_job_is_not_replayed_by_later_quiescent_close(self):
        self.usb();self.submit_closures();self.tx.bus();expected=self.stream()
        self.assertEqual(self.state(guard.JOB),guard.IDLE)
        self.close();self.tx.reconnect();self.pump();self.assertEqual(self.stream(),expected)
        self.assertEqual(self.out.send(0,[0x90,49,96]),1)

    def test_native_completion_during_arming_is_committed_once(self):
        self.usb();self.on();_,tg=guard.arm_code(prior.fixed.STATE_BASE,prior.fixed.FLUSH_BUSY)
        injected,_=self.tx.reset.inject_once(tg['tg_finish'],[(0x0805268E,(self.tx.native.completion_wrapper,self.tx.native.usb_controller,1))])
        self.out.note(0,48,0,on=False);self.out.send(0,[0xFC,0,0]);self.out.poll()
        self.assertEqual(len(injected),1);self.assertEqual(self.state(guard.JOB),guard.IDLE)
        self.tx.bus();self.assertEqual(self.stream(),b'\x09\x90\x30\x60\x08\x80\x30\0\x0F\xFC\0\0')

    def test_native_close_between_admission_and_finish_preserves_shadow(self):
        self.usb();self.on();_,tg=guard.arm_code(prior.fixed.STATE_BASE,prior.fixed.FLUSH_BUSY)
        once=[]
        def offline(u,p,n,d):
            if not once:once.append(p);u.mem_write(self.tx.native.usb_controller+0x274,b'\0')
        self.u.hook_add(base.UC_HOOK_CODE,offline,begin=tg['tg_finish'],end=tg['tg_finish'])
        self.tx.reset.inject_once(tg['tg_finish'],[(guard.CLOSE_SITE,(self.tx.wrapper,self.tx.native.usb_controller,0))])
        self.out.note(0,48,0,on=False);self.out.send(0,[0xFC,0,0]);self.out.poll()
        self.assertEqual(self.state(guard.JOB),guard.ACTIVE);self.assertEqual(self.state(guard.PHASE),guard.REQUEST)
        self.tx.reconnect();self.pump()
        self.assertEqual(self.stream(),b'\x09\x90\x30\x60\x08\x80\x30\0\x0F\xFC\0\0')

    def test_repeated_close_restarts_generation_without_releasing_payload(self):
        self.usb();job,payload=self.submit_closures();self.tx.auto_barrier=False;self.close();self.tx.reconnect()
        self.out.poll();self.tx.ack_disable();self.out.poll()
        self.assertEqual(self.state(guard.PHASE),guard.WAIT_FLUSH)
        self.close();self.assertEqual(self.state(guard.GEN),2);self.assertEqual(self.state(guard.PHASE),guard.REQUEST)
        self.assertEqual(self.u.mem_read(*job),payload)
        self.tx.finish_flush();self.tx.reconnect();self.tx.auto_barrier=True;self.pump()
        self.assertEqual(self.stream(),b'\x09\x90\x30\x60\x08\x80\x30\0\x0F\xFC\0\0')

    def test_only_in1_masks_and_fifo_are_touched(self):
        self.usb();self.submit_closures();masks=dict(self.tx.regs);self.close();self.tx.reconnect();self.pump()
        for reg in (guard.DAINTMSK,guard.DEACHMSK):self.assertEqual(self.tx.regs[reg],masks[reg])
        self.assertEqual(self.tx.regs[guard.EMPMSK]&~2,masks[guard.EMPMSK]&~2)
        self.assertTrue(all(value==0x60 for reg,value in self.tx.writes if reg==guard.GRSTCTL))
        self.assertFalse(any(reg in (0xB20,0xB28) for reg,value in self.tx.writes))

    def test_service_in_irq_or_masked_context_does_not_touch_hardware(self):
        self.usb();self.submit_closures();self.close();_,tg=guard.arm_code(prior.fixed.STATE_BASE,prior.fixed.FLUSH_BUSY)
        self.u.mem_write(self.entry(0)+core.BUSY,b'\x01') # explicit context-only lease
        before=dict(self.tx.regs);state=bytes(self.u.mem_read(guard.STATE_BASE,128))
        for mask,irq in ((1,0),(0,16)):
            self.u.reg_write(base.UC_ARM_REG_PRIMASK,mask);self.u.reg_write(base.UC_ARM_REG_IPSR,irq)
            try:self.call(tg['tg_service'])
            finally:self.u.reg_write(base.UC_ARM_REG_PRIMASK,0);self.u.reg_write(base.UC_ARM_REG_IPSR,0)
            self.assertEqual(self.tx.regs,before);self.assertEqual(self.u.mem_read(guard.STATE_BASE,128),state)

    def test_generation_wrap_keeps_job_frozen_and_latches_fault(self):
        self.usb();job,payload=self.submit_closures();self.word(guard.STATE_BASE+guard.GEN,0xFFFFFFFF)
        self.close();self.tx.reconnect();self.pump()
        self.assertEqual(self.state(guard.PHASE),guard.BROKEN);self.assertEqual(self.u.mem_read(*job),payload)
        self.assertEqual(self.out.send(0,[0x90,49,96]),0)

    def test_replay_filters_on_clock_sysex_and_keeps_only_closures(self):
        self.usb();self.on()
        events=[b'\x09\x90\x31\x60',b'\x0F\xF8\0\0',b'\x04\xF0\x01\x02',b'\x08\x80\x30\x7F',
                b'\x09\x90\x32\0',b'\x08\x90\x33\x60',b'\x0F\xFC\0\0']
        for event in events:self.stage(event)
        self.call(prior.fixed.USB_FLUSH,self.out.drivers[0]);self.close();self.tx.reconnect();self.pump()
        self.assertEqual(self.stream(),b'\x09\x90\x30\x60'+events[3]+events[4]+events[6])

    def test_cancelled_first_chunk_of_64_off_is_replayed_before_remaining_fifo(self):
        for mode in (0,1):
            self.setUp();self.usb();self.u.mem_write(base.seq.SEQ_STATE_ADDR+4,bytes([mode]))
            for note in range(64):self.out.note(0,note);self.out.poll();self.tx.bus()
            for note in range(64):self.out.send(0,[0x80,note,0])
            self.out.send(0,[0xFC,0,0]);self.out.poll();self.close();self.tx.reconnect();self.pump()
            expected=b''.join(bytes([9,0x90,n,96]) for n in range(64))+b''.join(bytes([8,0x80,n,0]) for n in range(64))+b'\x0F\xFC\0\0'
            self.assertEqual(self.stream(),expected)

    def test_untagged_callback_during_close_cannot_release_job(self):
        self.usb();job,payload=self.submit_closures();self.tx.auto_barrier=False;self.close();self.tx.reconnect()
        self.call(guard.DONE_SITE,self.tx.native.usb_endpoint);self.done()
        self.assertEqual(self.state(guard.JOB),guard.ACTIVE);self.assertEqual(self.tx.native.in_flight,job)
        self.assertEqual(self.u.mem_read(*job),payload)

    def test_wrong_caller_cannot_release_active_normal_job(self):
        self.usb();self.submit_closures();self.call(guard.DONE_SITE,self.tx.native.usb_endpoint)
        self.assertEqual(self.state(guard.JOB),guard.ACTIVE)
        self.tx.bus();self.assertEqual(self.state(guard.JOB),guard.IDLE)

    def test_barrier_violating_old_untagged_callback_is_an_explicit_limit(self):
        self.usb();self.submit_closures();self.close();self.tx.reconnect();self.pump()
        self.assertEqual(self.out.send(0,[0x80,49,0]),1);self.out.poll();self.out.poll()
        self.assertEqual(self.state(guard.JOB),guard.ACTIVE)
        # An old XFRC forged after retirement has no epoch in the stock ABI.
        # This violates the modeled barrier;it must remain an M7 limitation.
        self.done();self.assertEqual(self.state(guard.JOB),guard.IDLE)

    def test_read_only_tx_fifo_empty_flag_does_not_block_retirement(self):
        self.usb();self.submit_closures();self.tx.regs[guard.IN_INT]|=0x80
        self.close();self.tx.reconnect();self.pump()
        self.assertEqual(self.tx.regs[guard.IN_INT]&0x80,0x80)
        self.assertEqual(self.state(guard.PHASE),guard.OPEN)
        self.assertEqual(self.stream(),b'\x09\x90\x30\x60\x08\x80\x30\0\x0F\xFC\0\0')

    def test_existing_allocator_clears_journal_without_extra_reservation(self):
        self.word(base.seq.HEAP_LIMIT_PTR,base.seq.HEAP_LIMIT);self.word(base.seq.HEAP_CUR_PTR,0x2004EA98)
        self.u.mem_write(prior.fixed.STATE_BASE,b'\xA5'*1088)
        self.assertEqual(self.call(self.labels['c_seq_state']),base.seq.SEQ_STATE_ADDR)
        self.assertEqual(self.u.mem_read(guard.STATE_BASE,128),bytes(128))
        self.assertEqual(self.read(base.seq.HEAP_LIMIT_PTR),prior.fixed.STATE_BASE)

    def test_dma_mode_is_frozen_without_releasing_the_old_job(self):
        self.usb();job,payload=self.submit_closures();self.word(self.tx.handle+0x10,1)
        self.close();self.tx.reconnect();self.pump()
        self.assertEqual(self.state(guard.PHASE),guard.BROKEN)
        self.assertEqual(self.tx.native.in_flight,job);self.assertEqual(self.u.mem_read(*job),payload)


if __name__=='__main__':unittest.main()
