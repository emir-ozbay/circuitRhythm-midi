"""Packaged image + readonly MSC storage overlay; mandatory NO-GO."""
import hashlib,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'src'),str(ROOT/'scripts')]
import test_midi_usb_storage as tests
from patch_firmware import unpack_syx
from audit_midi_usb_storage_prototype import audit
from trace_midi_usb_storage import trace
from probe_sequencer_stop import probe as candidate_negative


def probe(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    syx=(ROOT/'build/circuitrhythm-5706-phase1-sequencer.syx').read_bytes();image=unpack_syx(syx,allow_extended=True)['image']
    class PackagedStorage(tests.UsbStorageTests):
        @classmethod
        def setUpClass(cls): cls.image,cls.labels=image,tests.base.seq.arm_code()[1]
    with (out/'tests.txt').open('w',encoding='utf-8') as f:
        r=unittest.TextTestRunner(stream=f,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(PackagedStorage))
    assert r.wasSuccessful(),'Readonly MSC storage experiment failed'
    report=dict(scope='Native readonly MSC/SCSI/queued backend/drain/worker and USB CPU FIFO; RAM flash + RTOS edges',
        hardware_release='NO-GO',production_integrated=False,experimental_tests=r.testsRun,
        packaged_syx_sha256=hashlib.sha256(syx).hexdigest(),packaged_image_sha256=hashlib.sha256(image).hexdigest(),
        read10_data_csw_and_cancel='PASS_CONDITIONAL_LOWER_FLASH_RTOS_MMIO',
        matching_worker_error_not_last_status='PASS_FAILED_CSW_NO_SUCCESS_DATA',
        original_native_callback_hides_read_error='FAIL_EXPECTED_NEGATIVE',
        write10='REJECTED_BY_PINNED_STOCK_READONLY_CALLBACK',
        buffer_and_csw_reader_lifetime='PASS',stale_tx_xfrc_after_broken_barrier='FAIL_EXPECTED_NEGATIVE',
        actual_flash_rtos_and_hardware_cancellation='NOT_ESTABLISHED',production_caller_compatibility='FAIL_FULL_TASK_CLASS_POWER_BOOT_RAM_GATES',
        code_audit=audit(out/'audit'),native_contract=trace(out/'stock-contract'),unchanged_candidate_probe=candidate_negative(image,tests.base.seq.arm_code()[1]),
        remaining=['Readonly table only; writable rebinding or other media producers are not established. Lower flash copies RAM and wake/yield are explicit synthetic boundaries.',
                   'Native queue/drain/worker and per-read result are real, but real flash/DMA/RTOS latency, interrupts,cache,NVIC and physical cancellation are unproven.',
                   'Only known composite class list/manual service wiring. Full power/boot/OOM,2296B production RAM/init,storage project alias/short-read,DIN input and production integration remain open.',
                   'Production firmware is unchanged and loses Off/Stop; mandatory old untagged XFRC negative retained. No physical device APIs. M7 NO-GO.'])
    (out/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8');return report


if __name__=='__main__': print(json.dumps(probe(sys.argv[1]),indent=2));raise SystemExit(2)
