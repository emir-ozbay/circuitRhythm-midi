"""Synthetic-RAM physical ownership policy around the native cleanup call.

Stock update is an observed leaf here;actual Note1/7 routing/release is tested
separately after native reset. No claim of a full native graph in this fixture.
"""
import unittest
import test_phase1_safety as base


class NoteCleanupTests(unittest.TestCase):
    setUpClass=classmethod(base.SafetyTests.setUpClass.__func__)
    setUp=base.SafetyTests.setUp
    word=base.SafetyTests.word
    read=base.SafetyTests.read
    call=base.SafetyTests.call

    def test_cleanup_retains_nonstep_physical_ownership_in_all_old_modes(self):
        for enabled in (0,1):
            for mode in range(11):
                with self.subTest(enabled=enabled,mode=mode):
                    self.setUp();grid=0x20005000
                    self.u.mem_write(base.seq.SEQ_STATE_ADDR+4,bytes([enabled]))
                    self.word(grid+0x228,0x81000081)
                    self.u.mem_write(base.seq.STOCK_GRID_MODE_UPDATE,bytes.fromhex('7047'))
                    self.word(0x20040000,7)
                    self.call(self.labels['c_grid_mode_cleanup'],grid,0,mode,0)
                    step_mask=(0xFFFFFFFF if enabled and mode==0 else 0xFFFF if mode in (0,1,2,3,5,6) else 0)
                    self.assertEqual(self.read(grid+0x228),0x81000081&~step_mask)


if __name__=='__main__':unittest.main()
