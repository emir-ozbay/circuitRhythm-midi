"""Native UI Load + SyncAll + Mutate + IRQ66 playback of step byte6 tie."""
import unittest
import test_phase1_safety as base
import midi_recovery_patch as fixed
from patch_firmware import apply_patches
from recovery_timer_test_support import boot_timer_session
from recovery_native_tie_test_support import exercise_native_tie


class RecoveryNativeTieTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.image=apply_patches(base.load_image(),fixed.build_patches())[0]
    def test_native_ui_load_sync_mutate_and_playback_of_step_tie_across_boundaries(self):
        s,timer=boot_timer_session(self.image,sample_status=(0,)*20000,compare_credits=14000,
            record_status=(0xFFFFFF,)*8000,adc_scan=(1500,3700,2048),adc_frame_credits=128)
        type(self).session=s
        r=exercise_native_tie(s,timer,progress=getattr(type(self),'progress',None))
        self.assertEqual([v['mode'] for v in r['runs']],[0,1])
        self.assertEqual(len(r['mutations']),2)
        self.assertEqual(r['midi_faults'],'000000')
        self.assertFalse(r['application_ram_repaired'])
        type(self).report=r


if __name__=='__main__':unittest.main()
