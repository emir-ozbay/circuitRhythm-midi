"""Packaged-image native CPU-FIFO IRQ experiment. Hardware release stays NO-GO."""
import hashlib
import json
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'scripts'),str(ROOT/'src')]
import test_midi_usb_irq as tests
from audit_midi_usb_irq_prototype import audit
from trace_midi_usb_irq import trace
from patch_firmware import unpack_syx
from probe_sequencer_stop import probe as negative_candidate


def probe(out):
    out=Path(out); out.mkdir(parents=True,exist_ok=True)
    syx=(ROOT/'build/circuitrhythm-5706-phase1-sequencer.syx').read_bytes()
    image=unpack_syx(syx,allow_extended=True)['image']; labels=tests.base.seq.arm_code()[1]
    class PackagedIrq(tests.UsbIrqTests):
        @classmethod
        def setUpClass(cls): cls.image,cls.labels=image,labels
    with (out/'tests.txt').open('w',encoding='utf-8') as stream:
        result=unittest.TextTestRunner(stream=stream,verbosity=2).run(
            unittest.defaultTestLoader.loadTestsFromTestCase(PackagedIrq))
    assert result.wasSuccessful(),'Native CPU-FIFO IRQ experiment failed'
    report=dict(scope='Native HAL submit4293E IRQ/FIFO/callback chain; synthetic RAM + USBx40040000 MMIO; IPSR injection, no real NVIC/device',
        hardware_release='NO-GO',production_integrated=False,
        packaged_syx_sha256=hashlib.sha256(syx).hexdigest(),packaged_image_sha256=hashlib.sha256(image).hexdigest(),
        experimental_tests=result.testsRun,
        native_cpu_fifo_completion_irq_bridge='PASS_CONDITIONAL_MMIO',
        external_test_supplied_completion_tokens=False,
        coalesced_and_multiframe_fifo_publication='PASS',
        immutable_irq_entry_snapshot_and_native_lr='PASS',
        native_hal_cpu_fifo_configuration='PASS_PARTIAL_INIT_PREFIX',
        close_time_cpu_fifo_drain_and_epoch_discard='PASS_CONDITIONAL_MMIO',
        direct_native_disconnect='PASS_FAIL_CLOSED_ONLY',
        all_control_reset_irq_and_dma_modes='UNSUPPORTED_FAIL_CLOSED',
        stale_untagged_xfrc_after_broken_barrier='FAIL_EXPECTED_NEGATIVE',
        actual_cancel_barrier_and_late_bus_master='NOT_ESTABLISHED',
        full_irq_nvic_cache_timing_and_boot='NOT_ESTABLISHED',
        production_caller_compatibility='FAIL_CONTROL_RESET_RECOVERY',
        code_audit=audit(out/'audit'),native_contract=trace(out/'stock-contract'),
        unchanged_candidate_probe=negative_candidate(image,labels),
        remaining=[
            'Native CPU-FIFO submit/IRQ/callback chains execute without Python supplying tokens. The bridge snapshots the still-owned submitted job before native callbacks, defers publication past native CPU FIFO reads and never copies current tokens at callback time.',
            'This snapshot is not a hardware generation tag. A fabricated stale XFRC after the assumed cancellation barrier completes a new job in the required negative test. Real disable/FIFO/cache/bus-master cancellation must still be proven.',
            'Only the masked RXFLVL/IEPINT/OEPINT subset and CPU mode0 are supported. Control/reset/DMA IRQ causes fail closed; direct native disconnect freezes ownership. Full stock USB lifecycle compatibility and recovery remain open.',
            'Native2C82A prefix selects USBx40040000, handle200054B4, mode0 and6 endpoints, but the live tests use a synthetic handle/controller/list binding. Full boot/OOM and actual silicon/NVIC/cache/cycle behavior are not proven.',
            '1720B state is synthetic, not production reserved. General shared-reader/RX-debt cancellation, storage recovery, all producers/observers/modes and DIN input remain gates.',
            'Production candidate and stock bytes remain unchanged; production Off/Stop failure is retained. No physical USB/MIDI/device API was accessed.'
        ])
    (out/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


if __name__=='__main__':
    print(json.dumps(probe(sys.argv[1] if len(sys.argv)>1 else ROOT/'logs/usb-irq-probe'),indent=2))
    raise SystemExit(2)
