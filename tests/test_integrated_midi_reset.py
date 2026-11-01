"""Integrated native MIDI class-parent clear guard;no USB reset overlay."""
import unittest
import test_integrated_midi_recovery as prior
import midi_recovery_patch as fixed
import midi_recovery_prototype as core
from integrated_reset_test_support import IntegratedResetFixture
from native_midi_driver_test_support import NativeMidiDriverFixture
base=prior.base


class IntegratedResetTests(unittest.TestCase):
    setUpClass=classmethod(prior.IntegratedRecoveryTests.setUpClass.__func__)
    instruction_budget=500000
    for name in ('setUp','word','read','store','call','output','entry','settle'):
        locals()[name]=getattr(prior.IntegratedRecoveryTests,name)
    def setup_reset(self):self.output();self.reset=IntegratedResetFixture(self,self.out)

    def test_native_parent_preserves_64_queued_closures_in_both_modes(self):
        for mode in (0,1):
            self.setUp();self.setup_reset();self.u.mem_write(base.seq.SEQ_STATE_ADDR+4,bytes([mode]))
            for note in range(64):
                for port in range(3):self.out.send(port,[0x90,note,96])
            self.out.poll()
            for port in range(3):
                for note in range(64):self.out.send(port,[0x80,note,0])
                self.out.send(port,[0xFC,0,0])
            before=self.reset.snapshot();state=bytes(self.u.mem_read(fixed.STATE_BASE,832))
            self.assertEqual(self.reset.parent(),0);self.assertEqual(self.reset.snapshot(),before)
            self.assertEqual(self.u.mem_read(fixed.STATE_BASE,832),state)
            self.assertEqual(self.reset.events,['parent','rx_rearm']);self.settle();self.reset.check_rx()
            for messages in self.out.delivered:
                self.assertEqual(sum(m[0]==8 for m in messages),64);self.assertEqual(messages[-1],b'\x0F\xFC\0\0')

    def test_native_parent_keeps_healthy_on_off_order_without_new_quarantine(self):
        self.setup_reset();self.out.note(0,48);self.out.note(0,48,0,on=False)
        before=self.reset.snapshot();self.assertEqual(self.reset.parent(),0);self.assertEqual(self.reset.snapshot(),before)
        self.out.poll();self.assertEqual(self.out.delivered,[[b'\x09\x90\x30\x60',b'\x08\x80\x30\0']]*3)
        self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR+base.seq.OFF_MIDI_TX_FAULT,1),b'\0')

    def test_native_parent_is_read_only_in_irq_and_masked_contexts(self):
        for mask in (0,1):
            self.setUp();self.setup_reset();self.out.note(0,48);self.out.poll();self.out.note(0,48,0,on=False)
            before=self.reset.snapshot();state=bytes(self.u.mem_read(fixed.STATE_BASE,832))
            self.u.reg_write(base.UC_ARM_REG_IPSR,16);self.u.reg_write(base.UC_ARM_REG_PRIMASK,mask)
            try:
                self.assertEqual(self.reset.parent(),0)
                self.assertEqual(self.u.reg_read(base.UC_ARM_REG_PRIMASK),mask)
                self.assertEqual(self.u.reg_read(base.UC_ARM_REG_IPSR),16)
            finally:
                self.u.reg_write(base.UC_ARM_REG_IPSR,0);self.u.reg_write(base.UC_ARM_REG_PRIMASK,0)
            self.assertEqual(self.reset.snapshot(),before);self.assertEqual(self.u.mem_read(fixed.STATE_BASE,832),state)
            self.assertEqual(self.reset.events,['parent','rx_rearm'])

    def test_parent_nested_inside_native_output_worker_does_not_erase_reader(self):
        self.setup_reset();self.out.note(0,48);self.out.poll();self.out.note(0,48,0,on=False)
        observed=[]
        def busy(u,p,n,d):
            if u.reg_read(base.UC_ARM_REG_R0)==self.out.ports[0]:observed.append(u.mem_read(self.entry(0)+core.BUSY,1)[0])
        self.u.hook_add(base.UC_HOOK_CODE,busy,begin=0x080403A2,end=0x080403A2)
        injected,results=self.reset.inject_once(0x080403A2,[(self.reset.PARENT,())])
        self.out.poll();self.assertEqual(len(injected),1);self.assertEqual(results(),[0]);self.assertEqual(set(observed),{1})
        self.assertEqual(self.reset.events,['parent','rx_rearm'])
        for messages in self.out.delivered:self.assertEqual(messages.count(b'\x08\x80\x30\0'),1)

    def test_parent_keeps_borrowed_sysex_pointer_cursor_and_payload(self):
        self.setup_reset();descriptor,payload=0x20005000,0x20005010
        body=b'\xF0'+bytes(range(58))+b'\xF7';self.word(descriptor,payload);self.word(descriptor+4,len(body));self.u.mem_write(payload,body)
        self.u.mem_write(self.out.drivers[0]+5,b'\x01');port=self.out.ports[0]
        self.assertEqual(self.call(self.read(self.read(port)+12),port,descriptor),1)
        before=bytes(self.u.mem_read(port+8,12));counter=self.read(port+0x10);cursor=bytes(self.u.mem_read(counter,4))
        self.assertEqual(self.reset.parent(),0)
        self.assertEqual(self.u.mem_read(port+8,12),before);self.assertEqual(self.u.mem_read(counter,4),cursor)
        self.assertEqual(self.u.mem_read(payload,len(body)),body)
        self.u.mem_write(self.out.drivers[0]+5,b'\0');self.settle()
        self.assertEqual(sum(m[0] in (4,5,6,7) for m in self.out.delivered[0]),20)

    def test_standalone_router_clear_keeps_stock_semantics(self):
        self.setup_reset();self.out.note(0,48);self.out.note(0,48,0,on=False)
        self.call(0x080297C0,self.out.router) # native void function has no R0 result contract
        self.assertEqual([self.out.pending(n) for n in range(3)],[0]*3)
        self.assertEqual(self.reset.events.count('port_clear'),3)

    def test_wrong_caller_cannot_use_parent_preservation_gate(self):
        self.setup_reset();_,_,_,ip=fixed.arm_code();self.out.note(0,48)
        self.call(ip['ip_parent_clear'],self.out.router)
        self.assertEqual([self.out.pending(n) for n in range(3)],[0]*3)
        self.assertEqual(self.reset.events.count('port_clear'),3)

    def test_mismatched_registry_uses_original_clear(self):
        self.setup_reset();self.out.note(0,48);self.word(self.entry(2),0)
        self.assertEqual(self.reset.parent(),0)
        self.assertEqual([self.out.pending(n) for n in range(3)],[0]*3)
        self.assertEqual(self.reset.events,['parent','router_clear','port_clear','port_clear','port_clear','rx_rearm'])

    def test_parent_during_native_usb_tx_keeps_buffer_and_exact_closing_stream(self):
        for mode in (0,1):
            self.setUp();self.output();native=NativeMidiDriverFixture(self,self.out);self.reset=IntegratedResetFixture(self,self.out)
            self.u.mem_write(base.seq.SEQ_STATE_ADDR+4,bytes([mode]));din=[bytearray(),bytearray()]
            def bus():
                if native.in_flight is not None:native.release_usb_endpoint()
                for n in range(2):din[n].extend(native.drain_uart(n))
            for note in range(64):self.out.note(0,note);self.out.poll();bus()
            for port in range(3):
                for note in range(64):self.out.send(port,[0x80,note,0])
                self.out.send(port,[0xFC,0,0])
            self.out.poll();self.assertIsNotNone(native.in_flight)
            job=native.in_flight;data=bytes(self.u.mem_read(*job));state=bytes(self.u.mem_read(fixed.STATE_BASE,832))
            self.assertEqual(self.reset.parent(),0);self.assertEqual(native.in_flight,job)
            self.assertEqual(self.u.mem_read(*job),data);self.assertEqual(self.u.mem_read(fixed.STATE_BASE,832),state)
            bus()
            for _ in range(128):self.out.poll();bus()
            expected_usb=b''.join(bytes([9,0x90,n,96]) for n in range(64))+b''.join(bytes([8,0x80,n,0]) for n in range(64))+b'\x0F\xFC\0\0'
            expected_din=b'\x90'+b''.join(bytes([n,96]) for n in range(64))+b'\x80'+b''.join(bytes([n,0]) for n in range(64))+b'\xFC'
            self.assertEqual(b''.join(native.usb_completed),expected_usb);self.assertEqual([bytes(b) for b in din],[expected_din]*2)
            self.assertEqual(self.reset.events,['parent','rx_rearm'])


if __name__=='__main__':unittest.main()
