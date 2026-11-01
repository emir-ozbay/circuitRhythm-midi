"""Ledger local CFG/ABI and stock SPSC byte-publication audit; no release GO."""
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
import midi_usb_ledger_prototype as ledger
import midi_usb_inquiry_prototype as prior
import midi_sysex_retry_prototype as retry
import midi_recovery_prototype as recovery
from thumb_asm import b_w


def audit(out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    code, labels = ledger.arm_code()
    stock = load_image()
    assert stock[prior.NATIVE_POLL-0x08010000:prior.NATIVE_POLL-0x08010000+4] == prior.POLL_PROLOGUE
    assert stock[prior.CIN_TABLE-0x08010000:prior.CIN_TABLE-0x08010000+16] == prior.CIN_LENGTHS
    assert stock[prior.REPLY_ADDR-0x08010000:prior.REPLY_ADDR-0x08010000+len(prior.REPLY)] == prior.REPLY
    _, tx = retry.arm_code(notifications=True, reservations=True)
    md = Cs(CS_ARCH_ARM, CS_MODE_THUMB | CS_MODE_MCLASS); md.detail = True
    instructions = {i.address: i for i in md.disasm(code, ledger.CODE_BASE)}
    assert sum(i.size for i in instructions.values()) == len(code)
    external = {0x0802A37E, 0x080269F0, 0x080269AC, 0x080404BC,
                0x08025B1A, 0x08024B68, tx['sr_submit']}
    loops = []
    calls = []
    for i in instructions.values():
        assert i.mnemonic not in ('blx', 'msr', 'cpsid', 'cpsie')
        if i.mnemonic in ('bl', 'b', 'b.w') or conditional_branch(i.mnemonic):
            target = i.operands[-1].imm
            assert target in instructions or i.mnemonic == 'bl' and target in external
            if i.mnemonic == 'bl':
                calls.append(target)
            elif target <= i.address:
                loops.append((i.address, target))
    bounds = {'poll_record': ledger.MAX_RING//6+1, 'copy_byte': 64,
              'validate_header': 16, 'record_packet': 16, 'packet_byte': 4}
    assert {t for _,t in loops} == {labels[n] for n in bounds}
    assert calls.count(0x080404BC) == calls.count(labels['ul_byte']) == 1
    assert calls.count(0x080269F0) == calls.count(labels['ul_try_reply']) == 1
    assert 0x08029C1A not in calls  # no musical realtime shortcut
    functions = {}
    for name, start in labels.items():
        if not name.startswith('ul_'):
            continue
        todo, seen, exits, maximum = [(start, 0)], set(), set(), 0
        while todo:
            pc, depth = todo.pop()
            if (pc, depth) in seen:
                continue
            seen.add((pc, depth)); assert len(seen) < 4000
            i = instructions[pc]
            if i.mnemonic.startswith('push'):
                depth -= 4*len(i.operands)
            if i.mnemonic.startswith('pop'):
                depth += 4*len(i.operands)
            if i.mnemonic in ('add', 'sub') and i.operands[0].reg == ARM_REG_SP:
                depth += i.operands[-1].imm*(1 if i.mnemonic == 'add' else -1)
            maximum = max(maximum, -depth)
            if i.mnemonic == 'bl':
                assert depth % 8 == 0
            if i.mnemonic == 'bx' or i.mnemonic.startswith('pop') and 'pc' in i.op_str:
                exits.add(depth); continue
            if i.mnemonic in ('b', 'b.w'):
                todo.append((i.operands[-1].imm, depth)); continue
            if conditional_branch(i.mnemonic):
                todo.append((i.operands[-1].imm, depth))
            todo.append((pc+i.size, depth))
        assert exits == {0}
        functions[name] = dict(max_local_stack_bytes=maximum, exit_sp_deltas=sorted(exits))
    windows = [(0x08025AEC, 0x76), (0x0802A37E, 0x114), (0x08026828, 0x52),
               (0x0802C71C, 0x1A), (0x080404BC, 0x118), (prior.NATIVE_POLL, 0x1A4)]
    native = []
    for address, size in windows:
        data = stock[address-0x08010000:address-0x08010000+size]
        native.append(dict(address=hex(address), bytes=size, sha256=hashlib.sha256(data).hexdigest()))
        (out/f'native-{address:08x}.txt').write_text('\n'.join(
            f'{i.address:08x} {i.bytes.hex():12} {i.mnemonic} {i.op_str}' for i in md.disasm(data, address)), encoding='utf-8')
    report = {
        'scope': 'LOCAL_CODE_PASS; synthetic RAM/consumer-owned RX headers',
        'production_integrated': False, 'code_bytes': len(code),
        'code_sha256': hashlib.sha256(code).hexdigest(),
        'additional_synthetic_ram_bytes': ledger.STATE_SIZE,
        'combined_synthetic_ram_bytes': ledger.STATE_SIZE+retry.REQUEST_STATE_SIZE+recovery.STATE_SIZE,
        'max_ring_capacity': ledger.MAX_RING, 'max_local_pending_replies': ledger.MAX_PENDING,
        'max_native_rx_pops_per_pass': 1, 'max_reply_attempts_per_pass': 1,
        'max_native_parser_byte_calls_per_pass': 3*ledger.MAX_RING//4,
        'loop_bounds': bounds, 'forced_irq_mask_instructions': 0, 'functions': functions,
        'emulator_overlay': dict(address=hex(prior.NATIVE_POLL), expected=prior.POLL_PROLOGUE.hex(),
                                 replacement=b_w(prior.NATIVE_POLL, labels['ul_poll']).hex()),
        'native_windows': native,
        'limits': ['SPSC producer/main consumer and publication tests are synthetic, not real IRQ/DMA proof.',
                   'Guarantees cover fully committed admitted records; host data outside a full FIFO is excluded.',
                   'Marker/provenance lifecycle must integrate with every reset, flush, consumer and disconnect path.',
                   'Native total stack/cycles, real timing, unarmed USB rearm, boot/RAM and full registry compatibility are not proven.']
    }
    (out/'ledger-code.txt').write_text('\n'.join(f'{i.address:08x} {i.bytes.hex():12} {i.mnemonic} {i.op_str}'
                                                for i in instructions.values()), encoding='utf-8')
    (out/'ledger-code-report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    print(json.dumps(audit(sys.argv[1] if len(sys.argv)>1 else ROOT/'logs/usb-ledger-audit'), indent=2))
