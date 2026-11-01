"""Synthetic receiver ABI and failed-Load quarantine;not native boot proof."""
import unittest
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import *
import test_phase1_safety as base
import midi_recovery_patch as fixed
import project_load_recovery_patch as guard
from patch_firmware import apply_patches
from shared_project_test_support import SharedModeFixture


class ProjectLoadGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.image=apply_patches(base.load_image(),fixed.build_patches())[0]
        cls.labels=fixed.seq_code()[1]
        cls.g=guard.arm_code(cls.labels['c_seq_state'],fixed.STATE_BASE)[1]
    setUp=base.SafetyTests.setUp
    word=base.SafetyTests.word
    read=base.SafetyTests.read
    call=base.SafetyTests.call
    store=base.SafetyTests.store

    def fixture(self,other=False):
        self.bridge,self.cb,self.header,self.raw=0x20001000,0x2000110C,0x20001200,0x20002000
        self.word(self.bridge,self.cb);self.word(self.cb,guard.PROJECT_LOAD_VTABLE)
        self.word(self.cb+8,self.raw);self.word(self.header,2)
        self.word(0x20040004,self.bridge)
        self.calls=[]
        for pc in (guard.NATIVE_CLOSE,0x08037E3C,0x0800EF00):
            self.u.mem_write(pc,bytes.fromhex('7047'))
            self.u.hook_add(UC_HOOK_CODE,lambda u,a,n,d:self.calls.append((a,[u.reg_read(r) for r in base.REGS],u.reg_read(UC_ARM_REG_SP))),begin=pc,end=pc)
        if other:
            self.word(self.cb,0x20001300);self.word(0x20001300,0x0800EF01)

    def test_read_errors_skip_apply_retire_callback_queue_close_and_latch_taint(self):
        for status in (2,4,5):
            with self.subTest(status=status):
                self.setUp();self.fixture()
                self.call(guard.SITE,self.header,0,status,self.raw)
                self.assertEqual(self.read(self.bridge),0)
                self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR+base.seq.OFF_PROJECT_TAINTED,1),b'\1')
                self.assertEqual([(x[0],x[1][:3]) for x in self.calls],[(guard.NATIVE_CLOSE,[self.header,self.g['close_done']|1,1])])
                self.assertTrue(all(x[2]%8==0 for x in self.calls))
                self.assertEqual(self.u.reg_read(UC_ARM_REG_PRIMASK),0)

    def test_complete_read_and_other_receiver_preserve_native_callback(self):
        for other,status in ((False,0),(True,4)):
            with self.subTest(other=other,status=status):
                self.setUp();self.fixture(other)
                self.call(guard.SITE,self.header,0,status,self.raw)
                self.assertEqual([x[0] for x in self.calls],[0x0800EF00 if other else 0x08037E3C])
                self.assertEqual(self.read(self.bridge),0)
                self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR+base.seq.OFF_PROJECT_TAINTED,1),b'\0')

    def test_real_error_taint_rejects_both_mode_directions_even_if_phase_is_idle(self):
        for mode in (0,1):
            with self.subTest(mode=mode):
                self.setUp();self.fixture();f=SharedModeFixture(self)
                self.u.mem_write(base.seq.SEQ_STATE_ADDR+4,bytes([mode]))
                self.call(guard.SITE,self.header,0,4,self.raw)
                before=bytes(self.u.mem_read(self.raw,32));f.press()
                self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR+4,1),bytes([mode]))
                self.assertEqual(bytes(self.u.mem_read(self.raw,32)),before)
                self.assertEqual(f.h.read(f.phase+0x44),0)


if __name__=='__main__':unittest.main()
