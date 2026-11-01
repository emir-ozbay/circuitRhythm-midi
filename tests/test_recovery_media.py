"""Real FatFs/Storage/QSPI over synthetic NOR bytes and native sync scratch."""
import unittest
from unicorn import UcError
from unicorn.arm_const import UC_ARM_REG_PC
import test_phase1_safety as base
import midi_recovery_patch as fixed
from patch_firmware import apply_patches
from recovery_spi_test_support import UnmodeledSPIResponse,NativeMediaUnavailable
from recovery_media_test_support import MediaStartup,SparseNOR,MissingNORData,STREAM,QSPI,fat12_fixture
from recovery_input_test_support import MAIN_LOOP,MAIN_INPUT_READY


class RecoveryMediaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stock=base.load_image();cls.image=apply_patches(cls.stock,fixed.build_patches())[0]
        cls.labels=fixed.seq_code()[1]

    def boot(self,image=None,**options):
        h=MediaStartup(self.image if image is None else image,peer_policy='ready',**options)
        return h.main_setup().start_tasks().checkpoint().start_input().checkpoint(MAIN_INPUT_READY,budget=800000).start_spi()

    def data_boundary(self,h):
        with self.assertRaises(UnmodeledSPIResponse):h.checkpoint(MAIN_LOOP,budget=5000000)
        self.assertEqual(h.unmodeled_response['caller'],'0x803151a')
        self.assertEqual(h.memory_selector,0x37300)
        self.assertFalse(h.invalid)
        self.assertTrue(h.validate_stacks())

    def test_nor_program_requires_wel_page_bounds_and_erase_for_zero_to_one(self):
        n=SparseNOR()
        with self.assertRaises(AssertionError):n.program(0x1000,b'\x00')
        n.wel=True;n.program(0x1000,b'\x0f');self.assertFalse(n.wel)
        n.wel=True
        with self.assertRaises(AssertionError):n.program(0x1000,b'\xff')
        self.assertEqual(n.read(0x1000,1),b'\x0f')
        with self.assertRaises(AssertionError):n.program(0x10ff,b'\x00\x00')
        with self.assertRaises(AssertionError):n.erase(0x1001)
        n.erase(0x1000);self.assertEqual(n.read(0x1000,1),b'\xff')
        self.assertFalse(n.wel)
        with self.assertRaises(AssertionError):n.read(len(n.data),1)
        with self.assertRaises(AssertionError):n.read(-1,1)

    def test_missing_dma_data_is_rejected_before_completion_or_ram_update(self):
        h=MediaStartup(self.image,peer_policy='ready',data_enabled=False)
        with self.assertRaises(MissingNORData):
            h.main_setup().start_tasks().checkpoint()
        self.assertEqual(h.u.reg_read(UC_ARM_REG_PC),0x08041C2E)
        self.assertEqual(h.read(STREAM+4),23)
        self.assertTrue(h.read(STREAM)&1)
        self.assertEqual(h.qspi_dma_irqs,[])
        self.assertEqual(h.medium.mutations,[])
        self.assertFalse(h.read(QSPI+8)&2)
        self.assertFalse(h.invalid)

    def test_erased_medium_does_not_fabricate_native_media_ownership(self):
        h=self.boot(medium=SparseNOR())
        with self.assertRaises(NativeMediaUnavailable):h.checkpoint(MAIN_LOOP,budget=5000000)
        self.assertEqual(h.bindings,[])
        self.assertTrue(all(not m['ready'] for m in h.mounts))
        self.assertFalse(h.invalid)
        self.assertTrue(h.validate_stacks())

    def test_valid_fat12_binds_native_owner_and_syncs_without_null_access(self):
        h=self.boot();self.data_boundary(h)
        self.assertTrue(h.bindings)
        for b in h.bindings:self.assertEqual(h.read(b['owner']+0x3C),b['root'])
        self.assertTrue(any(m['ready']==1 for m in h.mounts))
        self.assertEqual(h.u.mem_read(0x20000AC0,1),b'\x01')
        self.assertTrue(h.scratch_uses)
        self.assertTrue(all(s['command']==0 and s['buffer_before']==0 for s in h.scratch_uses))
        self.assertTrue(h.medium.mutations)
        self.assertEqual(bytes(h.u.mem_read(0x08010000,len(self.image))),self.image)

    def test_prior_recovery_faults_on_real_null_sync_output(self):
        prior=apply_patches(self.stock,[p for p in fixed.build_patches() if not p.name.startswith('flash_sync_')])[0]
        h=self.boot(prior)
        with self.assertRaises(UcError):h.checkpoint(MAIN_LOOP,budget=5000000)
        self.assertEqual(h.u.reg_read(UC_ARM_REG_PC),0x08041AA2)
        self.assertEqual(h.invalid[-1]['address'],0)
        self.assertTrue(h.bindings)
        self.assertFalse(h.scratch_uses)

    def test_native_nor_mutations_survive_new_boot_without_seeded_owner(self):
        first=self.boot();self.data_boundary(first)
        persisted=bytes(first.medium.data)
        self.assertNotEqual(persisted,fat12_fixture())
        second=self.boot(medium=SparseNOR(persisted));self.data_boundary(second)
        self.assertTrue(second.bindings)
        self.assertTrue(all(second.read(b['owner']+0x3C)==b['root'] for b in second.bindings))


if __name__=='__main__':unittest.main()
