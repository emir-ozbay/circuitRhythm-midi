"""Exact packaged-image experiment: owned synchronous admission notification.

Independent from production acceptance; all existing negative probes remain.
"""
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'tests'), str(ROOT/'scripts'), str(ROOT/'src')]
import test_midi_sysex_notification as tests
from audit_midi_sysex_retry_prototype import audit
from trace_midi_sysex_notification import trace
from patch_firmware import unpack_syx
from probe_sequencer_stop import probe as negative_candidate


def probe(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    syx = (ROOT/'build/circuitrhythm-5706-phase1-sequencer.syx').read_bytes()
    image = unpack_syx(syx, allow_extended=True)['image']
    labels = tests.base.seq.arm_code()[1]
    class PackagedNotifications(tests.SysexNotificationTests):
        @classmethod
        def setUpClass(cls):
            cls.image, cls.labels = image, labels
    with (out/'tests.txt').open('w', encoding='utf-8') as stream:
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(
            unittest.defaultTestLoader.loadTestsFromTestCase(PackagedNotifications))
    assert result.wasSuccessful(), 'owned notification experiment regression failed'
    report = {
        'scope': 'Pinned bytes/scatter-load plus synthetic-RAM real Thumb caller/event/USB-DIN code',
        'hardware_release': 'NO-GO', 'production_integrated': False,
        'packaged_syx_sha256': hashlib.sha256(syx).hexdigest(),
        'packaged_image_sha256': hashlib.sha256(image).hexdigest(),
        'experimental_tests': result.testsRun,
        'owned_native_admission_notification': 'PASS',
        'all_twelve_tested_caller_payloads_and_returns': 'PASS',
        'callback_reentry_after_payload_drain': 'PASS',
        'legacy_queue_notification_delivery': 'FAIL',
        'native_wire_completion_notification': 'NOT_ESTABLISHED',
        'production_caller_compatibility': 'FAIL',
        'code_audit': audit(out, notifications=True),
        'native_contract': trace(out/'stock-contract'),
        'unchanged_candidate_probe': negative_candidate(image, labels),
        'remaining': [
            'Optional event0 admission notification is synchronous in native code; snapshot extension delays it to all-port acceptance. No physical completion is asserted.',
            'Full-slot/recursive caller rejection still needs request-side backpressure. Caller bodies may require reentrant send success; callbacks are rejected while current dispatch owns the slot.',
            '424B retry plus832B recovery is1256B synthetic RAM; checked heap/atomic boot init, whole lifecycle and producer integration are absent.',
            'Notification listener snapshot is bounded3 but arbitrary callback body latency/whole call stack and all indirect writers/events are not proven.',
            'Mode guard/reset-resume, stock storage failure recovery, full boot/OOM and actual IRQ/DMA/USB disconnect/PRIMASK time remain open.'
        ]
    }
    (out/'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    print(json.dumps(probe(sys.argv[1] if len(sys.argv)>1 else ROOT/'logs/sysex-notification-prototype'), indent=2))
    raise SystemExit(2)
