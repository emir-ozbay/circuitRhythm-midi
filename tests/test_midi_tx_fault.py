"""Mode admission must fail closed after a known output FIFO delivery loss."""
import unittest
import test_phase1_safety as base
import test_midi_output_transport as output_tests


class MidiTxFaultTests(unittest.TestCase):
    setUpClass = classmethod(base.SafetyTests.setUpClass.__func__)
    setUp = base.SafetyTests.setUp
    word = base.SafetyTests.word
    read = base.SafetyTests.read
    store = base.SafetyTests.store
    call = base.SafetyTests.call
    setup_graph = output_tests.MidiOutputTransportTests.setup_graph

    def test_lost_off_keeps_mode_closed_even_after_queue_is_empty(self):
        for mode in (0, 1):
            with self.subTest(mode=mode):
                self.setUp()
                self.setup_graph(slots=2)
                self.u.mem_write(base.seq.SEQ_STATE_ADDR+4, bytes([mode]))
                self.output.note(0, 48)
                self.output.note(0, 49)
                self.output.note(0, 48, velocity=0, on=False)  # full FIFO drops Off
                self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR+base.seq.OFF_MIDI_TX_FAULT, 1), b'\x01')
                self.output.poll()
                self.assertEqual([self.output.pending(n) for n in range(3)], [0]*3)
                self.mode_ui.press()
                self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR+4, 1), bytes([mode]))
                self.mode_ui.release()
                self.output.note(0, 49, velocity=0, on=False)
                self.output.poll()
                self.mode_ui.press()
                self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR+4, 1), bytes([mode]))

    def test_successful_enqueue_and_disabled_port_do_not_latch_fault(self):
        self.setup_graph(slots=2)
        self.output.note(0, 48)
        self.output.note(0, 48, velocity=0, on=False)  # exact capacity still succeeds
        for driver in self.output.drivers:
            self.u.mem_write(driver+4, b'\x00')
        self.output.note(0, 49)  # disabled-port return0 is not FIFO-overflow branch
        self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR+base.seq.OFF_MIDI_TX_FAULT, 1), b'\x00')
        self.mode_ui.press()
        self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR+4, 1), b'\x01')

    def test_fault_observer_preserves_stock_noop_registers_flags_and_primask(self):
        registers = base.REGS + base.SAVED + [base.UC_ARM_REG_R12, base.UC_ARM_REG_LR]
        for valid in (False, True):
            for mask in (0, 1):
                for flags in (0, 0xF80F0000, 0x90020000, 0x68050000):
                    with self.subTest(valid_heap=valid, primask=mask, apsr=hex(flags)):
                        outcomes = []
                        for observed in (False, True):
                            self.setUp()
                            if not valid:
                                self.word(base.seq.HEAP_CUR_PTR, base.seq.SEQ_STATE_ADDR+4)
                            state_before = bytes(self.u.mem_read(base.seq.SEQ_STATE_ADDR, 256))
                            self.u.reg_write(base.UC_ARM_REG_R12, 0xCCCC1212)
                            self.u.reg_write(base.UC_ARM_REG_PRIMASK, mask)
                            self.u.reg_write(base.UC_ARM_REG_APSR, flags)
                            address = self.labels['c_midi_tx_overflow'] if observed else base.seq.STOCK_DIAGNOSTIC_NOOP
                            self.call(address, 0x11110000, 0x22221111, 0x33332222, 0x44443333)
                            outcomes.append(([self.u.reg_read(r) for r in registers],
                                             self.u.reg_read(base.UC_ARM_REG_APSR),
                                             self.u.reg_read(base.UC_ARM_REG_PRIMASK)))
                            after = bytearray(self.u.mem_read(base.seq.SEQ_STATE_ADDR, 256))
                            if observed and valid:
                                self.assertEqual(after[base.seq.OFF_MIDI_TX_FAULT], 1)
                                after[base.seq.OFF_MIDI_TX_FAULT] = 0
                            self.assertEqual(bytes(after), state_before)
                        self.assertEqual(outcomes[1], outcomes[0])

    def test_only_fault_byte_is_written_and_layout_checks_include_it(self):
        self.setup_graph(slots=2)
        self.output.note(0, 48)
        self.output.note(0, 49)
        raw_before = bytes(self.u.mem_read(0x20010000, 0x29484))
        writes = []
        self.u.hook_add(base.UC_HOOK_MEM_WRITE,
                        lambda u,k,a,n,v,d: writes.append((a,n,v)),
                        begin=base.seq.SEQ_STATE_ADDR, end=base.seq.HEAP_LIMIT-1)
        self.output.note(0, 48, velocity=0, on=False)
        self.assertEqual(writes, [(base.seq.SEQ_STATE_ADDR+base.seq.OFF_MIDI_TX_FAULT, 1, 1)]*3)
        self.assertEqual(bytes(self.u.mem_read(0x20010000, 0x29484)), raw_before)
        self.assertEqual(base.seq.OFF['midi_tx_fault'], (base.seq.OFF_MIDI_TX_FAULT, 1))
        base.seq.check_layout()


if __name__ == '__main__':
    unittest.main()
