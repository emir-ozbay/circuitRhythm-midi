"""Packaged candidate plus unsubmitted-debt carry experiment; NO-GO."""
import hashlib,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'src'),str(ROOT/'scripts')]
import test_midi_usb_carry as tests
from patch_firmware import unpack_syx
from audit_midi_usb_carry_prototype import audit
from trace_midi_usb_carry import trace
from probe_sequencer_stop import probe as candidate_negative


def probe(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True);syx=(ROOT/'build/circuitrhythm-5706-phase1-sequencer.syx').read_bytes()
    image=unpack_syx(syx,allow_extended=True)['image'];labels=tests.base.seq.arm_code()[1]
    class PackagedCarry(tests.UsbCarryTests):
        @classmethod
        def setUpClass(cls):cls.image,cls.labels=image,labels
    with (out/'tests.txt').open('w',encoding='utf-8') as f:
        r=unittest.TextTestRunner(stream=f,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(PackagedCarry))
    assert r.wasSuccessful(),'Carry experiment failed'
    report=dict(scope='Unsubmitted logical MIDI debt across full modeled USB cancellation; native main/parser/driver/IRQ code',hardware_release='NO-GO',
        production_integrated=False,experimental_tests=r.testsRun,packaged_syx_sha256=hashlib.sha256(syx).hexdigest(),
        packaged_image_sha256=hashlib.sha256(image).hexdigest(),previous_task_debt_counterexample='PASS_WITH_CARRY_OVERLAY',
        normal_and_sequencer_mode='PASS',reset_sleep_repeated_epochs_and_irq_races='PASS_CONDITIONAL_MMIO',
        payload360_note_off_clock_stop_and_wrapped_owed_record='PASS_MODELED_IRQ_COMPLETION_STREAM',
        inflight_staged_partial_parser_and_real_fault='CARRY_NOT_ADMITTED_NEGATIVES_PRESERVED',
        code_audit=audit(out/'audit'),native_contract=trace(out/'stock-contract'),unchanged_candidate_probe=candidate_negative(image,labels),
        remaining=['Carry eligibility is bounded: no in-flight TX/staging/partial native TX cursor, idle parser/no held input/no genuine fault. Ambiguous already-submitted delivery is not replayed or claimed fixed.',
                   'Legacy no-carry logical-idle cancellation behavior remains;original task negative still reproduces without this overlay. Production Off/Stop failure unchanged.',
                   'Native parser/driver/IRQ/worker spans with synthetic clock/PHY/disable ACK/flush/RTOS/lower flash and UART drain; no actual host receiver/UART IRQ/timing proof.',
                   '2712B checked production RAM/init,full boot/OOM/task/other poll callers/Packs/project/storage alias/DIN input/integration and stale XFRC physical barrier remain. No device APIs; M7 NO-GO.'])
    (out/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8');return report


if __name__=='__main__':print(json.dumps(probe(sys.argv[1]),indent=2));raise SystemExit(2)
