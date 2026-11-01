"""Packaged-image synthetic cancellation probe; NO-GO remains explicit."""
import hashlib
import json
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'scripts'),str(ROOT/'src')]
import test_midi_usb_session as tests
from audit_midi_usb_session_prototype import audit
from trace_midi_usb_session import trace
from patch_firmware import unpack_syx
from probe_sequencer_stop import probe as negative_candidate


def probe(out):
    out=Path(out); out.mkdir(parents=True,exist_ok=True)
    syx=(ROOT/'build/circuitrhythm-5706-phase1-sequencer.syx').read_bytes()
    image=unpack_syx(syx,allow_extended=True)['image']; labels=tests.base.seq.arm_code()[1]
    class PackagedSession(tests.UsbSessionTests):
        @classmethod
        def setUpClass(cls): cls.image,cls.labels=image,labels
    with (out/'tests.txt').open('w',encoding='utf-8') as stream:
        result=unittest.TextTestRunner(stream=stream,verbosity=2).run(
            unittest.defaultTestLoader.loadTestsFromTestCase(PackagedSession))
    assert result.wasSuccessful(),'USB session experiment regression failed'
    report=dict(scope='Native/generated Thumb + explicit synthetic MMIO contract + immutable tagged-job bridge',
        hardware_release='NO-GO',production_integrated=False,
        packaged_syx_sha256=hashlib.sha256(syx).hexdigest(),packaged_image_sha256=hashlib.sha256(image).hexdigest(),
        experimental_tests=result.testsRun,
        software_quiescent_old_tx_cancellation='PASS_UNDER_MMIO_CONTRACT',
        old_tagged_rx_callback_after_reopen='PASS_WITH_IMMUTABLE_JOB_BRIDGE',
        same_epoch_duplicate_and_nested_completion='PASS',
        disable_ack_flush_wait_and_resume_revalidation='PASS_UNDER_MMIO_CONTRACT',
        shared_payload_rx_debt_held_note_preservation='PASS_BY_REFUSAL',
        midi_only_masks_and_tx_fifo1_selection='PASS_LOCAL_MODEL',
        din_native_driver_during_usb_close='PASS_SYNTHETIC',
        raw_stock_completion_compatibility='FAIL_REQUIRES_IRQ_BRIDGE',
        hardware_late_dma_after_barrier='NOT_ESTABLISHED',
        generation_without_dma_barrier='FAIL_EXPECTED_NEGATIVE',
        cancel_with_shared_payload_readers_or_rx_debts='UNSUPPORTED_REFUSED',
        all_inline_writers_full_irq_rtos_and_cache='NOT_ESTABLISHED',
        production_caller_compatibility='FAIL',
        code_audit=audit(out/'audit'),native_contract=trace(out/'stock-contract'),
        unchanged_candidate_probe=negative_candidate(image,labels),
        remaining=[
            'Model disable acknowledgment and TX FIFO flush release the old hardware reader by contract. Real bus-master cancellation/cache visibility is not proven. The negative test shows a stale DMA write corrupts a reused RX buffer even when its callback token is rejected.',
            'Stock26988/268D0 callbacks are untagged and deliberately refused. No complete native IRQ bridge or constructor/reset/disconnect wiring exists. A callback must never borrow the current endpoint token.',
            'Accepted RX debts, partial messages, held notes, fault/Off ownership and active shared SysEx readers refuse closure; they are not silently cleared. General active-transaction cancellation/drain remains open.',
            '1624B synthetic state is not reserved in production. Full boot/OOM, exact silicon/IRQ/DMA/cache semantics, timing, all modes/producers/observers, storage recovery and DIN input remain release gates.',
            'Production firmware remains byte-for-byte unchanged and retains its Off/Stop failure. No physical MIDI/USB/device API was accessed.'
        ])
    (out/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


if __name__=='__main__':
    print(json.dumps(probe(sys.argv[1] if len(sys.argv)>1 else ROOT/'logs/usb-session-probe'),indent=2))
    raise SystemExit(2)
