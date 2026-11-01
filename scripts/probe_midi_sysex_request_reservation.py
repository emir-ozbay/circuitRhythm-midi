"""Packaged-image upper reservation experiment; native RX loss stays NO-GO."""
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'tests'), str(ROOT/'scripts'), str(ROOT/'src')]
import test_midi_sysex_request_reservation as tests
from audit_midi_sysex_retry_prototype import audit
from trace_midi_sysex_requests import trace
from patch_firmware import unpack_syx
from probe_sequencer_stop import probe as negative_candidate


def probe(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    syx = (ROOT/'build/circuitrhythm-5706-phase1-sequencer.syx').read_bytes()
    image = unpack_syx(syx, allow_extended=True)['image']
    labels = tests.base.seq.arm_code()[1]
    class PackagedRequests(tests.SysexRequestTests):
        @classmethod
        def setUpClass(cls):
            cls.image, cls.labels = image, labels
    with (out/'tests.txt').open('w', encoding='utf-8') as stream:
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(
            unittest.defaultTestLoader.loadTestsFromTestCase(PackagedRequests))
    assert result.wasSuccessful(), 'request reservation regression failed'
    report = {
        'scope': 'Synthetic RAM; actual upper formatter, parser, dispatcher and USB/DIN driver Thumb code',
        'hardware_release': 'NO-GO', 'production_integrated': False,
        'packaged_syx_sha256': hashlib.sha256(syx).hexdigest(),
        'packaged_image_sha256': hashlib.sha256(image).hexdigest(),
        'experimental_tests': result.testsRun,
        'tested_upper_reservation_before_source_mutation': 'PASS',
        'reserved_capacity_not_stolen_by_nested_calls': 'PASS',
        'explicit_caller_retry_after_drain': 'PASS',
        'legacy_upper_source_preservation': 'FAIL',
        'native_usb_din_consumed_request_retry': 'FAIL',
        'production_caller_compatibility': 'FAIL',
        'code_audit': audit(out, notifications=True, reservations=True),
        'native_contract': trace(out/'stock-contract'),
        'unchanged_candidate_probe': negative_candidate(image, labels),
        'remaining': [
            'Five upper entry guards prevent mutation but do not add RX retry. Native USB/DIN listener return is ignored and a busy inquiry is consumed; explicit upstream resend succeeds.',
            'RX cursor/pop/ack ownership and realtime/Off/Stop fairness need bounded backpressure. Whole input26DE8/update/storage handlers are not executed.',
            '428B retry plus832B recovery is1260B synthetic RAM; checked heap/atomic boot init and full producer/lifecycle integration are absent.',
            'Return-PC token and IPSR0 checks only cover the five audited main-context call chains; not actual exceptions/RTOS task-switch ordering or arbitrary indirect callers.',
            'Production recovery/SysEx integration, mode guard/reset-resume, stock storage failure recovery, full boot/OOM and IRQ/DMA/USB-disconnect/PRIMASK time remain open.'
        ]
    }
    (out/'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    print(json.dumps(probe(sys.argv[1] if len(sys.argv)>1 else ROOT/'logs/sysex-request-reservation'), indent=2))
    raise SystemExit(2)
