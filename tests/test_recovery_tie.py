"""Exact recovery image,tie bit/expiry/flush with explicitly synthetic objects."""
import unittest
import test_phase1_safety as base
import midi_recovery_patch as fixed
from patch_firmware import apply_patches
from integrated_midi_test_support import IntegratedMidiFixture
from sequencer_playback_test_support import SequencerPlaybackFixture


class RecoveryTieTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.image=apply_patches(base.load_image(),fixed.build_patches())[0];cls.labels=fixed.seq_code()[1]
    setUp=base.SafetyTests.setUp
    word=base.SafetyTests.word
    read=base.SafetyTests.read
    store=base.SafetyTests.store
    call=base.SafetyTests.call
    instruction_budget=500000
    def setup_player(self,mode):
        self.out=IntegratedMidiFixture(self);self.player=SequencerPlaybackFixture(self,self.out)
        self.u.mem_write(base.seq.SEQ_STATE_ADDR+4,bytes((mode,)))
    def check_wire(self,expected):
        self.out.poll();self.assertEqual(self.out.delivered,[expected]*3)
        self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR+base.seq.OFF_MIDI_CONTEXT_FAULT,3),bytes(3))
    def test_same_pitch_tie_suppresses_retrigger_then_gate_expires_at_both_boundaries(self):
        for mode in (0,1):
            for track in range(8):
                for first,last in ((15,16),(31,0)):
                    with self.subTest(mode=mode,track=track,boundary=(first,last)):
                        self.setUp();self.setup_player(mode)
                        self.player.step(track,first,60,gate=96,tie=1)
                        self.player.step(track,last,60,gate=96,tie=0)
                        self.assertEqual(len(self.player.active(track)),1)
                        expected=[bytes((9,0x90|track,48,96))];self.check_wire(expected)
                        ticks=0
                        while self.player.active(track) and ticks<128:
                            self.player.expire_tick(track);ticks+=1
                        self.assertGreater(ticks,1);self.assertLess(ticks,128)
                        expected.append(bytes((8,0x80|track,48,0)));self.check_wire(expected)
                        self.player.flush(track);self.check_wire(expected)
    def test_tied_different_pitch_is_not_suppressed_and_stop_closes_both(self):
        for mode in (0,1):
            for track in range(8):
                with self.subTest(mode=mode,track=track):
                    self.setUp();self.setup_player(mode)
                    self.player.step(track,31,60,gate=96,tie=1)
                    self.player.step(track,0,61,gate=96,tie=0)
                    self.assertEqual(len(self.player.active(track)),2)
                    expected=[bytes((9,0x90|track,48,96)),bytes((9,0x90|track,49,96))]
                    self.check_wire(expected);self.player.flush(track)
                    self.assertEqual(self.player.active(track),[])
                    expected.extend((bytes((8,0x80|track,48,0)),bytes((8,0x80|track,49,0))))
                    self.check_wire(expected)
    def test_untied_same_pitch_retriggers_off_before_on_at_both_boundaries(self):
        for mode in (0,1):
            for track in range(8):
                for first,last in ((15,16),(31,0)):
                    with self.subTest(mode=mode,track=track,boundary=(first,last)):
                        self.setUp();self.setup_player(mode)
                        self.player.step(track,first,60,gate=96,tie=0)
                        self.player.step(track,last,60,gate=96,tie=0)
                        self.assertEqual(len(self.player.active(track)),1)
                        expected=[bytes((9,0x90|track,48,96)),bytes((8,0x80|track,48,0)),bytes((9,0x90|track,48,96))]
                        self.check_wire(expected);self.player.flush(track)
                        expected.append(bytes((8,0x80|track,48,0)));self.check_wire(expected)


if __name__=='__main__':unittest.main()
