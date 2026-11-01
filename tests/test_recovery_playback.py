"""Exact-image native32-step player/cursor and Stop lifecycle."""
import unittest
import test_phase1_safety as base
import midi_recovery_patch as fixed
from patch_firmware import apply_patches
from recovery_live_mode_test_support import boot_session
from recovery_playback_test_support import exercise_native_playback


class RecoveryPlaybackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.image=apply_patches(base.load_image(),fixed.build_patches())[0]

    def test_native_play_stop_all_tracks_both_modes_32step_wrap(self):
        type(self).session=boot_session(self.image,sample_status=(0,)*2048)
        r=exercise_native_playback(type(self).session,progress=getattr(type(self),'progress',None))
        self.assertEqual(len(r['runs']),2)
        self.assertEqual(len(r['leds']),544)
        self.assertEqual([a['steps'] for a in r['runs']],[list(range(32))+[0]]*2)
        self.assertEqual(r['midi_faults'],'000000')
        self.assertEqual(r['project_io'],[])
        self.assertEqual(len(r['sample_status_inputs']),r['main_cycles'])
        type(self).report=r


if __name__=='__main__':unittest.main()
