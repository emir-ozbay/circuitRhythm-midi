"""Audit generated detours, inherited frame tails and bounded atomic commits."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from capstone import Cs,CS_ARCH_ARM,CS_MODE_THUMB,CS_MODE_MCLASS
from capstone.arm_const import ARM_REG_SP
from audit_midi_recovery_prototype import conditional_branch
from audit_midi_usb_task_prototype import audit as task_audit
from thumb_asm import b_w,bl
import midi_usb_carry_prototype as carry
import midi_usb_task_prototype as task
import midi_usb_session_prototype as session
import midi_usb_lifecycle_prototype as life
import midi_recovery_prototype as recovery
import seq_Patch as seq


def audit(out,staging=False):
    out=Path(out);out.mkdir(parents=True,exist_ok=True);inherited=task_audit(out/'task')
    code,labels=carry.arm_code(staging=staging);_,ss=session.arm_code();_,lc=life.arm_code();_,rp=recovery.arm_code();_,sq=seq.arm_code();_,ut=task.arm_code()
    hooks=carry.sites(staging=staging);seal=next(p for p,(_,n) in hooks.items() if n=='cy_seal')
    resume=next(p for p,(_,n) in hooks.items() if n=='cy_resume')
    md=Cs(CS_ARCH_ARM,CS_MODE_THUMB|CS_MODE_MCLASS);md.detail=True
    insns={i.address:i for i in md.disasm(code,carry.CODE_BASE)}
    assert sum(i.size for i in insns.values())==len(code)
    assert 0x0806A570<=carry.CODE_BASE<carry.CODE_BASE+len(code)<=0x08080000 and carry.CODE_BASE%4==0
    gates=[]
    for p,(expected,name) in hooks.items():
        assert sum(i.size for i in md.disasm(expected,p))==len(expected)
        assert 0x08010200<=p<p+len(expected)<=0x08080000
        for o in gates:
            q=int(o['address'],16);n=len(bytes.fromhex(o['expected_generated']));assert p+len(expected)<=q or q+n<=p
        gates.append(dict(address=hex(p),expected_generated=expected.hex(),replacement=(b_w(p,labels[name])+b'\x00\xbf'*(len(expected)//2-2)).hex()))
    p=task.MAIN_CALL;gates.append(dict(address=hex(p),expected_generated=bl(p,ut['ut_main']).hex(),replacement=bl(p,labels['cy_task']).hex()))
    # Copied prefixes end in checked original continuations. Their native
    # bodies consume the specified original frames; detours preserve that ABI.
    tails={labels['cy_original_quiet']+6:(ss['ss_quiet']+6,-16),
           labels['cy_original_step']+6:(ss['ss_step']+6,-24),
           labels['cy_original_poll']+6:(rp['rp_poll']+6,-40),
           labels['cy_original_resume']+6:(resume+6,-16),
           labels['cy_original_seal']+10:(seal+10,0)}
    if staging:
        tails[labels['cy_original_flush']+4]=(0x0802B49C,-16)
        p=labels['cy_original_flush']-carry.CODE_BASE;assert code[p:p+4]==hooks[0x0802B498][0]
    for name,target in (('cy_original_quiet',ss['ss_quiet']),('cy_original_step',ss['ss_step']),('cy_original_poll',rp['rp_poll']),('cy_original_resume',resume)):
        p=labels[name]-carry.CODE_BASE;assert code[p:p+6]==hooks[target][0]
    external={ss['ss_binding'],sq['c_midi_inputs_idle'],0x0802A37E,ss['ss_native_080401ac'],ut['ut_main']}
    if staging:external.add(0x08026880)
    exits={ss['step_ok'],ss['step_wait']}
    for i in insns.values():
        assert i.mnemonic!='blx'
        if i.mnemonic in ('b','b.w','bl') or conditional_branch(i.mnemonic):
            t=i.operands[-1].imm
            assert t in insns or i.mnemonic=='bl' and t in external or t in exits or tails.get(i.address,(None,))[0]==t,(hex(i.address),hex(t))
    functions={}
    for name in ('cy_stable','cy_quiet','cy_step','cy_poll','cy_seal','cy_resume','cy_task')+(('cy_staging','cy_flush') if staging else ()):
        todo,seen,ends,maximum=[(labels[name],0)],set(),set(),0
        while todo:
            pc,depth=todo.pop()
            if (pc,depth) in seen:continue
            seen.add((pc,depth));assert len(seen)<9000;i=insns[pc]
            if i.mnemonic.startswith('push'):depth-=4*len(i.operands)
            if i.mnemonic.startswith('pop'):depth+=4*len(i.operands)
            if i.mnemonic in ('add','sub') and i.operands[0].reg==ARM_REG_SP:
                depth+=(1 if i.mnemonic=='add' else -1)*i.operands[-1].imm
            maximum=max(maximum,-depth)
            if i.mnemonic=='bl':assert depth%8==0,(name,hex(pc),depth)
            if i.mnemonic=='bx' or i.mnemonic.startswith('pop') and 'pc' in i.op_str:ends.add(depth);continue
            if i.mnemonic in ('b','b.w'):
                t=i.operands[-1].imm
                if i.address in tails:
                    assert (t,depth)==tails[i.address],(name,hex(pc),depth);ends.add(0);continue
                if t in exits:assert depth==0;ends.add(0);continue
                todo.append((t,depth));continue
            if conditional_branch(i.mnemonic):todo.append((i.operands[-1].imm,depth))
            todo.append((pc+i.size,depth))
        assert ends=={0},(name,ends)
        functions[name]=dict(max_frame_including_original_prefix=maximum,exit_sp_deltas=sorted(ends))
    masks=[]
    for i in insns.values():
        if i.mnemonic!='cpsid':continue
        todo=[(i.address+i.size,frozenset())];paths=[]
        while todo:
            pc,path=todo.pop();assert pc not in path;path=path|{pc};j=insns[pc]
            assert j.mnemonic not in ('bl','blx','bx','pop','pop.w')
            if j.mnemonic=='msr' and j.op_str.startswith('primask,'):paths.append(len(path));continue
            if j.mnemonic in ('b','b.w'):todo.append((j.operands[-1].imm,path));continue
            if conditional_branch(j.mnemonic):todo.append((j.operands[-1].imm,path))
            todo.append((pc+j.size,path))
        masks.append(max(paths))
    r=dict(scope='LOCAL_CODE_PASS; unsubmitted logical MIDI debt carry, not ambiguous in-flight replay',production_integrated=False,
        code_bytes=len(code),code_sha256=hashlib.sha256(code).hexdigest(),additional_synthetic_ram_bytes=carry.STATE_SIZE,
        combined_synthetic_ram_bytes=inherited['combined_synthetic_ram_bytes']+carry.STATE_SIZE,functions=functions,
        new_frame_max_bytes=32,inherited_seal_frame_bytes=24,forced_mask_sections=len(masks),
        max_forced_mask_instructions=max(masks),masked_calls_or_loops=False,emulator_overlays=gates,inherited_task=inherited,
        limits='Only no in-flight TX/no staged bytes/no partial cursor, idle parser/no held musical input/no genuine USB port fault. Software debt/SCANNED/FIFO/cursors are retained; physical barrier remains. Local frames, not full stack/cycle/IRQ or production RAM/init proof. Old in-flight cancellation and physical/RTOS/PHY/DIN boundaries remain.')
    if staging:
        r.update(scope='LOCAL_CODE_PASS; native unsubmitted MAIN staging and owned partial SysEx cursor carry',staging_variant=True,
            limits='MAIN0..64 bytes/multiple4, native64B CPU mode/ALT idle, no TX_ACTIVE and no producer/flush owner. Partial cursor must belong to the immutable accepted retry slot. Registered flush consumes MAIN only after TX ticket changes. Already-submitted ambiguity/raw ALT mode/partial parser/held input/fault, hardware timing and production integration remain outside scope.')
    (out/'carry-code.txt').write_text('\n'.join(f'{i.address:08x} {i.bytes.hex():12} {i.mnemonic} {i.op_str}' for i in insns.values()),encoding='utf-8')
    (out/'carry-code-report.json').write_text(json.dumps(r,indent=2),encoding='utf-8');return r


if __name__=='__main__':print(json.dumps(audit(sys.argv[1]),indent=2))
