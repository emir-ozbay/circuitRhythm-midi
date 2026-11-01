"""Local lifecycle guard/trampoline/ABI/PRIMASK audit; synthetic only."""
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
import midi_usb_lifecycle_prototype as life
import midi_usb_ledger_prototype as ledger
import midi_usb_inquiry_prototype as rx
import midi_sysex_retry_prototype as retry
import midi_recovery_prototype as recovery
import seq_Patch as seq
from thumb_asm import b_w


def audit(out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    code, labels = life.arm_code(); stock = load_image()
    _, ul = ledger.arm_code(); _, sq = seq.arm_code()
    md = Cs(CS_ARCH_ARM, CS_MODE_THUMB | CS_MODE_MCLASS); md.detail = True
    insns = {i.address:i for i in md.disasm(code, life.CODE_BASE)}
    assert sum(i.size for i in insns.values()) == len(code)
    tails, overlays = {}, []
    starts = set()
    for address, (_,_,original) in life.GATES.items():
        assert stock[address-0x08010000:address-0x08010000+len(original)] == original
        assert sum(i.size for i in md.disasm(original,address)) == len(original)
        assert 0x08010200 <= address < address+len(original) <= 0x08080000
        replacement = b_w(address, labels[f'cl_gate_{address:08x}'])+b'\x00\xBF'*(len(original)//2-2)
        for old in overlays:
            assert address+len(original) <= int(old['address'],16) or int(old['address'],16)+len(bytes.fromhex(old['replacement'])) <= address
        overlays.append(dict(address=hex(address), expected=original.hex(), replacement=replacement.hex()))
        start = labels[f'cl_trampoline_{address:08x}']; starts.add(start)
        offset = start-life.CODE_BASE
        assert code[offset:offset+len(original)] == original
        tails[start+len(original)] = address+len(original)
    overlays.append(dict(address=hex(rx.NATIVE_POLL), expected=rx.POLL_PROLOGUE.hex(),
                         replacement=b_w(rx.NATIVE_POLL,labels['cl_poll']).hex()))
    external = {0x0802A37E,0x0802A374,0x080405D4,ul['ul_poll'],sq['c_midi_inputs_idle']}
    for i in insns.values():
        if i.mnemonic in ('bl','b','b.w') or conditional_branch(i.mnemonic):
            target = i.operands[-1].imm
            assert target in insns or i.mnemonic == 'bl' and target in external or tails.get(i.address) == target
        assert i.mnemonic != 'blx'
    functions = {}
    for name,start in labels.items():
        if not name.startswith('cl_') or name.startswith('cl_trampoline_'):
            continue
        todo,seen,exits,maximum = [(start,0)],set(),set(),0
        while todo:
            pc,depth=todo.pop()
            if (pc,depth) in seen:
                continue
            seen.add((pc,depth)); assert len(seen)<5000
            i=insns[pc]
            if i.mnemonic.startswith('push'): depth-=4*len(i.operands)
            if i.mnemonic.startswith('pop'): depth+=4*len(i.operands)
            if i.mnemonic in ('add','sub') and i.operands[0].reg==ARM_REG_SP:
                depth+=i.operands[-1].imm*(1 if i.mnemonic=='add' else -1)
            maximum=max(maximum,-depth)
            if i.mnemonic=='bl': assert depth%8==0
            if i.mnemonic=='bx' or i.mnemonic.startswith('pop') and 'pc' in i.op_str:
                exits.add(depth); continue
            if i.mnemonic in ('b','b.w'):
                target=i.operands[-1].imm
                if target in starts:
                    exits.add(depth); continue
                todo.append((target,depth)); continue
            if conditional_branch(i.mnemonic): todo.append((i.operands[-1].imm,depth))
            todo.append((pc+i.size,depth))
        assert exits=={0}, (name,exits)
        functions[name]=dict(max_local_stack_bytes=maximum,exit_sp_deltas=sorted(exits))
    masked=[]
    for i in insns.values():
        if i.mnemonic!='cpsid': continue
        todo=[(i.address+i.size,frozenset())]; paths=[]
        while todo:
            pc,path=todo.pop(); assert pc not in path
            path=path|{pc}; j=insns[pc]
            assert j.mnemonic not in ('bl','blx','bx','pop','pop.w')
            if j.mnemonic=='msr' and j.op_str.startswith('primask,'):
                paths.append(len(path)); continue
            if j.mnemonic in ('b','b.w'):
                todo.append((j.operands[-1].imm,path)); continue
            if conditional_branch(j.mnemonic): todo.append((j.operands[-1].imm,path))
            todo.append((pc+j.size,path))
        masked.append(max(paths))
    report={
        'scope':'LOCAL_CODE_PASS; typed native entry gates only','production_integrated':False,
        'code_bytes':len(code),'code_sha256':hashlib.sha256(code).hexdigest(),
        'additional_synthetic_ram_bytes':life.STATE_SIZE,
        'combined_synthetic_ram_bytes':life.STATE_SIZE+ledger.STATE_SIZE+retry.REQUEST_STATE_SIZE+recovery.STATE_SIZE,
        'max_forced_mask_instructions':max(masked),'masked_calls_or_loops':False,
        'functions':functions,'emulator_overlays':overlays,
        'limits':'No full IRQ/RTOS/cycle, arbitrary inline-writer or active-TX/disconnect cancellation proof.'}
    (out/'lifecycle-code.txt').write_text('\n'.join(f'{i.address:08x} {i.bytes.hex():12} {i.mnemonic} {i.op_str}' for i in insns.values()),encoding='utf-8')
    (out/'lifecycle-code-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


if __name__=='__main__':
    print(json.dumps(audit(sys.argv[1] if len(sys.argv)>1 else ROOT/'logs/usb-lifecycle-audit'),indent=2))
