"""Native reset/data initialization plus real constructor OOM regressions."""
import unittest
import struct
import test_phase1_safety as base
import midi_recovery_patch as fixed
import midi_recovery_prototype as core
from patch_firmware import apply_patches
from recovery_boot_test_support import NativeStartup, MAIN, STOP
from unicorn.arm_const import UC_ARM_REG_PC, UC_ARM_REG_SP, UC_ARM_REG_PRIMASK


class RecoveryBootTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stock = base.load_image()
        cls.image = apply_patches(cls.stock, fixed.build_patches())[0]
        cls.labels = fixed.seq_code()[1]

    def boot(self, fill=0xA5):
        return NativeStartup(self.image, fill).startup()

    def assert_initialized(self, h):
        expected = bytearray(1088)
        struct.pack_into('<I', expected, 0, core.MAGIC)
        struct.pack_into('<I', expected, 832, base.seq.SEQ_STATE_MAGIC)
        expected[832+base.seq.OFF_LAST_SEQ_PROJ] = base.seq.DEFAULT_SEQ_PROJ
        self.assertEqual(h.first_allocation_state, bytes(expected))
        self.assertEqual(bytes(h.u.mem_read(fixed.STATE_BASE, 1088)), bytes(expected))
        self.assertEqual(h.read(base.seq.HEAP_LIMIT_PTR), fixed.STATE_BASE)
        self.assertEqual(h.read(base.seq.HEAP_CUR_PTR), 0x20007B90)
        self.assertFalse(h.invalid)

    def test_reset_vector_initializes_dirty_ram_before_first_bump(self):
        for fill in (0, 0xA5, 0xFF):
            with self.subTest(fill=fill):
                h = self.boot(fill)
                self.assert_initialized(h)
                self.assertEqual(h.u.reg_read(UC_ARM_REG_PC), MAIN)
                self.assertEqual(h.allocations[0], dict(size=64, current=0x20006F60, limit=base.seq.HEAP_LIMIT))
                self.assertTrue(all(a['limit'] == fixed.STATE_BASE for a in h.allocations[1:]))
                self.assertEqual(len(h.allocations), 10)
                self.assertTrue(all(w['masked'] == 1 for w in h.reserved_writes))
                self.assertEqual(len(h.reserved_writes), 276)  #272 clear +core magic +two defaults +seq magic

    def test_retained_valid_magics_and_active_journal_are_cleared_on_reset(self):
        h = NativeStartup(self.image)
        h.u.mem_write(fixed.STATE_BASE, b'\xFF'*1088)
        h.word(fixed.STATE_BASE, core.MAGIC)
        h.word(base.seq.SEQ_STATE_ADDR, base.seq.SEQ_STATE_MAGIC)
        h.word(base.seq.HEAP_LIMIT_PTR, fixed.STATE_BASE)
        h.word(base.seq.HEAP_CUR_PTR, fixed.STATE_BASE)
        h.startup()
        self.assert_initialized(h)
        self.assertEqual(h.u.reg_read(UC_ARM_REG_PRIMASK), 0)

    def test_native_objects_and_allocations_match_stock_static_startup(self):
        old = NativeStartup(self.stock).startup()
        h = self.boot()
        self.assertEqual([(a['size'], a['current']) for a in h.allocations],
                         [(a['size'], a['current']) for a in old.allocations])
        # Native class roots, endpoints, RX descriptor and all allocated data.
        for address, size in ((0x200000C0, 0x4C), (0x20005CC8, 0x280), (0x20006F60, 0xC30)):
            self.assertEqual(bytes(h.u.mem_read(address, size)), bytes(old.u.mem_read(address, size)))
        self.assertEqual(h.read(0x200000C0), 0x20005F70)
        self.assertEqual(h.read(0x200000C8), 0x20005F94)
        self.assertEqual(h.read(0x20005F94+0x18), 0x20006FA0)
        self.assertEqual(h.read(0x20006FA0+4), 1057)

    def test_native_initial_sp_and_measured_static_stack_do_not_touch_state(self):
        h = self.boot()
        self.assertEqual(h.initial_sp, 0x20050000)
        self.assertEqual(h.min_sp, 0x2004FF60)
        self.assertEqual(h.u.reg_read(UC_ARM_REG_SP), h.initial_sp-8)
        self.assertGreaterEqual(h.min_sp, base.seq.HEAP_LIMIT)
        # This covers this startup window only, not main/task/exception stacks.
        self.assertEqual(h.min_sp-base.seq.HEAP_LIMIT, 2048)

    def test_each_native_endpoint_allocation_failure_stops_before_invalid_pointer_use(self):
        for available in (0, 64, 76, 1136, 2160, 2224):
            with self.subTest(available=available):
                h = self.boot()
                state = bytes(h.u.mem_read(fixed.STATE_BASE, 1088))
                result = h.oom_constructor(available)
                self.assertEqual(result['pc'], self.labels['alloc_fatal'])
                self.assertEqual(result['primask'], 1)
                self.assertIsNone(result['error'])
                self.assertFalse(h.invalid)
                self.assertLessEqual(h.read(base.seq.HEAP_CUR_PTR), fixed.STATE_BASE)
                self.assertEqual(bytes(h.u.mem_read(fixed.STATE_BASE, 1088)), state)

    def test_alignment_and_address_overflow_are_terminal_without_bump_or_state_write(self):
        for size in (0xFFFFFFFF, 0xFFFFFFFE, 0xFFFFFFFD, 0xFFFFFFFC, 0xE0000000):
            with self.subTest(size=size):
                h = self.boot()
                current = h.read(base.seq.HEAP_CUR_PTR)
                state = bytes(h.u.mem_read(fixed.STATE_BASE, 1088))
                result = h.call(base.seq.STOCK_ALLOCATOR_ADDR, size)
                self.assertEqual(result['pc'], self.labels['alloc_fatal'])
                self.assertIsNone(result['error'])
                self.assertEqual(h.read(base.seq.HEAP_CUR_PTR), current)
                self.assertEqual(bytes(h.u.mem_read(fixed.STATE_BASE, 1088)), state)
                self.assertFalse(h.invalid)

    def test_invalid_reservation_never_falls_through_to_unreserved_allocator(self):
        for limit, current in ((base.seq.HEAP_LIMIT-4, 0x20007B90),
                               (base.seq.HEAP_LIMIT, fixed.STATE_BASE+4),
                               (fixed.STATE_BASE, fixed.STATE_BASE+4)):
            with self.subTest(limit=limit, current=current):
                h = self.boot()
                h.word(base.seq.HEAP_LIMIT_PTR, limit)
                h.word(base.seq.HEAP_CUR_PTR, current)
                state = bytes(h.u.mem_read(fixed.STATE_BASE, 1088))
                result = h.call(base.seq.STOCK_ALLOCATOR_ADDR, 4)
                self.assertEqual(result['pc'], self.labels['alloc_fatal'])
                self.assertIsNone(result['error'])
                self.assertEqual(h.read(base.seq.HEAP_LIMIT_PTR), limit)
                self.assertEqual(h.read(base.seq.HEAP_CUR_PTR), current)
                self.assertEqual(bytes(h.u.mem_read(fixed.STATE_BASE, 1088)), state)

    def test_successful_tail_allocation_preserves_mask_stack_and_registers(self):
        for mask in (0, 1):
            h = self.boot()
            h.word(base.seq.HEAP_CUR_PTR, fixed.STATE_BASE-4)
            h.u.reg_write(UC_ARM_REG_PRIMASK, mask)
            sp = h.u.reg_read(UC_ARM_REG_SP)
            saved = [h.u.reg_read(r) for r in base.SAVED]
            result = h.call(base.seq.STOCK_ALLOCATOR_ADDR, 1)
            self.assertEqual(result, dict(pc=STOP, result=fixed.STATE_BASE-4, primask=mask, error=None))
            self.assertEqual(h.read(base.seq.HEAP_CUR_PTR), fixed.STATE_BASE)
            self.assertEqual(h.u.reg_read(UC_ARM_REG_SP), sp)
            self.assertEqual([h.u.reg_read(r) for r in base.SAVED], saved)


if __name__ == '__main__':
    unittest.main()
