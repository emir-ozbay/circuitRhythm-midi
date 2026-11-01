"""Packaged-image real class parent/composite experiment; always NO-GO."""
import hashlib,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'scripts'),str(ROOT/'src')]
import test_midi_usb_composite as tests
from audit_midi_usb_composite_prototype import audit
from trace_midi_usb_composite import trace
from patch_firmware import unpack_syx
from probe_sequencer_stop import probe as negative_candidate


def probe(out):
    out=Path(out); out.mkdir(parents=True,exist_ok=True)
    syx=(ROOT/'build/circuitrhythm-5706-phase1-sequencer.syx').read_bytes()
    image=unpack_syx(syx,allow_extended=True)['image']; labels=tests.base.seq.arm_code()[1]
    class PackagedComposite(tests.UsbCompositeTests):
        @classmethod
        def setUpClass(cls): cls.image,cls.labels=image,labels
    with (out/'tests.txt').open('w',encoding='utf-8') as stream:
        result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(PackagedComposite))
    assert result.wasSuccessful(),'Native composite experiment failed'
    report=dict(scope='Native static initialization trace + real MIDI/MSC class parents/list/descriptor; synthetic RAM/MMIO; storage Init boundary',
        hardware_release='NO-GO',production_integrated=False,experimental_tests=result.testsRun,
        packaged_syx_sha256=hashlib.sha256(syx).hexdigest(),packaged_image_sha256=hashlib.sha256(image).hexdigest(),
        real_midi_parent_din_queue_retention='PASS_BOUND_CALLSITE',
        midi_msc_init_after_barrier_and_native_teardown='PASS_CONDITIONAL_QUIESCENT_MMIO',
        native_composite_descriptor='PASS_125_BYTES_THREE_INTERFACES',
        reset_between_parents_and_software_ownership='PASS_BY_ABORT_OR_CLOSED_RETENTION',
        unprotected_real_parent_din_loss='FAIL_EXPECTED_NEGATIVE',
        active_msc_cancellation='UNSUPPORTED_REJECTS_INIT_WHILE_ENDPOINT_ACTIVE_OR_COMPLETION_PENDING',
        storage_init='PINNED_NATIVE_RETURN0_BOUNDARY_NO_MEDIA',
        production_caller_compatibility='FAIL_ACTIVE_MSC_POWER_TASK_AND_FULL_BOOT_GATES',
        code_audit=audit(out/'audit'),native_contract=trace(out/'stock-contract'),
        unchanged_candidate_probe=negative_candidate(image,labels),
        remaining=['Active MSC data/cancel/drain and class-specific requests are not covered. Native MSC teardown execution is not a hardware cancellation proof.',
                   'Only the known2-class list is admitted. Main service is manually pumped; full power/scheduler/production state reservation/init is open.',
                   'Stale untagged XFRC after a broken assumed barrier remains a negative in the inherited IRQ/control suite. No device APIs or physical tests.',
                   'Production firmware remains unchanged and loses Off/Stop under saturation. No M7/hardware release.'])
    (out/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


if __name__=='__main__':
    print(json.dumps(probe(sys.argv[1]),indent=2)); raise SystemExit(2)
