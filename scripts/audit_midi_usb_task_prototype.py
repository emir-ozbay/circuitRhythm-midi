"""Main call-site/ABI/CFG evidence; the native RTOS wait remains a boundary."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from capstone import Cs,CS_ARCH_ARM,CS_MODE_THUMB,CS_MODE_MCLASS
from audit_midi_recovery_prototype import conditional_branch
from audit_midi_usb_power_prototype import audit as power_audit
from inspect_ui import load_image
from thumb_asm import bl
import midi_usb_task_prototype as task
import midi_usb_power_prototype as power
import midi_sysex_retry_prototype as retry


def audit(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True);inherited=power_audit(out/'power')
    code,labels=task.arm_code();stock=load_image();_,pw=power.arm_code();_,sr=retry.arm_code(notifications=True,reservations=True)
    md=Cs(CS_ARCH_ARM,CS_MODE_THUMB|CS_MODE_MCLASS);md.detail=True
    insns={i.address:i for i in md.disasm(code,task.CODE_BASE)}
    assert sum(i.size for i in insns.values())==len(code)
    assert 0x0806A570<=task.CODE_BASE<task.CODE_BASE+len(code)<=0x08080000 and task.CODE_BASE%4==0
    p=task.MAIN_CALL;expected=task.GATES[p]
    assert stock[p-0x08010000:p-0x08010000+4]==expected
    original=list(md.disasm(expected,p));assert len(original)==1 and original[0].mnemonic=='bl' and original[0].operands[0].imm==0x08027624
    external={sr['sr_service'],pw['pw_service'],0x08027624}
    for i in insns.values():
        assert i.mnemonic not in ('blx','cpsid','cpsie','msr')
        if i.mnemonic in ('b','b.w','bl') or conditional_branch(i.mnemonic):
            t=i.operands[-1].imm;assert t in insns or i.mnemonic=='bl' and t in external
            if i.mnemonic!='bl':assert t>i.address,'No local task service loop permitted'
    todo,seen,exits,maximum=[(labels['ut_main'],0)],set(),set(),0
    while todo:
        pc,depth=todo.pop()
        if (pc,depth) in seen:continue
        seen.add((pc,depth));assert len(seen)<2500;i=insns[pc]
        if i.mnemonic.startswith('push'):depth-=4*len(i.operands)
        if i.mnemonic.startswith('pop'):depth+=4*len(i.operands)
        maximum=max(maximum,-depth)
        if i.mnemonic=='bl':assert depth%8==0
        if i.mnemonic=='bx' or i.mnemonic.startswith('pop') and 'pc' in i.op_str:exits.add(depth);continue
        if i.mnemonic in ('b','b.w'):todo.append((i.operands[-1].imm,depth));continue
        if conditional_branch(i.mnemonic):todo.append((i.operands[-1].imm,depth))
        todo.append((pc+i.size,depth))
    assert exits=={0}
    r=dict(scope='LOCAL_CODE_PASS; native main USB-slot reachability, not full task/RTOS/boot safety',production_integrated=False,
        code_bytes=len(code),code_sha256=hashlib.sha256(code).hexdigest(),additional_synthetic_ram_bytes=task.STATE_SIZE,
        combined_synthetic_ram_bytes=inherited['combined_synthetic_ram_bytes']+task.STATE_SIZE,
        max_local_stack_bytes=maximum,exit_sp_deltas=sorted(exits),forced_mask_sections=0,masked_calls_or_loops=False,
        emulator_overlays=[dict(address=hex(p),expected_stock=expected.hex(),replacement=bl(p,labels['ut_main']).hex())],
        native_calls_per_main_pass=dict(sysex_retry=1,power_service=1,msc_poll_max=1),inherited_power=inherited,
        remaining='Accepted ledger/TX software debt can still block closure/reopen; native27624 callers2DE92/53E78 are not wired. Worker648AE loop executes with modeled RTOS wait/return, ACK/IRQ/flash. Full scheduler/boot/OOM/RAM/init/timing and production integration remain open.')
    (out/'task-code.txt').write_text('\n'.join(f'{i.address:08x} {i.bytes.hex():12} {i.mnemonic} {i.op_str}' for i in insns.values()),encoding='utf-8')
    (out/'task-code-report.json').write_text(json.dumps(r,indent=2),encoding='utf-8');return r


if __name__=='__main__':print(json.dumps(audit(sys.argv[1]),indent=2))
