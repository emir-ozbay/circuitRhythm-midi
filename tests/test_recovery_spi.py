"""Native SPI completion and explicit strict/busy/conditional-ready peer cases."""
import unittest
import test_phase1_safety as base
import midi_recovery_patch as fixed
import midi_accepted_tx_patch as accepted
from patch_firmware import apply_patches
from recovery_input_test_support import MAIN_INPUT_READY
from recovery_spi_test_support import (SPIStartup,UnmodeledSPIResponse,MEDIA_GATE,RX,TX,DMA1)
from unicorn.arm_const import *


class RecoverySPITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stock = base.load_image()
        cls.image = apply_patches(cls.stock,fixed.build_patches())[0]
        cls.labels = fixed.seq_code()[1]

    def boot(self,**options):
        return SPIStartup(self.image,**options).main_setup().start_tasks().checkpoint().start_input().checkpoint(MAIN_INPUT_READY,budget=800000).start_spi()

    def test_strict_response_stops_then_explicit_delayed_peer_reaches_later_native_boot(self):
        h = self.boot()
        state = bytes(h.u.mem_read(fixed.STATE_BASE,1088))
        with self.assertRaises(UnmodeledSPIResponse):
            h.checkpoint(MEDIA_GATE,budget=5000000)
        self.assertEqual(len(h.spi_transfers),3605)
        self.assertEqual(len(h.spi_irqs),7210)
        self.assertEqual(h.status_reads,[])
        self.assertEqual(h.unmodeled_response['register'],dict(bank=0,register=0x802B))
        ram,mmio = bytes(h.u.mem_read(0x20000000,0x50000)),bytes(h.u.mem_read(DMA1,0x90))
        with self.assertRaises(UnmodeledSPIResponse):
            h.complete_spi_dma()
        self.assertEqual(bytes(h.u.mem_read(0x20000000,0x50000)),ram)
        self.assertEqual(bytes(h.u.mem_read(DMA1,0x90)),mmio)
        h.peer_policy='ready'
        h.checkpoint(MEDIA_GATE,budget=5000000)
        self.assertEqual([x['reply'] for x in h.status_reads],['000000','000000','000001'])
        self.assertEqual(len(h.spi_transfers),3819)
        self.assertEqual(len(h.spi_irqs),7638)
        self.assertEqual(len(h.allocations),1296)
        self.assertEqual(h.read(base.seq.HEAP_CUR_PTR),0x20043D78)
        # Cold USB close legitimately updates the accepted-TX journal. Core
        # and first128B seq state remain intact;no host writes touch either.
        intact = accepted.STATE_BASE-fixed.STATE_BASE
        self.assertEqual(bytes(h.u.mem_read(fixed.STATE_BASE,intact)),state[:intact])
        self.assertEqual(bytes(h.u.mem_read(0x08010000,len(self.image))),self.image)
        self.assertTrue(h.validate_stacks())
        self.assertFalse(h.invalid)

    def test_completed_wire_without_rx_irq_keeps_native_wait_pending(self):
        h = self.boot().first_spi_wait()
        caller = h.u.reg_read(UC_ARM_REG_LR)&~1
        event = h.complete_spi_dma(deliver=('tx',))
        self.assertEqual(event['tokens_after'],[1,1,0,1])
        self.assertTrue(h.read(DMA1)&(1<<27))
        self.assertFalse(h.read(DMA1+4)&32)
        h.checkpoint(0x0802B67A,budget=1000)
        self.assertEqual(h.u.reg_read(UC_ARM_REG_R1),0)
        h.deliver_spi_irq('rx')
        h.checkpoint(caller,budget=10000)
        self.assertEqual(h.u.reg_read(UC_ARM_REG_PC),caller)
        self.assertFalse(h.read(DMA1)&(1<<27))

    def test_dummy_rx_without_memory_increment_writes_exactly_one_byte(self):
        h = self.boot(discarded_byte=0xA5).first_spi_wait()
        target = h.read(RX+12)
        before = bytes(h.u.mem_read(target-4,12))
        event = h.complete_spi_dma()
        after = bytes(h.u.mem_read(target-4,12))
        self.assertEqual(event['length'],30)
        self.assertEqual(event['rx_bytes_written'],1)
        self.assertFalse(event['rx_increment'])
        self.assertEqual(after[:4],before[:4])
        self.assertEqual(after[4],0xA5)
        self.assertEqual(after[5:],before[5:])
        self.assertTrue(h.validate_stacks())

    def test_bad_dma_configuration_rejected_before_any_rx_write_or_irq(self):
        h = self.boot().first_spi_wait()
        ram = bytes(h.u.mem_read(0x20000000,0x50000))
        for address,value in ((RX,0x10014),(TX,0x10055),(RX+4,31),
                              (RX+8,0x4001300C),(RX+12,fixed.STATE_BASE)):
            old = h.read(address)
            h.word(address,value)
            with self.assertRaises(AssertionError):
                h.complete_spi_dma()
            h.word(address,old)
            self.assertEqual(bytes(h.u.mem_read(0x20000000,0x50000)),ram)
            self.assertEqual(h.spi_transfers,[])
            self.assertEqual(h.spi_irqs,[])

    def test_masked_spi_irq_does_not_publish_completion(self):
        h = self.boot().first_spi_wait()
        h.complete_spi_dma(deliver=())
        self.assertEqual(list(h.u.mem_read(0x20000170,4)),[0,1,0,1])
        for register,value in ((UC_ARM_REG_PRIMASK,1),(UC_ARM_REG_BASEPRI,0x10)):
            h.u.reg_write(register,value)
            with self.assertRaises(AssertionError):
                h.deliver_spi_irq('rx')
            self.assertEqual(h.spi_irqs,[])
            self.assertEqual(h.u.mem_read(0x20000172,1)[0],0)
            h.u.reg_write(register,0)
        h.deliver_spi_irq('rx')
        self.assertEqual(h.u.mem_read(0x20000172,1)[0],1)

    def test_peer_busy_response_keeps_native_status_polling(self):
        h = self.boot(peer_policy='busy')
        h.checkpoint(0x080312AC,budget=5000000)
        for _ in range(3):
            h.checkpoint(0x080312C8,budget=20000)
            self.assertEqual(h.u.reg_read(UC_ARM_REG_R0),0)
            self.assertEqual(h.u.reg_read(UC_ARM_REG_R6),1)
            self.assertTrue(h.u.reg_read(UC_ARM_REG_XPSR)&(1<<30))
            h.checkpoint(0x080312B4,budget=1000)
        self.assertEqual([x['reply'] for x in h.status_reads],['000000']*3)
        self.assertEqual(len(h.allocations),203)
        self.assertEqual(h.read(base.seq.HEAP_CUR_PTR),0x20010BEC)
        self.assertFalse(h.invalid)


if __name__=='__main__':
    unittest.main()
