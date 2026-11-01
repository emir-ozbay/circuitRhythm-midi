"""Packaged-image ordered inquiry admission experiment; never device release."""
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'tests'), str(ROOT/'scripts'), str(ROOT/'src')]
import test_midi_usb_order as tests
from audit_midi_usb_inquiry_prototype import audit
from patch_firmware import unpack_syx
from probe_sequencer_stop import probe as negative_candidate


def probe(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    syx = (ROOT/'build/circuitrhythm-5706-phase1-sequencer.syx').read_bytes()
    image = unpack_syx(syx, allow_extended=True)['image']
    labels = tests.base.seq.arm_code()[1]
    class PackagedUsbOrder(tests.UsbOrderTests):
        @classmethod
        def setUpClass(cls):
            cls.image, cls.labels = image, labels
    with (out/'tests.txt').open('w', encoding='utf-8') as stream:
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(
            unittest.defaultTestLoader.loadTestsFromTestCase(PackagedUsbOrder))
    assert result.wasSuccessful(), 'ordered USB admission regression failed'
    report = {
        'scope': 'Generated Thumb/native parser/receiver/FIFO/transport/TX, synthetic RAM only',
        'hardware_release': 'NO-GO', 'production_integrated': False,
        'packaged_syx_sha256': hashlib.sha256(syx).hexdigest(),
        'packaged_image_sha256': hashlib.sha256(image).hexdigest(),
        'experimental_tests': result.testsRun,
        'deferred_note_on_stop_order': 'PASS',
        'legitimate_post_stop_note_and_running_status': 'PASS',
        'capacity_barrier_order_and_exact_reply_count': 'PASS',
        'native_receiver_ownership_and_64_voice_closures': 'PASS',
        'two_inquiries_next_buffer_realtime': 'PASS',
        'unconditional_realtime_latency_at_capacity': 'FAIL',
        'din_input_retry': 'NOT_IMPLEMENTED',
        'production_caller_compatibility': 'FAIL',
        'code_audit': audit(out/'audit', ordered=True),
        'unchanged_candidate_probe': negative_candidate(image, labels),
        'remaining': [
            'Order is preserved by never bypassing bytes. At eight pending inquiries, a new F0 and its suffix wait; queued Clock/Stop latency remains open.',
            'The count tracks identical cable0 identity replies only. No general SysEx/update ACK or native multicast observer compatibility proof.',
            'DIN input retry is not implemented. Native DIN OUTPUT tests do not close that input gap.',
            '1432B synthetic RAM is not reserved in production; checked allocation/init, boot/OOM, lifecycle, storage and IRQ/DMA/disconnect gates remain.'
        ]
    }
    (out/'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    print(json.dumps(probe(sys.argv[1] if len(sys.argv)>1 else ROOT/'logs/usb-order-probe'), indent=2))
    raise SystemExit(2)
