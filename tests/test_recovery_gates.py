"""Native reset/UI Gate endpoint expiry across both32-step boundaries."""
import unittest
import test_phase1_safety as base
import midi_recovery_patch as fixed
from patch_firmware import apply_patches
from recovery_timer_test_support import boot_timer_session
from recovery_gate_test_support import exercise_native_gates


class RecoveryGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.image=apply_patches(base.load_image(),fixed.build_patches())[0]
    def test_native_ui_gates_expire_across_page_and_pattern_wrap_in_both_modes(self):
        s,timer=boot_timer_session(self.image,sample_status=(0,)*16000,compare_credits=12000,
            record_status=(0xFFFFFF,)*6000,adc_scan=(1500,3700,2048),adc_frame_credits=128)
        type(self).session=s
        r=exercise_native_gates(s,timer,progress=getattr(type(self),'progress',None))
        self.assertEqual([v['mode'] for v in r['runs']],[0,1]);self.assertEqual(r['midi_faults'],'000000')
        type(self).report=r
