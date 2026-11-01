"""Packaged-image native main task experiment with explicit unresolved debt."""
import hashlib,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'src'),str(ROOT/'scripts')]
import test_midi_usb_task as tests
from patch_firmware import unpack_syx
from audit_midi_usb_task_prototype import audit
from trace_midi_usb_task import trace
from probe_sequencer_stop import probe as candidate_negative


def probe(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True);syx=(ROOT/'build/circuitrhythm-5706-phase1-sequencer.syx').read_bytes()
    image=unpack_syx(syx,allow_extended=True)['image'];labels=tests.base.seq.arm_code()[1]
    class PackagedTask(tests.UsbTaskTests):
        @classmethod
        def setUpClass(cls):cls.image,cls.labels=image,labels
    with (out/'tests.txt').open('w',encoding='utf-8') as f:
        r=unittest.TextTestRunner(stream=f,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(PackagedTask))
    assert r.wasSuccessful(),'Task experiment failed'
    report=dict(scope='Native main25870..25880 and worker648AE..648B8; synthetic RTOS/IRQ/ACK/flash boundaries',hardware_release='NO-GO',
        production_integrated=False,experimental_tests=r.testsRun,packaged_syx_sha256=hashlib.sha256(syx).hexdigest(),
        packaged_image_sha256=hashlib.sha256(image).hexdigest(),main_reachability_and_read_query_progress='PASS_CONDITIONAL_EMULATION',
        worker_irq_and_nested_service_ownership='PASS',unwired_main_power_and_retry='FAIL_EXPECTED_NEGATIVE_WITHOUT_HOOK',
        pending_ledger_debt_at_suspend_then_wake='FAIL_EXPECTED_BOUNDED_RECOVERY_STALL',
        code_audit=audit(out/'audit'),native_contract=trace(out/'stock-contract'),unchanged_candidate_probe=candidate_negative(image,labels),
        remaining=['Closure with retained ledger/queued TX debt remains stalled even after wake;64 native main passes show no progress. Do not bypass ownership/barrier checks.',
                   'Only main2587C wired;2DE92/53E78 caller contexts, full task loop/RTOS priorities/wake dispatch and boot/OOM are unproven.',
                   'Worker loop is native but its wait/return is modeled; ACK/flush/PHY/clock/IRQ/NVIC/RTOS/lower flash remain boundaries.2584B checked production RAM/init missing.',
                   'Production Off/Stop, storage short-read/live-pattern alias,DIN input/integration and stale untagged XFRC after broken barrier remain. No device APIs; M7 NO-GO.'])
    (out/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8');return report


if __name__=='__main__':print(json.dumps(probe(sys.argv[1]),indent=2));raise SystemExit(2)
