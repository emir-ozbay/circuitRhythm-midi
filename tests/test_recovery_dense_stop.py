"""Native64-voice Stop closure and explicit recovery-state characterization."""
import unittest
import test_phase1_safety as base
import midi_recovery_patch as fixed
from patch_firmware import apply_patches
from recovery_timer_test_support import boot_timer_session
from recovery_dense_stop_test_support import exercise_dense_stop


class RecoveryDenseStopTests(unittest.TestCase):
    mode=0
    before_output=True
    @classmethod
    def setUpClass(cls):cls.image=apply_patches(base.load_image(),fixed.build_patches())[0]
    def test_native_64voice_stop(self):
        s,timer=boot_timer_session(self.image,sample_status=(0,)*4096,compare_credits=2000,
            record_status=(0xFFFFFF,)*1024,adc_scan=(1500,3700,2048),adc_frame_credits=128)
        type(self).session=s
        r=exercise_dense_stop(s,timer,mode=self.mode,before_output=self.before_output,progress=getattr(type(self),'progress',None))
        self.assertEqual([c['counts'] for c in r['growth']],[[i]*8 for i in range(1,9)])
        self.assertEqual(sum(len(a) for a in r['live_before_stop']),64)
        self.assertEqual(sum(len(m)==3 and m[0]&0xF0==0x80 for m in r['messages']),64)
        self.assertEqual(r['midi_faults'],'000000')
        self.assertTrue(all(row['flags']==0 for row in r['settled']))
        type(self).report=r
