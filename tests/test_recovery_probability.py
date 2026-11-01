"""Exact-image native Probability and enriched Mutate preservation contract."""
import unittest
import test_phase1_safety as base
import midi_recovery_patch as fixed
from patch_firmware import apply_patches
from recovery_live_mode_test_support import boot_session
from recovery_probability_test_support import exercise_native_probability


class RecoveryProbabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.image=apply_patches(base.load_image(),fixed.build_patches())[0]

    def test_native_probability_all_tracks_both_modes_pages_and_rich_mutate(self):
        type(self).session=boot_session(self.image,sample_status=(0,)*2048)
        r=exercise_native_probability(type(self).session,progress=getattr(type(self),'progress',None))
        self.assertEqual(r['tracks'],list(range(8)))
        self.assertEqual(len(r['top_mapping']),512)
        self.assertEqual(len(r['cases']),64)
        self.assertEqual(len(r['held_guards']),64)
        self.assertEqual(len(r['leds']),128)
        self.assertEqual(len(r['preserved_parameters']),32)
        self.assertEqual(len(r['idle_edits']),32)
        self.assertEqual(len(r['rich_mutations']),32)
        self.assertEqual(r['project_io'],[])
        self.assertEqual(r['midi_faults'],'000000')
        self.assertEqual(len(r['sample_status_inputs']),r['main_cycles'])
        type(self).report=r


if __name__=='__main__':unittest.main()
