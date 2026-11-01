"""Exact packaged ADC input-readiness proof; no physical device access."""
import hashlib
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'scripts'), str(ROOT/'src')]
from inspect_ui import load_image
from patch_firmware import unpack_syx
from recovery_input_test_support import InputStartup, MAIN_INPUT_READY, SPI_WAIT, STREAM
from recovery_worker_test_support import READY_GATE
from recovery_boot_test_support import STOP
from unicorn.arm_const import UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_LR
import midi_recovery_patch as fixed
import seq_Patch as seq


def ready_result(h):
    context = h.u.context_save()
    h.in_service = True
    try:
        result = h.call(READY_GATE)
        assert result['pc'] == STOP and result['error'] is None
        return result['result']
    finally:
        h.u.context_restore(context)
        h.in_service = False


def probe(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    raw = (ROOT/'build/circuitrhythm-5706-phase1-recovery.syx').read_bytes()
    image = unpack_syx(raw, allow_extended=True)['image']
    report = dict(hardware_release='NO-GO', firmware_changed=False, device_apis_accessed=False,
        syx_sha256=hashlib.sha256(raw).hexdigest(), image_sha256=hashlib.sha256(image).hexdigest(),
        scope='Native ADC DMA646E8/27762 producer and265BA sampler consumer through unforced26596 ready branch2582E. Synthetic96-halfword ADC sample=2048, factory calibration=1500;basic PSP-frame/MSP-call IRQ adapter,not full NVIC/elapsed timing/physical ADC or complete Main boot.')
    for name, data in (('stock', load_image()), ('candidate', image)):
        h = InputStartup(data).main_setup().start_tasks().checkpoint()
        state = bytes(h.u.mem_read(fixed.STATE_BASE, 1088))
        assert ready_result(h) == 0
        h.start_input().checkpoint(MAIN_INPUT_READY, budget=800000)
        assert ready_result(h) == 1
        assert h.readiness()['counters'] == [2, 2, 2]
        assert len(h.dma_transfers) == len(h.input_irqs) == 64
        assert h.validate_stacks() and not h.invalid
        names = {t['tcb']:t['name'] for t in h.tasks}
        evidence = dict(ready_branch=hex(h.u.reg_read(UC_ARM_REG_PC)),
            native_ready_before=0, native_ready_after=1, readiness=h.readiness(),
            sample=h.sample, calibration=h.calibration, transfers=h.dma_transfers,
            irq_adapters=h.input_irqs, readiness_checks=h.ready_checks,
            allocation_count=len(h.allocations), allocations=h.allocations,
            heap=hex(h.read(seq.HEAP_CUR_PTR)), switch_count=len(h.switches),
            requests=len(h.requests), completions=len(h.completions),
            minimum_msp=hex(h.minimum_msp),
            lowest_task_stack_addresses={names[k]:hex(v) for k,v in h.thread_min.items()},
            reserved_state_intact=bytes(h.u.mem_read(fixed.STATE_BASE,1088)) == state,
            instruction_image_identical=bytes(h.u.mem_read(0x08010000,len(data))) == data,
            full_main_complete=False, physical_test=False)
        assert evidence['reserved_state_intact'] and evidence['instruction_image_identical']
        h.input_enabled = False
        # Function entry alone is not proof of a blocked wait: the previous
        # transfer can already be complete. Observe its conditional branch,
        # return natively when ready, then follow the next real transaction.
        passed_spi_waits = []
        for _ in range(8):
            h.checkpoint(0x0802B67A, budget=600000)
            driver = h.u.reg_read(UC_ARM_REG_R0)
            pending = h.u.mem_read(h.read(driver+12)+2,1)[0]
            if not pending:
                break
            caller = h.u.reg_read(UC_ARM_REG_LR) & ~1
            passed_spi_waits.append(dict(caller=hex(caller),pending=pending))
            h.checkpoint(caller,budget=10000)
        else:
            raise AssertionError('native SPI wait with no completion not reached')
        driver = h.u.reg_read(UC_ARM_REG_R0)
        evidence['next_gate'] = dict(pc=hex(h.u.reg_read(UC_ARM_REG_PC)), driver=hex(driver),
            caller_return=hex(h.u.reg_read(UC_ARM_REG_LR)),
            already_completed_spi_waits=passed_spi_waits,
            pending_byte=h.u.mem_read(h.read(driver+12)+2,1)[0],
            dma_streams={hex(base):[hex(h.read(base+4*i)) for i in range(6)]
                         for base in (0x40026058,0x40026070)},
            note='Native31110/46414 waits for SPI DMA completion;no scripted SPI response or readiness flag is supplied.')
        assert evidence['next_gate']['pending_byte'] == 0
        assert bytes(h.u.mem_read(0x08010000,len(data))) == data
        assert len(h.allocations) == 203 and h.read(seq.HEAP_CUR_PTR) == 0x20010BEC
        report[name] = evidence
    a, b = report['stock'], report['candidate']
    assert [(x['size'],x['current']) for x in a['allocations']] == [(x['size'],x['current']) for x in b['allocations']]
    assert a['readiness_checks'] == b['readiness_checks'] and a['transfers'] == b['transfers']
    assert a['lowest_task_stack_addresses'] == b['lowest_task_stack_addresses']
    assert a['next_gate'] == b['next_gate']
    report['next_task'] = 'Trace native31110/310B0 SPI startup transfer contract and DMA1 stream3/4 completion/response semantics,then continue Main25864. Do not force completion flags or protocol replies.'
    (out/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


if __name__ == '__main__':
    r = probe(sys.argv[1]); c = r['candidate']
    print(json.dumps(dict(ready_branch=c['ready_branch'],native_ready=c['native_ready_after'],
        counters=c['readiness']['counters'],transfers=len(c['transfers']),heap=c['heap'],
        next_gate=c['next_gate']['pc'],hardware_release=r['hardware_release'])))
    raise SystemExit(2)
