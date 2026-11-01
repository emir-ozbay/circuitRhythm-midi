"""Run packaged native UI Load + SyncAll + Mutate + IRQ66 tie verification."""
import hashlib,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'scripts'),str(ROOT/'src')]
import test_recovery_native_tie as tie_tests
from patch_firmware import unpack_syx


def main(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    syx=(ROOT/'build/circuitrhythm-5706-phase1-recovery.syx').read_bytes()
    image=unpack_syx(syx,allow_extended=True)['image']
    progress_path=out/'progress.json'
    def progress(status):
        progress_path.write_text(json.dumps(status,indent=2),encoding='utf-8')
    class PackagedNativeTie(tie_tests.RecoveryNativeTieTests):
        @classmethod
        def setUpClass(cls):cls.image=image;cls.progress= staticmethod(progress)
    with (out/'tests.txt').open('w',encoding='utf-8') as f:
        suite=unittest.defaultTestLoader.loadTestsFromTestCase(PackagedNativeTie)
        result=unittest.TextTestRunner(stream=f,verbosity=2).run(suite)
    if not result.wasSuccessful():raise SystemExit(1)
    report=dict(PackagedNativeTie.report,hardware_release='NO-GO',packaged_tests=result.testsRun,
        syx_sha256=hashlib.sha256(syx).hexdigest(),image_sha256=hashlib.sha256(image).hexdigest())
    (out/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(dict(tests=result.testsRun,runs=len(report['runs']),
        mutations=len(report['mutations']),hardware_release='NO-GO')))
    raise SystemExit(2)


if __name__=='__main__':
    main(sys.argv[1] if len(sys.argv)>1 else ROOT/'logs/recovery-native-tie-20261101/probe')
