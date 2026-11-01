"""One fresh exact-SYX64-voice native Stop case;no device access."""
import hashlib,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'src'),str(ROOT/'tests')]
from patch_firmware import unpack_syx
from test_recovery_dense_stop import RecoveryDenseStopTests


def probe(out,mode=0,before_output=True):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    raw=(ROOT/'build/circuitrhythm-5706-phase1-recovery.syx').read_bytes();image=unpack_syx(raw,allow_extended=True)['image']
    class PackagedDenseStop(RecoveryDenseStopTests):
        progress=staticmethod(lambda e:(out/'progress.json').write_text(json.dumps(e),encoding='utf-8'))
        @classmethod
        def setUpClass(cls):
            super().setUpClass();assert cls.image==image;cls.image=image
    PackagedDenseStop.mode=mode;PackagedDenseStop.before_output=before_output
    with (out/'tests.txt').open('w',encoding='utf-8') as f:
        result=unittest.TextTestRunner(stream=f,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(PackagedDenseStop))
    if not result.wasSuccessful() and hasattr(PackagedDenseStop,'session'):
        s=PackagedDenseStop.session
        (out/'failure-ram.bin').write_bytes(bytes(s.h.u.mem_read(0x20000000,0x50000)))
        (out/'failure.json').write_text(json.dumps(dict(state=s.snapshot(),inputs=s.inputs,guards=s.guards,
            unmodeled_response=s.h.unmodeled_response,dsp_read=s.h.dsp_read,trace=list(s.h.trace)),indent=2),encoding='utf-8')
    assert result.wasSuccessful()
    r=PackagedDenseStop.report;r.update(syx_sha256=hashlib.sha256(raw).hexdigest(),image_sha256=hashlib.sha256(image).hexdigest(),
        packaged_tests=result.testsRun,firmware_changed_by_probe=False,device_apis_accessed=False,hardware_release='NO-GO')
    (out/'report.json').write_text(json.dumps(r,indent=2),encoding='utf-8');return r


if __name__=='__main__':
    r=probe(sys.argv[1],int(sys.argv[2]) if len(sys.argv)>2 else 0,len(sys.argv)<4 or sys.argv[3]!='after-output')
    print(json.dumps(dict(voices=64,midi_faults=r['midi_faults'],before_output=r['before_output'],mode=r['mode'],hardware_release='NO-GO')))
    raise SystemExit(2)
