"""Live UI parameter edits and player decisions through native IRQ/Main."""
import unittest
import test_phase1_safety as base
import midi_recovery_patch as fixed
from patch_firmware import apply_patches
from recovery_timer_test_support import boot_timer_session
from recovery_running_edit_test_support import exercise_running_edits


class RecoveryRunningEditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.image=apply_patches(base.load_image(),fixed.build_patches())[0]
    def test_running_microstep_probability_and_note_closure_in_both_modes(self):
        s,timer=boot_timer_session(self.image,sample_status=(0,)*10000,compare_credits=8000,
            record_status=(0xFFFFFF,)*4000,adc_scan=(1500,3700,2048),adc_frame_credits=128)
        type(self).session=s
        r=exercise_running_edits(s,timer,progress=getattr(type(self),'progress',None))
        self.assertEqual([x['mode'] for x in r['runs']],[0,1]);self.assertEqual(r['midi_faults'],'000000')
        self.assertEqual(len(r['held_mode_guards']),32)
        type(self).report=r
