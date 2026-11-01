"""Packaged candidate plus power emulator overlay; never a release image."""
import hashlib,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'src'),str(ROOT/'scripts')]
import test_midi_usb_power as tests
from patch_firmware import unpack_syx
from audit_midi_usb_power_prototype import audit
from trace_midi_usb_power import trace
from probe_sequencer_stop import probe as candidate_negative


def probe(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True);syx=(ROOT/'build/circuitrhythm-5706-phase1-sequencer.syx').read_bytes()
    image=unpack_syx(syx,allow_extended=True)['image'];labels=tests.base.seq.arm_code()[1]
    class PackagedPower(tests.UsbPowerTests):
        @classmethod
        def setUpClass(cls):cls.image,cls.labels=image,labels
    with (out/'tests.txt').open('w',encoding='utf-8') as f:
        r=unittest.TextTestRunner(stream=f,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(PackagedPower))
    assert r.wasSuccessful(),'Power experiment failed'
    report=dict(scope='Normal suspend/wakeup with native state save/restore/ungate; synthetic clock/MMIO/IRQ/RTOS/flash',
        hardware_release='NO-GO',production_integrated=False,experimental_tests=r.testsRun,
        packaged_syx_sha256=hashlib.sha256(syx).hexdigest(),packaged_image_sha256=hashlib.sha256(image).hexdigest(),
        suspend_after_reader_retirement='PASS_CONDITIONAL_MMIO',early_wake_and_reset_generation='PASS',
        midi_only_and_composite_resume='PASS',native_early_clock_stop='FAIL_EXPECTED_NEGATIVE_UNPROTECTED_NATIVE',
        deep_stop_lpm_dma='UNSUPPORTED_FAIL_CLOSED',code_audit=audit(out/'audit'),native_contract=trace(out/'stock-contract'),
        unchanged_candidate_probe=candidate_negative(image,labels),
        remaining=['No real clock/PLL/PHY/wakeup reachability/interrupt timing proof; ACK/flush/NVIC/RTOS/lower flash remain synthetic boundaries.',
                   'Normal CPU-FIFO/handle low-power flag0 only. LPM/deep stop/remote wake policy/full power graph and full Packs UI not established.',
                   'Main service manually pumped;2520B production RAM/init and task/boot/OOM/real backend/storage alias/DIN input/integration gates remain.',
                   'Production Off/Stop failure and untagged stale XFRC after broken barrier remain. Stock/candidate unchanged; no device APIs; M7 NO-GO.'])
    (out/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8');return report


if __name__=='__main__':print(json.dumps(probe(sys.argv[1]),indent=2));raise SystemExit(2)
