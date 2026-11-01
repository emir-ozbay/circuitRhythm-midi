"""Exact packaged native port/worker proof; no physical device APIs."""
import hashlib
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'scripts'), str(ROOT/'src')]
from inspect_ui import load_image
from patch_firmware import unpack_syx
from recovery_worker_test_support import WorkerStartup, READY_GATE
from unicorn.arm_const import UC_ARM_REG_PC
import midi_recovery_patch as fixed
import seq_Patch as seq


def probe(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    path = ROOT/'build/circuitrhythm-5706-phase1-recovery.syx'
    raw = path.read_bytes()
    image = unpack_syx(raw, allow_extended=True)['image']
    report = dict(hardware_release='NO-GO', firmware_changed=False, device_apis_accessed=False,
        syx_sha256=hashlib.sha256(raw).hexdigest(), image_sha256=hashlib.sha256(image).hexdigest(),
        scope='Native port/SVC/PendSV/basic-frame shim and all five tasks through Storage handshakes to Main26596 input-readiness gate. Inherited RCC/QSPI/no-response SDIO/IRQ adapter models;not full NVIC/timing/FPU/media boot.')
    for name, data in (('stock', load_image()), ('candidate', image)):
        h = WorkerStartup(data).main_setup()
        state = bytes(h.u.mem_read(fixed.STATE_BASE, 1088))
        h.start_tasks().checkpoint()
        assert h.validate_stacks() and not h.invalid
        assert bytes(h.u.mem_read(0x08010000,len(data))) == data, 'emulated firmware bytes changed'
        names = {t['tcb']:t['name'] for t in h.tasks}
        context = h.u.context_save()
        ready_result = h.call(READY_GATE)['result']
        h.u.context_restore(context)
        assert ready_result == 0
        report[name] = dict(pc=hex(h.u.reg_read(UC_ARM_REG_PC)), heap=hex(h.read(seq.HEAP_CUR_PTR)),
            allocations=h.allocations, allocation_count=len(h.allocations), port_heap=hex(h.port_heap),
            critical_before=hex(h.critical_before), critical_after=h.read(h.critical_pointer),
            svc=dict(handler='08025C6C',old_msp_frame=hex(h.svc_msp),first_task='IDLE',native_handler_executed=True),
            switches=[dict(**s,old_task=names[s['old']],new_task=names[s['new']]) for s in h.switches],
            switch_count=len(h.switches), requests=[dict(**e,name=names[e['task']]) for e in h.requests],
            completions=[dict(**e,name=names[e['task']]) for e in h.completions],
            worker_calls=[dict(**e,name=names[e['task']]) for e in h.worker_calls], wfi_timer_wakes=h.wfi_wakes,
            minimum_msp=hex(h.minimum_msp), lowest_task_stack_addresses={names[k]:hex(v) for k,v in h.thread_min.items()},
            task_stack_bases={t['name']:hex(t['stack']) for t in h.tasks},
            native_ready_result=ready_result,readiness=h.readiness(),reserved_state_intact=bytes(h.u.mem_read(fixed.STATE_BASE,1088))==state,
            instruction_image_identical=True,thread_fp_instructions_executed=False,full_main_complete=False,physical_test=False)
    before, after = report['stock'], report['candidate']
    assert [(a['size'],a['current']) for a in before['allocations']] == [(a['size'],a['current']) for a in after['allocations']]
    assert after['reserved_state_intact'] and after['allocation_count']==203
    assert len(after['requests'])==len(after['completions'])==9
    report['next_task']='Trace native input sample/IRQ producer and265BA/2BB64/2BC28/2BEE2 readiness counters required by26596;continue Main25864 without forcing counters/ready return.'
    (out/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


if __name__ == '__main__':
    r = probe(sys.argv[1]);c=r['candidate']
    print(json.dumps(dict(heap=c['heap'],allocations=c['allocation_count'],switches=c['switch_count'],requests=len(c['requests']),completed=len(c['completions']),native_ready=c['native_ready_result'],hardware_release='NO-GO')))
    raise SystemExit(2)
