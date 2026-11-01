"""Synthetic native player flush ABI,context/registration gates and faults."""
import unittest
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import *
import test_phase1_safety as base
import midi_recovery_patch as fixed
import midi_recovery_prototype as core
import midi_dense_stop_patch as dense
from integrated_midi_test_support import IntegratedMidiFixture
from patch_firmware import apply_patches


class DenseStopPatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.image=apply_patches(base.load_image(),fixed.build_patches())[0];cls.labels=fixed.seq_code()[1]
    setUp=base.SafetyTests.setUp
    word=base.SafetyTests.word
    read=base.SafetyTests.read
    call=base.SafetyTests.call
    instruction_budget=500000
    def fixture(self):
        self.out=IntegratedMidiFixture(self);self.player=0x20004000
        self.word(self.player,0x08068D24);self.u.mem_write(self.player+0x8A,b'\xff')
        self.polls=[]
        self.u.hook_add(UC_HOOK_CODE,lambda u,a,n,d:self.polls.append((u.reg_read(UC_ARM_REG_R0),u.reg_read(UC_ARM_REG_SP))),begin=dense.NATIVE_POLL,end=dense.NATIVE_POLL)
    def flush(self):return self.call(0x080552F6,self.player)

    def test_native_flush_services_ready_registered_router_once_and_preserves_abi(self):
        self.fixture();self.out.note(0,48)
        self.assertEqual(self.flush(),0)
        self.assertEqual(len(self.polls),1);self.assertEqual(self.polls[0][0],self.out.router)
        self.assertEqual(self.polls[0][1]%8,0)
        self.assertEqual(self.out.delivered,[[bytes((9,0x90,48,96))]]*3)
        self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR+base.seq.OFF_MIDI_TX_FAULT,1),b'\0')

    def test_masked_and_irq_flushes_do_not_service_output(self):
        for mask,priority,exception in ((1,0,0),(0,0x40,0),(0,0,66)):
            with self.subTest(mask=mask,priority=priority,exception=exception):
                self.setUp();self.fixture()
                self.u.reg_write(UC_ARM_REG_PRIMASK,mask);self.u.reg_write(UC_ARM_REG_BASEPRI,priority)
                self.u.reg_write(UC_ARM_REG_XPSR,0x01000000|exception)
                self.assertEqual(self.flush(),0);self.assertFalse(self.polls)
                self.assertEqual(self.u.reg_read(UC_ARM_REG_PRIMASK),mask)
                self.assertEqual(self.u.reg_read(UC_ARM_REG_BASEPRI),priority)
                self.assertEqual(self.u.reg_read(UC_ARM_REG_IPSR),exception)

    def test_other_virtual_flush_keeps_original_call_and_skips_service(self):
        self.fixture();vt=0x20004100;self.word(self.player,vt);self.word(vt+12,0x0800EB0D)
        seen=[];self.u.hook_add(UC_HOOK_CODE,lambda u,a,n,d:seen.append(u.reg_read(UC_ARM_REG_R0)),begin=0x0800EB0C,end=0x0800EB0C)
        self.assertEqual(self.flush(),0);self.assertEqual(seen,[self.player]);self.assertFalse(self.polls)

    def test_invalid_or_unregistered_router_skips_service_without_dereferencing_it(self):
        for case in ('null','unaligned','high','magic','count','list','port'):
            with self.subTest(case=case):
                self.setUp();self.fixture()
                if case in ('null','unaligned','high'):self.word(dense.GLOBAL_ROUTER,{'null':0,'unaligned':self.out.router+1,'high':0xFFFFFFFF}[case])
                if case=='magic':self.word(fixed.STATE_BASE,0)
                if case=='count':self.u.mem_write(self.out.router+0x18,b'\x04')
                if case=='list':self.word(self.out.router+0x14,0xFFFFFFFF)
                if case=='port':self.word(fixed.STATE_BASE+core.HEADER_SIZE+core.ENTRY_SIZE,0)
                self.assertEqual(self.flush(),0);self.assertFalse(self.polls)

    def test_service_never_clears_real_overflow_quarantine(self):
        self.fixture()
        for _ in range(64):self.out.send(1,[0xF8,0,0])
        self.out.send(1,[0x80,48,0]);self.out.send(1,[0xFC,0,0])
        self.flush()
        for _ in range(64):self.out.poll()
        entry=fixed.STATE_BASE+core.HEADER_SIZE+core.ENTRY_SIZE
        self.assertEqual(self.u.mem_read(entry+core.FLAGS,1),bytes((core.FAULT,)))
        self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR+base.seq.OFF_MIDI_TX_FAULT,1),b'\1')
        self.assertEqual(self.out.send(1,[0x90,49,96]),0)
        self.assertEqual(self.out.delivered[1][-1],bytes((15,0xFC,0,0)))


if __name__=='__main__':unittest.main()
