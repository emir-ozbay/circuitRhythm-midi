"""Separate exact-candidate retry experiment. Passing tests never imply GO."""
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'tests'), str(ROOT/'scripts'), str(ROOT/'src')]
import test_midi_sysex_retry_prototype as tests
import midi_sysex_retry_prototype as retry
from audit_midi_sysex_retry_prototype import audit
from patch_firmware import unpack_syx
from probe_sequencer_stop import probe as negative_candidate
from trace_midi_sysex_contract import trace


def probe(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    syx = (ROOT/'build/circuitrhythm-5706-phase1-sequencer.syx').read_bytes()
    image = unpack_syx(syx, allow_extended=True)['image']
    labels = tests.base.seq.arm_code()[1]
    class PackagedRetry(tests.SysexRetryTests):
        @classmethod
        def setUpClass(cls):
            cls.image, cls.labels = image, labels
    with (out/'tests.txt').open('w', encoding='utf-8') as stream:
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(
            unittest.defaultTestLoader.loadTestsFromTestCase(PackagedRetry))
    assert result.wasSuccessful(), 'retry experiment regression failed'
    report = {
        'scope': 'Synthetic RAM / real Thumb caller, formatter and USB/DIN driver code',
        'hardware_release': 'NO-GO', 'production_integrated': False,
        'packaged_syx_sha256': hashlib.sha256(syx).hexdigest(),
        'packaged_image_sha256': hashlib.sha256(image).hexdigest(),
        'experimental_tests': result.testsRun, 'owned_payload_and_port_retry': 'PASS',
        'guarded_formatter_reentry_and_active_callback_owner': 'PASS',
        'unguarded_formatter_source_preservation': 'FAIL',
        'unguarded_active_callback_owner_preservation': 'FAIL',
        'ignored_full_queue_response_delivery': 'FAIL',
        'native_completion_callback_contract': 'NOT_IMPLEMENTED',
        'production_caller_compatibility': 'FAIL',
        'code_audit': audit(out), 'caller_contracts': trace(out/'stock-contract'),
        'unchanged_candidate_probe': negative_candidate(image, labels),
        'remaining': [
            'A single bounded slot cannot prevent ignored-rejection response loss; caller/request backpressure is missing.',
            'submit0 only means owned local copy. Native router success notification/global callback job completion and snapshot ownership are not wired; no callback is fabricated.',
            'The12 guarded direct producer entries do not prove all indirect writers or IRQ/task scheduling. General notification owner lifetime after native readers finish remains open.',
            '384B extra synthetic state plus832B recovery is1216B, with no checked heap reservation, atomic boot initialization or OOM proof.',
            'Production integration, mode admission/reset-resume, storage failure recovery, actual IRQ/DMA/disconnect and PRIMASK cycle budget remain NO-GO.'
        ]}
    (out/'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    result = probe(sys.argv[1] if len(sys.argv) > 1 else ROOT/'logs/sysex-retry-prototype')
    print(json.dumps(result, indent=2))
    raise SystemExit(2)
