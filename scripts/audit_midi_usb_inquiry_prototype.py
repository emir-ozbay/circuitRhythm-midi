"""Pin, local CFG/ABI and explicit bounded-loop audit; never hardware GO."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT/'scripts')]
from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB, CS_MODE_MCLASS
from capstone.arm_const import ARM_REG_SP
from audit_midi_recovery_prototype import conditional_branch
from inspect_ui import load_image
import midi_usb_inquiry_prototype as rx
import midi_sysex_retry_prototype as retry
import midi_recovery_prototype as recovery
from thumb_asm import b_w


def audit(out, ordered=False):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    stock = load_image()
    code, labels = rx.arm_code(ordered=ordered)
    _, tx = retry.arm_code(notifications=True, reservations=True)
    assert stock[rx.NATIVE_POLL-0x08010000:rx.NATIVE_POLL-0x08010000+4] == rx.POLL_PROLOGUE
    assert stock[rx.CIN_TABLE-0x08010000:rx.CIN_TABLE-0x08010000+16] == rx.CIN_LENGTHS
    assert stock[rx.REPLY_ADDR-0x08010000:rx.REPLY_ADDR-0x08010000+len(rx.REPLY)] == rx.REPLY
    assert stock[0x170D0:0x170D6] == rx.INQUIRY
    md = Cs(CS_ARCH_ARM, CS_MODE_THUMB | CS_MODE_MCLASS)
    md.detail = True
    insns = {i.address: i for i in md.disasm(code, rx.CODE_BASE)}
    assert sum(i.size for i in insns.values()) == len(code)
    external = {tx['sr_submit'], 0x080269F0, 0x080269AC, 0x0802A37E,
                0x080404BC, 0x08025B1A, 0x08024B68, 0x08029C1A}
    edges = []
    for i in insns.values():
        assert i.mnemonic not in ('cpsid', 'cpsie', 'msr', 'blx')
        if i.mnemonic in ('b', 'b.w', 'bl') or conditional_branch(i.mnemonic):
            target = i.operands[-1].imm
            assert target in insns or i.mnemonic == 'bl' and target in external
            if i.mnemonic != 'bl' and target <= i.address:
                edges.append((i.address, target))
    # Every local backedge belongs to a fixed64B buffer walk. There are no
    # wait-for-TX or repeat-until-port-ready loops in the new code.
    bounds = {'clear_seen': 64, 'validate_cables': 16, 'poll_bytes': 49,
              'next_packet': 17, 'scan_byte': 49}  # includes terminal checks
    if ordered:
        del bounds['clear_seen']
        del bounds['scan_byte']
        assert 'ui_scan_realtime' not in labels
        calls = [i.operands[0].imm for i in insns.values() if i.mnemonic == 'bl']
        assert calls.count(0x080404BC) == calls.count(labels['ui_byte']) == 1
        assert 0x08029C1A not in calls  # no native alternate realtime delivery
        assert calls.count(labels['ui_try_reply']) == 1
        hold = insns[labels['poll_hold']+4]
        assert hold.mnemonic in ('b', 'b.w') and hold.operands[0].imm == labels['poll_done']
        assert labels['poll_hold'] < labels['poll_deliver'] < labels['poll_clear']
    assert {target for _, target in edges} == {labels[name] for name in bounds}
    functions = {}
    for name, start in labels.items():
        if not name.startswith('ui_'):
            continue
        todo, seen, exits, deepest = [(start, 0)], set(), set(), 0
        while todo:
            pc, depth = todo.pop()
            if (pc, depth) in seen:
                continue
            seen.add((pc, depth)); assert len(seen) < 2000
            i = insns[pc]
            if i.mnemonic.startswith('push'):
                depth -= 4*len(i.operands)
            if i.mnemonic.startswith('pop'):
                depth += 4*len(i.operands)
            if i.mnemonic in ('add', 'sub') and i.operands[0].reg == ARM_REG_SP:
                depth += i.operands[-1].imm*(1 if i.mnemonic == 'add' else -1)
            deepest = max(deepest, -depth)
            if i.mnemonic == 'bl':
                assert depth % 8 == 0
            if i.mnemonic == 'bx' or i.mnemonic.startswith('pop') and 'pc' in i.op_str:
                exits.add(depth); continue
            if i.mnemonic in ('b', 'b.w'):
                todo.append((i.operands[0].imm, depth)); continue
            if conditional_branch(i.mnemonic):
                todo.append((i.operands[-1].imm, depth))
            todo.append((pc+i.size, depth))
        assert exits == {0}
        functions[name] = {'max_local_stack_bytes': deepest, 'exit_sp_deltas': sorted(exits)}
    # Save the exact native windows supporting pop/publication/parser contracts.
    windows = [(0x08025AEC, 0x76), (0x0802691E, 0x6A), (0x080269F0, 0x10),
               (0x08029AC8, 0x1A4), (0x0802A37E, 0x114), (0x080404BC, 0x118),
               (0x08026F0C, 0x2C)]
    native = []
    for start, size in windows:
        data = stock[start-0x08010000:start-0x08010000+size]
        native.append({'start': hex(start), 'size': size, 'sha256': hashlib.sha256(data).hexdigest()})
        (out/f'native-{start:08x}.txt').write_text('\n'.join(
            f'{i.address:08x} {i.bytes.hex():12} {i.mnemonic} {i.op_str}'
            for i in md.disasm(data, start)), encoding='utf-8')
    report = {
        'scope': 'LOCAL_CODE_PASS; synthetic RAM only', 'production_integrated': False,
        'code_bytes': len(code), 'code_sha256': hashlib.sha256(code).hexdigest(),
        'additional_synthetic_ram_bytes': rx.STATE_SIZE,
        'combined_synthetic_ram_bytes': rx.STATE_SIZE+retry.REQUEST_STATE_SIZE+recovery.STATE_SIZE,
        'ordered_admission': ordered,
        'owned_usb_buffer_bytes': 64, 'pending_inquiry_tokens': rx.MAX_PENDING if ordered else 1,
        'max_reply_attempts_per_pass': 1 if ordered else 9,
        'max_native_rx_pops_per_pass': 1, 'loop_bounds': bounds,
        'forced_irq_mask_instructions': 0, 'functions': functions,
        'emulator_overlay': {'address': hex(rx.NATIVE_POLL), 'expected': rx.POLL_PROLOGUE.hex(),
                             'replacement': b_w(rx.NATIVE_POLL, labels['ui_poll']).hex()},
        'native_windows': native,
        'limits': ['Local ABI and buffer bounds do not prove native call stack or timing.',
                   'One initialized endpoint/cable0; no boot/RAM/OOM/real IRQ or device test.',
                   ('At inquiry capacity the next SysEx start blocks its suffix in order; realtime latency remains open.'
                    if ordered else 'Realtime beyond a retained non-RT buffer remains blocked. No global fairness claim.'),
                   'Exact inquiry bypasses native multicast listeners; whole registry compatibility unproven.']
    }
    (out/'usb-inquiry-code.txt').write_text('\n'.join(
        f'{i.address:08x} {i.bytes.hex():12} {i.mnemonic} {i.op_str}' for i in insns.values()), encoding='utf-8')
    (out/'usb-inquiry-code-report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    print(json.dumps(audit(sys.argv[1] if len(sys.argv)>1 else ROOT/'logs/usb-inquiry-audit'), indent=2))
