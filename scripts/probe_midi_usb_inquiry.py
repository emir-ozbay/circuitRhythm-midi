"""Packaged-image USB inquiry retry experiment, preserving honest NO-GO gates."""
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'tests'), str(ROOT/'scripts'), str(ROOT/'src')]
import test_midi_usb_inquiry as tests
from audit_midi_usb_inquiry_prototype import audit
from patch_firmware import unpack_syx
from probe_sequencer_stop import probe as negative_candidate


def probe(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    syx = (ROOT/'build/circuitrhythm-5706-phase1-sequencer.syx').read_bytes()
    image = unpack_syx(syx, allow_extended=True)['image']
    labels = tests.base.seq.arm_code()[1]
    class PackagedUsbInquiry(tests.UsbInquiryTests):
        @classmethod
        def setUpClass(cls):
            cls.image, cls.labels = image, labels
    with (out/'tests.txt').open('w', encoding='utf-8') as stream:
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(
            unittest.defaultTestLoader.loadTestsFromTestCase(PackagedUsbInquiry))
    assert result.wasSuccessful(), 'USB inquiry regression failed'
    report = {
        'scope': 'Generated Thumb and native parser/FIFO/transport/TX, synthetic RAM only',
        'hardware_release': 'NO-GO', 'production_integrated': False,
        'packaged_syx_sha256': hashlib.sha256(syx).hexdigest(),
        'packaged_image_sha256': hashlib.sha256(image).hexdigest(),
        'experimental_tests': result.testsRun,
        'usb_inquiry_automatic_retry_without_host_resend': 'PASS',
        'owned_cursor_no_duplicate_reply_or_realtime': 'PASS',
        'retained_buffer_clock_stop_and_64_note_closures': 'PASS',
        'native_usb_din_output_stall_and_exact_bytes': 'PASS',
        'realtime_behind_another_queued_buffer': 'FAIL',
        'deferred_note_on_stop_order': 'FAIL',
        'din_input_retry': 'NOT_IMPLEMENTED',
        'production_caller_compatibility': 'FAIL',
        'code_audit': audit(out/'audit'),
        'unchanged_candidate_probe': negative_candidate(image, labels),
        'remaining': [
            'Bounded realtime ingress lane/queued-buffer lookahead is needed before this can replace native USB poll.',
            'Bypass can reorder realtime ahead of deferred non-realtime; delayed NoteOn/Stop ordering needs a policy and tests.',
            'Exact inquiry is handled directly; native multicast side observers and other SysEx/update ACK ownership are unproven.',
            'DIN input still consumes busy inquiry; native DIN OUTPUT test is not a DIN input fix.',
            '1432B synthetic state is not reserved in production. Checked heap/init, boot/OOM, lifecycle, storage and IRQ/DMA/disconnect remain open.'
        ]
    }
    (out/'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    print(json.dumps(probe(sys.argv[1] if len(sys.argv)>1 else ROOT/'logs/usb-inquiry-probe'), indent=2))
    raise SystemExit(2)
