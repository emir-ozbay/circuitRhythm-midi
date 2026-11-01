"""Finite DSP inputs, native busy loops and fail-closed unknown MISO reads."""
import unittest
from unicorn.arm_const import UC_ARM_REG_PC,UC_ARM_REG_R4,UC_ARM_REG_SP
import test_phase1_safety as base
import midi_recovery_patch as fixed
from patch_firmware import apply_patches
from recovery_dsp_test_support import DSPRead,ScriptedDSPPeer,DSPStartup,mailbox_script,empty_sample_lengths
from recovery_spi_test_support import UnmodeledSPIResponse,DMA1
from recovery_input_test_support import MAIN_INPUT_READY,MAIN_LOOP


class DSPInputTests(unittest.TestCase):
    def test_no_default_reply_inactive_wrong_bank_wrong_address_or_exhausted(self):
        p=ScriptedDSPPeer([DSPRead(0x37300,0x123456)])
        with self.assertRaises(UnmodeledSPIResponse):p.peek(0,0x37300)
        p.active=True
        for bank,address in ((1,0x37300),(0,0x37301)):
            with self.assertRaises(UnmodeledSPIResponse):p.peek(bank,address)
            self.assertEqual(p.position,0)
        self.assertEqual(p.peek(0,0x37300),bytes.fromhex('123456'))
        p.commit(0,0x37300,bytes.fromhex('123456'))
        with self.assertRaises(UnmodeledSPIResponse):p.peek(0,0x37300)
        self.assertEqual(p.position,1)

    def test_completion_reply_requires_exact_prior_wire_write(self):
        p=ScriptedDSPPeer([DSPRead(0x372FB,0,after_write=(0,0x372FB,1))]);p.active=True
        for bank,address,payload in ((1,0x372FB,b'\0\0\1'),(0,0x372FC,b'\0\0\1'),(0,0x372FB,b'\0\1\0')):
            p.write(bank,address,payload)
            with self.assertRaises(UnmodeledSPIResponse):p.peek(0,0x372FB)
        p.write(0,0x372FB,b'\0\0\1')
        self.assertEqual(p.peek(0,0x372FB),bytes(3))

    def test_failed_commit_and_peek_do_not_consume_input(self):
        p=ScriptedDSPPeer([DSPRead(0x37300,1)]);p.active=True
        for _ in range(3):self.assertEqual(p.peek(0,0x37300),b'\0\0\1')
        with self.assertRaises(AssertionError):p.commit(0,0x37300,bytes(3))
        self.assertEqual((p.position,p.reads),(0,[]))

    def test_reset_invalidates_ready_and_previous_write_evidence(self):
        p=ScriptedDSPPeer([DSPRead(0x372FB,0,after_write=(0,0x372FB,1))]);p.active=True
        p.write(0,0x372FB,b'\0\0\1');p.commit(0,0x372FB,bytes(3));p.reset()
        self.assertEqual((p.active,p.position,p.writes,p.reads),(False,0,{},[]))
        p.active=True
        with self.assertRaises(UnmodeledSPIResponse):p.peek(0,0x372FB)

    def test_invalid_script_cannot_truncate_bank_address_or_value(self):
        for options in (dict(bank=2),dict(address=0x40000),dict(address=-1),dict(value=0x1000000),dict(value=-1),dict(after_write=(0,0x80000,1))):
            values=dict(address=0x37300,value=0);values.update(options)
            with self.assertRaises(AssertionError):DSPRead(**values)
        for options in (dict(initial_busy=-1),dict(command_busy=17)):
            with self.assertRaises(AssertionError):mailbox_script(**options)

    def test_explicit_empty_lengths_are_finite_and_separate_from_mailbox(self):
        rows=empty_sample_lengths()
        self.assertEqual(len(rows),128)
        self.assertEqual((rows[0].address,rows[-1].address),(0x30001,0x301FD))
        self.assertTrue(all(row.value==0 and row.address!=0x37300 for row in rows))


class RecoveryDSPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stock=base.load_image();cls.image=apply_patches(cls.stock,fixed.build_patches())[0]
        cls.labels=fixed.seq_code()[1]

    def test_native_mailbox_busy_and_completion_then_unknown_data_stops(self):
        h=DSPStartup(self.image,peer_policy='ready')
        h.main_setup().start_tasks().checkpoint().start_input().checkpoint(MAIN_INPUT_READY,budget=800000).start_spi()
        with self.assertRaises(UnmodeledSPIResponse):h.checkpoint(MAIN_LOOP,budget=5000000)
        self.assertEqual(h.dsp_read,dict(bank=0,address=0x37300))
        self.assertEqual(len(h.dsp_writes),516)
        self.assertFalse(any(w['address']==0x37300 for w in h.dsp_writes))
        ram,mmio=bytes(h.u.mem_read(0x20000000,0x50000)),bytes(h.u.mem_read(DMA1,0x90))
        with self.assertRaises(UnmodeledSPIResponse):h.complete_spi_dma()
        self.assertEqual(bytes(h.u.mem_read(0x20000000,0x50000)),ram)
        self.assertEqual(bytes(h.u.mem_read(DMA1,0x90)),mmio)
        # Explicit test input is attached only after proving the strict stop.
        # This models a peer scenario; it does not establish DSP initialization.
        p=ScriptedDSPPeer(mailbox_script());p.active=True;h.dsp_peer=p
        h.checkpoint(0x08064434,budget=20000)
        self.assertEqual(h.u.reg_read(UC_ARM_REG_R4),0x100)
        for value in (0x100,0):
            h.checkpoint(0x08064426,budget=20000)
            h.checkpoint(0x08064434,budget=20000)
            self.assertEqual(h.u.reg_read(UC_ARM_REG_R4),value)
        h.checkpoint(0x08064558,budget=20000)
        self.assertEqual(h.u.reg_read(UC_ARM_REG_R4),0x100)
        self.assertEqual(p.writes[0,0x372FB],1)
        for value in (0x100,0):
            h.checkpoint(0x0806454A,budget=20000)
            h.checkpoint(0x08064558,budget=20000)
            self.assertEqual(h.u.reg_read(UC_ARM_REG_R4),value)
        self.assertEqual([r['address'] for r in p.reads],[0x37300]*3+[0x372FB,0x37300,0x37300])
        h.checkpoint(0x0806455C,budget=100)
        caller=h.read(h.u.reg_read(UC_ARM_REG_SP)+12)&~1
        h.checkpoint(caller,budget=100)
        self.assertEqual(p.position,len(p.script))
        with self.assertRaises(UnmodeledSPIResponse):p.peek(0,0x37300)
        self.assertNotEqual(h.u.reg_read(UC_ARM_REG_PC),MAIN_LOOP)
        self.assertFalse(h.invalid)
        self.assertTrue(h.validate_stacks())
        self.assertEqual(bytes(h.u.mem_read(0x08010000,len(self.image))),self.image)


if __name__=='__main__':unittest.main()
