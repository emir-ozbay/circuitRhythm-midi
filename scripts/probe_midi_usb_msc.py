"""Packaged candidate + emulator-only MSC CBW cancellation overlay; NO-GO."""
import hashlib,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'scripts'),str(ROOT/'src')]
import test_midi_usb_msc as tests
from patch_firmware import unpack_syx
from audit_midi_usb_msc_prototype import audit
from trace_midi_usb_msc import trace
from probe_sequencer_stop import probe as negative_candidate


def probe(out):
    out=Path(out); out.mkdir(parents=True,exist_ok=True)
    syx=(ROOT/'build/circuitrhythm-5706-phase1-sequencer.syx').read_bytes()
    image=unpack_syx(syx,allow_extended=True)['image']; labels=tests.base.seq.arm_code()[1]
    class PackagedMsc(tests.UsbMscTests):
        @classmethod
        def setUpClass(cls): cls.image,cls.labels=image,labels
    with (out/'tests.txt').open('w',encoding='utf-8') as stream:
        result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(PackagedMsc))
    assert result.wasSuccessful(),'MSC cancellation experiment failed'
    report=dict(scope='Native MSC reset/poll/endpoint/HAL code + synthetic RAM/MMIO; storage Init boundary',
        hardware_release='NO-GO',production_integrated=False,experimental_tests=result.testsRun,
        packaged_syx_sha256=hashlib.sha256(syx).hexdigest(),packaged_image_sha256=hashlib.sha256(image).hexdigest(),
        cbw_receive_cancel_before_native_teardown='PASS_CONDITIONAL_DISABLE_ACK_AHB_FIFO_CONTRACT',
        native_bulk_only_reset_then_single_rearm='PASS_CONDITIONAL_MMIO',
        shared_rx_midi_debt_and_din_retention='PASS',native_msc_irq_cpu_fifo_publication='PASS_CONDITIONAL_MMIO',
        oversized_cbw_cpu_write='GUARDED_FAIL_CLOSED_PRIVATE_SCRATCH',
        storage_commands_and_active_msc_tx='UNSUPPORTED_CLOSED_RETENTION',
        stale_untagged_xfrc_after_broken_barrier='FAIL_EXPECTED_NEGATIVE',
        real_hardware_cancellation='NOT_ESTABLISHED',production_caller_compatibility='FAIL_STORAGE_POWER_TASK_BOOT_AND_RAM_GATES',
        code_audit=audit(out/'audit'),native_contract=trace(out/'stock-contract'),
        unchanged_candidate_probe=negative_candidate(image,labels),
        remaining=['Only31B CBW receive before a storage command is covered. BOT data/CSW/TX and async media work are retained closed, not cancelled.',
                   'MC service and native poll are manually pumped. Main/IRQ task wiring,2168B checked RAM/init,boot/OOM,power state and all class lists remain open.',
                   'The barrier is an explicit MMIO contract. A late untagged old XFRC injected after reopening is still indistinguishable; required negative retained.',
                   'Production firmware is unchanged and still loses Off/Stop under saturation. No physical USB/MIDI/device API. M7 NO-GO.'])
    (out/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


if __name__=='__main__': print(json.dumps(probe(sys.argv[1]),indent=2)); raise SystemExit(2)
