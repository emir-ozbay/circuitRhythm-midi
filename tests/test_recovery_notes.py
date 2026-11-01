"""Native Note1/7 contract against the complete current candidate image."""
import unittest
import test_phase1_safety as base
import midi_recovery_patch as fixed
from patch_firmware import apply_patches
from recovery_live_mode_test_support import boot_session
from recovery_notes_test_support import exercise_native_notes


class RecoveryNotesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.image=apply_patches(base.load_image(),fixed.build_patches())[0]

    def test_native_notes_pages_and_retained_release_all_tracks_both_modes(self):
        type(self).session=boot_session(self.image,sample_status=(0,)*2048)
        r=exercise_native_notes(type(self).session,progress=getattr(type(self),'progress',None))
        self.assertEqual(len(r['keys']),1536)
        self.assertEqual(len(r['top_mapping']),512)
        self.assertEqual(len(r['retained']),64)
        self.assertEqual(len(r['cancelled']),48)
        self.assertEqual(sum(p['view_mode']==7 for p in r['page_buttons']),64)
        self.assertEqual(len(r['pitch_edits']),64)
        self.assertEqual(len(r['leds']),64)
        self.assertEqual(len(r['length_extensions']),8)
        self.assertEqual(r['midi_faults'],'000000')
        self.assertEqual(r['project_io'],[])
        self.assertEqual(len(r['sample_status_inputs']),r['main_cycles'])
        type(self).report=r


if __name__=='__main__':unittest.main()
