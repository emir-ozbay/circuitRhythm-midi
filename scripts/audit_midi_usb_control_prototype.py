"""Local deferred-control CFG/ABI/mask/gate audit; no silicon proof."""
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from capstone import Cs,CS_ARCH_ARM,CS_MODE_THUMB,CS_MODE_MCLASS
from capstone.arm_const import ARM_REG_SP
from audit_midi_recovery_prototype import conditional_branch
from audit_midi_usb_irq_prototype import audit as audit_default_irq
from inspect_ui import load_image
from thumb_asm import b_w
import midi_usb_control_prototype as control
import midi_usb_irq_prototype as irq
import midi_usb_session_prototype as session


def audit(out):
    out=Path(out); out.mkdir(parents=True,exist_ok=True)
    code,labels=control.arm_code(); stock=load_image(); _,ss=session.arm_code()
    default,ib=irq.arm_code(); variant,variant_labels=control.irq_variant()
    assert ib==variant_labels and len(default)==len(variant)
    md=Cs(CS_ARCH_ARM,CS_MODE_THUMB|CS_MODE_MCLASS); md.detail=True
    old=list(md.disasm(default,irq.CODE_BASE)); new=list(md.disasm(variant,irq.CODE_BASE))
    changes=[]
    for before,after in zip(old,new):
        assert before.address==after.address and before.size==after.size
        if before.bytes!=after.bytes:
            assert before.mnemonic==after.mnemonic and before.mnemonic in ('movw','cmp')
            assert before.operands[0].reg==after.operands[0].reg
            changes.append(dict(address=hex(before.address),before=before.op_str,after=after.op_str))
    assert len(changes)==2
    inherited=audit_default_irq(out/'default-irq')
    insns={i.address:i for i in md.disasm(code,control.CODE_BASE)}
    assert sum(i.size for i in insns.values())==len(code)
    targets={irq.NATIVE_IRQ:'cc_irq',0x080525B2:'cc_init',0x0805261C:'cc_deinit',0x080268D0:'cc_tx_callback',
             0x0802C928:'cc_flush',0x080268EC:'cc_rx_poll',0x0802C9D4:'cc_rx_submit',0x080269AC:'cc_rx_rearm'}
    overlays=[]
    for address,original in control.GATES.items():
        assert stock[address-0x08010000:address-0x08010000+len(original)]==original
        assert 0x08010200<=address<address+len(original)<=0x08080000
        assert sum(i.size for i in md.disasm(original,address))==len(original)
        for other in overlays:
            p=int(other['address'],16); n=len(bytes.fromhex(other['expected']))
            assert address+len(original)<=p or p+n<=address
        patch=b_w(address,labels[targets[address]])+b'\x00\xBF'*(len(original)//2-2)
        overlays.append(dict(address=hex(address),expected=original.hex(),replacement=patch.hex()))
    tails={}; starts=set()
    for name,address in (('cc_native_init',0x080525B2),('cc_native_flush',0x0802C928),('cc_native_rx_poll',0x080268EC)):
        p=labels[name]; starts.add(p); original=control.GATES[address]
        assert code[p-control.CODE_BASE:p-control.CODE_BASE+len(original)]==original
        tails[p+len(original)]=address+len(original)
    calls={ss[x] for x in ('ss_step','ss_binding','ss_quiet','ss_resume')}|{ib['ib_irq'],0x0802A39E}
    external_tails={ib[x] for x in ('ib_irq','ib_native_disconnect','ib_tx_callback')}|{
        ss[x] for x in ('ss_native_080268d0','ss_gate_0802c9d4','ss_gate_080269ac')}
    for i in insns.values():
        if i.mnemonic in ('b','b.w','bl') or conditional_branch(i.mnemonic):
            target=i.operands[-1].imm
            assert target in insns or i.mnemonic=='bl' and target in calls or target in external_tails or tails.get(i.address)==target,(hex(i.address),hex(target))
        assert i.mnemonic!='blx'
    functions={}
    for name in sorted(set(targets.values())|{'cc_request','cc_service'}):
        todo,seen,exits,maximum=[(labels[name],0)],set(),set(),0
        while todo:
            pc,depth=todo.pop()
            if pc in starts: exits.add(depth); continue
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
                if target in starts|external_tails: exits.add(depth); continue
                todo.append((target,depth)); continue
            if conditional_branch(i.mnemonic): todo.append((i.operands[-1].imm,depth))
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
            if j.mnemonic=='msr' and j.op_str.startswith('primask,'): paths.append(len(path)); continue
            if j.mnemonic in ('b','b.w'): todo.append((j.operands[-1].imm,path)); continue
            if conditional_branch(j.mnemonic): todo.append((j.operands[-1].imm,path))
            todo.append((pc+j.size,path))
        masks.append(max(paths))
    report=dict(scope='LOCAL_CODE_PASS; deferred native MIDI class control subset over synthetic MMIO',
        production_integrated=False,code_bytes=len(code),code_sha256=hashlib.sha256(code).hexdigest(),
        irq_variant_sha256=hashlib.sha256(variant).hexdigest(),irq_variant_policy_changes=changes,
        additional_synthetic_ram_bytes=control.STATE_SIZE,
        combined_synthetic_ram_bytes=inherited['combined_synthetic_ram_bytes']+control.STATE_SIZE,
        functions=functions,max_forced_mask_instructions=max(masks),masked_calls_or_loops=False,
        emulator_overlays=overlays,default_irq_audit=inherited,
        limits='Local frames only. Parent notification is a pinned native no-op boundary; power states/descriptors/MSC/full RTOS/NVIC/cache/cycle and physical cancellation are unproven.')
    (out/'control-code.txt').write_text('\n'.join(f'{i.address:08x} {i.bytes.hex():12} {i.mnemonic} {i.op_str}' for i in insns.values()),encoding='utf-8')
    (out/'control-code-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


if __name__=='__main__': print(json.dumps(audit(sys.argv[1] if len(sys.argv)>1 else ROOT/'logs/usb-control-audit'),indent=2))
