"""Packaged-image RX lifecycle guards; active TX disconnect remains negative."""
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'scripts'),str(ROOT/'src')]
import test_midi_usb_lifecycle as tests
from audit_midi_usb_lifecycle_prototype import audit
from trace_midi_usb_lifecycle import trace
from patch_firmware import unpack_syx
from probe_sequencer_stop import probe as negative_candidate


def probe(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    syx=(ROOT/'build/circuitrhythm-5706-phase1-sequencer.syx').read_bytes()
    image=unpack_syx(syx,allow_extended=True)['image']
    labels=tests.base.seq.arm_code()[1]
    class PackagedLifecycle(tests.UsbLifecycleTests):
        @classmethod
        def setUpClass(cls):
            cls.image,cls.labels=image,labels
    with (out/'tests.txt').open('w',encoding='utf-8') as stream:
        result=unittest.TextTestRunner(stream=stream,verbosity=2).run(
            unittest.defaultTestLoader.loadTestsFromTestCase(PackagedLifecycle))
    assert result.wasSuccessful(),'RX lifecycle regression failed'
    report={
        'scope':'Generated/native Thumb; typed RX objects in synthetic RAM; partial native constructor only',
        'hardware_release':'NO-GO','production_integrated':False,
        'packaged_syx_sha256':hashlib.sha256(syx).hexdigest(),
        'packaged_image_sha256':hashlib.sha256(image).hexdigest(),
        'experimental_tests':result.testsRun,
        'registered_reader_writer_and_rearm_gates':'PASS',
        'quiescent_reset_close_resume_epoch':'PASS',
        'owned_or_partial_reset_rejection':'PASS',
        'producer_publish_and_nested_reset_interleaving':'PASS',
        'native_static_rx_ring_1057_bytes':'PASS_PARTIAL_CONSTRUCTOR',
        'rx_freeze_on_disconnect_or_binding_change':'PASS',
        'active_tx_disconnect_new_session_safety':'FAIL',
        'late_rx_dma_completion_after_resume':'NOT_ESTABLISHED',
        'all_inline_writers_and_real_irq_rtos':'NOT_ESTABLISHED',
        'production_caller_compatibility':'FAIL',
        'code_audit':audit(out/'audit'),
        'native_contract':trace(out/'stock-contract'),
        'unchanged_candidate_probe':negative_candidate(image,labels),
        'remaining':[
            'Active TX payload can outlive the retry slot in the native endpoint. RX freeze cannot cancel an old transfer before reconnection; the required negative test reproduces it.',
            'A completion arriving after reset/resume cannot be assigned to an old/new hardware session by these entry guards alone. Coordinated RX/TX endpoint cancellation/generation ownership is still required.',
            'Generic reset direct callers found are MIDI TX paths. Typed entry gates do not prove absence of arbitrary inline writers or complete indirect/IRQ/DMA paths.',
            '1496B is synthetic RAM, not a checked production reservation. Full boot/OOM, timing, mode/lifecycle, storage, all producers/observers and DIN input remain open.'
        ]}
    (out/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


if __name__=='__main__':
    print(json.dumps(probe(sys.argv[1] if len(sys.argv)>1 else ROOT/'logs/usb-lifecycle-probe'),indent=2))
    raise SystemExit(2)
