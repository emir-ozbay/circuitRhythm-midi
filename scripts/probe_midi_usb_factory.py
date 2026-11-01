"""Packaged candidate + emulation-only native factory experiment; NO-GO."""
import hashlib,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'src'),str(ROOT/'scripts')]
import test_midi_usb_factory as tests
from patch_firmware import unpack_syx
from audit_midi_usb_factory_prototype import audit
from trace_midi_usb_factory import trace
from probe_sequencer_stop import probe as candidate_negative


def probe(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True);syx=(ROOT/'build/circuitrhythm-5706-phase1-sequencer.syx').read_bytes()
    image=unpack_syx(syx,allow_extended=True)['image'];labels=tests.base.seq.arm_code()[1]
    class PackagedFactory(tests.UsbFactoryTests):
        @classmethod
        def setUpClass(cls):cls.image,cls.labels=image,labels
    with (out/'tests.txt').open('w',encoding='utf-8') as f:
        r=unittest.TextTestRunner(stream=f,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(PackagedFactory))
    assert r.wasSuccessful(),'Factory experiment failed'
    report=dict(scope='Native class factory/stop/start/descriptors and HAL prefix; synthetic HAL init/tick/NVIC/clock/flash/RTOS edges',
        hardware_release='NO-GO',production_integrated=False,experimental_tests=r.testsRun,
        packaged_syx_sha256=hashlib.sha256(syx).hexdigest(),packaged_image_sha256=hashlib.sha256(image).hexdigest(),
        midi_only_and_composite_rebuild='PASS_CONDITIONAL_MMIO',native_midi_query_and_msc_read_after_reenumeration='PASS',
        class_list_clear_before_old_reader_retirement='FAIL_EXPECTED_NEGATIVE_UNPROTECTED_NATIVE',
        latest_factory_generation_and_external_reset='PASS',din_and_project_ram='PASS_SYNTHETIC_RAM',
        unsupported_msc_only_or_disabled_lists='REJECTED_WITHOUT_MUTATION',actual_hal_timing_and_full_packs_ui='NOT_ESTABLISHED',
        code_audit=audit(out/'audit'),native_contract=trace(out/'stock-contract'),unchanged_candidate_probe=candidate_negative(image,labels),
        remaining=['HAL init427FC returns0 boundary; native stop/start/init-prefix/FIFO setup and waits execute with synthetic ticks/NVIC/clock memory. Real PLL/PHY/IRQ scheduling unproven.',
                   'Only MIDI-first1/2-class layouts and four low16-bit arguments. No MSC-only/disabled list support or complete indirect/caller/Packs project flow proof.',
                   'Main service is manually pumped;full task/power/boot/OOM,2424B production RAM/init,physical cancellation,storage alias,DIN input and production integration remain gates.',
                   'Production image unchanged with Off/Stop failure. No physical USB/MIDI/device APIs; inherited stale untagged XFRC negative remains. M7 NO-GO.'])
    (out/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8');return report


if __name__=='__main__':print(json.dumps(probe(sys.argv[1]),indent=2));raise SystemExit(2)
