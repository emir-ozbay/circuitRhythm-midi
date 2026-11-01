"""Compare exact packaged candidates through native reset and OOM caller.

No physical device libraries, firmware overlays, seeded heap or test callbacks.
"""
import hashlib
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'scripts'), str(ROOT/'src')]
from inspect_ui import load_image
from patch_firmware import unpack_syx
from recovery_boot_test_support import NativeStartup, MAIN
from unicorn.arm_const import UC_ARM_REG_PC, UC_ARM_REG_SP
import midi_recovery_patch as fixed
import seq_Patch as seq


def probe(out, previous):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    paths = dict(previous=Path(previous), current=ROOT/'build/circuitrhythm-5706-phase1-recovery.syx')
    result = dict(hardware_release='NO-GO', scope='Actual reset vector, data decoder and static constructors to native main entry; passive RCC/SCS RAM only. No main/RTOS/full boot/peripheral timing proof.')
    stock = NativeStartup(load_image()).startup()
    result['stock'] = dict(initial_sp=hex(stock.initial_sp), reset=hex(stock.reset),
        current=hex(stock.read(seq.HEAP_CUR_PTR)), limit=hex(stock.read(seq.HEAP_LIMIT_PTR)),
        allocations=[dict(size=a['size'], current=hex(a['current'])) for a in stock.allocations])
    for name, path in paths.items():
        raw = path.read_bytes()
        image = unpack_syx(raw, allow_extended=True)['image']
        h = NativeStartup(image).startup()
        assert h.u.reg_read(UC_ARM_REG_PC) == MAIN and not h.invalid
        assert [(a['size'], a['current']) for a in h.allocations] == [(a['size'], a['current']) for a in stock.allocations]
        result[name] = dict(syx_sha256=hashlib.sha256(raw).hexdigest(), image_sha256=hashlib.sha256(image).hexdigest(),
            pc=hex(h.u.reg_read(UC_ARM_REG_PC)), sp=hex(h.u.reg_read(UC_ARM_REG_SP)),
            min_sp=hex(h.min_sp), max_static_stack_bytes=h.initial_sp-h.min_sp,
            static_stack_gap_above_state_bytes=h.min_sp-seq.HEAP_LIMIT,
            heap_current=hex(h.read(seq.HEAP_CUR_PTR)), heap_limit=hex(h.read(seq.HEAP_LIMIT_PTR)),
            allocation_count=len(h.allocations), instructions=h.instructions, masked_instructions=h.masked,
            state_sha256_before_first_bump=hashlib.sha256(h.first_allocation_state).hexdigest(),
            heap_writes=h.heap_writes.copy(), reserved_write_count=len(h.reserved_writes),
            initializer_records=h.initializer_records)
        state = bytes(h.u.mem_read(fixed.STATE_BASE, 1088))
        oom = h.oom_constructor()
        oom['invalid_memory_accesses'] = h.invalid.copy()
        oom['state_intact'] = bytes(h.u.mem_read(fixed.STATE_BASE, 1088)) == state
        oom['last_pcs'] = [hex(p) for p in h.trace]
        result[name]['native_endpoint_oom'] = oom
    old, new = result['previous']['native_endpoint_oom'], result['current']['native_endpoint_oom']
    assert old['error'] and old['invalid_memory_accesses'][-1]['address'] == 0xFFFFFFFF
    assert new['error'] is None and not new['invalid_memory_accesses']
    assert new['pc'] == fixed.seq_code()[1]['alloc_fatal'] and new['primask'] == 1 and new['state_intact']
    assert len(set(new['last_pcs'])) == 1
    result['comparison'] = 'FAIL invalid write to FFFFFFFF -> PASS terminal fault without invalid access;OOM still stops firmware and requires restart'
    from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB, CS_MODE_MCLASS
    md = Cs(CS_ARCH_ARM, CS_MODE_THUMB | CS_MODE_MCLASS)
    for address, size in ((0x08069588, 8), (0x08069764, 0x16), (0x08068A54, 0x20),
                          (0x08022C5E, 0x38), (0x080669DC, 0x72), (0x08068DDC, 0x38),
                          (0x08025278, 0x1A), (0x08025ACC, 0x28), (0x0806668C, 0x76)):
        data = load_image()
        (out/f'native-{address:08x}.txt').write_text('\n'.join(
            f'{i.address:08x} {i.bytes.hex():12} {i.mnemonic} {i.op_str}'
            for i in md.disasm(data[address-0x08010000:address-0x08010000+size], address)), encoding='utf-8')
    (out/'report.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    return result


if __name__ == '__main__':
    report = probe(sys.argv[1], sys.argv[2])
    print(json.dumps(dict(comparison=report['comparison'], hardware_release=report['hardware_release'])))
    raise SystemExit(2)
