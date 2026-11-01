"""Exact-SYX synthetic timer boundary plus native-reset IRQ/Main regression."""
import hashlib,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'src'),str(ROOT/'tests')]
from patch_firmware import unpack_syx
from test_recovery_timer import TimerPeripheralTests,RecoveryTimerTests


def probe(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    raw=(ROOT/'build/circuitrhythm-5706-phase1-recovery.syx').read_bytes()
    image=unpack_syx(raw,allow_extended=True)['image']
    class PackagedPeripheral(TimerPeripheralTests):
        @classmethod
        def setUpClass(cls):
            super().setUpClass();assert cls.image==image;cls.image=image
    class PackagedTimer(RecoveryTimerTests):
        progress=staticmethod(lambda e:(out/'progress.json').write_text(json.dumps(e),encoding='utf-8'))
        @classmethod
        def setUpClass(cls):
            super().setUpClass();assert cls.image==image;cls.image=image
    with (out/'tests.txt').open('w',encoding='utf-8') as f:
        suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(c) for c in (PackagedPeripheral,PackagedTimer))
        result=unittest.TextTestRunner(stream=f,verbosity=2).run(suite)
    if not result.wasSuccessful() and hasattr(PackagedTimer,'session'):
        s=PackagedTimer.session
        (out/'failure-ram.bin').write_bytes(bytes(s.h.u.mem_read(0x20000000,0x50000)))
        (out/'failure.json').write_text(json.dumps(dict(state=s.snapshot(),inputs=s.inputs,guards=s.guards,
            unmodeled_response=s.h.unmodeled_response,dsp_read=s.h.dsp_read,trace=list(s.h.trace)),indent=2),encoding='utf-8')
    assert result.wasSuccessful()
    r=PackagedTimer.report;r['synthetic_peripheral']=PackagedPeripheral.report
    r.update(syx_sha256=hashlib.sha256(raw).hexdigest(),image_sha256=hashlib.sha256(image).hexdigest(),
        packaged_tests=result.testsRun,hardware_release='NO-GO',firmware_changed=False,device_apis_accessed=False)
    (out/'report.json').write_text(json.dumps(r,indent=2),encoding='utf-8');return r


if __name__=='__main__':
    r=probe(sys.argv[1]);print(json.dumps(dict(tests=2,timer_irqs=len(r['timer_peer']['events']),leds=len(r['leds']),hardware_release='NO-GO')))
    raise SystemExit(2)
