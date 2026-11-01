"""Packaged candidate plus unchanged experimental overlays; full native loader."""
import hashlib,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'src'),str(ROOT/'scripts')]
import test_midi_usb_long_loop as tests
from patch_firmware import unpack_syx
from audit_midi_usb_carry_prototype import audit
from trace_midi_usb_long_loop import trace
from probe_sequencer_stop import probe as candidate_negative


def probe(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    syx=(ROOT/'build/circuitrhythm-5706-phase1-sequencer.syx').read_bytes()
    image=unpack_syx(syx,allow_extended=True)['image'];labels=tests.base.seq.arm_code()[1]
    class PackagedLongLoop(tests.UsbLongLoopTests):
        @classmethod
        def setUpClass(cls):cls.image,cls.labels,cls.evidence=image,labels,[]
    with (out/'tests.txt').open('w',encoding='utf-8') as f:
        result=unittest.TextTestRunner(stream=f,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(PackagedLongLoop))
    assert result.wasSuccessful(),'Native long-loop tests failed'
    r=dict(scope='Full native128-slot loader/control/WAV path with synthetic file/flash/UI/allocator boundaries',
        hardware_release='NO-GO',production_integrated=False,implementation_changed=False,experimental_tests=result.testsRun,
        packaged_syx_sha256=hashlib.sha256(syx).hexdigest(),packaged_image_sha256=hashlib.sha256(image).hexdigest(),
        full_native_loader='PASS_BOUNDED_BOTH_MODES',sample_double_buffer_and_partial_tail='PASS_RAM_FILE_FLASH_MODEL',
        msc_data_csw='PASS_BOTH_MODES',active_reader_and_nested_worker='PASS_BOUNDED_OWNERSHIP',
        midi_retry_power_progress='MAIN_SERVICE_REQUIRED_NEGATIVE',
        observations=PackagedLongLoop.evidence,code_audit=audit(out/'audit',staging=True),native_contract=trace(out/'stock-contract'),
        unchanged_candidate_probe=candidate_negative(image,labels),
        remaining=['Native file dispatcher task/queue/callback lifetime,real allocator/progress UI,pack mount errors and full43E1C transfer handler remain open.',
                   'Long-loop main reachability/MIDI retry and power latency remain unresolved;no full-service callsite patch was added.',
                   'Production Off/Stop loss,storage partial-read/live-pattern alias,accepted TX ambiguity/raw ALT/parser/held/fault recovery remain.',
                   'Full boot/RTOS/OOM/checked2712B RAM/init,integration and PHY/flash/DIN timing are unproved;no device APIs.'])
    (out/'report.json').write_text(json.dumps(r,indent=2),encoding='utf-8');return r


if __name__=='__main__':
    r=probe(sys.argv[1]);print(json.dumps(dict(tests=r['experimental_tests'],hardware_release=r['hardware_release'],report=str(Path(sys.argv[1])/'report.json'))));raise SystemExit(2)
