"""Local CFG/ABI/gate/IRQ-mask audit, without claiming real USB cancellation."""
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from capstone import Cs,CS_ARCH_ARM,CS_MODE_THUMB,CS_MODE_MCLASS
from capstone.arm_const import ARM_REG_SP
from audit_midi_recovery_prototype import conditional_branch
from inspect_ui import load_image
from thumb_asm import b_w
import midi_usb_session_prototype as session
import midi_usb_lifecycle_prototype as life
import midi_usb_ledger_prototype as ledger
import midi_recovery_prototype as recovery
import midi_sysex_retry_prototype as retry
import seq_Patch as seq


def audit(out):
    out=Path(out); out.mkdir(parents=True,exist_ok=True)
    code,labels=session.arm_code(); stock=load_image()
    lc,lp=life.arm_code(); rc,_=recovery.arm_code(); _,sp=seq.arm_code()
    md=Cs(CS_ARCH_ARM,CS_MODE_THUMB|CS_MODE_MCLASS); md.detail=True
    insns={i.address:i for i in md.disasm(code,session.CODE_BASE)}
    assert sum(i.size for i in insns.values())==len(code)
    tails={}; starts=set(); overlays=[]
    for address,(kind,registered,original) in session.gates().items():
        if address>=life.CODE_BASE:
            actual=lc[address-life.CODE_BASE:address-life.CODE_BASE+len(original)]
            scope='generated lifecycle entry'
        elif address>=recovery.CODE_BASE:
            actual=rc[address-recovery.CODE_BASE:address-recovery.CODE_BASE+len(original)]
            scope='generated recovery entry'
        else:
            actual=stock[address-0x08010000:address-0x08010000+len(original)]
            scope='stock entry, possibly replaces asserted lifecycle overlay'
        assert actual==original,hex(address)
        assert 0x08010200<=address<address+len(original)<=session.CODE_BASE
        assert sum(i.size for i in md.disasm(original,address))==len(original)
        for old in overlays:
            p=int(old['address'],16); n=len(bytes.fromhex(old['expected']))
            assert address+len(original)<=p or p+n<=address
        replacement=b_w(address,labels[f'ss_gate_{address:08x}'])+b'\x00\xBF'*(len(original)//2-2)
        overlays.append(dict(address=hex(address),expected=original.hex(),replacement=replacement.hex(),scope=scope,kind=kind))
        start=labels[f'ss_native_{address:08x}']; starts.add(start)
        if address==0x080268D0:
            # LDR, relocated CBZ, MOVS, long branch, long branch.
            assert insns[start].mnemonic=='ldr' and insns[start+2].mnemonic=='cbz'
            tails[start+6]=address+6; tails[start+10]=0x080268DE
        else:
            assert code[start-session.CODE_BASE:start-session.CODE_BASE+len(original)]==original
            tails[start+len(original)]=address+len(original)
    external={lp['cl_binding'],sp['c_midi_inputs_idle'],0x0802A37E,0x080269AC}
    def cond(i): return conditional_branch(i.mnemonic) or i.mnemonic in ('cbz','cbnz')
    for i in insns.values():
        if i.mnemonic in ('bl','b','b.w') or cond(i):
            target=i.operands[-1].imm
            assert target in insns or i.mnemonic=='bl' and target in external or tails.get(i.address)==target,(hex(i.address),hex(target))
        assert i.mnemonic!='blx'
    functions={}
    for name,start in labels.items():
        if not name.startswith('ss_') or name.startswith('ss_native_') or name.endswith('_after_native'): continue
        todo,seen,exits,maximum=[(start,0)],set(),set(),0
        while todo:
            pc,depth=todo.pop()
            if (pc,depth) in seen: continue
            seen.add((pc,depth)); assert len(seen)<6000
            i=insns[pc]
            if i.mnemonic.startswith('push'): depth-=4*len(i.operands)
            if i.mnemonic.startswith('pop'): depth+=4*len(i.operands)
            if i.mnemonic in ('add','sub') and i.operands[0].reg==ARM_REG_SP:
                depth+=i.operands[-1].imm*(1 if i.mnemonic=='add' else -1)
            maximum=max(maximum,-depth)
            if i.mnemonic=='bl': assert depth%8==0,(name,hex(pc),depth)
            if i.mnemonic=='bx' or i.mnemonic.startswith('pop') and 'pc' in i.op_str:
                exits.add(depth); continue
            if i.mnemonic in ('b','b.w'):
                target=i.operands[-1].imm
                if target in starts: exits.add(depth); continue
                todo.append((target,depth)); continue
            if cond(i): todo.append((i.operands[-1].imm,depth))
            todo.append((pc+i.size,depth))
        assert exits=={0},(name,exits)
        functions[name]=dict(max_local_stack_bytes=maximum,exit_sp_deltas=sorted(exits))
    masks=[]
    for i in insns.values():
        if i.mnemonic!='cpsid': continue
        todo=[(i.address+i.size,frozenset())]; paths=[]
        while todo:
            pc,path=todo.pop(); assert pc not in path
            path=path|{pc}; j=insns[pc]
            assert j.mnemonic not in ('bl','blx','bx','pop','pop.w')
            if j.mnemonic=='msr' and j.op_str.startswith('primask,'):
                paths.append(len(path)); continue
            if j.mnemonic in ('b','b.w'): todo.append((j.operands[-1].imm,path)); continue
            if cond(j): todo.append((j.operands[-1].imm,path))
            todo.append((pc+j.size,path))
        masks.append(max(paths))
    report=dict(scope='LOCAL_CODE_PASS; MMIO semantics and tagged IRQ bridge remain assumptions',
        production_integrated=False,code_bytes=len(code),code_sha256=hashlib.sha256(code).hexdigest(),
        additional_synthetic_ram_bytes=session.STATE_SIZE,
        combined_synthetic_ram_bytes=session.STATE_SIZE+life.STATE_SIZE+ledger.STATE_SIZE+retry.REQUEST_STATE_SIZE+recovery.STATE_SIZE,
        max_forced_mask_instructions=max(masks),masked_calls_or_loops=False,
        functions=functions,emulator_overlays=overlays,
        limits='Only software-quiescent cancellation; stock callbacks have no immutable job token. No full IRQ/DMA/RTOS/cache or physical timing proof.')
    (out/'session-code.txt').write_text('\n'.join(f'{i.address:08x} {i.bytes.hex():12} {i.mnemonic} {i.op_str}' for i in insns.values()),encoding='utf-8')
    (out/'session-code-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


if __name__=='__main__': print(json.dumps(audit(sys.argv[1] if len(sys.argv)>1 else ROOT/'logs/usb-session-audit'),indent=2))
