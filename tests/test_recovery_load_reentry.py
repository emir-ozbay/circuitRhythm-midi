"""Native Close-confirmed Projects recovery; supersedes sticky-taint characterization."""
import unittest
import test_phase1_safety as base
import midi_recovery_patch as fixed
from patch_firmware import apply_patches
from recovery_timer_test_support import boot_timer_session
from recovery_load_recovery_test_support import exercise_load_recovery


class RecoveryLoadReentryTests(unittest.TestCase):
    mode=0
    @classmethod
    def setUpClass(cls):cls.image=apply_patches(base.load_image(),fixed.build_patches())[0]
    def test_native_failed_retry_then_load_and_new_recover_through_projects(self):
        s,timer=boot_timer_session(self.image,sample_status=(0,)*8192,compare_credits=4096,
            record_status=(0xFFFFFF,)*4096,adc_scan=(1500,3700,2048),adc_frame_credits=512)
        type(self).session=s
        type(self).report=exercise_load_recovery(s,timer,self.mode,progress=getattr(type(self),'progress',None))


if __name__=='__main__':unittest.main()
