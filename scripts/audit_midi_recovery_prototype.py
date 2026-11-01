"""Read-only Capstone/CFG audit of the isolated experiment, not a release GO."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT/'scripts')]
import midi_recovery_prototype as recovery
from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB, CS_MODE_MCLASS


def conditional_branch(mnemonic):
    return mnemonic.split('.')[0] in ('beq', 'bne', 'bhi', 'bls', 'bhs', 'blo',
                                      'bge', 'blt', 'bgt', 'ble', 'bpl', 'bmi',
                                      'bvs', 'bvc', 'bcs', 'bcc')


def audit(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    code, labels = recovery.arm_code()
    from inspect_ui import load_image
    from thumb_asm import b_w
    stock = load_image()  # pinned stock validation, read-only
    overlays = []
    for address, expected, replacement in (
        (recovery.NATIVE_ROUTER, recovery.ROUTER_PROLOGUE,
         b_w(recovery.NATIVE_ROUTER, labels['rp_sysex_route'])),
        (recovery.ROUTER_WAIT, recovery.ROUTER_WAIT_BYTES,
         b_w(recovery.ROUTER_WAIT, recovery.ROUTER_FAILURE)),
    ):
        assert stock[address-0x08010000:address-0x08010000+4] == expected
        assert 0x08010200 <= address < address+4 <= 0x08080000
        overlays.append({'address': hex(address), 'expected_hex': expected.hex(),
                         'replacement_hex': replacement.hex(), 'scope': 'Unicorn only'})
    assert bytes(code[labels['native_router_trampoline']-recovery.CODE_BASE:]) == (
        recovery.ROUTER_PROLOGUE+b_w(labels['native_router_trampoline']+4, recovery.NATIVE_ROUTER+4))
    md = Cs(CS_ARCH_ARM, CS_MODE_THUMB | CS_MODE_MCLASS)
    md.detail = True
    insns = {i.address: i for i in md.disasm(code, recovery.CODE_BASE)}
    assert sum(i.size for i in insns.values()) == len(code)
    (out/'prototype-code.txt').write_text('\n'.join(
        f'{i.address:08X} {i.bytes.hex():12} {i.mnemonic} {i.op_str}' for i in insns.values()), encoding='utf-8')
    external = {recovery.NATIVE_SEND, recovery.NATIVE_POLL, recovery.NATIVE_COUNT}
    constants, masked_paths = [], []
    for i in insns.values():
        if i.mnemonic in ('b', 'b.w', 'bl') or (i.mnemonic.startswith('b') and i.mnemonic != 'blx' and i.operands[-1].type == 2):
            target = i.operands[-1].imm
            assert (target in insns or i.mnemonic == 'bl' and target in external
                    or i.address == labels['native_router_trampoline']+4
                    and target == recovery.NATIVE_ROUTER+4), (hex(i.address), hex(target))
        if i.mnemonic == 'blx':
            assert i.op_str == 'r2' and i.address > labels['rp_ready']
            assert i.address < labels['rp_sysex_remaining']
        if i.mnemonic == 'movw':
            nxt = insns.get(i.address+i.size)
            if nxt and nxt.mnemonic == 'movt' and nxt.operands[0].reg == i.operands[0].reg:
                value = i.operands[1].imm | nxt.operands[1].imm << 16
                constants.append(hex(value))
                assert not 0x40000000 <= value < 0x60000000
                assert not 0x1FFF0000 <= value < 0x20000000
    functions = {}
    for name, start in labels.items():
        if not name.startswith('rp_'):
            continue
        work = [(start, 0)]
        visited, exits, calls, max_depth = set(), set(), set(), 0
        while work:
            pc, depth = work.pop()
            if (pc, depth) in visited:
                continue
            visited.add((pc, depth))
            assert len(visited) < 3000
            i = insns[pc]
            m, op = i.mnemonic, i.op_str
            if m.startswith('push'):
                depth -= 4*len(i.operands)
            if m.startswith('pop'):
                depth += 4*len(i.operands)
            if m in ('sub', 'add') and op.startswith('sp,'):
                depth += (-1 if m == 'sub' else 1)*i.operands[-1].imm
            max_depth = max(max_depth, -depth)
            if m in ('bl', 'blx'):
                assert depth % 8 == 0, (name, hex(pc), depth)
                calls.add(hex(i.operands[0].imm) if m == 'bl' else 'driver.ready vtable+C')
            if m == 'bx' and op == 'lr' or m.startswith('pop') and 'pc' in op:
                assert depth == 0, (name, hex(pc), depth)
                exits.add(depth)
                continue
            if m in ('b', 'b.w'):
                work.append((i.operands[0].imm, depth))
                continue
            if conditional_branch(m):
                work.append((i.operands[-1].imm, depth))
            work.append((pc+i.size, depth))
        assert exits == {0}
        functions[name] = {'entry': hex(start), 'local_stack_max_bytes': max_depth,
                           'exit_sp_deltas': sorted(exits), 'calls': sorted(calls)}
    # Enumerate every explicit CPSID -> MSR PRIMASK path: no calls/loops while
    # this prototype masks interrupts. Incoming PRIMASK1 is separately tested.
    for ins in insns.values():
        if ins.mnemonic != 'cpsid':
            continue
        work = [(ins.address+ins.size, 0, frozenset())]
        lengths = []
        while work:
            pc, count, path = work.pop()
            assert pc not in path, 'loop while PRIMASK forced1'
            path = path | {pc}
            i = insns[pc]
            count += 1
            assert i.mnemonic not in ('bl', 'blx', 'bx', 'pop', 'pop.w')
            if i.mnemonic == 'msr' and i.op_str.startswith('primask,'):
                lengths.append(count)
                continue
            if i.mnemonic in ('b', 'b.w'):
                work.append((i.operands[0].imm, count, path))
                continue
            if conditional_branch(i.mnemonic):
                work.append((i.operands[-1].imm, count, path))
            work.append((pc+i.size, count, path))
        masked_paths.append({'cpsid': hex(ins.address), 'max_instructions_until_restore': max(lengths)})
    report = {'status': 'EXPERIMENTAL_CODE_CHECKS_PASS', 'production_integrated': False,
              'code_sha256': hashlib.sha256(code).hexdigest(), 'code_bytes': len(code),
              'ram_bytes': recovery.STATE_SIZE, 'port_bitmap_capacity': 2048,
              'word_or_off_attempt_budget_per_poll': recovery.WORD_BUDGET,
              'sysex_native_service_pass_budget': 1,
              'emulator_only_overlay_manifest': overlays,
              'router_trampoline': {'replayed_prologue': recovery.ROUTER_PROLOGUE.hex(),
                                    'native_continuation': hex(recovery.NATIVE_ROUTER+4),
                                    'native_frame_bytes': 32},
              'functions': functions, 'forced_mask_paths': masked_paths,
              'constants': constants,
              'limits': 'No production hooks/allocator/initialization or full boot/IRQ proof. Native queue/driver stack and elapsed CPU cycles are outside this local CFG audit.'}
    (out/'prototype-code-report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    print(json.dumps(audit(sys.argv[1] if len(sys.argv) > 1 else ROOT/'logs/recovery-prototype-audit'), indent=2))
