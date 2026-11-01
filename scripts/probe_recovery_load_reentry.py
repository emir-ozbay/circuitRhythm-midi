"""Exact-SYX Close-confirmed Projects Load/New recovery acceptance. Offline; M7 remains NO-GO."""
import hashlib,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'src'),str(ROOT/'tests')]
from patch_firmware import unpack_syx
from test_recovery_load_reentry import RecoveryLoadReentryTests


def probe(out,mode):
    assert mode in (0,1)
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    raw=(ROOT/'build/circuitrhythm-5706-phase1-recovery.syx').read_bytes()
    image=unpack_syx(raw,allow_extended=True)['image']
    class PackagedReentry(RecoveryLoadReentryTests):
        progress=staticmethod(lambda e:(out/'progress.json').write_text(json.dumps(e),encoding='utf-8'))
        @classmethod
        def setUpClass(cls):super().setUpClass();assert cls.image==image;cls.image=image
    PackagedReentry.mode=mode
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(PackagedReentry)
    with (out/'tests.txt').open('w',encoding='utf-8') as f:result=unittest.TextTestRunner(stream=f,verbosity=2).run(suite)
    if not result.wasSuccessful() and hasattr(PackagedReentry,'session'):
        s=PackagedReentry.session
        (out/'failure-ram.bin').write_bytes(bytes(s.h.u.mem_read(0x20000000,0x50000)))
        (out/'failure.json').write_text(json.dumps(dict(state=s.snapshot(),debug=getattr(s,'reentry_debug',getattr(s,'load_debug',{})),trace=list(s.h.trace)),indent=2),encoding='utf-8')
    assert result.wasSuccessful()
    r=PackagedReentry.report;r.update(packaged_tests=result.testsRun,syx_sha256=hashlib.sha256(raw).hexdigest(),image_sha256=hashlib.sha256(image).hexdigest())
    (out/'report.json').write_text(json.dumps(r,indent=2),encoding='utf-8');return r


if __name__=='__main__':
    r=probe(sys.argv[1],int(sys.argv[2]))
    print(json.dumps(dict(mode=r['mode'],tests=r['packaged_tests'],cycles=r['total_cycles'],hardware_release='NO-GO')))
    raise SystemExit(2)
