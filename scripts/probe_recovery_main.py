"""Packaged native main/task prefix and non-neutral observer comparison."""
import hashlib
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'scripts'), str(ROOT/'src')]
from inspect_ui import load_image
from patch_firmware import unpack_syx
from recovery_boot_test_support import NativeStartup, STOP
from recovery_main_test_support import MainStartup
from unicorn import UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_PC
import midi_recovery_patch as fixed
import seq_Patch as seq


def probe(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    path = ROOT/'build/circuitrhythm-5706-phase1-recovery.syx'
    raw = path.read_bytes()
    image = unpack_syx(raw, allow_extended=True)['image']
    result = dict(hardware_release='NO-GO', firmware_changed=False,
        syx_sha256=hashlib.sha256(raw).hexdigest(), image_sha256=hashlib.sha256(image).hexdigest(),
        scope='Native reset/main to scheduler entry and first Main task to worker request. RCC/QSPI/no-response SDIO model;manual IRQ calls and first-frame unstack,not NVIC/full RTOS/complete boot/timing.',
        device_apis_accessed=False, observer={})
    for global_hook in (True, False):
        h = NativeStartup(image).startup()
        if global_hook:
            h.u.hook_add(UC_HOOK_MEM_WRITE, lambda *args: None)
        h.u.mem_write(0x20010000, b'\xA5'*512)
        call = h.call(0x08023F30, 0x20010010, 48, budget=100)
        escaped = bytes(h.u.mem_read(0x20010040, 16)) != b'\xA5'*16
        result['observer']['global' if global_hook else 'scoped'] = dict(returned=call['pc'] == STOP,
            escaped_zero_fill=escaped, pc=hex(call['pc']), error=call['error'])
    assert result['observer']['global']['escaped_zero_fill'] and not result['observer']['global']['returned']
    assert not result['observer']['scoped']['escaped_zero_fill'] and result['observer']['scoped']['returned']
    for name, data in (('stock', load_image()), ('candidate', image)):
        h = MainStartup(data).main_setup()
        state = bytes(h.u.mem_read(fixed.STATE_BASE, 1088))
        router = h.read(0x20006F04)
        ports = [h.read(h.read(router+0x14)+4*n) for n in range(3)]
        section = dict(main_setup_heap=hex(h.setup_heap_current), allocation_count=len(h.allocations),
            min_msp=hex(h.setup_min_sp), observed_main_stack_bytes=h.initial_sp-h.setup_min_sp,
            gap_above_reserved_state=h.setup_min_sp-seq.HEAP_LIMIT,
            tasks=h.tasks, allocations=h.allocations.copy(), native_qspi_irqs=h.qspi_irqs,
            sdio_command_counts={str(c):h.sdio_commands.count(c) for c in set(h.sdio_commands)},
            scripted_qspi_commands=list(map(hex, h.commands)), timer_events=h.ticks,
            invalid_accesses=h.invalid.copy(), reserved_write_count=len(h.reserved_writes),
            native_router=hex(router),native_ports=list(map(hex,ports)),
            registered_ports=[hex(h.read(fixed.STATE_BASE+16+0x110*n)) for n in range(3)] if name=='candidate' else None)
        h.first_main_task()
        main = next(t for t in h.tasks if t['name'] == 'Main')
        section['main_task_prefix'] = dict(pc=hex(h.u.reg_read(UC_ARM_REG_PC)),
            heap=hex(h.read(seq.HEAP_CUR_PTR)), total_allocations=len(h.allocations),
            initial_psp=hex(main['saved_sp']+68), minimum_psp=hex(h.task_min_sp),
            stack_bottom=hex(main['stack']), stack_bytes=main['words']*4,
            observed_task_stack_bytes=main['saved_sp']+68-h.task_min_sp,
            native_ready_list_selection=list(map(hex,h.selection_steps)),
            invalid_accesses=h.invalid, state_intact=bytes(h.u.mem_read(fixed.STATE_BASE,1088))==state,
            worker_executed=False, full_main_initialization=False)
        result[name] = section
    assert [(a['size'],a['current']) for a in result['stock']['allocations']] == [(a['size'],a['current']) for a in result['candidate']['allocations']]
    assert result['stock']['tasks'] == result['candidate']['tasks']
    assert result['candidate']['main_task_prefix']['state_intact']
    result['next_task'] = 'Run native worker/PendSV handshake at2C23A/2C260 and continue Main toward25864 runtime/controller/project setup. Router/three ports already constructed. Do not use2004EA98 as measured final heap.'
    (out/'report.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


if __name__ == '__main__':
    r = probe(sys.argv[1])
    print(json.dumps(dict(main_heap=r['candidate']['main_setup_heap'], tasks=len(r['candidate']['tasks']),
                         observer='FAIL_TO_PASS', firmware_changed=False, hardware_release='NO-GO')))
    raise SystemExit(2)
