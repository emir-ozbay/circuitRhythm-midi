"""Native boot allocation/task frames;explicit RCC/QSPI/no-response SDIO model."""
import unittest
import struct
import test_phase1_safety as base
import midi_recovery_patch as fixed
from patch_firmware import apply_patches
from recovery_boot_test_support import NativeStartup, STOP
from recovery_main_test_support import MainStartup, MAIN, SCHEDULER, MAIN_WORKER
from unicorn import UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_PC, UC_ARM_REG_SP, UC_ARM_REG_CONTROL


class RecoveryMainTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stock = base.load_image()
        cls.image = apply_patches(cls.stock, fixed.build_patches())[0]
        cls.labels = fixed.seq_code()[1]

    def test_global_write_observer_negative_corrupts_stock_it_stm_execution(self):
        h = NativeStartup(self.image).startup()
        h.u.hook_add(UC_HOOK_MEM_WRITE, lambda *args: None)
        h.u.mem_write(0x20010000, b'\xA5'*512)
        result = h.call(0x08023F30, 0x20010000, 48, budget=100)
        self.assertNotEqual(result['pc'], STOP)
        self.assertEqual(bytes(h.u.mem_read(0x20010030, 16)), bytes(16))
        # This is an emulator instrumentation negative,not a firmware defect.

    def test_scoped_observer_preserves_stock_zeroer_bounds_and_return(self):
        h = NativeStartup(self.image).startup()
        for size in (0, 1, 7, 15, 16, 17, 48, 64):
            with self.subTest(size=size):
                h.u.mem_write(0x20010000, b'\xA5'*128)
                sp = h.u.reg_read(UC_ARM_REG_SP)
                result = h.call(0x08023F30, 0x20010010, size, budget=100)
                self.assertEqual(result['pc'], STOP)
                self.assertIsNone(result['error'])
                self.assertEqual(h.u.reg_read(UC_ARM_REG_SP), sp)
                self.assertEqual(bytes(h.u.mem_read(0x20010000, 128)),
                                 b'\xA5'*16+bytes(size)+b'\xA5'*(112-size))

    def test_native_main_reaches_scheduler_preserving_state_and_registering_native_ports(self):
        h = MainStartup(self.image)
        state = bytes(h.u.mem_read(fixed.STATE_BASE, 1088))
        h.main_setup()
        self.assertEqual(h.u.reg_read(UC_ARM_REG_PC), SCHEDULER)
        self.assertEqual(h.static_heap_current, 0x20007B90)
        self.assertEqual(h.setup_heap_current, 0x2000B618)
        self.assertEqual(len(h.allocations), 129)
        self.assertEqual(sum(w['address'] == base.seq.HEAP_CUR_PTR and w['size'] == 4
                             for w in h.heap_writes), 129)
        self.assertEqual(sum((a['size']+3)&~3 for a in h.allocations), 0x2000B618-0x20006F60)
        self.assertEqual(h.setup_min_sp, 0x2004FF08)
        router = h.read(0x20006F04)
        ports = [h.read(h.read(router+0x14)+4*n) for n in range(3)]
        expected = bytearray(state)
        for n, port in enumerate(ports):
            struct.pack_into('<I', expected, 16+0x110*n, port)
            self.assertEqual(h.read(port), fixed.VTABLE)
            self.assertEqual(h.read(fixed.STATE_BASE+16+0x110*n), port)
        self.assertEqual(bytes(h.u.mem_read(fixed.STATE_BASE, 1088)), bytes(expected))
        self.assertEqual(len(h.reserved_writes), 279)  #init plus three native port registrations
        self.assertFalse(h.invalid)
        self.assertEqual(h.qspi_irqs, 4)
        self.assertEqual(h.sdio_commands[:2], [0, 8])
        self.assertEqual(set(h.sdio_commands[2:]), {55})

    def test_native_task_stacks_frames_and_tcbs_are_disjoint(self):
        h = MainStartup(self.image).main_setup()
        self.assertEqual([(t['name'], t['words']) for t in h.tasks],
                         [('Main', 768), ('UI', 512), ('Storage', 320), ('Content', 320), ('IDLE', 256)])
        ranges = []
        for task in h.tasks:
            ranges += [(task['stack'], task['stack']+task['words']*4), (task['tcb'], task['tcb']+92)]
            frame = task['frame']
            self.assertEqual(frame[:8], [0xA5A5A5A5]*8)
            self.assertEqual(frame[8], 0xFFFFFFFD)
            self.assertEqual(frame[9], task['argument'])
            self.assertEqual(frame[14], 0x08025409)
            self.assertEqual(frame[15], task['entry'] & ~1)
            self.assertEqual(frame[16], 0x01000000)
            self.assertTrue(task['stack'] <= task['saved_sp'] < task['saved_sp']+68 <= task['stack']+task['words']*4)
            self.assertEqual(task['priority'], 0)
        ranges.sort()
        self.assertTrue(all(a[1] <= b[0] for a, b in zip(ranges, ranges[1:])))
        self.assertTrue(all(0x20006F60 <= a < b <= fixed.STATE_BASE for a, b in ranges))

    def test_native_ready_list_selects_main_and_actual_frame_reaches_worker_boundary(self):
        h = MainStartup(self.image).main_setup()
        state = bytes(h.u.mem_read(fixed.STATE_BASE, 1088))
        h.first_main_task()
        main = next(t for t in h.tasks if t['name'] == 'Main')
        self.assertEqual(h.selection_steps, [h.tasks[-1]['tcb'], main['tcb']])
        self.assertEqual(h.u.reg_read(UC_ARM_REG_PC), MAIN_WORKER)
        self.assertEqual(h.u.reg_read(UC_ARM_REG_CONTROL) & 2, 2)
        self.assertEqual(h.task_min_sp, 0x200086B8)
        self.assertGreaterEqual(h.task_min_sp, main['stack'])
        self.assertEqual(h.read(base.seq.HEAP_CUR_PTR), 0x2000B620)
        self.assertEqual(len(h.allocations), 130)
        self.assertEqual(bytes(h.u.mem_read(fixed.STATE_BASE, 1088)), state)
        self.assertFalse(h.invalid)
        # No claim that Main finishes initialization;the worker has not run.

    def test_main_allocation_and_task_frame_layout_matches_stock(self):
        old = MainStartup(self.stock).main_setup()
        h = MainStartup(self.image).main_setup()
        self.assertEqual([(a['size'], a['current']) for a in h.allocations],
                         [(a['size'], a['current']) for a in old.allocations])
        self.assertEqual(h.tasks, old.tasks)
        self.assertEqual(h.setup_heap_current, old.setup_heap_current)
        self.assertEqual(old.read(base.seq.HEAP_LIMIT_PTR), base.seq.HEAP_LIMIT)
        self.assertEqual(h.read(base.seq.HEAP_LIMIT_PTR), fixed.STATE_BASE)

    def test_missing_clock_ack_keeps_native_main_before_task_allocations(self):
        h = MainStartup(self.image, clock_ack=False)
        pc = h.run(MAIN, SCHEDULER, budget=10000)
        self.assertIn(pc, (0x0802353E, 0x08023540, 0x08023542))
        self.assertEqual(len(h.allocations), 10)
        self.assertEqual(h.tasks, [])
        self.assertFalse(h.invalid)

    def test_missing_qspi_completion_does_not_fabricate_boot_progress(self):
        h = MainStartup(self.image, qspi_complete=False)
        pc = h.run(MAIN, SCHEDULER, budget=15000)
        self.assertNotEqual(pc, SCHEDULER)
        self.assertEqual(h.read(base.seq.HEAP_CUR_PTR), 0x20009F04)
        self.assertEqual(len(h.allocations), 31)
        self.assertEqual(h.qspi_irqs, 0)
        self.assertFalse(h.invalid)


if __name__ == '__main__':
    unittest.main()
