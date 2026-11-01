"""Same native Stop scenario and polling budget,base versus integrated SYX."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'scripts'),str(ROOT/'src')]
import seq_Patch as seq
import midi_recovery_patch as integrated
from patch_firmware import unpack_syx
from probe_sequencer_stop import probe as stop_probe


def probe(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    base_path=ROOT/'build/circuitrhythm-5706-phase1-sequencer.syx'
    fixed_path=ROOT/'build/circuitrhythm-5706-phase1-recovery.syx'
    raw=fixed_path.read_bytes();base=unpack_syx(base_path.read_bytes(),allow_extended=True)['image']
    fixed=unpack_syx(raw,allow_extended=True)['image']
    before=stop_probe(base,seq.arm_code()[1],poll_rounds=128,instruction_budget=500000)
    after=stop_probe(fixed,integrated.seq_code()[1],poll_rounds=128,instruction_budget=500000)
    assert before['note_off_delivery']==before['stop_delivery']=='FAIL'
    assert after['note_off_delivery']==after['stop_delivery']=='PASS'
    report=dict(scope='Native63/64-note Stop burst and single-buffer F8+FC,both modes,three ready driver boundaries,128 native output polls;no recovery overlays',
        hardware_release='NO-GO',firmware_integrated=True,physical_test=False,
        candidate_syx_sha256=hashlib.sha256(raw).hexdigest(),before=before,after=after,
        result='FAIL_TO_PASS',remaining='Hardware release requires boot/OOM/timing/USB-session and remaining Phase1 gates;fault quarantine persists until reboot.')
    (out/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8');return report


if __name__=='__main__':
    r=probe(sys.argv[1]);print(json.dumps(dict(result=r['result'],note_off=r['after']['note_off_delivery'],stop=r['after']['stop_delivery'],hardware_release=r['hardware_release'])));raise SystemExit(2)
