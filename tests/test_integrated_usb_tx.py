"""Packaged MAIN admission ownership and modeled accepted-cancel replay."""
import unittest
import test_integrated_midi_recovery as prior
import midi_recovery_patch as fixed
from integrated_usb_tx_test_support import IntegratedUsbTxFixture
base=prior.base


class IntegratedUsbTxTests(unittest.TestCase):
    setUpClass=classmethod(prior.IntegratedRecoveryTests.setUpClass.__func__)
    instruction_budget=500000
    for name in ('setUp','word','read','store','call','output','entry','settle'):
        locals()[name]=getattr(prior.IntegratedRecoveryTests,name)
    def usb(self):self.output();self.tx=IntegratedUsbTxFixture(self,self.out)
    def pump(self):
        for _ in range(128):self.out.poll();self.tx.bus()
    def stream(self):return b''.join(self.tx.native.usb_completed)
    def on(self):self.out.note(0,48);self.out.poll();self.tx.bus()
    def stage(self,event=b'\x08\x80\x30\0'):
        self.u.mem_write(0x20009000,event)
        self.assertEqual(self.call(0x0802B460,self.out.drivers[0],0x20009000),1)

    def test_class_deinit_before_admission_keeps_off_stop_in_both_modes(self):
        for mode in (0,1):
            self.setUp();self.usb();self.u.mem_write(base.seq.SEQ_STATE_ADDR+4,bytes([mode]));self.on()
            self.out.note(0,48,0,on=False);self.out.send(0,[0xFC,0,0]);self.tx.disconnect_before_flush(no_credit=True)
            self.out.poll();self.assertEqual(self.tx.main()[0],8);self.assertEqual(self.out.pending(0),0)
            self.assertEqual(len(self.tx.closes),1);self.assertIsNone(self.tx.native.in_flight)
            self.tx.reconnect();self.pump()
            self.assertEqual(self.stream(),b'\x09\x90\x30\x60\x08\x80\x30\0\x0F\xFC\0\0')

    def test_configured_credit_race_retains_main_without_a_hal_submit(self):
        self.usb();self.on();self.out.note(0,48,0,on=False);self.out.send(0,[0xFC,0,0])
        seen=[]
        def exhaust(u,p,n,d):
            if not seen:seen.append(p);u.mem_write(self.tx.native.usb_endpoint+0x1C,b'\0')
        hook=self.u.hook_add(base.UC_HOOK_CODE,exhaust,begin=0x08026880,end=0x08026880)
        self.out.poll();self.u.hook_del(hook)
        self.assertEqual(self.tx.main()[0],8);self.assertEqual(len(self.tx.native.usb_submissions),1)
        self.u.mem_write(self.tx.native.usb_endpoint+0x1C,b'\x01');self.pump()
        self.assertEqual(self.stream(),b'\x09\x90\x30\x60\x08\x80\x30\0\x0F\xFC\0\0')

    def test_retained_full_main_flushes_before_remaining_fifo(self):
        self.usb()
        for note in range(16):self.out.note(0,note)
        self.out.poll();self.tx.bus()
        for note in range(16):self.out.send(0,[0x80,note,0])
        self.out.send(0,[0xFC,0,0]);self.tx.disconnect_before_flush(no_credit=True)
        self.out.poll();self.assertEqual(self.tx.main()[0],64);self.assertEqual(self.out.pending(0),1)
        self.tx.reconnect();self.pump()
        expected=b''.join(bytes([9,0x90,n,96]) for n in range(16))+b''.join(bytes([8,0x80,n,0]) for n in range(16))+b'\x0F\xFC\0\0'
        self.assertEqual(self.stream(),expected)

    def test_native_64_off_burst_after_reconnect_keeps_exact_stream(self):
        for mode in (0,1):
            self.setUp();self.usb();self.u.mem_write(base.seq.SEQ_STATE_ADDR+4,bytes([mode]))
            for note in range(64):self.out.note(0,note);self.out.poll();self.tx.bus()
            for note in range(64):self.out.send(0,[0x80,note,0])
            self.out.send(0,[0xFC,0,0]);self.tx.disconnect_before_flush(no_credit=True)
            self.out.poll();self.assertEqual(self.tx.main()[0],64)
            self.tx.reconnect();self.pump()
            expected=b''.join(bytes([9,0x90,n,96]) for n in range(64))+b''.join(bytes([8,0x80,n,0]) for n in range(64))+b'\x0F\xFC\0\0'
            self.assertEqual(self.stream(),expected)

    def test_nested_flush_and_poll_cannot_reuse_staged_reader(self):
        self.usb();self.on();self.out.note(0,48,0,on=False)
        driver=self.out.drivers[0]
        _,_,_,ip=fixed.arm_code()
        injected,results=self.tx.reset.inject_once(0x08026880,[(fixed.USB_FLUSH,(driver,)),(ip['ip_poll'],(self.out.ports[0],))])
        self.out.poll();self.tx.bus();self.pump()
        self.assertEqual(len(injected),1);self.assertEqual(results()[0],0)
        self.assertEqual(self.stream(),b'\x09\x90\x30\x60\x08\x80\x30\0')
        self.assertEqual(self.u.mem_read(self.entry(0)+fixed.FLUSH_BUSY,1),b'\0')

    def test_irq_and_masked_flush_leave_main_untouched(self):
        self.usb();self.stage();before=self.tx.main()
        for mask,irq in ((1,0),(0,16)):
            self.u.reg_write(base.UC_ARM_REG_PRIMASK,mask);self.u.reg_write(base.UC_ARM_REG_IPSR,irq)
            try:
                self.assertEqual(self.call(fixed.USB_FLUSH,self.out.drivers[0]),0)
                self.assertEqual(self.u.reg_read(base.UC_ARM_REG_PRIMASK),mask)
                self.assertEqual(self.u.reg_read(base.UC_ARM_REG_IPSR),irq)
            finally:self.u.reg_write(base.UC_ARM_REG_PRIMASK,0);self.u.reg_write(base.UC_ARM_REG_IPSR,0)
            self.assertEqual(self.tx.main(),before)
        self.pump();self.assertEqual(self.stream(),b'\x08\x80\x30\0')

    def test_foreign_usb_driver_keeps_native_flush(self):
        self.usb();driver=0x20009200
        self.call(0x0802B408,driver,self.tx.native.usb_raw,0)
        self.u.mem_write(0x20009000,b'\x08\x80\x30\0')
        self.assertEqual(self.call(0x0802B460,driver,0x20009000),1)
        self.call(fixed.USB_FLUSH,driver);self.tx.bus()
        self.assertEqual(self.u.mem_read(self.read(driver+8),2),b'\0\0')
        self.assertEqual(self.stream(),b'\x08\x80\x30\0')

    def test_native_no_credit_from_other_caller_keeps_original_frame_contract(self):
        self.usb();self.u.mem_write(self.tx.native.usb_endpoint+0x1C,b'\0')
        self.call(0x08026880,self.tx.native.usb_endpoint,0x20009000,4)
        self.assertEqual(self.tx.native.usb_submissions,[])
        self.assertEqual(self.u.mem_read(self.tx.native.usb_endpoint+0x1C,1),b'\0')

    def test_native_alt_selection_keeps_original_flush_and_is_not_preflushed(self):
        self.usb();driver=self.out.drivers[0];command,payload=0x20009020,0x20009040
        self.u.mem_write(command,b'\0'*4+payload.to_bytes(4,'little')+(8).to_bytes(4,'little'))
        self.assertEqual(self.call(0x0802B4E2,driver,command),0)
        self.u.mem_write(command,b'\x02');self.assertEqual(self.call(0x0802B4E2,driver,command),0)
        self.stage();alt=self.read(driver+12);self.assertEqual(self.u.mem_read(alt,2),b'\x04\0')
        _,_,_,ip=fixed.arm_code();self.call(ip['ip_usb_preflush'],self.out.ports[0])
        self.assertEqual(self.tx.native.usb_submissions,[]);self.assertEqual(self.u.mem_read(alt,2),b'\x04\0')
        self.call(fixed.USB_FLUSH,driver);self.tx.bus()
        self.assertEqual(self.u.mem_read(alt,2),b'\0\0');self.assertEqual(self.stream(),b'\x08\x80\x30\0')

    def test_partial_borrowed_sysex_continues_without_cursor_rewind(self):
        self.usb();body=b'\xF0'+bytes(n%128 for n in range(148))+b'\xF7'
        descriptor,payload=0x20009400,0x20009500;self.word(descriptor,payload);self.word(descriptor+4,len(body));self.u.mem_write(payload,body)
        port=self.out.ports[0];self.assertEqual(self.call(self.read(self.read(port)+12),port,descriptor),1)
        self.tx.disconnect_before_flush(no_credit=True);self.out.poll()
        cursor=int.from_bytes(self.u.mem_read(self.read(port+0x10),2),'little')
        self.assertEqual(cursor,48);self.assertEqual(self.tx.main()[0],64)
        self.tx.reconnect();self.assertEqual(int.from_bytes(self.u.mem_read(self.read(port+0x10),2),'little'),48)
        self.pump();expected=b''.join(bytes([4 if n<147 else 7])+body[n:n+3] for n in range(0,150,3))
        self.assertEqual(self.stream(),expected);self.assertEqual(self.u.mem_read(payload,len(body)),body)

    def test_accepted_tx_cancellation_replays_closing_events_after_barrier(self):
        self.usb();self.on();self.out.note(0,48,0,on=False);self.out.send(0,[0xFC,0,0]);self.out.poll()
        self.assertIsNotNone(self.tx.native.in_flight);self.assertEqual(self.tx.main()[0],0)
        self.u.mem_write(self.tx.native.usb_controller+0x274,b'\0')
        self.call(0x0805261C,self.tx.wrapper,self.tx.native.usb_controller,0)
        self.assertEqual(self.tx.cancelled,[b'\x08\x80\x30\0\x0F\xFC\0\0'])
        self.tx.reconnect();self.pump();self.assertEqual(self.stream(),b'\x09\x90\x30\x60\x08\x80\x30\0\x0F\xFC\0\0')


if __name__=='__main__':unittest.main()
