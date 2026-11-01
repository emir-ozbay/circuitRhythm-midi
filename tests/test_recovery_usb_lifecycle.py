"""Unified packaged-SYX MIDI TX/RX + Composite MSC + Power/Reset lifecycle tests."""
import unittest
import test_integrated_accepted_tx as prior
import midi_accepted_tx_patch as guard
import midi_recovery_patch as fixed
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0
from recovery_usb_lifecycle_test_support import UnifiedUsbLifecycleFixture

base = prior.base


class RecoveryUsbLifecycleTests(unittest.TestCase):
    setUpClass = classmethod(prior.AcceptedTxTests.setUpClass.__func__)
    instruction_budget = 500000
    for name in ('setUp', 'word', 'read', 'store', 'call', 'output', 'entry', 'settle',
                 'pump', 'stream', 'on', 'stage', 'state', 'submit_closures'):
        locals()[name] = getattr(prior.AcceptedTxTests, name)

    def usb(self):
        self.output()
        self.tx = UnifiedUsbLifecycleFixture(self, self.out)

    def reconfigure(self):
        self.tx.enumerate_irq()
        self.tx.address()
        self.tx.configure()

    def test_unified_midi_tx_rx_msc_suspend_wake_and_reset_lifecycle_in_both_modes(self):
        for mode in (0, 1):
            with self.subTest(mode=mode):
                self.setUp()
                self.usb()
                self.u.mem_write(base.seq.SEQ_STATE_ADDR + 4, bytes([mode]))
                self.tx.arm_midi_rx()
                self.tx.arm_msc_bot()
                self.assertTrue(self.tx.regs[0xB20] & guard.EPENA)
                self.assertTrue(self.tx.regs[0xB40] & guard.EPENA)

                # 1. Active 64-note production across USB + DIN1/DIN2 interleaved with
                # incoming USB-MIDI RX (OUT1) and MSC SCSI INQUIRY / TEST UNIT READY (OUT2/IN2).
                din = [bytearray(), bytearray()]
                def step_bus():
                    for i, data in enumerate(self.tx.bus()):
                        din[i].extend(data)

                for note in range(64):
                    for port in range(3):
                        self.out.send(port, [0x90, note, 96])
                    self.out.poll()
                    step_bus()
                    if note in (0, 31, 63):
                        rx_pkt = bytes([0x09, 0x90, 60 + (note & 3), 100, 0x08, 0x80, 60 + (note & 3), 0, 0x0F, 0xF8, 0, 0])
                        self.tx.send_usb_midi_rx(rx_pkt)
                        self.assertEqual(self.tx.drain_usb_midi_rx(), rx_pkt)
                        self.assertTrue(self.tx.regs[0xB20] & guard.EPENA)
                    if note in (15, 47):
                        inq, csw = self.tx.msc_inquiry(tag=0x11110000 + note)
                        self.assertIn(b'Novation', inq)
                        self.assertTrue(self.tx.regs[0xB40] & guard.EPENA)
                        self.tx.msc_test_unit_ready(tag=0x22220000 + note)

                # 2. Queue 64 Note Offs + Stop across all 3 ports; admit first USB IN1 chunk.
                for port in range(3):
                    for note in range(64):
                        self.out.send(port, [0x80, note, 0])
                    self.out.send(port, [0xFC, 0, 0])
                self.out.poll()
                self.assertEqual(self.state(guard.JOB), guard.ACTIVE)
                self.assertIsNotNone(self.tx.native.in_flight)

                # 3. USB Suspend (GINTSTS bit11 -> 0802C7E6 -> 0804279E) while closing debt is active:
                # DIN1/DIN2 continue draining to completion while USB retains remaining debt.
                self.tx.suspend_irq()
                self.assertEqual(self.u.mem_read(self.tx.native.usb_controller + 0x274, 2), b'\x04\x03')
                self.assertEqual(self.tx.regs[0xE00] & 1, 1)
                for _ in range(96):
                    self.out.poll()
                    for i in range(2):
                        din[i].extend(self.tx.native.drain_uart(i))
                self.assertEqual(self.out.pending(1), 0)
                self.assertEqual(self.out.pending(2), 0)
                self.assertGreater(self.out.pending(0), 0)

                # 4. USB Wakeup (GINTSTS bit31 -> 0802C9F8 + 0802C802 -> 080427AE) followed by
                # mid-transfer USBRST (bit12 -> 08042D20) and EP0 reconfigure.
                self.tx.wakeup_irq()
                self.assertEqual(self.u.mem_read(self.tx.native.usb_controller + 0x274, 1), b'\x03')
                self.assertEqual(self.tx.regs[0xE00] & 1, 0)

                init_order = []
                self.u.hook_add(UC_HOOK_CODE, lambda u, p, n, d: init_order.append(u.reg_read(UC_ARM_REG_R0)),
                                begin=0x080525B6, end=0x080525B6)
                self.tx.reset_irq()
                self.assertEqual(self.state(guard.PHASE), guard.REQUEST)
                self.reconfigure()
                self.assertEqual(self.state(guard.INIT_CLASS), self.tx.root)
                self.assertEqual(init_order, [])

                # Advance barrier to REPLAY, then verify Suspend pauses deferred INIT_CLASS until Wakeup.
                self.out.poll()
                self.tx.ack_disable()
                self.out.poll()
                self.out.poll()
                self.out.poll()
                self.assertEqual(self.state(guard.PHASE), guard.REPLAY)
                self.tx.suspend_irq()
                self.assertEqual(self.u.mem_read(self.tx.native.usb_controller + 0x274, 1), b'\x04')
                for _ in range(8):
                    self.out.poll()
                self.assertEqual(self.state(guard.INIT_CLASS), self.tx.root)
                self.assertEqual(init_order, [])
                self.tx.wakeup_irq()
                self.assertEqual(self.u.mem_read(self.tx.native.usb_controller + 0x274, 1), b'\x03')

                # 5. Complete deferred composite init (MIDI + MSC) and full closure replay.
                for _ in range(128):
                    self.out.poll()
                    step_bus()
                self.assertEqual(init_order, [self.tx.wrapper, self.tx.msc])
                self.assertEqual(self.state(guard.PHASE), guard.OPEN)
                self.assertEqual(self.state(guard.JOB), guard.IDLE)
                self.assertEqual(self.state(guard.INIT_CLASS), 0)

                expected_usb = (b''.join(bytes([9, 0x90, n, 96]) for n in range(64)) +
                                b''.join(bytes([8, 0x80, n, 0]) for n in range(64)) + b'\x0F\xFC\x00\x00\x0F\xFC\x00\x00')
                expected_din = (b'\x90' + b''.join(bytes([n, 96]) for n in range(64)) +
                                b'\x80' + b''.join(bytes([n, 0]) for n in range(64)) + b'\xFC')
                self.assertEqual(self.stream(), expected_usb)
                self.assertEqual([bytes(b) for b in din], [expected_din, expected_din])

                # 6. Verify both MIDI RX (OUT1) and MSC BOT (OUT2/IN2) were re-armed by
                # deferred composite init and operate cleanly after recovery.
                self.assertTrue(self.tx.regs[0xB20] & guard.EPENA)
                self.assertTrue(self.tx.regs[0xB40] & guard.EPENA)
                post_rx = b'\x09\x90\x40\x7F\x08\x80\x40\x00'
                self.tx.send_usb_midi_rx(post_rx)
                self.assertEqual(self.tx.drain_usb_midi_rx(), post_rx)
                inq_after, _ = self.tx.msc_inquiry(tag=0x33334444)
                self.assertIn(b'Novation', inq_after)
                self.tx.msc_test_unit_ready(tag=0x55556666)

    def test_deconfigure_and_reconfigure_tears_down_and_rearms_both_midi_and_msc_classes(self):
        self.usb()
        self.tx.arm_midi_rx()
        self.tx.arm_msc_bot()
        self.submit_closures()
        deinit_visits = []
        for pc in (0x0805261C, 0x080661EE):
            self.u.hook_add(UC_HOOK_CODE, lambda u, p, n, d: deinit_visits.append(p), begin=pc, end=pc)
        self.tx.configure(0)
        self.assertEqual(deinit_visits, [0x0805261C, 0x0805261C, 0x080661EE])
        self.assertEqual(self.read(0x20006DD4 + 0x10), 0)
        self.tx.configure(1)
        self.assertEqual(self.state(guard.INIT_CLASS), self.tx.root)
        self.pump()
        self.assertEqual(self.stream(), b'\x09\x90\x30\x60\x08\x80\x30\x00\x0F\xFC\x00\x00')
        self.assertTrue(self.tx.regs[0xB20] & guard.EPENA)
        self.assertTrue(self.tx.regs[0xB40] & guard.EPENA)
        self.tx.send_usb_midi_rx(b'\x09\x90\x30\x60')
        self.assertEqual(self.tx.drain_usb_midi_rx(), b'\x09\x90\x30\x60')
        inq, _ = self.tx.msc_inquiry(tag=0xABCDEF01)
        self.assertIn(b'Novation', inq)

    def test_msc_in2_completion_and_fifo2_flush_never_alias_owned_midi_in1_journal(self):
        self.usb()
        self.tx.arm_midi_rx()
        self.tx.arm_msc_bot()
        job, payload = self.submit_closures()
        # Concurrent MSC INQUIRY on IN2/OUT2 while MIDI IN1 job is ACTIVE in flight:
        inq, _ = self.tx.msc_inquiry(tag=0xCAFEBABE)
        self.assertIn(b'Novation', inq)
        # MIDI IN1 job must still be ACTIVE and untouched by IN2 XFRC/FIFO2 activity:
        self.assertEqual(self.state(guard.JOB), guard.ACTIVE)
        self.assertEqual(self.tx.native.in_flight, job)
        self.assertEqual(self.u.mem_read(*job), payload)
        # Complete MIDI IN1 transfer:
        self.tx.bus()
        self.assertEqual(self.state(guard.JOB), guard.IDLE)
        self.assertEqual(self.stream(), b'\x09\x90\x30\x60\x08\x80\x30\x00\x0F\xFC\x00\x00')


if __name__ == '__main__':
    unittest.main()
