"""Local ABI/CFG/masked-section audit, including inherited factory evidence."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from capstone import Cs,CS_ARCH_ARM,CS_MODE_THUMB,CS_MODE_MCLASS
from audit_midi_recovery_prototype import conditional_branch
from audit_midi_usb_factory_prototype import audit as factory_audit
from inspect_ui import load_image
from thumb_asm import b_w
import midi_usb_power_prototype as power
import midi_usb_factory_prototype as factory
import midi_usb_control_prototype as control
import midi_usb_irq_prototype as irq


def audit(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    inherited=factory_audit(out/'factory');stock=load_image()
    code,labels=power.arm_code();_,fx=factory.arm_code();(_,mc),(_,sd)=factory.variants();_,cc=control.arm_code()
    md=Cs(CS_ARCH_ARM,CS_MODE_THUMB|CS_MODE_MCLASS);md.detail=True
    insns={i.address:i for i in md.disasm(code,power.CODE_BASE)}
    assert sum(i.size for i in insns.values())==len(code)
    assert 0x0806A570<=power.CODE_BASE<power.CODE_BASE+len(code)<=0x08080000 and power.CODE_BASE%4==0
    old,ol=control.irq_variant();variant,nl=power.irq_variant()
    assert ol==nl and len(old)==len(variant)
    oi=list(md.disasm(old,irq.CODE_BASE));ni=list(md.disasm(variant,irq.CODE_BASE))
    differences=[]
    for i,j in zip(oi,ni):
        assert (i.address,i.size,i.mnemonic)==(j.address,j.size,j.mnemonic)
        if i.bytes!=j.bytes:
            assert i.mnemonic in ('movw','movt')
            differences.append(dict(address=hex(i.address),before=i.bytes.hex(),after=j.bytes.hex()))
    assert differences
    gates=[]
    for address,label in ((irq.NATIVE_IRQ,'pw_irq'),(0x0802C7E6,'pw_suspend'),(0x0802C802,'pw_wakeup'),(cc['cc_service'],'pw_service')):
        expected=(b_w(address,fx['fx_service'])+b'\x00\xbf') if address==cc['cc_service'] else power.GATES[address]
        if address!=cc['cc_service']:assert stock[address-0x08010000:address-0x08010000+len(expected)]==expected
        assert 0x08010200<=address<address+len(expected)<=0x08080000
        for o in gates:
            p=int(o['address'],16);n=len(bytes.fromhex(o['expected']));assert address+len(expected)<=p or p+n<=address
        gates.append(dict(address=hex(address),expected=expected.hex(),replacement=(b_w(address,labels[label])+b'\x00\xbf'*(len(expected)//2-2)).hex()))
    external={cc['cc_request'],sd['sd_irq'],fx['fx_service'],fx['fx_config_ready'],mc['mc_init_list'],0x0802C9F8,0x0804279E,0x080427AE}
    external_tails={sd['sd_irq']};native={labels['pw_suspend_native'],labels['pw_wakeup_native']}
    tails={labels['pw_suspend_native']+4:0x0802C7EA,labels['pw_wakeup_native']+4:0x0802C806}
    for i in insns.values():
        assert i.mnemonic!='blx'
        if i.mnemonic in ('b','b.w','bl') or conditional_branch(i.mnemonic):
            t=i.operands[-1].imm
            assert t in insns or i.mnemonic=='bl' and t in external or t in external_tails or tails.get(i.address)==t,(hex(i.address),hex(t))
    functions={}
    for name in ('pw_request','pw_wake_event','pw_irq','pw_suspend','pw_wakeup','pw_service','pw_binding'):
        todo,seen,exits,maximum=[(labels[name],0)],set(),set(),0
        while todo:
            pc,depth=todo.pop()
            if pc in native:exits.add(depth);continue
            if (pc,depth) in seen:continue
            seen.add((pc,depth));assert len(seen)<7000
            i=insns[pc]
            if i.mnemonic.startswith('push'):depth-=4*len(i.operands)
            if i.mnemonic.startswith('pop'):depth+=4*len(i.operands)
            maximum=max(maximum,-depth)
            if i.mnemonic=='bl':assert depth%8==0,(name,hex(pc),depth)
            if i.mnemonic=='bx' or i.mnemonic.startswith('pop') and 'pc' in i.op_str:exits.add(depth);continue
            if i.mnemonic in ('b','b.w'):
                t=i.operands[-1].imm
                if t in native|external_tails:exits.add(depth);continue
                todo.append((t,depth));continue
            if conditional_branch(i.mnemonic):todo.append((i.operands[-1].imm,depth))
            todo.append((pc+i.size,depth))
        assert exits=={0},(name,exits)
        functions[name]=dict(max_local_stack_bytes=maximum,exit_sp_deltas=sorted(exits))
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
    r=dict(scope='LOCAL_CODE_PASS; normal USB suspend/wakeup over synthetic MMIO',production_integrated=False,
        code_bytes=len(code),code_sha256=hashlib.sha256(code).hexdigest(),irq_variant_sha256=hashlib.sha256(variant).hexdigest(),
        additional_synthetic_ram_bytes=power.STATE_SIZE,combined_synthetic_ram_bytes=inherited['combined_synthetic_ram_bytes']+power.STATE_SIZE,
        functions=functions,forced_mask_sections=len(masks),max_forced_mask_instructions=max(masks),masked_calls_or_loops=False,
        emulator_overlays=gates,irq_policy_changes=differences,inherited_factory=inherited,
        limits='Local frames/instruction counts, not full native stack/cycles. Only CPU-FIFO, handle+20hex=0 and normal11/31 suspend/wakeup; LPM/deep stop/DMA unsupported. Native save/restore/ungate execute, clock availability/ACK/NVIC/timing remain modeled; periodic task wiring and production RAM/init unproven.')
    (out/'power-code.txt').write_text('\n'.join(f'{i.address:08x} {i.bytes.hex():12} {i.mnemonic} {i.op_str}' for i in insns.values()),encoding='utf-8')
    (out/'power-code-report.json').write_text(json.dumps(r,indent=2),encoding='utf-8');return r


if __name__=='__main__':print(json.dumps(audit(sys.argv[1]),indent=2))
