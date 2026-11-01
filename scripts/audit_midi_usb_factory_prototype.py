"""Factory layer and both dependent variants: local CFG/ABI/mask audit."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from capstone import Cs,CS_ARCH_ARM,CS_MODE_THUMB,CS_MODE_MCLASS
from audit_midi_recovery_prototype import conditional_branch
from audit_midi_usb_storage_prototype import audit as storage_audit
from inspect_ui import load_image
from thumb_asm import b_w
import midi_usb_factory_prototype as factory
import midi_usb_control_prototype as control


def audit(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    code,labels=factory.arm_code();(mc_code,mc),(sd_code,sd)=factory.variants();_,cc=control.arm_code();stock=load_image()
    inherited=storage_audit(out/'storage-variant',dict(class_policy=factory.CODE_BASE,config_ready=factory.CODE_BASE+4))
    md=Cs(CS_ARCH_ARM,CS_MODE_THUMB|CS_MODE_MCLASS);md.detail=True
    insns={i.address:i for i in md.disasm(code,factory.CODE_BASE)}
    assert sum(i.size for i in insns.values())==len(code)
    assert labels['fx_class_policy']==factory.CODE_BASE and labels['fx_config_ready']==factory.CODE_BASE+4
    overlays=[]
    for p,label in ((0x080432A8,'fx_request'),(0x08040B7E,'fx_deinit')):
        original=factory.GATES[p];assert stock[p-0x08010000:p-0x08010000+len(original)]==original
        assert 0x08010200<=p<p+len(original)<=0x08080000
        overlays.append(dict(address=hex(p),expected_stock=original.hex(),replacement=b_w(p,labels[label]).hex()))
    p=cc['cc_service'];original=control.arm_code()[0][p-control.CODE_BASE:p-control.CODE_BASE+6]
    overlays.append(dict(address=hex(p),expected_generated=original.hex(),replacement=(b_w(p,labels['fx_service'])+b'\x00\xbf').hex()))
    for i,o in enumerate(overlays):
        p=int(o['address'],16);n=len(bytes.fromhex(o['replacement']))
        for other in overlays[:i]:
            q=int(other['address'],16);k=len(bytes.fromhex(other['replacement']));assert p+n<=q or q+k<=p
    external_calls={mc['mc_deinit_list'],mc['mc_service']};external_tails={mc['mc_native_deinit'],mc['mc_deinit_list']}
    native={labels['fx_native_factory']};p=labels['fx_native_factory']
    reloc=list(md.disasm(code[p-factory.CODE_BASE:p-factory.CODE_BASE+14],p))
    assert [i.mnemonic for i in reloc]==['push','movw','movt','b.w']
    assert reloc[1].operands[1].imm==0xD0 and reloc[2].operands[1].imm==0x2000
    assert int.from_bytes(stock[0x080432FC-0x08010000:0x080432FC-0x08010000+4],'little')==0x200000D0
    tails={reloc[3].address:0x080432AC}
    for i in insns.values():
        assert i.mnemonic!='blx'
        if i.mnemonic in ('b','b.w','bl') or conditional_branch(i.mnemonic):
            t=i.operands[-1].imm
            assert t in insns or t in external_tails or i.mnemonic=='bl' and t in external_calls or tails.get(i.address)==t,(hex(i.address),hex(t))
    functions={}
    for name in ('fx_class_policy','fx_config_ready','fx_request','fx_deinit','fx_service','fx_binding'):
        todo,seen,exits,maximum=[(labels[name],0)],set(),set(),0
        while todo:
            pc,depth=todo.pop()
            if pc in native:exits.add(depth);continue
            if (pc,depth) in seen:continue
            seen.add((pc,depth));assert len(seen)<6000
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
    r=dict(scope='LOCAL_CODE_PASS; queued native USB factory for MIDI-only or MIDI+MSC list',production_integrated=False,
        code_bytes=len(code),code_sha256=hashlib.sha256(code).hexdigest(),msc_variant_bytes=len(mc_code),
        msc_variant_sha256=hashlib.sha256(mc_code).hexdigest(),storage_variant_bytes=len(sd_code),storage_variant_sha256=hashlib.sha256(sd_code).hexdigest(),
        additional_synthetic_ram_bytes=factory.STATE_SIZE,combined_synthetic_ram_bytes=inherited['combined_synthetic_ram_bytes']+factory.STATE_SIZE,
        functions=functions,forced_mask_sections=len(masks),max_forced_mask_instructions=max(masks),masked_calls_or_loops=False,
        emulator_overlays=overlays,inherited_storage_variant=inherited,
        limits='Local frames only. Native factory/stop/start/descriptors/init prefix execute; HAL init is return0, time/NVIC/clock are synthetic. Full power/IRQ/task/boot/RAM/init/caller graph and hardware timing remain unproven; MSC-only/disabled lists rejected.')
    (out/'factory-code.txt').write_text('\n'.join(f'{i.address:08x} {i.bytes.hex():12} {i.mnemonic} {i.op_str}' for i in insns.values()),encoding='utf-8')
    (out/'factory-code-report.json').write_text(json.dumps(r,indent=2),encoding='utf-8');return r


if __name__=='__main__':print(json.dumps(audit(sys.argv[1]),indent=2))
