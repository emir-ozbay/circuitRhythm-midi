"""Run the Note regression once against the exact packaged SYX."""
import hashlib,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'src'),str(ROOT/'tests')]
from patch_firmware import unpack_syx
from test_recovery_notes import RecoveryNotesTests


def probe(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    raw=(ROOT/'build/circuitrhythm-5706-phase1-recovery.syx').read_bytes()
    image=unpack_syx(raw,allow_extended=True)['image']
    class PackagedNotes(RecoveryNotesTests):
        progress=staticmethod(lambda event:(out/'progress.json').write_text(json.dumps(event),encoding='utf-8'))
        @classmethod
        def setUpClass(cls):
            super().setUpClass()
            assert cls.image==image,'source codegen differs from packaged SYX'
            cls.image=image
    with (out/'tests.txt').open('w',encoding='utf-8') as f:
        result=unittest.TextTestRunner(stream=f,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(PackagedNotes))
    if not result.wasSuccessful() and hasattr(PackagedNotes,'session'):
        s=PackagedNotes.session
        (out/'failure-ram.bin').write_bytes(bytes(s.h.u.mem_read(0x20000000,0x50000)))
        (out/'failure.json').write_text(json.dumps(dict(state=s.snapshot(),inputs=s.inputs,guards=s.guards),indent=2),encoding='utf-8')
    assert result.wasSuccessful()
    r=PackagedNotes.report
    r.update(syx_sha256=hashlib.sha256(raw).hexdigest(),image_sha256=hashlib.sha256(image).hexdigest(),
        packaged_tests=result.testsRun,hardware_release='NO-GO',firmware_changed=True,device_apis_accessed=False)
    (out/'report.json').write_text(json.dumps(r,indent=2),encoding='utf-8');return r


if __name__=='__main__':
    r=probe(sys.argv[1]);print(json.dumps(dict(keys=len(r['keys']),retained=len(r['retained']),hardware_release='NO-GO')))
    raise SystemExit(2)
