"""Native runtime mode graph plus strict disabled-DWT environment boundary."""
import unittest
import test_phase1_safety as base
import midi_recovery_patch as fixed
from patch_firmware import apply_patches
from recovery_live_mode_test_support import LiveModeStartup,boot_session,exercise_live_mode,UnsupportedDWTClock


class RecoveryLiveModeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stock=base.load_image();cls.image=apply_patches(cls.stock,fixed.build_patches())[0]
        cls.labels=fixed.seq_code()[1]

    def test_native_shift_pad_track_roundtrip_and_fault_admission(self):
        s=boot_session(self.image)
        result=exercise_live_mode(s)
        self.assertEqual(result['initial']['ready'],14)
        self.assertEqual(result['initial']['phase'],0)
        self.assertEqual(result['final']['mode'],0)
        self.assertEqual(result['project_io'],[])
        self.assertEqual(len(result['transient_fault_cases']),10)
        self.assertNotEqual(result['initial']['raw_sha256'],result['final']['raw_sha256'])
        self.assertEqual([row['pad'] for row in result['pad_matrix']],list(range(32)))
        self.assertEqual(result['long_press']['synthetic_timer_ticks'],[255,44,1])
        self.assertTrue(any(row['pc']==0x0805CE48 for row in result['timer_events']))
        self.assertTrue(any(row['pc']==0x08046E2A and row['r0']==6 and row['caller']==0x0805CD6B
                            for row in result['timer_events']))

    def test_disabled_dwt_counter_holds_value_without_invented_elapsed_time(self):
        h=LiveModeStartup(self.image)
        ram=0x2004E000;h.u.mem_write(ram,bytes.fromhex('08687047'))  # LDR R0,[R1];BX LR
        h.word(0xE0001004,123)
        for _ in range(2):
            result=h.call(ram,0,0xE0001004)
            self.assertIsNone(result['error']);self.assertEqual(result['result'],123)
        self.assertEqual(h.dwt_reads,2)

    def test_enabled_dwt_clock_is_rejected_without_a_fake_counter_reply(self):
        h=LiveModeStartup(self.image)
        ram=0x2004E000;h.u.mem_write(ram,bytes.fromhex('08687047'))
        h.word(0xE0001000,1)
        with self.assertRaises(UnsupportedDWTClock):h.call(ram,0,0xE0001004)
        self.assertEqual(h.dwt_reads,0)


if __name__=='__main__':unittest.main()
