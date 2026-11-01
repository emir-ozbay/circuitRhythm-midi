"""Packaged-image committed USB RX ledger experiment; no physical devices."""
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'tests'), str(ROOT/'scripts'), str(ROOT/'src')]
import test_midi_usb_ledger as tests
from audit_midi_usb_ledger_prototype import audit
from patch_firmware import unpack_syx
from probe_sequencer_stop import probe as negative_candidate


def probe(out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    syx = (ROOT/'build/circuitrhythm-5706-phase1-sequencer.syx').read_bytes()
    image = unpack_syx(syx, allow_extended=True)['image']
    labels = tests.base.seq.arm_code()[1]
    class PackagedLedger(tests.UsbLedgerTests):
        @classmethod
        def setUpClass(cls):
            cls.image, cls.labels = image, labels
    with (out/'tests.txt').open('w', encoding='utf-8') as stream:
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(
            unittest.defaultTestLoader.loadTestsFromTestCase(PackagedLedger))
    assert result.wasSuccessful(), 'USB RX ledger regression failed'
    report = {
        'scope': 'Committed native software RX FIFO; generated/native Thumb in synthetic RAM',
        'hardware_release': 'NO-GO', 'production_integrated': False,
        'packaged_syx_sha256': hashlib.sha256(syx).hexdigest(),
        'packaged_image_sha256': hashlib.sha256(image).hexdigest(),
        'experimental_tests': result.testsRun,
        'deferred_note_on_stop_order': 'PASS',
        'full_pending_committed_next_buffer_clock_stop': 'PASS',
        'admitted_inquiry_exact_reply_count_and_ack_ownership': 'PASS',
        'partial_publication_and_new_snapshot_boundary': 'PASS',
        'private_marker_provenance_and_no_parser_replay': 'PASS',
        'native_usb_din_output_stall_and_64_voice_closures': 'PASS',
        'pre_admission_host_usb_latency': 'NOT_ESTABLISHED',
        'real_irq_dma_timing_and_full_lifecycle': 'NOT_ESTABLISHED',
        'din_input_retry': 'NOT_IMPLEMENTED',
        'production_caller_compatibility': 'FAIL',
        'observed_instructions_maximum_query_window_case': PackagedLedger.maximum_window_instructions,
        'maximum_query_window_test_budget_instructions': 500000,
        'code_audit': audit(out/'audit'),
        'unchanged_candidate_probe': negative_candidate(image, labels),
        'remaining': [
            'SPSC/main ownership and producer-during-consumer injection are synthetic; real IRQ/DMA timing and the native boot-created ring must be proven.',
            'Every reset/flush/disconnect/other consumer must coordinate the private headers and SCANNED boundary. No production integration until lifecycle ownership is complete.',
            'Finite RX storage can refuse new input. Tests guarantee service only for fully committed admitted records; no host-side latency or unlimited inquiry acceptance promise.',
            'Exact cable0 identity inquiries only; full native multicast/other SysEx/update ACK compatibility and DIN input retry remain open.',
            '1432B is synthetic, not production-reserved RAM. Checked init/boot/OOM, mode/lifecycle, storage and IRQ/DMA/disconnect gates remain.'
        ]
    }
    (out/'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    print(json.dumps(probe(sys.argv[1] if len(sys.argv)>1 else ROOT/'logs/usb-ledger-probe'), indent=2))
    raise SystemExit(2)
