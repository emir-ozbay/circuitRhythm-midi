"""Synthetic register/RAM sentinels over native M4F PendSV and IRQ bodies."""
import struct,unittest
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import *
import test_phase1_safety as base
import midi_recovery_patch as fixed
from patch_firmware import apply_patches
from recovery_fpu_test_support import FPUStartup,FP_REGS,FPCCR,FPCAR,CPACR,UnsupportedFPContext
from recovery_worker_test_support import BasicFrameOnly,SAVED_REGS


class RecoveryFPUTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stock=base.load_image();cls.image=apply_patches(cls.stock,fixed.build_patches())[0]
        cls.labels=fixed.seq_code()[1]

    def boot(self):return FPUStartup(self.image,peer_policy='ready').main_setup().start_tasks()

    def fp_bank(self,h,tag):
        # Native VMRS/VMSR setup exercises CP10/11 and sets FPCA in Unicorn.
        u=h.u;pc,lr=u.reg_read(UC_ARM_REG_PC),u.reg_read(UC_ARM_REG_LR)
        result=h.call(0x08068C2C)
        self.assertIsNone(result['error'])
        u.reg_write(UC_ARM_REG_PC,pc|1);u.reg_write(UC_ARM_REG_LR,lr)
        values=tuple((tag<<24)|(i*0x10203+1) for i in range(32))
        for r,v in zip(FP_REGS,values):u.reg_write(r,v)
        u.reg_write(UC_ARM_REG_FPSCR,0xA0000000|(tag&3)<<22)
        self.assertTrue(u.reg_read(UC_ARM_REG_CONTROL)&4)
        return values+(u.reg_read(UC_ARM_REG_FPSCR),)

    def test_three_native_task_contexts_keep_all_fp_bits_and_fpscr(self):
        h=self.boot();banks={};integer={};seen=[]
        for i in range(15):
            task=h.running_tcb;seen.append(task)
            if len(banks)<3 and task not in banks:
                banks[task]=self.fp_bank(h,len(banks)+1)
                integer[task]=tuple(0xA0000000|(len(banks)<<16)|i for i in range(8))
                for r,value in zip(SAVED_REGS,integer[task]):h.u.reg_write(r,value)
            if task in banks:self.assertEqual(tuple(h.u.reg_read(r) for r in FP_REGS)+(h.u.reg_read(UC_ARM_REG_FPSCR),),banks[task])
            if task in integer:self.assertEqual(tuple(h.u.reg_read(r) for r in SAVED_REGS),integer[task])
            h.reason='pendsv';h._switch(h.u.reg_read(UC_ARM_REG_PC))
        self.assertEqual(len(banks),3)
        self.assertTrue(any(s['outgoing_extended'] and not s['incoming_extended'] for s in h.switches))
        self.assertTrue(any(not s['outgoing_extended'] and s['incoming_extended'] for s in h.switches))
        self.assertTrue(any(s['outgoing_extended'] and s['incoming_extended'] for s in h.switches))
        self.assertTrue(all(s['materialized'] for s in h.switches if s['outgoing_extended']))
        self.assertTrue(h.validate_stacks());self.assertFalse(h.invalid)
        self.assertEqual(bytes(h.u.mem_read(0x08010000,len(self.image))),self.image)

    def test_lazy_irq_without_fp_leaves_reserved_low_words_unwritten(self):
        h=self.boot();bank=self.fp_bank(h,1);sp=h.u.reg_read(UC_ARM_REG_PSP)
        address=(sp-104)&~7;before=bytes(h.u.mem_read(address+32,72))
        event=h._irq_call(0x08066BD0,15)
        self.assertTrue(event['extended'] and event['lazy']);self.assertFalse(event['materialized'])
        self.assertEqual(bytes(h.u.mem_read(address+32,72)),before)
        self.assertEqual(h.u.reg_read(UC_ARM_REG_PSP),sp)
        self.assertEqual(tuple(h.u.reg_read(r) for r in FP_REGS)+(h.u.reg_read(UC_ARM_REG_FPSCR),),bank)
        self.assertFalse(h.read(FPCCR)&1);self.assertIsNone(h.lazy_frame)

    def test_basic_irq_keeps_fp_inactive_and_psp_thumb_state(self):
        h=self.boot();u=h.u;sp=u.reg_read(UC_ARM_REG_PSP)
        event=h._irq_call(0x08066BD0,15)
        self.assertFalse(event['extended'] or event['lazy'] or event['materialized'])
        self.assertEqual(u.reg_read(UC_ARM_REG_PSP),sp)
        self.assertEqual(u.reg_read(UC_ARM_REG_CONTROL),2)
        self.assertTrue(u.reg_read(UC_ARM_REG_XPSR)&0x01000000)
        self.assertFalse(h.read(FPCCR)&1)

    def test_fp_using_irq_materializes_before_clobber_and_unstacks_low_bank(self):
        h=self.boot();bank=self.fp_bank(h,2);u=h.u
        # Synthetic executable RAM, not a replacement for firmware bytes:
        # native VMOV S0,R0 encoding followed by BX LR. ISR clobbers S0.
        ram=0x2004E000;u.mem_write(ram,self.image[0x2C090:0x2C094]+bytes.fromhex('7047'))
        u.reg_write(UC_ARM_REG_R0,0xDEADBEEF)
        event=h._irq_call(ram,15)
        self.assertTrue(event['materialized'])
        self.assertEqual(struct.unpack('<17I',u.mem_read(event['frame_sp']+32,68)),bank[:16]+(bank[32],))
        self.assertEqual(tuple(u.reg_read(r) for r in FP_REGS)+(u.reg_read(UC_ARM_REG_FPSCR),),bank)
        self.assertEqual(u.reg_read(UC_ARM_REG_R0),0xDEADBEEF)

    def test_eager_frame_and_four_byte_alignment_restore_original_psp(self):
        h=self.boot();self.fp_bank(h,1);u=h.u
        h.word(FPCCR,h.read(FPCCR)&~0x40000000)
        sp=((u.reg_read(UC_ARM_REG_PSP)-128)&~7)+4;u.reg_write(UC_ARM_REG_PSP,sp)
        event=h._irq_call(0x08066BD0,15)
        self.assertTrue(event['extended'] and event['materialized']);self.assertFalse(event['lazy'])
        self.assertEqual(event['frame_sp']+108,sp)
        self.assertTrue(h.read(event['frame_sp']+28)&512)
        self.assertEqual(u.reg_read(UC_ARM_REG_PSP),sp)

    def test_invalid_config_nested_owner_and_stack_overflow_fail_before_writes(self):
        h=self.boot();self.fp_bank(h,1);u=h.u
        for address,value in ((CPACR,0),(FPCCR,0x40000000),(FPCCR,0xC0000001)):
            old=h.read(address);h.word(address,value)
            ram=bytes(u.mem_read(0x20000000,0x50000))
            with self.assertRaises(UnsupportedFPContext):h._make_frame(u.reg_read(UC_ARM_REG_PC),u.reg_read(UC_ARM_REG_PSP))
            self.assertEqual(bytes(u.mem_read(0x20000000,0x50000)),ram)
            h.word(address,old)
        ram=bytes(u.mem_read(0x20000000,0x50000))
        with self.assertRaises(AssertionError):h._make_frame(u.reg_read(UC_ARM_REG_PC),h.task_by_tcb[h.running_tcb]['stack']+80,reserve_software=True)
        self.assertEqual(bytes(u.mem_read(0x20000000,0x50000)),ram)

    def test_corrupted_native_saved_high_bank_is_detected(self):
        h=self.boot();self.fp_bank(h,3)
        def corrupt(u,pc,size,_):
            if pc==0x08025C26 and h.in_service:
                address=u.reg_read(UC_ARM_REG_R0)
                u.mem_write(address,b'\xFF\xFF\xFF\xFF')
        h.u.hook_add(UC_HOOK_CODE,corrupt,begin=0x08025C26,end=0x08025C26)
        h.reason='pendsv'
        with self.assertRaises(AssertionError):h._switch(h.u.reg_read(UC_ARM_REG_PC))

    def test_unknown_coprocessor_is_not_admitted_by_fp_extension(self):
        h=self.boot();ram=0x2004E000
        h.u.mem_write(ram,bytes.fromhex('10ee100f7047'))  # MRC p15
        with self.assertRaises(BasicFrameOnly):h.call(ram)


if __name__=='__main__':unittest.main()
