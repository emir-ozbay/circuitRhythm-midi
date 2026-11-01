"""Native ADC DMA publisher/consumer and unforced Main readiness branch."""
import unittest
import test_phase1_safety as base
import midi_recovery_patch as fixed
from patch_firmware import apply_patches
from recovery_boot_test_support import STOP
from recovery_worker_test_support import READY_GATE
from recovery_input_test_support import (InputStartup, STREAM, DMA, MAIN_INPUT_READY,
                                         SPI_WAIT, MAIN_LOOP)
from unicorn.arm_const import *


class RecoveryInputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stock = base.load_image()
        cls.image = apply_patches(cls.stock, fixed.build_patches())[0]
        cls.labels = fixed.seq_code()[1]

    def boot(self):
        return InputStartup(self.image).main_setup().start_tasks().checkpoint()

    def native_call(self, h, address):
        context = h.u.context_save()
        h.in_service = True
        try:
            result = h.call(address)
            self.assertEqual(result['pc'], STOP)
            self.assertIsNone(result['error'])
            return result['result']
        finally:
            h.u.context_restore(context)
            h.in_service = False

    def test_native_64_dma_samples_pass_readiness_without_counter_or_return_override(self):
        h = self.boot()
        state = bytes(h.u.mem_read(fixed.STATE_BASE,1088))
        self.assertEqual(self.native_call(h, READY_GATE), 0)
        h.start_input().checkpoint(MAIN_INPUT_READY,budget=800000)
        self.assertEqual(h.readiness()['counters'], [2,2,2])
        self.assertEqual(self.native_call(h, READY_GATE), 1)
        self.assertEqual(len(h.dma_transfers), 64)
        self.assertEqual(len(h.input_irqs), 64)
        self.assertEqual(h.ready_checks[-1], [2,2,2])
        self.assertTrue(all(any(c < 2 for c in check) for check in h.ready_checks[:-1]))
        self.assertEqual([e['ct_before'] for e in h.dma_transfers], [False,True]*32)
        self.assertEqual(len(h.allocations), 203)
        self.assertEqual(h.read(base.seq.HEAP_CUR_PTR), 0x20010BEC)
        self.assertEqual(bytes(h.u.mem_read(fixed.STATE_BASE,1088)), state)
        self.assertEqual(bytes(h.u.mem_read(0x08010000,len(self.image))), self.image)
        self.assertTrue(h.validate_stacks())
        self.assertFalse(h.invalid)
        h.input_enabled = False
        h.checkpoint(SPI_WAIT,budget=10000)
        self.assertNotEqual(h.u.reg_read(UC_ARM_REG_PC), MAIN_LOOP)
        self.assertEqual(h.u.reg_read(UC_ARM_REG_R0), 0x20000318)
        self.assertEqual(h.u.reg_read(UC_ARM_REG_LR), 0x0803111D)

    def test_dma_completion_needs_native_irq_and_consumer(self):
        h = self.boot()
        raw = h.read(0x080266B4)
        before = bytes(h.u.mem_read(raw+4,192))
        event = h.complete_input_dma(deliver=False)
        self.assertNotEqual(bytes(h.u.mem_read(event['target'],192)), before)
        self.assertEqual(bytes(h.u.mem_read(raw+4,192)), before)
        self.assertEqual(h.u.mem_read(raw+2,1)[0], 0)
        self.assertEqual(h.readiness()['counters'], [0,0,0])
        h.deliver_input_irq()
        self.assertEqual(h.u.mem_read(raw+2,1)[0], 1)
        self.assertEqual(bytes(h.u.mem_read(raw+4,192)), bytes(h.u.mem_read(event['target'],192)))
        self.assertFalse(h.read(DMA) & 32)
        self.assertEqual(h.readiness()['counters'], [0,0,0])
        self.native_call(h, 0x080265BA)
        self.assertEqual(h.u.mem_read(raw+2,1)[0], 0)
        self.assertEqual(h.readiness()['counters'], [0,0,0])
        self.assertEqual(self.native_call(h, READY_GATE), 0)

    def test_64_irqs_without_consumer_coalesce_pending_and_never_make_ready(self):
        h = self.boot()
        for _ in range(64):
            event = h.complete_input_dma()
            self.assertEqual(event['pending'], 1)
        self.assertEqual(len(h.input_irqs), 64)
        self.assertEqual(h.readiness()['counters'], [0,0,0])
        self.assertEqual(self.native_call(h, READY_GATE), 0)
        self.assertTrue(h.validate_stacks())

    def test_completed_buffer_without_irq_keeps_main_in_readiness_loop(self):
        h = self.boot()
        h.complete_input_dma(deliver=False)
        pc = h.run(h.u.reg_read(UC_ARM_REG_PC), MAIN_INPUT_READY,budget=30000)
        self.assertNotEqual(pc, MAIN_INPUT_READY)
        self.assertEqual(h.input_irqs, [])
        self.assertEqual(h.readiness()['counters'], [0,0,0])
        self.assertEqual(self.native_call(h, READY_GATE), 0)
        self.assertFalse(h.invalid)

    def test_unsupported_dma_configuration_rejected_before_sample_write(self):
        h = self.boot()
        ram = bytes(h.u.mem_read(0x20000400,0x200))
        for offset, value in ((0,0x52C14),(4,95),(8,0x4001204C),(12,h.readiness()['objects'][0]+0x2A)):
            address = STREAM+offset
            old = h.read(address)
            h.word(address,value)
            with self.assertRaises(AssertionError):
                h.complete_input_dma()
            h.word(address,old)
            self.assertEqual(bytes(h.u.mem_read(0x20000400,0x200)), ram)
            self.assertEqual(h.readiness()['counters'], [0,0,0])
            self.assertEqual(h.dma_transfers, [])

    def test_masked_irq_is_not_delivered_or_counted(self):
        h = self.boot()
        h.complete_input_dma(deliver=False)
        for register,value in ((UC_ARM_REG_PRIMASK,1),(UC_ARM_REG_BASEPRI,0x10)):
            h.u.reg_write(register,value)
            with self.assertRaises(AssertionError):
                h.deliver_input_irq()
            self.assertEqual(h.input_irqs, [])
            self.assertEqual(h.readiness()['counters'], [0,0,0])
            h.u.reg_write(register,0)
        h.deliver_input_irq()
        self.assertEqual(len(h.input_irqs), 1)


if __name__ == '__main__':
    unittest.main()
