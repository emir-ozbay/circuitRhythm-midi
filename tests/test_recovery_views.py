"""Exact-image native Velocity/Gate page and bottom-pad contracts."""
import unittest
import test_phase1_safety as base
import midi_recovery_patch as fixed
from patch_firmware import apply_patches
from recovery_live_mode_test_support import boot_session
from recovery_views_test_support import exercise_native_views


class RecoveryViewsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.image=apply_patches(base.load_image(),fixed.build_patches())[0]

    def test_native_both_modes_all_tracks_pages_parameters_and_leds(self):
        type(self).session=boot_session(self.image,sample_status=(0,)*1024)
        result=exercise_native_views(type(self).session,progress=getattr(type(self),'progress',None))
        self.assertEqual(result['tracks'],list(range(8)))
        self.assertEqual(len(result['top_mapping']),1024)
        self.assertEqual(len(result['cases']),128)
        self.assertEqual(len(result['length_extensions']),8)
        self.assertEqual(result['midi_faults'],'000000')
        self.assertGreater(result['main_cycles'],0)
        self.assertEqual(len(result['sample_status_inputs']),result['main_cycles'])
        self.assertGreater(result['uart']['used_credits'],0)
        self.assertTrue(all(p['bytes_hex'] for p in result['uart']['ports']))
        self.assertEqual(result['project_io'],[])
        self.assertEqual(result['final']['heap'],result['initial']['heap'])
        type(self).report=result


if __name__=='__main__':unittest.main()
