"""Full native reset and file worker;one synthetic lower-read fault per boot."""
import unittest
import test_phase1_safety as base
import midi_recovery_patch as fixed
from patch_firmware import apply_patches
from recovery_timer_test_support import boot_timer_session
from recovery_load_test_support import exercise_load


class RecoveryLoadTests(unittest.TestCase):
    mode=0
    @classmethod
    def setUpClass(cls):cls.image=apply_patches(base.load_image(),fixed.build_patches())[0]
    def test_native_complete_then_short_read_quarantines_alias_and_mode(self):
        s,timer=boot_timer_session(self.image,sample_status=(0,)*4096,compare_credits=2048,
            record_status=(0xFFFFFF,)*2048,adc_scan=(1500,3700,2048),adc_frame_credits=256)
        type(self).session=s
        type(self).report=exercise_load(s,timer,self.mode,progress=getattr(type(self),'progress',None))


if __name__=='__main__':unittest.main()
