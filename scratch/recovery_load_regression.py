"""Bounded exact-SYX regressions for failed-Load changes;no native long suite."""
import sys,json,unittest,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'src'),str(ROOT/'tests')]
from patch_firmware import unpack_syx
import midi_recovery_patch as fixed
import test_shared_project as shared
import test_note_cleanup as cleanup
import test_integrated_midi_recovery as midi
import test_dense_stop_patch as dense
import test_project_load_guard as guard
import verify_phase1_candidate as phase

out=ROOT/'logs/recovery-load-short-read-20261031/regression'
out.mkdir(exist_ok=False)
raw=(ROOT/'build/circuitrhythm-5706-phase1-recovery.syx').read_bytes()
image=unpack_syx(raw,allow_extended=True)['image'];labels=fixed.seq_code()[1]
suite=unittest.TestSuite();excluded=[]
for c in (shared.SharedProjectTests,cleanup.NoteCleanupTests,midi.IntegratedRecoveryTests,dense.DenseStopPatchTests,guard.ProjectLoadGuardTests):
    def setup(cls):cls.image,cls.labels=image,labels
    packaged=type('Packaged'+c.__name__,(c,),dict(setUpClass=classmethod(setup)))
    for t in unittest.defaultTestLoader.loadTestsFromTestCase(packaged):
        if t._testMethodName=='test_primask_restored_and_commit_serialized_voice_calls_outside_lock':
            excluded.append(dict(test=t.id(),reason='historical test reads CPU registers in a memory-write hook;not executed'))
        else:suite.addTest(t)
with (out/'tests.txt').open('w') as f:result=unittest.TextTestRunner(stream=f,verbosity=2).run(suite)
assert result.wasSuccessful()
criteria={}
for name in ('run_criterion_1_mode_toggle','run_criterion_2_32pad_step_toggle','run_criterion_3_32step_led_compositor',
             'run_criterion_4_velocity_gate_preservation','run_criterion_5_shared_projects','run_criterion_6_sample_engine_muting'):
    criteria[name]=getattr(phase,name)(image,labels);assert criteria[name]['status']=='PASS'
report=dict(tests=result.testsRun,excluded=excluded,criteria=criteria,syx_sha256=hashlib.sha256(raw).hexdigest(),hardware_release='NO-GO')
(out/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(dict(tests=result.testsRun,criteria=len(criteria))))
