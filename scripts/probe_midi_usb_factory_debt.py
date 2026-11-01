"""Packaged candidate plus existing staging/factory prototypes with MIDI debt."""
import hashlib,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'src'),str(ROOT/'scripts')]
import test_midi_usb_factory_debt as tests
from patch_firmware import unpack_syx
from audit_midi_usb_carry_prototype import audit
from trace_midi_usb_factory_debt import trace
from probe_sequencer_stop import probe as candidate_negative


def probe(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    syx=(ROOT/'build/circuitrhythm-5706-phase1-sequencer.syx').read_bytes()
    image=unpack_syx(syx,allow_extended=True)['image'];labels=tests.base.seq.arm_code()[1]
    class PackagedFactoryDebt(tests.UsbFactoryDebtTests):
        @classmethod
        def setUpClass(cls):cls.image,cls.labels,cls.evidence=image,labels,[]
    with (out/'tests.txt').open('w',encoding='utf-8') as f:
        r=unittest.TextTestRunner(stream=f,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(PackagedFactoryDebt))
    assert r.wasSuccessful(),'Factory with retained MIDI debt failed'
    report=dict(scope='Existing staging carry across native factory changes with unsubmitted MIDI debt; synthetic RAM/MMIO',
        hardware_release='NO-GO',production_integrated=False,experimental_tests=r.testsRun,
        packaged_syx_sha256=hashlib.sha256(syx).hexdigest(),packaged_image_sha256=hashlib.sha256(image).hexdigest(),
        implementation_changed=False,retained_main_both_class_directions='PASS',normal_and_sequencer='PASS',
        pending_queries_and_committed_clock_stop='PASS_NO_REPLAY',staged_note_off='PASS',
        native_settings_and_boot_wrapper='PASS_SYNTHETIC_STORE',
        active_msc_read_and_missing_ack='CANCEL_READER_BEFORE_CLASS_MUTATION',
        newer_request_and_native_reset_irq_during_factory='PASS',
        already_accepted_tx_and_missing_staging='NEGATIVE_CONTROLS_RETAINED',
        streams=PackagedFactoryDebt.evidence,code_audit=audit(out/'audit',staging=True),native_contract=trace(out/'stock-contract'),
        unchanged_candidate_probe=candidate_negative(image,labels),
        remaining=['This closes only bounded factory/class changes with unsubmitted MAIN/owned cursor/ledger debt. Actual Packs UI/project operations were not executed.',
                   'Accepted MIDI TX ambiguity,raw ALT mode,partial parser/held input/genuine port fault recovery and other poll callers remain open.',
                   'CPU FIFO with modeled ACK/flush/clock/tick/RTOS/lower flash/UART drain;no physical receiver/timing proof.',
                   'Production Off/Stop loss,storage partial-read/live-pattern alias,2712B checked production RAM/init/full boot and integration remain. No device APIs;M7 NO-GO.'])
    (out/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8');return report


if __name__=='__main__':print(json.dumps(probe(sys.argv[1]),indent=2));raise SystemExit(2)
