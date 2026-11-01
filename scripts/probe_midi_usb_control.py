"""Packaged-image native USB reset/EP0/deferred class experiment; NO-GO."""
import hashlib
import json
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'scripts'),str(ROOT/'src')]
import test_midi_usb_control as tests
from audit_midi_usb_control_prototype import audit
from trace_midi_usb_control import trace
from patch_firmware import unpack_syx
from probe_sequencer_stop import probe as negative_candidate


def probe(out):
    out=Path(out); out.mkdir(parents=True,exist_ok=True)
    syx=(ROOT/'build/circuitrhythm-5706-phase1-sequencer.syx').read_bytes()
    image=unpack_syx(syx,allow_extended=True)['image']; labels=tests.base.seq.arm_code()[1]
    class PackagedControl(tests.UsbControlTests):
        @classmethod
        def setUpClass(cls): cls.image,cls.labels=image,labels
    with (out/'tests.txt').open('w',encoding='utf-8') as stream:
        result=unittest.TextTestRunner(stream=stream,verbosity=2).run(
            unittest.defaultTestLoader.loadTestsFromTestCase(PackagedControl))
    assert result.wasSuccessful(),'Native deferred USB control experiment failed'
    report=dict(scope='Native USBRST/ENUMDONE/EP0 SET_ADDRESS/SET_CONFIGURATION + deferred class code; synthetic RAM/MMIO; parent notification boundary',
        hardware_release='NO-GO',production_integrated=False,
        packaged_syx_sha256=hashlib.sha256(syx).hexdigest(),packaged_image_sha256=hashlib.sha256(image).hexdigest(),
        experimental_tests=result.testsRun,
        native_reset_ep0_configuration_close_and_resume='PASS_CONDITIONAL_MMIO',
        old_tx_cancel_before_native_class_rebuild='PASS_CONDITIONAL_MMIO',
        init_generation_commit_races_and_single_notification='PASS',
        accepted_rx_shared_payload_and_held_note_ownership='PASS_BY_CLOSED_RETENTION',
        constructor_global_rx_flush_guard='PASS_BOUND_NATIVE_CALLSITE',
        sof_partial_poll_and_phantom_rearm_prevention='PASS_ONE_MTU_AND_EXPLICIT_PAUSE',
        default_irq_codegen_preserved='PASS',
        real_class_parent_callback_and_composite_msc='NOT_ESTABLISHED',
        suspend_resume_dma_descriptor_and_full_task_graph='UNSUPPORTED_OR_UNPROVEN',
        stale_hardware_xfrc_after_broken_barrier='FAIL_EXPECTED_NEGATIVE',
        actual_hardware_cancellation_nvic_cache_timing='NOT_ESTABLISHED',
        production_caller_compatibility='FAIL_FULL_LIFECYCLE_PARENT_AND_TASK_INTEGRATION',
        code_audit=audit(out/'audit'),native_contract=trace(out/'stock-contract'),
        unchanged_candidate_probe=negative_candidate(image,labels),
        remaining=[
            'Reset/deinit requests freeze admission, retain owners and defer native class525B2 until main-context quiescence and the session barrier. Native EP0 setup executes SET_ADDRESS/SET_CONFIGURATION and native endpoint reconstruction; parent notification is deliberately a pinned native no-op boundary.',
            'The bound deferred OUT1 global RX flush is skipped only at its verified native callsite after the barrier. Native USBRST global TX flush remains native behavior; all composite MSC/control interactions are not proven.',
            'Native SOF partial publication bypasses completion, so the experiment suppresses that bound poll and limits MIDI RX jobs to64B. A66B record-capacity guard pauses without phantom ownership and explicit main service rearms after space is freed. Task/RTOS integration and throughput/latency are unproven.',
            'Accepted software RX debts, shared payload readers, partial messages, held notes and fault/Off ownership retain closed state. General active-transaction cancellation/drain is not implemented.',
            'A stale untagged hardware XFRC injected after a broken assumed barrier still completes a new job in the required negative test. Real silicon disable/FIFO/cache/bus-master cancellation and full NVIC ordering remain release gates.',
            'Suspend/wakeup, DMA modes, complete descriptors/composite class parents, full boot/OOM and production reservation/init of1816B state remain open. Production firmware is unchanged and retains Off/Stop failure. No physical USB/MIDI/device API was accessed.'
        ])
    (out/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


if __name__=='__main__':
    print(json.dumps(probe(sys.argv[1] if len(sys.argv)>1 else ROOT/'logs/usb-control-probe'),indent=2))
    raise SystemExit(2)
