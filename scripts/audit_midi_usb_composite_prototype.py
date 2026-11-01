"""Local composite gate/CFG/ABI proof; not timing, storage or silicon proof."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'src')]
from capstone import Cs,CS_ARCH_ARM,CS_MODE_THUMB,CS_MODE_MCLASS
from audit_midi_recovery_prototype import conditional_branch
from audit_midi_usb_control_prototype import audit as audit_control
from inspect_ui import load_image
from thumb_asm import b_w
import midi_usb_composite_prototype as composite
import midi_usb_control_prototype as control


def audit(out):
    out=Path(out); out.mkdir(parents=True,exist_ok=True)
    code,labels=composite.arm_code(); cc_code,cc=control.arm_code(); stock=load_image()
    inherited=audit_control(out/'control'); md=Cs(CS_ARCH_ARM,CS_MODE_THUMB|CS_MODE_MCLASS); md.detail=True
    insns={i.address:i for i in md.disasm(code,composite.CODE_BASE)}
    assert sum(i.size for i in insns.values())==len(code)
    overlays=[]
    targets={0x08040B5A:'xc_init_list',0x080525B2:'xc_init_class',0x080297C0:'xc_clear_router',0x0802C928:'xc_flush'}
    for address,original in composite.GATES.items():
        assert stock[address-0x08010000:address-0x08010000+len(original)]==original
        assert 0x08010200<=address<address+len(original)<=0x08080000
        assert sum(i.size for i in md.disasm(original,address))==len(original)
        for other in overlays:
            p=int(other['address'],16); n=len(bytes.fromhex(other['expected_stock']))
            assert address+len(original)<=p or p+n<=address
        patch=b_w(address,labels[targets[address]])+b'\x00\xBF'*(len(original)//2-2)
        overlays.append(dict(address=hex(address),expected_stock=original.hex(),replacement=patch.hex()))
    p=cc['cc_native_init']; expected=control.GATES[0x080525B2]
    assert cc_code[p-control.CODE_BASE:p-control.CODE_BASE+4]==expected
    overlays.append(dict(address=hex(p),expected_generated=expected.hex(),replacement=b_w(p,labels['xc_deferred_list']).hex()))
    external_tails={cc['cc_init'],cc['cc_flush']}; tails={}; native_starts=set()
    for name,address in (('xc_native_list',0x08040B5A),('xc_native_ctor',0x080525B2),('xc_native_clear',0x080297C0)):
        p=labels[name]; n=len(composite.GATES[address]); native_starts.add(p)
        assert code[p-composite.CODE_BASE:p-composite.CODE_BASE+n]==composite.GATES[address]
        tails[p+n]=address+n
    calls={cc['cc_init']}
    for i in insns.values():
        assert i.mnemonic not in ('blx','cpsid')
        if i.mnemonic in ('b','b.w','bl') or conditional_branch(i.mnemonic):
            target=i.operands[-1].imm
            assert (target in insns or target in external_tails or i.mnemonic=='bl' and target in calls
                    or tails.get(i.address)==target),(hex(i.address),hex(target))
    functions={}
    for name in set(targets.values())|{'xc_deferred_list','xc_msc_quiet'}:
        todo,seen,exits,maximum=[(labels[name],0)],set(),set(),0
        while todo:
            pc,depth=todo.pop()
            if pc in native_starts: exits.add(depth); continue
            if (pc,depth) in seen: continue
            seen.add((pc,depth)); assert len(seen)<4000
            i=insns[pc]
            if i.mnemonic.startswith('push'): depth-=4*len(i.operands)
            if i.mnemonic.startswith('pop'): depth+=4*len(i.operands)
            maximum=max(maximum,-depth)
            if i.mnemonic=='bl': assert depth%8==0,(name,hex(pc),depth)
            if i.mnemonic=='bx' or i.mnemonic.startswith('pop') and 'pc' in i.op_str:
                exits.add(depth); continue
            if i.mnemonic in ('b','b.w'):
                target=i.operands[-1].imm
                if target in native_starts|external_tails: exits.add(depth); continue
                todo.append((target,depth)); continue
            if conditional_branch(i.mnemonic): todo.append((i.operands[-1].imm,depth))
            todo.append((pc+i.size,depth))
        assert exits=={0},(name,exits)
        functions[name]=dict(local_stack_bytes=maximum,exit_sp_deltas=sorted(exits))
    report=dict(scope='LOCAL_CODE_PASS; bounded quiescent composite configuration subset',production_integrated=False,
        code_bytes=len(code),code_sha256=hashlib.sha256(code).hexdigest(),additional_synthetic_ram_bytes=composite.STATE_SIZE,
        combined_synthetic_ram_bytes=inherited['combined_synthetic_ram_bytes']+composite.STATE_SIZE,
        forced_mask_sections_added=0,functions=functions,emulator_overlays=overlays,inherited_control=inherited,
        limits='Local frames/branch targets only. Main service is manually pumped. Active MSC cancellation, storage I/O, full boot/RAM/init/OOM, hardware disable/NVIC/cache/timing and production integration are unproven.')
    (out/'composite-code.txt').write_text('\n'.join(f'{i.address:08x} {i.bytes.hex():12} {i.mnemonic} {i.op_str}' for i in insns.values()),encoding='utf-8')
    (out/'composite-code-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


if __name__=='__main__': print(json.dumps(audit(sys.argv[1]),indent=2))
