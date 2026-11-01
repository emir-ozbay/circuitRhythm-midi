"""One exact-SYX native-reset live edit test;never accesses a device."""
import hashlib,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'src'),str(ROOT/'tests')]
from patch_firmware import unpack_syx
from test_recovery_running_edits import RecoveryRunningEditTests


def probe(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    raw=(ROOT/'build/circuitrhythm-5706-phase1-recovery.syx').read_bytes();image=unpack_syx(raw,allow_extended=True)['image']
    class PackagedRunningEdit(RecoveryRunningEditTests):
        progress=staticmethod(lambda e:(out/'progress.json').write_text(json.dumps(e),encoding='utf-8'))
        @classmethod
        def setUpClass(cls):super().setUpClass();assert cls.image==image;cls.image=image
    with (out/'tests.txt').open('w',encoding='utf-8') as f:
        result=unittest.TextTestRunner(stream=f,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(PackagedRunningEdit))
    if not result.wasSuccessful() and hasattr(PackagedRunningEdit,'session'):
        s=PackagedRunningEdit.session
        (out/'failure-ram.bin').write_bytes(bytes(s.h.u.mem_read(0x20000000,0x50000)))
        (out/'failure.json').write_text(json.dumps(dict(state=s.snapshot(),inputs=s.inputs,debug=s.running_edit_debug,trace=list(s.h.trace)),indent=2),encoding='utf-8')
    assert result.wasSuccessful()
    r=PackagedRunningEdit.report;r.update(syx_sha256=hashlib.sha256(raw).hexdigest(),image_sha256=hashlib.sha256(image).hexdigest(),
        packaged_tests=result.testsRun,firmware_changed=False,device_apis_accessed=False,hardware_release='NO-GO')
    (out/'report.json').write_text(json.dumps(r,indent=2),encoding='utf-8');return r


if __name__=='__main__':
    r=probe(sys.argv[1]);print(json.dumps(dict(tests=r['packaged_tests'],timer_events=r['timer_events'],midi_faults=r['midi_faults'],hardware_release='NO-GO')))
    raise SystemExit(2)
