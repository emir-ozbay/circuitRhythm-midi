"""Negative probe: native Stop flushes64 player notes before enqueuing FC.

Synthetic player state, manual tick scheduling, real step/voice/Stop/FIFO code.
This is not a full boot or physical scheduling measurement. Exit1 on loss.
"""
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'tests'), str(ROOT/'scripts'), str(ROOT/'src')]
import test_phase1_safety as base
from patch_firmware import unpack_syx
from midi_output_test_support import MidiOutputFixture
from midi_ingress_test_support import MidiIngressFixture, TransportControlFixture
from shared_project_test_support import SharedModeFixture
from sequencer_playback_test_support import SequencerPlaybackFixture


def probe(image=None, labels=None, *, poll_rounds=1, instruction_budget=100000):
    if not 1 <= poll_rounds <= 128:
        raise ValueError('poll_rounds must be within1..128')
    if not 100000 <= instruction_budget <= 500000:
        raise ValueError('instruction_budget must be within100000..500000')
    if image is None:
        image = unpack_syx((ROOT/'build/circuitrhythm-5706-phase1-sequencer.syx').read_bytes(),
                           allow_extended=True)['image']
        labels = base.seq.arm_code()[1]
    assert labels is not None
    cases = []
    for mode in (0, 1):
        for count, clock_before_stop in ((63, False), (64, False), (64, True)):
            h = base.SafetyTests()
            h.instruction_budget=instruction_budget
            h.image, h.labels = image, labels
            h.setUp()
            ui = SharedModeFixture(h, ctrl=0x2000B000, view=0x2000B400, grid=0x2000B800)
            midi = SimpleNamespace(decoder=0x20004000, receiver=0x20004100, router=0x2000C000)
            h.word(midi.decoder, midi.receiver)
            transport = TransportControlFixture(h, midi, ui)
            ingress = MidiIngressFixture(h, midi)
            output = MidiOutputFixture(h, transport)
            playback = SequencerPlaybackFixture(h, output, transport.transport)
            playback.attach_stop_listeners()
            h.u.mem_write(base.seq.SEQ_STATE_ADDR+4, bytes([mode]))
            for t in range(8):
                for n in range(7 if t == 7 and count == 63 else 8):
                    playback.step(t, n, 48+n, gate=96)
                    output.poll()
            active = [len(playback.active(t)) for t in range(8)]
            h.word(h.call(0x0803FD26, transport.transport, 0), 1)
            h.call(0x0803FE00, transport.transport)
            raw = bytes(h.u.mem_read(0x20010000, 0x29484))
            trace = []
            def call_order(u, pc, size, data):
                if pc == 0x0804AED8:
                    trace.append('flush_track_'+str(playback.players.index(u.reg_read(base.UC_ARM_REG_R0))))
                elif pc == 0x08032024:
                    trace.append('emit_stop')
            h.u.hook_add(base.UC_HOOK_CODE, call_order, begin=0x0804AED8, end=0x0804AED8)
            h.u.hook_add(base.UC_HOOK_CODE, call_order, begin=0x08032024, end=0x08032024)
            if clock_before_stop:
                ingress.usb([15, 0xF8, 0, 0, 15, 0xFC, 0, 0])
            else:
                h.call(0x08033EAE, transport.root+0x0C, 0)
            pending = [output.pending(p) for p in range(3)]
            for _ in range(poll_rounds):output.poll()
            ons = [sum(m[0] == 9 for m in msgs) for msgs in output.delivered]
            offs = [sum(m[0] == 8 for m in msgs) for msgs in output.delivered]
            stops = [sum(m == bytes([15, 0xFC, 0, 0]) for m in msgs) for msgs in output.delivered]
            h.assertEqual(sum(active), count)
            h.assertEqual(ons, [count]*3)
            h.assertEqual(trace, ['flush_track_'+str(t) for t in range(8)]+['emit_stop'])
            h.assertEqual([playback.active(t) for t in range(8)], [[]]*8)
            h.assertEqual(bytes(h.u.mem_read(0x20010000, 0x29484)), raw)
            fault = bool(h.u.mem_read(base.seq.SEQ_STATE_ADDR+base.seq.OFF_MIDI_TX_FAULT, 1)[0])
            cases.append({'mode': mode, 'usb_clock_before_stop': clock_before_stop,
                          'active_notes_before_stop': active,
                          'delivered_on_per_port': ons, 'delivered_off_per_port': offs,
                          'delivered_stop_per_port': stops, 'pending_before_poll': pending,
                          'native_stop_order': trace, 'midi_tx_fault_latched': fault,
                          'post_stop_poll_rounds': poll_rounds,
                          'per_call_instruction_budget': instruction_budget,
                          'note_off_delivery': 'PASS' if offs == [count]*3 else 'FAIL',
                          'stop_delivery': 'PASS' if stops == [1]*3 else 'FAIL'})
    return {'stop_delivery': 'PASS' if all(c['stop_delivery'] == 'PASS' for c in cases) else 'FAIL',
            'note_off_delivery': 'PASS' if all(c['note_off_delivery'] == 'PASS' for c in cases) else 'FAIL',
            'candidate_image_sha256': hashlib.sha256(image).hexdigest(),
            'hardware_release': 'NO-GO', 'cases': cases,
            'scope': 'Synthetic constructor-derived player/voice/store RAM; native4AEEE/4AFBC generates notes, native33EAE/FBEC/player listeners flush before FC. Additional case feeds F8+FC in one real USB parser buffer. Drivers ready throughout. Backend Stop is a boundary stub; timers/IRQs/full boot and complete live reachability are not proven.',
            'open_requirement': 'Protect Off/Stop delivery for native synchronous flush bursts, not only USB RX bursts. Eight records per player is not a bound on all UI/preview/tied ownership sources.'}


if __name__ == '__main__':
    result = probe()
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['stop_delivery'] == result['note_off_delivery'] == 'PASS' else 1)
