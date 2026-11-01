"""Negative safety probe: a full native64-slot FIFO can lose Note Off.

No hardware/device APIs. Run against the packaged image by default. Exit1 when
the loss is reproduced; a characterization regression passing is not a GO.
"""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'tests'), str(ROOT/'scripts'), str(ROOT/'src')]
import test_phase1_safety as base
from patch_firmware import unpack_syx
from midi_record_test_support import MidiRecordFixture
from midi_ingress_test_support import MidiIngressFixture, TransportControlFixture
from midi_output_test_support import MidiOutputFixture
from shared_project_test_support import SharedModeFixture


def probe(image=None, labels=None):
    h = base.SafetyTests()
    if image is None:
        image = unpack_syx((ROOT/'build/circuitrhythm-5706-phase1-sequencer.syx').read_bytes(),
                           allow_extended=True)['image']
        labels = base.seq.arm_code()[1]
    assert labels is not None
    h.image, h.labels = image, labels
    h.setUp()
    midi = MidiRecordFixture(h, 0, router=0x2000C000)
    ui = SharedModeFixture(h, ctrl=0x2000B000, view=0x2000B400, grid=0x2000B800)
    ingress = MidiIngressFixture(h, midi)
    transport = TransportControlFixture(h, midi, ui)
    output = MidiOutputFixture(h, transport, slots=64)
    stock = base.load_image()
    spans = [(0x08031F08, 0x0803223C), (0x0804016C, 0x0804042C),
             (0x0802986A, 0x080298B4), (0x080468FA, 0x0804691A)]
    same_code = all(image[a-0x08010000:b-0x08010000] == stock[a-0x08010000:b-0x08010000]
                    for a, b in spans)
    hook = base.seq.HOOK_MIDI_TX_OVERFLOW-0x08010000
    observer_present = image[hook:hook+4] == base.seq.bl(base.seq.HOOK_MIDI_TX_OVERFLOW,
                                                      labels['c_midi_tx_overflow'])
    core = bytearray(image)
    if observer_present:
        core[hook:hook+4] = base.seq.EXPECTED_MIDI_TX_OVERFLOW
    same_core = all(core[a-0x08010000:b-0x08010000] == stock[a-0x08010000:b-0x08010000]
                    for a, b in spans)
    output.note(0, 48)
    output.poll()
    # Controlled producer-before-consumer schedule, not a claim that the live
    # scheduler permits64 incoming clocks without an intervening worker poll.
    for _ in range(64):
        ingress.din([0xF8])
    pending_before = [output.pending(n) for n in range(3)]
    output.note(0, 48, velocity=0, on=False)
    pending_after = [output.pending(n) for n in range(3)]
    output.poll()
    offs = [sum(p == bytes([8, 0x80, 48, 0]) for p in delivered) for delivered in output.delivered]
    ons = [sum(p == bytes([9, 0x90, 48, 96]) for p in delivered) for delivered in output.delivered]
    clocks = [sum(p == bytes([0x0F, 0xF8, 0, 0]) for p in delivered) for delivered in output.delivered]
    lost = any(on and not off for on, off in zip(ons, offs))
    fault_latched = bool(h.u.mem_read(base.seq.SEQ_STATE_ADDR+base.seq.OFF_MIDI_TX_FAULT, 1)[0])
    mode_before = h.u.mem_read(base.seq.SEQ_STATE_ADDR+4, 1)[0]
    ui.press()
    mode_after = h.u.mem_read(base.seq.SEQ_STATE_ADDR+4, 1)[0]
    return {
        'note_off_delivery': 'FAIL' if lost else 'PASS',
        'hardware_release': 'NO-GO',
        'candidate_image_sha256': hashlib.sha256(image).hexdigest(),
        'stock_output_code_identical': same_code,
        'overflow_observer_hook_present': observer_present,
        'stock_output_core_identical_except_observer': same_core,
        'midi_tx_fault_latched': fault_latched,
        'mode_admission_after_loss': 'BLOCKED' if fault_latched and mode_after == mode_before else 'UNCONTAINED',
        'fifo_slots_from_boot_297A8': 64,
        'pending_before_off': pending_before,
        'pending_after_off': pending_after,
        'delivered_on_per_port': ons,
        'delivered_clock_per_port': clocks,
        'delivered_off_per_port': offs,
        'remaining_after_worker_poll': [output.pending(n) for n in range(3)],
        'scope': 'Synthetic RAM, native parser/Clock/output adapter/router/FIFO/worker; final driver boundaries. Controlled64-event gap before consumer poll. No physical timing/ISR or actual sequencer-generated Note On proof.',
        'open_requirement': 'Prove a bound preventing this queue state in the live scheduler, or implement and verify a safe backpressure/Note Off recovery policy before GO.',
    }


if __name__ == '__main__':
    result = probe()
    print(json.dumps(result, indent=2))
    raise SystemExit(1 if result['note_off_delivery'] == 'FAIL' else 0)
