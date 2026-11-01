"""Packaged firmware plus optional MAIN staging carry; emulator only, NO-GO."""
import hashlib,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'src'),str(ROOT/'scripts')]
import test_midi_usb_staging as tests
import test_midi_usb_carry as prior
from midi_usb_carry_test_support import UsbCarryFixture
from patch_firmware import unpack_syx
from audit_midi_usb_carry_prototype import audit
from trace_midi_usb_staging import trace
from probe_sequencer_stop import probe as candidate_negative


def probe(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    syx=(ROOT/'build/circuitrhythm-5706-phase1-sequencer.syx').read_bytes()
    image=unpack_syx(syx,allow_extended=True)['image'];labels=tests.base.seq.arm_code()[1]
    class PackagedStaging(tests.UsbStagingTests):
        @classmethod
        def setUpClass(cls):cls.image,cls.labels=image,labels
    class CarryRegression(prior.UsbCarryTests):
        @classmethod
        def setUpClass(cls):cls.image,cls.labels=image,labels
        def setup_carry(self):self.setup_task();self.cy=UsbCarryFixture(self,staging=True)
    suites=[unittest.defaultTestLoader.loadTestsFromTestCase(t) for t in (PackagedStaging,CarryRegression)]
    with (out/'tests.txt').open('w',encoding='utf-8') as f:
        r=unittest.TextTestRunner(stream=f,verbosity=2).run(unittest.TestSuite(suites))
    assert r.wasSuccessful(),'Staging carry experiment failed'
    report=dict(scope='Native formatter and rejected pre-submit MAIN preservation, synthetic RAM/MMIO',
        hardware_release='NO-GO',production_integrated=False,experimental_tests=r.testsRun,
        new_staging_scenarios=12,previous_carry_scenarios_with_staging_variant=15,
        packaged_syx_sha256=hashlib.sha256(syx).hexdigest(),packaged_image_sha256=hashlib.sha256(image).hexdigest(),
        previous_native_loss_counterexample='REPRODUCED_WITHOUT_STAGING_GUARD',
        prepared_main_partial_cursor_sleep_reset='PASS_WITH_STAGING_VARIANT',
        completed_chunks_and_committed_realtime='NO_REPLAY_MODELED_STREAM',
        already_admitted_transfer='STRICT_NEGATIVE_RETAINED',
        code_audit=audit(out/'audit',staging=True),native_contract=trace(out/'stock-contract'),
        unchanged_candidate_probe=candidate_negative(image,labels),
        remaining=['Already submitted delivery ambiguity/raw ALT buffer/partial parser/held input/genuine fault recovery remain unsolved.',
                   'Production Off/Stop still FAIL. No production builder integration or checked RAM/init/full boot.',
                   'CPU FIFO and explicit clock/ACK/flush/RTOS/lower flash/UART drain model. No physical host receiver/PHY/UART IRQ/timing proof.',
                   'Factory/Packs with retained debt,other poll callers,storage alias,DIN input and complete M7 validation remain.'])
    (out/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8');return report


if __name__=='__main__':print(json.dumps(probe(sys.argv[1]),indent=2));raise SystemExit(2)
