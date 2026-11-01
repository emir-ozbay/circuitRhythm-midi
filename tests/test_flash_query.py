"""Native disk_ioctl NULL CTRL_SYNC sink FAIL->PASS and unchanged normal ABI."""
import unittest
from unicorn.arm_const import *
from recovery_boot_test_support import NativeStartup,STOP
import test_phase1_safety as base
import midi_recovery_patch as fixed
import flash_query_patch as sync
from patch_firmware import apply_patches

SAVED=(UC_ARM_REG_R4,UC_ARM_REG_R5,UC_ARM_REG_R6,UC_ARM_REG_R7,
       UC_ARM_REG_R8,UC_ARM_REG_R9,UC_ARM_REG_R10,UC_ARM_REG_R11)


class FlashQueryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stock=base.load_image(); cls.image=apply_patches(cls.stock,fixed.build_patches())[0]
        cls.labels=fixed.seq_code()[1]

    def fixture(self,image):
        h=NativeStartup(image).startup()
        drive,physical,vt,part,out=0x20020000,0x20020100,0x20020200,0x20020300,0x20020400
        h.word(drive+4,physical);h.word(drive+8,part);h.u.mem_write(drive+12,b'\x00')
        h.word(physical,vt);h.word(vt+8,0x08041A81)
        for n,r in enumerate(SAVED):h.u.reg_write(r,0x44440000+n)
        return h,drive,part,out

    def invoke(self,image,command,sink_null=False,masked=0):
        h,drive,part,out=self.fixture(image)
        h.u.mem_write(out-4,b'\xa5'*12)
        sp=h.u.reg_read(UC_ARM_REG_SP);bank=[h.u.reg_read(r) for r in SAVED]
        h.u.reg_write(UC_ARM_REG_PRIMASK,masked)
        result=h.call(sync.SITE,drive,command,0 if sink_null else out)
        if result['error'] is None:
            self.assertEqual(result['pc'],STOP)
            self.assertEqual(h.u.reg_read(UC_ARM_REG_SP),sp)
            self.assertEqual([h.u.reg_read(r) for r in SAVED],bank)
            self.assertEqual(h.u.reg_read(UC_ARM_REG_PRIMASK),masked)
        return h,result,bytes(h.u.mem_read(out-4,12)),h.read(part+4)

    def test_native_null_sync_faults_in_stock_and_completes_with_stack_scratch(self):
        old,result,_,_=self.invoke(self.stock,0,True)
        self.assertIsNotNone(result['error'])
        self.assertEqual(result['pc'],0x08041AA2)
        self.assertEqual(old.invalid[-1]['address'],0)
        h,result,_,_=self.invoke(self.image,0,True)
        self.assertIsNone(result['error']);self.assertEqual(result['result'],0)
        self.assertFalse(h.invalid)

    def test_normal_queries_preserve_output_abi_flags_and_interrupt_mask(self):
        for command in (0,2,3,4):
            for masked in (0,1):
                with self.subTest(command=command,masked=masked):
                    old,a,adata,apart=self.invoke(self.stock,command,False,masked)
                    h,b,bdata,bpart=self.invoke(self.image,command,False,masked)
                    self.assertIsNone(a['error']);self.assertIsNone(b['error'])
                    self.assertEqual(a['result'],b['result']);self.assertEqual(adata,bdata)
                    self.assertEqual(apart,bpart)
                    self.assertEqual(old.u.reg_read(UC_ARM_REG_XPSR)&0xF0000000,
                                     h.u.reg_read(UC_ARM_REG_XPSR)&0xF0000000)

    def test_missing_required_query_buffer_still_fails(self):
        # Only CTRL_SYNC0 accepts NULL. GET_SECTOR_SIZE2 requires a word output.
        for image in (self.stock,self.image):
            h,result,_,_=self.invoke(image,2,True)
            self.assertIsNotNone(result['error']);self.assertEqual(h.invalid[-1]['address'],0)

    def test_patch_preserves_native_query_and_ioctl_body_and_uses_existing_frame(self):
        self.assertEqual(self.image[0x1316C:0x131D6],self.stock[0x1316C:0x131D6])
        self.assertEqual(self.image[0x31A80:0x31AC2],self.stock[0x31A80:0x31AC2])
        self.assertEqual(sync.EXPECTED,bytes.fromhex('f8b50d46'))
        self.assertEqual(len(sync.arm_code()),20)
        self.assertEqual(self.image[sync.CODE_BASE-0x08010000:sync.CODE_BASE-0x08010000+20],sync.arm_code())


if __name__=='__main__':unittest.main()
