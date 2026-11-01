"""Production-profile Off/Stop firmware integration;no recovery overlays."""
import struct,unittest
import test_phase1_safety as base
import midi_recovery_patch as fixed
import midi_recovery_prototype as core
from integrated_midi_test_support import IntegratedMidiFixture
from patch_firmware import apply_patches,unpack_syx


class IntegratedRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.image=apply_patches(base.load_image(),fixed.build_patches())[0]
        cls.labels=fixed.seq_code()[1]
    instruction_budget=500000
    setUp=base.SafetyTests.setUp
    word=base.SafetyTests.word
    read=base.SafetyTests.read
    store=base.SafetyTests.store
    call=base.SafetyTests.call
    def output(self):self.out=IntegratedMidiFixture(self)
    def entry(self,n):return fixed.STATE_BASE+core.HEADER_SIZE+n*core.ENTRY_SIZE
    def settle(self):
        for n in range(128):self.out.poll()
        for n in range(3):
            self.assertEqual(self.out.pending(n),0)
            self.assertEqual(self.u.mem_read(self.entry(n)+core.COUNT,2),b'\0\0')
            self.assertEqual(self.u.mem_read(self.entry(n)+core.BUSY,1),b'\0')
            self.assertEqual(self.u.mem_read(self.entry(n)+core.FLAGS,1)[0]&core.STOP_PENDING,0)

    def test_actual_boot_router_registers_exactly_three_native_heap_ports(self):
        self.output();_,_,_,ip=fixed.arm_code()
        self.assertEqual(self.read(base.seq.HEAP_LIMIT_PTR),fixed.STATE_BASE)
        self.assertEqual(self.read(fixed.STATE_BASE),core.MAGIC)
        self.assertEqual([self.read(self.entry(n)) for n in range(3)],self.out.ports)
        for port in self.out.ports:
            self.assertTrue(0x2004EA98<=port<fixed.STATE_BASE-24)
            self.assertEqual(self.read(port),fixed.VTABLE)
            self.assertEqual(self.read(self.read(port)+8),ip['ip_send']|1)
        self.assertLessEqual(self.read(base.seq.HEAP_CUR_PTR),fixed.STATE_BASE)
        self.assertEqual(self.read(base.seq.SEQ_STATE_ADDR),base.seq.SEQ_STATE_MAGIC)

    def test_extra_reservation_initializes_both_states_and_restores_primask(self):
        for mask in (0,1):
            self.word(base.seq.HEAP_LIMIT_PTR,base.seq.HEAP_LIMIT);self.word(base.seq.HEAP_CUR_PTR,0x2004EA98)
            self.u.mem_write(fixed.STATE_BASE,b'\xA5'*1088);self.u.reg_write(base.UC_ARM_REG_PRIMASK,mask)
            self.assertEqual(self.call(self.labels['c_seq_state']),base.seq.SEQ_STATE_ADDR)
            self.assertEqual(self.u.reg_read(base.UC_ARM_REG_PRIMASK),mask)
            self.assertEqual(self.read(base.seq.HEAP_LIMIT_PTR),fixed.STATE_BASE)
            self.assertEqual(self.read(fixed.STATE_BASE),core.MAGIC)
            self.assertEqual(self.u.mem_read(fixed.STATE_BASE+4,828),bytes(828))
        self.u.reg_write(base.UC_ARM_REG_PRIMASK,0)

    def test_reservation_refuses_overlap_without_touching_existing_heap(self):
        self.word(base.seq.HEAP_LIMIT_PTR,base.seq.HEAP_LIMIT);self.word(base.seq.HEAP_CUR_PTR,fixed.STATE_BASE+4)
        self.u.mem_write(fixed.STATE_BASE,b'\xA5'*1088)
        self.assertEqual(self.call(self.labels['c_seq_state']),0)
        self.assertEqual(self.read(base.seq.HEAP_LIMIT_PTR),base.seq.HEAP_LIMIT)
        self.assertEqual(self.u.mem_read(fixed.STATE_BASE,1088),b'\xA5'*1088)

    def test_allocator_never_crosses_reserved_recovery_state(self):
        before=bytes(self.u.mem_read(fixed.STATE_BASE,1088));self.word(base.seq.HEAP_CUR_PTR,fixed.STATE_BASE-4)
        self.assertEqual(self.call(base.seq.STOCK_ALLOCATOR_ADDR,4),fixed.STATE_BASE-4)
        self.u.reg_write(base.UC_ARM_REG_LR,base.STOP|1)
        self.u.reg_write(base.UC_ARM_REG_R0,1)
        self.u.emu_start(base.seq.STOCK_ALLOCATOR_ADDR|1,base.STOP,count=10000)
        self.assertEqual(self.u.reg_read(base.UC_ARM_REG_PC),self.labels['alloc_fatal'])
        self.assertEqual(self.u.reg_read(base.UC_ARM_REG_PRIMASK),1)
        self.assertEqual(self.read(base.seq.HEAP_CUR_PTR),fixed.STATE_BASE)
        self.assertEqual(self.u.mem_read(fixed.STATE_BASE,1088),before)

    def test_healthy_short_messages_keep_exact_native_bytes_in_both_modes(self):
        for mode in (0,1):
            self.setUp();self.output();self.u.mem_write(base.seq.SEQ_STATE_ADDR+4,bytes([mode]))
            self.out.note(0,48);self.out.note(0,48,0,on=False);self.out.poll()
            expected=[bytes([9,0x90,48,96]),bytes([8,0x80,48,0])]
            self.assertEqual(self.out.delivered,[expected]*3)
            self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR+base.seq.OFF_MIDI_TX_FAULT,1),b'\0')

    def test_full_fifo_stalled_driver_then_release_delivers_off_and_final_stop(self):
        self.output();self.out.note(0,48);self.out.poll()
        for driver in self.out.drivers:self.u.mem_write(driver+5,b'\x01')
        for n in range(3):
            for _ in range(64):self.assertEqual(self.out.send(n,[0xF8,0,0]),1)
            self.assertEqual(self.out.send(n,[0x80,48,0]),1)
            self.assertEqual(self.out.send(n,[0xFC,0,0]),1)
            self.assertEqual(self.out.send(n,[0x90,49,96]),0)
            self.assertEqual(self.u.mem_read(self.entry(n)+core.COUNT,2),b'\x01\0')
        for _ in range(8):self.out.poll()
        self.assertEqual([self.out.pending(n) for n in range(3)],[64]*3)
        for driver in self.out.drivers:self.u.mem_write(driver+5,b'\0')
        self.settle()
        for messages in self.out.delivered:
            self.assertEqual(messages.count(bytes([8,0x80,48,0])),1)
            self.assertEqual(messages[-1],bytes([15,0xFC,0,0]))
            self.assertEqual(messages.count(bytes([15,0xFC,0,0])),1)
        self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR+base.seq.OFF_MIDI_TX_FAULT,1),b'\x01')

    def test_not_ready_retains_queued_closures_until_driver_returns(self):
        self.output();self.out.note(0,48);self.out.poll();self.out.note(0,48,0,on=False)
        for driver in self.out.drivers:self.u.mem_write(driver+4,b'\0')
        before=[self.out.pending(n) for n in range(3)]
        for _ in range(4):self.out.poll()
        self.assertEqual([self.out.pending(n) for n in range(3)],before)
        for driver in self.out.drivers:self.u.mem_write(driver+4,b'\x01')
        self.settle()
        for messages in self.out.delivered:self.assertEqual(messages.count(bytes([8,0x80,48,0])),1)

    def test_duplicate_registration_does_not_reset_existing_closing_debt(self):
        self.output();_,_,_,ip=fixed.arm_code();port=self.out.ports[0]
        self.out.note(0,48);self.out.poll()
        for _ in range(64):self.out.send(0,[0xF8,0,0])
        self.out.send(0,[0x80,48,0]);before=bytes(self.u.mem_read(self.entry(0),core.ENTRY_SIZE))
        self.assertEqual(self.call(ip['ip_register'],port),1)
        self.assertEqual(self.u.mem_read(self.entry(0),core.ENTRY_SIZE),before)

    def test_fourth_port_is_unregistered_and_latches_admission_fault(self):
        self.output();port=0x20003100;self.call(fixed.CTOR,port,self.out.drivers[0],64)
        self.assertEqual([self.read(self.entry(n)) for n in range(3)],self.out.ports)
        self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR+base.seq.OFF_MIDI_TX_FAULT,1),b'\x01')
        self.u.mem_write(self.out.data,b'\x90\x30\x60')
        self.assertEqual(self.call(self.read(self.read(port)+8),port,self.out.data),0)

    def test_real_global_sysex_router_uses_integrated_owner_and_port_gates(self):
        self.output();descriptor,payload=0x20005000,0x20005010
        self.word(descriptor,payload);self.word(descriptor+4,6);self.u.mem_write(payload,b'\xF0\x00\x20\x29\x01\xF7')
        self.assertEqual(self.call(core.NATIVE_ROUTER,self.out.router,7,descriptor),0)
        self.assertEqual(self.read(fixed.STATE_BASE+core.ROUTER),self.out.router)
        self.settle()
        self.assertEqual(self.out.delivered,[[b'\x04\xF0\x00\x20',b'\x07\x29\x01\xF7']]*3)

    def test_fault_quarantine_blocks_port_sysex_before_borrowing(self):
        self.output();self.out.note(0,48);self.out.poll()
        for _ in range(64):self.out.send(0,[0xF8,0,0])
        self.out.send(0,[0x80,48,0]);port=self.out.ports[0]
        descriptor,payload=0x20005000,0x20005010
        self.word(descriptor,payload);self.word(descriptor+4,6);self.u.mem_write(payload,b'\xF0\x00\x20\x29\x01\xF7')
        before=bytes(self.u.mem_read(port+8,12))
        self.assertEqual(self.call(self.read(self.read(port)+12),port,descriptor),0)
        self.assertEqual(self.u.mem_read(port+8,12),before)


if __name__=='__main__':unittest.main()
