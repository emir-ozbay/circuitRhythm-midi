"""Local Thumb CFG/ABI/PRIMASK and emulator overlay audit; never release GO."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT/'scripts')]
import midi_sysex_retry_prototype as retry
import midi_recovery_prototype as recovery
from audit_midi_recovery_prototype import conditional_branch
from inspect_ui import load_image
from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB, CS_MODE_MCLASS
from capstone.arm_const import ARM_REG_SP
from thumb_asm import b_w, movw, movt, mov_reg, push


def audit(out, notifications=False, reservations=False):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    code, labels = retry.arm_code(notifications=notifications, reservations=reservations)
    _, rp = recovery.arm_code()
    md = Cs(CS_ARCH_ARM, CS_MODE_THUMB | CS_MODE_MCLASS)
    md.detail = True
    insns = {i.address: i for i in md.disasm(code, retry.CODE_BASE)}
    assert sum(i.size for i in insns.values()) == len(code)
    external = {retry.NATIVE_COPY, rp['rp_lookup'], rp['rp_sysex_send'], rp['rp_sysex_pending']}
    if notifications:
        external.add(retry.NATIVE_NOTIFY)
    stock = load_image()
    overlays, tails = [], {}
    for entry, original in retry.CALLER_GATES.items():
        assert stock[entry-0x08010000:entry-0x08010000+4] == original
        assert 0x08010200 <= entry < entry+4 <= 0x08080000
        assert all(entry+4 <= int(o['address'], 16) or int(o['address'], 16)+4 <= entry for o in overlays)
        overlays.append({'address': hex(entry), 'expected': original.hex(),
                         'replacement': b_w(entry, labels[f'sr_gate_{entry:08x}']).hex(), 'scope': 'Unicorn only'})
        replay = original
        if entry == 0x0802DE84:
            assert int.from_bytes(stock[0x1DEDC:0x1DEE0], 'little') == 0x20006F04
            replay = movw(0, 0x6F04)+movt(0, 0x2000)+mov_reg(2, 1)
        elif entry == 0x0802ED88:
            assert int.from_bytes(stock[0x1EE30:0x1EE34], 'little') == 0x20006F58
            replay = push([4, 5])+movw(3, 0x6F58)+movt(3, 0x2000)
        start = labels[f'caller_trampoline_{entry:08x}']
        expected = replay+b_w(start+len(replay), entry+4)
        assert code[start-retry.CODE_BASE:start-retry.CODE_BASE+len(expected)] == expected
        tails[start+len(replay)] = entry+4
    if reservations:
        for entry, (original, return_pc, stack_words) in retry.REQUEST_GATES.items():
            assert stock[entry-0x08010000:entry-0x08010000+4] == original
            site = (return_pc & ~1)-4
            call = list(md.disasm(stock[site-0x08010000:site-0x08010000+4], site))
            assert len(call) == 1 and call[0].mnemonic == 'bl' and call[0].operands[0].imm == 0x0804691A
            assert 0x08010200 <= entry < entry+4 <= 0x08080000
            assert all(entry+4 <= int(o['address'], 16) or int(o['address'], 16)+4 <= entry for o in overlays)
            overlays.append({'address': hex(entry), 'expected': original.hex(),
                             'replacement': b_w(entry, labels[f'sr_request_gate_{entry:08x}']).hex(),
                             'stack_arguments': stack_words, 'scope': 'Unicorn only'})
            start = labels[f'request_trampoline_{entry:08x}']
            expected = original+b_w(start+4, entry+4)
            assert code[start-retry.CODE_BASE:start-retry.CODE_BASE+8] == expected
            tails[start+4] = entry+4
    for i in insns.values():
        if i.mnemonic in ('bl', 'b', 'b.w') or conditional_branch(i.mnemonic):
            target = i.operands[-1].imm
            assert (target in insns or i.mnemonic == 'bl' and target in external
                    or tails.get(i.address) == target), (hex(i.address), hex(target))
        if i.mnemonic == 'blx':
            assert notifications and i.address == labels['owned_callback_call'] and i.op_str == 'r4'
    functions = {}
    for name, start in labels.items():
        if not name.startswith('sr_'):
            continue
        todo, seen, depths, max_stack = [(start, 0)], set(), set(), 0
        while todo:
            pc, depth = todo.pop()
            if (pc, depth) in seen:
                continue
            seen.add((pc, depth))
            assert len(seen) < 3000
            i = insns[pc]
            if i.mnemonic.startswith('push'):
                depth -= 4*len(i.operands)
            if i.mnemonic.startswith('pop'):
                depth += 4*len(i.operands)
            if i.mnemonic in ('add', 'sub') and i.operands[0].reg == ARM_REG_SP:
                depth += i.operands[-1].imm * (1 if i.mnemonic == 'add' else -1)
            max_stack = max(max_stack, -depth)
            if i.mnemonic in ('bl', 'blx'):
                assert depth % 8 == 0
            if i.mnemonic == 'bx' or i.mnemonic.startswith('pop') and 'pc' in i.op_str:
                assert depth == 0
                depths.add(depth)
                continue
            if i.mnemonic in ('b', 'b.w'):
                todo.append((i.operands[0].imm, depth))
                continue
            if conditional_branch(i.mnemonic):
                todo.append((i.operands[-1].imm, depth))
            todo.append((pc+i.size, depth))
        assert depths == {0}
        functions[name] = {'local_stack_bytes': max_stack, 'exit_sp_deltas': sorted(depths)}
    masked = []
    for i in insns.values():
        if i.mnemonic != 'cpsid':
            continue
        todo = [(i.address+i.size, frozenset())]
        lengths = []
        while todo:
            pc, path = todo.pop()
            assert pc not in path
            path = path | {pc}
            j = insns[pc]
            assert j.mnemonic not in ('bl', 'blx', 'bx', 'pop', 'pop.w')
            if j.mnemonic == 'msr' and j.op_str.startswith('primask,'):
                lengths.append(len(path))
                continue
            if j.mnemonic in ('b', 'b.w'):
                todo.append((j.operands[0].imm, path))
                continue
            if conditional_branch(j.mnemonic):
                todo.append((j.operands[-1].imm, path))
            todo.append((pc+j.size, path))
        masked.append(max(lengths))
    service = [i for i in insns.values() if labels['sr_service'] <= i.address < labels['sr_producer_begin']]
    assert sum(i.mnemonic == 'bl' and i.operands[0].imm == rp['rp_sysex_send'] for i in service) == 3
    assert all(i.operands[-1].imm > i.address for i in service
               if i.mnemonic in ('b', 'b.w') or conditional_branch(i.mnemonic))
    result = {'scope': 'LOCAL_EXPERIMENTAL_CODE_PASS', 'production_integrated': False,
              'owned_admission_notification': notifications,
              'upper_formatter_reservations': reservations,
              'code_bytes': len(code), 'code_sha256': hashlib.sha256(code).hexdigest(),
              'additional_synthetic_ram_bytes': retry.REQUEST_STATE_SIZE if reservations else retry.NOTIFICATION_STATE_SIZE if notifications else retry.STATE_SIZE,
              'combined_synthetic_ram_bytes': (retry.REQUEST_STATE_SIZE if reservations else retry.NOTIFICATION_STATE_SIZE if notifications else retry.STATE_SIZE)+recovery.STATE_SIZE,
              'payload_capacity': retry.CAPACITY, 'queue_slots': 1,
              'max_admission_attempts_per_service': 3, 'max_forced_mask_instructions': max(masked),
              'functions': functions, 'emulator_producer_overlays': overlays,
              'limits': 'No production heap/boot/IRQ cycle or whole-call-stack proof. Optional native admission notification is not wire completion or caller backpressure acceptance.'}
    (out/'retry-code.txt').write_text('\n'.join(f'{i.address:08X} {i.bytes.hex():12} {i.mnemonic} {i.op_str}' for i in insns.values()), encoding='utf-8')
    (out/'retry-code-report.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    return result


if __name__ == '__main__':
    print(json.dumps(audit(sys.argv[1] if len(sys.argv) > 1 else ROOT/'logs/sysex-retry-audit'), indent=2))
