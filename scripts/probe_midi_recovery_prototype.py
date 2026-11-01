"""Separate experimental evidence; never changes candidate or returns GO."""
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'tests'), str(ROOT/'scripts'), str(ROOT/'src')]
import test_midi_recovery_prototype as experiment_tests
import midi_recovery_prototype as recovery
from patch_firmware import unpack_syx
from probe_sequencer_stop import probe as candidate_probe
from audit_midi_recovery_prototype import audit


def probe(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    syx = (ROOT/'build/circuitrhythm-5706-phase1-sequencer.syx').read_bytes()
    image = unpack_syx(syx, allow_extended=True)['image']
    labels = experiment_tests.base.seq.arm_code()[1]
    cases = []
    for mode in (0, 1):
        for count, usb in ((63, False), (64, False), (64, True)):
            h = experiment_tests.MidiRecoveryPrototypeTests()
            h.image, h.labels = image, labels
            h.setUp()
            h.setup_recovery(mode)
            h.seed_notes(count)
            before = bytes(h.u.mem_read(0x20010000, 0x29484))
            if usb:
                h.ingress.usb([15, 0xF8, 0, 0, 15, 0xFC, 0, 0])
            else:
                h.call(0x08033EAE, h.transport.root+0x0C, 0)
            rounds = h.recovery.settle()
            offs = [sum(m[0] == 8 for m in messages) for messages in h.output.delivered]
            stops = [sum(m == bytes([15, 0xFC, 0, 0]) for m in messages) for messages in h.output.delivered]
            h.assertEqual(offs, [count]*3)
            h.assertEqual(stops, [1]*3)
            h.assertTrue(all(messages[-1] == bytes([15, 0xFC, 0, 0]) for messages in h.output.delivered))
            h.assertEqual(bytes(h.u.mem_read(0x20010000, 0x29484)), before)
            h.recovery.check_canaries()
            cases.append({'mode': mode, 'player_notes': count, 'single_usb_clock_stop_buffer': usb,
                          'off_per_port': offs, 'stop_per_port': stops, 'settle_polls': rounds,
                          'recovery': 'PASS'})
    code_audit = audit(out)
    control = candidate_probe(image, labels)
    # Preserve the old negative control and compare with hooked admission.
    sysex_cases = []
    for hooked in (False, True):
        h = experiment_tests.MidiRecoveryPrototypeTests()
        h.image, h.labels = image, labels
        h.setUp()
        h.setup_recovery(sysex=hooked)
        desc = h.sysex_descriptor()
        for port in range(3):
            h.call(h.recovery.labels['rp_fault'], h.recovery.entries[port])
            result = h.recovery.sysex_send(port, desc)
            h.assertEqual(result, 0 if hooked else 1)
        h.recovery.settle()
        emitted = [any(m[0] in (4, 5, 6, 7) for m in messages) for messages in h.output.delivered]
        h.assertEqual(emitted, [not hooked]*3)
        sysex_cases.append({'sysex_hooks_enabled': hooked, 'sysex_emitted_per_port': emitted})
    # Execute experimental regressions on this exact packaged image plus the
    # documented Unicorn overlays, not a silently rebuilt firmware fixture.
    class PackagedExperiment(experiment_tests.MidiRecoveryPrototypeTests):
        @classmethod
        def setUpClass(cls):
            cls.image, cls.labels = image, labels
    with (out/'experimental-tests.txt').open('w', encoding='utf-8') as stream:
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(
            unittest.defaultTestLoader.loadTestsFromTestCase(PackagedExperiment))
    assert result.wasSuccessful(), 'experimental regression failure'
    from trace_midi_sysex_contract import trace
    contract = trace(out/'stock-contract')
    report = {'tested_off_stop_recovery': 'PASS', 'production_integrated': False,
              'overall_status': 'EXPERIMENTAL_RECOVERY_PASS_WITH_BLOCKERS',
              'hardware_release': 'NO-GO', 'packaged_syx_sha256': hashlib.sha256(syx).hexdigest(),
              'packaged_image_sha256': hashlib.sha256(image).hexdigest(),
              'experimental_code_audit': code_audit, 'cases': cases,
              'unchanged_candidate_probe': control,
              'tested_sysex_quarantine': 'PASS',
              'sysex_negative_control_and_overlay': sysex_cases,
              'experimental_regression_tests': result.testsRun,
              'stock_sysex_contract': contract,
              'all_producer_quarantine': 'REVIEW_REQUIRED',
              'native_sysex_accepted_while_quarantined': True,
              'hooked_sysex_accepted_while_quarantined': False,
              'open_requirements': [
                  'Tested SysEx vtable entries and shared-buffer router are quarantined only in Unicorn. Direct/unmodeled producer/lifecycle paths and production hooks remain unproven.',
                  'Busy SysEx now returns failure instead of spinning. Some native callers ignore the result; caller retry/response policy and concurrent partial fanout need production review.',
                  '832B arena at20047000 is synthetic and below stock heap current; it is NOT a production RAM reservation. Checked heap/boot initialization/port lifetime are absent.',
                  'Recovery quarantine rejects new On/Clock until a reviewed reset/resume policy; mode-admission wiring is absent.',
                  'Disconnect during/after native FIFO or driver acceptance, actual IRQ/DMA/USB completion and elapsed timing are unproven.',
                  'Native stock storage failure/recovery and full boot/OOM remain release blockers.'
              ]}
    (out/'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT/'logs/recovery-prototype'
    result = probe(output)
    print(json.dumps(result, indent=2))
    # A passing isolated experiment is deliberately not firmware acceptance.
    raise SystemExit(2 if result['tested_off_stop_recovery'] == 'PASS' else 1)
