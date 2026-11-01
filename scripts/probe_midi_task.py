"""Packaged-image replay of main-loop USB fairness and stalled-driver limits."""
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
from midi_task_test_support import MidiTaskFixture
from shared_project_test_support import SharedModeFixture


def run_case(image, labels, *, stock_hook=False, driver_full=False):
    h = base.SafetyTests()
    h.image, h.labels = image, labels
    h.setUp()
    midi = MidiRecordFixture(h, 0, router=0x2000C000)
    ui = SharedModeFixture(h, ctrl=0x2000B000, view=0x2000B400, grid=0x2000B800)
    ingress = MidiIngressFixture(h, midi)
    transport = TransportControlFixture(h, midi, ui)
    output = MidiOutputFixture(h, transport)
    output.native_clock_backend()
    task = MidiTaskFixture(h, ingress, output)
    if stock_hook:
        h.u.mem_write(base.seq.HOOK_USB_RX_YIELD, base.seq.EXPECTED_USB_RX_YIELD)
    ingress.din([0xFA, 0xF8])
    output.poll()
    starts = [len(p) for p in output.delivered]
    if driver_full:
        for driver in output.drivers:
            h.u.mem_write(driver+5, b'\x01')
    task.queue_usb(bytes([0x0F, 0xF8, 0, 0])*64 + bytes([0x0F, 0xFC, 0, 0]))
    peak = 0
    for iteration in range(6):
        if driver_full and iteration == 5:
            for driver in output.drivers:
                h.u.mem_write(driver+5, b'\x00')
        task.step()
        peak = max(peak, *(output.pending(n) for n in range(3)))
    packets = [p[starts[n]:] for n, p in enumerate(output.delivered)]
    clocks = [p.count(bytes([0x0F, 0xF8, 0, 0])) for p in packets]
    stops = [p.count(bytes([0x0F, 0xFC, 0, 0])) for p in packets]
    return {'stop_delivery': 'PASS' if stops == [1]*3 and clocks == [64]*3 else 'FAIL',
            'clocks_per_port': clocks, 'stops_per_port': stops,
            'peak_queued_messages': peak, 'running_after': transport.running(),
            'rx_bytes_remaining': task.usb_bytes_pending(),
            'midi_tx_fault_latched': bool(h.u.mem_read(base.seq.SEQ_STATE_ADDR+base.seq.OFF_MIDI_TX_FAULT, 1)[0]),
            'tx_messages_remaining': [output.pending(n) for n in range(3)]}


def probe(image=None, labels=None):
    if image is None:
        image = unpack_syx((ROOT/'build/circuitrhythm-5706-phase1-sequencer.syx').read_bytes(),
                           allow_extended=True)['image']
        labels = base.seq.arm_code()[1]
    assert labels is not None
    return {
        'hardware_release': 'NO-GO',
        'candidate_image_sha256': hashlib.sha256(image).hexdigest(),
        'stock_hook_control': run_case(image, labels, stock_hook=True),
        'bounded_usb_ready_driver': run_case(image, labels),
        'bounded_usb_stalled_driver': run_case(image, labels, driver_full=True),
        'scope': 'Actual25870..2587C output-before-input span, native parser/clock/backend/output FIFO/worker, boot-sized synthetic USB RX ring. Final driver/timer/hardware boundaries; no IRQ/DMA,27624 USB endpoint service or full boot.',
    }


if __name__ == '__main__':
    result = probe()
    print(json.dumps(result, indent=2))
    passed = all(result[k]['stop_delivery'] == 'PASS'
                 for k in ('bounded_usb_ready_driver', 'bounded_usb_stalled_driver'))
    raise SystemExit(0 if passed else 1)
