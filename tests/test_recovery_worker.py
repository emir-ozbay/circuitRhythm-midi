"""Native scheduler port, basic SVC/PendSV and actual Storage drain proof."""
import struct
import unittest
import test_phase1_safety as base
import midi_recovery_patch as fixed
from patch_firmware import apply_patches
from recovery_boot_test_support import STOP
from recovery_worker_test_support import WorkerStartup, BasicFrameOnly, READY_GATE, MAIN_AFTER_FIRST_DRAIN
from unicorn.arm_const import *


class RecoveryWorkerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stock = base.load_image()
        cls.image = apply_patches(cls.stock, fixed.build_patches())[0]
        cls.labels = fixed.seq_code()[1]

    def boot(self, image=None):
        return WorkerStartup(self.image if image is None else image).main_setup().start_tasks()

    def test_native_port_resets_critical_sentinel_and_svc_starts_actual_idle_frame(self):
        h = self.boot()
        idle = h.tasks[-1]
        self.assertEqual(h.critical_before, 0xAAAAAAAA)
        self.assertEqual(h.read(h.critical_pointer), 0)
        self.assertEqual(h.port_heap, 0x2000B618)
        self.assertEqual(h.running_tcb, idle['tcb'])
        self.assertEqual(h.u.reg_read(UC_ARM_REG_PC), idle['entry'] & ~1)
        self.assertEqual(h.u.reg_read(UC_ARM_REG_PSP), idle['saved_sp']+68)
        self.assertEqual(h.u.reg_read(UC_ARM_REG_MSP), 0x2004FFE0)
        self.assertEqual(h.u.reg_read(UC_ARM_REG_BASEPRI), 0)
        self.assertEqual(h.u.reg_read(UC_ARM_REG_IPSR), 0)
        self.assertEqual(h.u.reg_read(UC_ARM_REG_CONTROL), 2)
        self.assertEqual(h.read(h.current_pointer), idle['tcb'])
        self.assertEqual(len(h.allocations), 129)

    def test_actual_storage_worker_clears_request_and_main_returns_to_its_caller(self):
        h = self.boot().checkpoint(MAIN_AFTER_FIRST_DRAIN)
        names = {t['tcb']:t['name'] for t in h.tasks}
        request, completion = h.requests[0], h.completions[0]
        self.assertEqual(names[request['task']], 'Main')
        self.assertEqual(completion['task'], request['task'])
        self.assertEqual(completion['driver'], request['driver'])
        self.assertEqual(request['flag_before'] & 1, 0)
        self.assertEqual(completion['flag_after'] & 1, 0)
        self.assertTrue(any(e['driver'] == request['driver'] and names[e['task']] == 'Storage' for e in h.worker_calls))
        self.assertEqual(h.u.reg_read(UC_ARM_REG_PC), MAIN_AFTER_FIRST_DRAIN)
        self.assertEqual(h.running_tcb, request['task'])
        self.assertEqual(h.read(base.seq.HEAP_CUR_PTR), 0x2000B620)
        self.assertGreaterEqual(h.wfi_wakes, 1)
        self.assertTrue(h.validate_stacks())
        self.assertFalse(h.invalid)

    def test_all_five_tasks_run_and_main_reaches_next_unforced_readiness_gate(self):
        h = self.boot()
        state = bytes(h.u.mem_read(fixed.STATE_BASE, 1088))
        h.checkpoint()
        self.assertEqual(h.u.reg_read(UC_ARM_REG_PC), READY_GATE)
        self.assertEqual(len(h.allocations), 203)
        self.assertEqual(h.read(base.seq.HEAP_CUR_PTR), 0x20010BEC)
        self.assertEqual(sum(w['address'] == base.seq.HEAP_CUR_PTR and w['size'] == 4 for w in h.heap_writes), 203)
        self.assertEqual(set(h.thread_min), {t['tcb'] for t in h.tasks})
        self.assertEqual(len(h.requests), 9)
        self.assertEqual(len(h.completions), 9)
        self.assertEqual(len(h.switches), 128)
        self.assertTrue(all(not e['flag_after'] & 1 for e in h.completions))
        self.assertEqual(bytes(h.u.mem_read(fixed.STATE_BASE, 1088)), state)
        self.assertTrue(h.validate_stacks())
        context = h.u.context_save()
        self.assertEqual(h.call(READY_GATE)['result'], 0)
        h.u.context_restore(context)
        self.assertTrue(any(c < 2 for c in h.readiness()['counters']))
        self.assertFalse(h.invalid)

    def test_pendsv_native_saved_frames_preserve_threads_and_stack_bounds(self):
        h = self.boot().checkpoint(MAIN_AFTER_FIRST_DRAIN)
        pairs = [(h.task_by_tcb[s['old']]['name'], h.task_by_tcb[s['new']]['name']) for s in h.switches]
        self.assertEqual(pairs[:5], [('IDLE','Main'),('Main','UI'),('UI','Storage'),('Storage','Content'),('Content','IDLE')])
        self.assertIn(('IDLE','Main'), pairs[5:])
        for switch in h.switches:
            self.assertEqual(switch['hardware_sp']-switch['saved_sp'], 36)
            h._bounds(switch['old'], switch['saved_sp'], 68)
            h._bounds(switch['new'], switch['incoming_sp'], 32)
        # Register banks and both native save/restore frames are checked on
        # every transition in the harness,not replaced with ready-list copies.
        self.assertEqual(h.read(h.critical_pointer), 0)
        self.assertTrue(h.validate_stacks())

    def test_missing_pendsv_dispatch_keeps_request_pending_without_completion(self):
        h = self.boot().checkpoint(0x0802C260)
        driver = h.requests[0]['driver']
        self.assertEqual(h.read(driver+0x10) & 1, 1)
        h.dispatch_enabled = False
        result = h.run(h.u.reg_read(UC_ARM_REG_PC), MAIN_AFTER_FIRST_DRAIN, budget=12000)
        self.assertNotEqual(result, MAIN_AFTER_FIRST_DRAIN)
        self.assertEqual(h.read(driver+0x10) & 1, 1)
        self.assertEqual(h.completions, [])
        self.assertEqual(h.worker_calls, [])
        self.assertTrue(h.pending_pendsv)
        self.assertEqual(h.read(base.seq.HEAP_CUR_PTR), 0x2000B620)

    def test_worker_clear_without_idle_wake_does_not_prove_main_resumption(self):
        h = self.boot()
        h.wake_enabled = False
        result = h.run(h.u.reg_read(UC_ARM_REG_PC), MAIN_AFTER_FIRST_DRAIN, budget=80000)
        self.assertEqual(result, 0x08025A28)
        self.assertEqual(h.stop_reason, 'wfi')
        self.assertEqual(h.read(h.requests[0]['driver']+0x10) & 1, 0)
        self.assertEqual(h.completions, [])
        h.wake_enabled = True
        h.checkpoint(MAIN_AFTER_FIRST_DRAIN)
        self.assertEqual(len(h.completions), 1)

    def test_frame_padding_and_unmodeled_fp_are_explicit(self):
        h = self.boot()
        idle = h.tasks[-1]
        sp = ((idle['stack']+128) & ~7)+4
        address, frame = h._hardware_frame(0x08025004, sp)
        self.assertEqual(address & 7, 0)
        self.assertTrue(frame[7] & 512)
        self.assertEqual(address+32+4, sp)
        self.assertEqual(list(struct.unpack('<8I', h.u.mem_read(address, 32))), frame)
        with self.assertRaises(BasicFrameOnly):
            h.call(0x08068C2C)  # real native FPSCR setup,not a test opcode

    def test_stock_and_candidate_match_through_worker_and_main_prefix(self):
        old = self.boot(self.stock).checkpoint()
        h = self.boot().checkpoint()
        self.assertEqual([(a['size'],a['current']) for a in old.allocations],
                         [(a['size'],a['current']) for a in h.allocations])
        self.assertEqual(old.readiness(), h.readiness())
        self.assertEqual(old.thread_min, h.thread_min)
        self.assertEqual([(e['task'],e['driver']) for e in old.requests],
                         [(e['task'],e['driver']) for e in h.requests])
        self.assertEqual(old.read(base.seq.HEAP_CUR_PTR), h.read(base.seq.HEAP_CUR_PTR))
        self.assertEqual(h.minimum_msp, 0x2004FF08)


if __name__ == '__main__':
    unittest.main()
