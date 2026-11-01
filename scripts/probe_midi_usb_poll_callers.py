"""Packaged candidate plus existing prototypes; native extra MSC callers."""
import hashlib,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'src'),str(ROOT/'scripts')]
import test_midi_usb_poll_callers as tests
from patch_firmware import unpack_syx
from audit_midi_usb_carry_prototype import audit
from trace_midi_usb_poll_callers import trace
from probe_sequencer_stop import probe as candidate_negative


def probe(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    syx=(ROOT/'build/circuitrhythm-5706-phase1-sequencer.syx').read_bytes()
    image=unpack_syx(syx,allow_extended=True)['image'];labels=tests.base.seq.arm_code()[1]
    class PackagedPollCallers(tests.UsbPollCallerTests):
        @classmethod
        def setUpClass(cls):cls.image,cls.labels,cls.evidence=image,labels,[]
    with (out/'tests.txt').open('w',encoding='utf-8') as f:
        r=unittest.TextTestRunner(stream=f,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(PackagedPollCallers))
    assert r.wasSuccessful(),'Native poll caller ownership tests failed'
    report=dict(scope='Bounded native callback/dispatch/callsite admission with synthetic owner/MMIO/RTOS boundaries',
        hardware_release='NO-GO',production_integrated=False,experimental_tests=r.testsRun,implementation_changed=False,
        packaged_syx_sha256=hashlib.sha256(syx).hexdigest(),packaged_image_sha256=hashlib.sha256(image).hexdigest(),
        native_callback_read_data_csw='PASS_BOTH_MODES',worker_irq_masked_and_recursive_reentry='PASS',
        closure_inside_poll_worker_completion_irq_factory_sleep='PASS_BOUNDED_OWNERSHIP',
        callback_only_main_service='DOES_NOT_PROGRESS_NEGATIVE',other53e78_leaf='GUARDS_PASS_FULL_53E24_NOT_RUN',
        observations=PackagedPollCallers.evidence,code_audit=audit(out/'audit',staging=True),native_contract=trace(out/'stock-contract'),
        unchanged_candidate_probe=candidate_negative(image,labels),
        remaining=['Full43E1C transfer handler/Packs UI and callback object lifetime not executed. Callback-only progress for retry/power remains dependent on main reachability.',
                   '53E24 full loop/storage owner graph,other indirect callers,RTOS/boot/checked2712B RAM-init and integration remain open.',
                   'Accepted MIDI TX ambiguity/raw ALT/partial parser/held input/fault recovery,production Off/Stop loss and storage partial-read/live-pattern alias remain.',
                   'Native byte streams over modeled ACK/flush/clock/RTOS/lower flash/UART drain;no physical receiver/timing proof;no device APIs.'])
    (out/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8');return report


if __name__=='__main__':print(json.dumps(probe(sys.argv[1]),indent=2));raise SystemExit(2)
