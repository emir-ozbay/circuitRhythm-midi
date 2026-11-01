"""Run the native view regression once against the exact current SYX."""
import hashlib,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'src'),str(ROOT/'tests')]
from patch_firmware import unpack_syx
from test_recovery_views import RecoveryViewsTests


def probe(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    raw=(ROOT/'build/circuitrhythm-5706-phase1-recovery.syx').read_bytes()
    image=unpack_syx(raw,allow_extended=True)['image']
    class PackagedViews(RecoveryViewsTests):
        progress=staticmethod(lambda event:(out/'progress.json').write_text(json.dumps(event),encoding='utf-8'))
        @classmethod
        def setUpClass(cls):
            super().setUpClass()
            assert cls.image==image,'source codegen does not match packaged SYX'
            cls.image=image
    with (out/'tests.txt').open('w',encoding='utf-8') as f:
        result=unittest.TextTestRunner(stream=f,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(PackagedViews))
    probe.last_session=getattr(PackagedViews,'session',None)
    if not result.wasSuccessful() and probe.last_session is not None:
        session=probe.last_session
        from seq_Patch import SEQ_STATE_ADDR
        (out/'failure-ram.bin').write_bytes(bytes(session.h.u.mem_read(0x20000000,0x50000)))
        (out/'failure.json').write_text(json.dumps(dict(state=session.snapshot(),inputs=session.inputs,
            guards=session.guards,seq_state=bytes(session.h.u.mem_read(SEQ_STATE_ADDR,256)).hex()),indent=2),encoding='utf-8')
    assert result.wasSuccessful()
    report=PackagedViews.report
    report.update(syx_sha256=hashlib.sha256(raw).hexdigest(),image_sha256=hashlib.sha256(image).hexdigest(),
                  hardware_release='NO-GO',firmware_changed=False,packaged_tests=result.testsRun,device_apis_accessed=False)
    (out/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


if __name__=='__main__':
    r=probe(sys.argv[1]);print(json.dumps(dict(cases=len(r['cases']),top_mappings=len(r['top_mapping']),inputs=len(r['inputs']),hardware_release='NO-GO')))
    raise SystemExit(2)
