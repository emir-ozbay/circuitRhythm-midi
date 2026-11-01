"""Local storage layer and hooked MSC variant CFG/ABI/mask/gate audit."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from capstone import Cs,CS_ARCH_ARM,CS_MODE_THUMB,CS_MODE_MCLASS
from audit_midi_recovery_prototype import conditional_branch
from audit_midi_usb_msc_prototype import audit as msc_audit
from inspect_ui import load_image
from thumb_asm import b_w
import midi_usb_storage_prototype as storage
import midi_usb_msc_prototype as msc
import midi_usb_control_prototype as control
import midi_usb_session_prototype as session


def audit(out,msc_options=None):
    out=Path(out); out.mkdir(parents=True,exist_ok=True)
    options=msc_options or {}
    code,labels=storage.arm_code(msc_options=options); variant,mc=storage.msc_variant(**options); stock=load_image()
    _,cc=control.arm_code(); _,ss=session.arm_code()
    hooks=(options['class_policy'],options['config_ready']) if options else None
    inherited=msc_audit(out/'msc-variant',(storage.CODE_BASE,storage.CODE_BASE+4),hooks)
    md=Cs(CS_ARCH_ARM,CS_MODE_THUMB|CS_MODE_MCLASS); md.detail=True
    insns={i.address:i for i in md.disasm(code,storage.CODE_BASE)}
    assert sum(i.size for i in insns.values())==len(code)
    assert labels['sd_policy']==storage.CODE_BASE and labels['sd_finalize']==storage.CODE_BASE+4
    assert msc.CODE_BASE+len(variant)<=storage.CODE_BASE and storage.CODE_BASE+len(code)<=0x08080000
    targets={0x080458D0:'sd_scsi',0x08065128:'sd_read',0x0802C9B8:'sd_tx_submit',
             0x080268D0:'sd_tx_callback',0x0804293E:'sd_irq',0x0802C328:'sd_worker_result'}
    overlays=[]
    for p,original in storage.GATES.items():
        assert stock[p-0x08010000:p-0x08010000+len(original)]==original
        assert 0x08010200<=p<p+len(original)<=0x08080000
        overlays.append(dict(address=hex(p),expected_stock=original.hex(),replacement=(b_w(p,labels[targets[p]])+b'\x00\xbf'*(len(original)//2-2)).hex()))
    p=mc['mc_poll']; expected=variant[p-msc.CODE_BASE:p-msc.CODE_BASE+6]
    overlays.append(dict(address=hex(p),expected_generated=expected.hex(),replacement=(b_w(p,labels['sd_poll'])+b'\x00\xbf').hex()))
    for i,o in enumerate(overlays):
        p=int(o['address'],16); n=len(bytes.fromhex(o['replacement']))
        for q in overlays[:i]:
            x=int(q['address'],16); k=len(bytes.fromhex(q['replacement'])); assert p+n<=x or x+k<=p
    tails={}; native=set()
    for name,p in (('sd_native_scsi',0x080458D0),('sd_native_read',0x08065128),('sd_native_tx',0x0802C9B8)):
        a=labels[name]; n=len(storage.GATES[p]); native.add(a)
        assert code[a-storage.CODE_BASE:a-storage.CODE_BASE+n]==storage.GATES[p]; tails[a+n]=p+n
    p=labels['sd_native_poll']; native.add(p)
    assert code[p-storage.CODE_BASE:p-storage.CODE_BASE+6]==expected; tails[p+6]=mc['mc_poll']+6
    p=labels['sd_native_worker_result']; native.add(p)
    assert insns[p].mnemonic=='strb'; tails[p+2]=0x0802C334
    external_calls={mc['mc_irq'],ss['ss_native_080268d0']}
    external_tails={mc['mc_irq'],cc['cc_tx_callback']}
    for i in insns.values():
        assert i.mnemonic!='blx'
        if i.mnemonic in ('b','b.w','bl') or conditional_branch(i.mnemonic):
            t=i.operands[-1].imm
            assert t in insns or t in external_tails or i.mnemonic=='bl' and t in external_calls or tails.get(i.address)==t,(hex(i.address),hex(t))
    funcs={}
    for name in set(targets.values())|{'sd_policy','sd_finalize','sd_quiet','sd_poll'}:
        todo,seen,exits,maximum=[(labels[name],0)],set(),set(),0
        while todo:
            pc,depth=todo.pop()
            if pc in native: exits.add(depth); continue
            if (pc,depth) in seen: continue
            seen.add((pc,depth)); assert len(seen)<6000
            i=insns[pc]
            if i.mnemonic.startswith('push'): depth-=4*len(i.operands)
            if i.mnemonic.startswith('pop'): depth+=4*len(i.operands)
            maximum=max(maximum,-depth)
            if i.mnemonic=='bl': assert depth%8==0,(name,hex(pc),depth)
            if i.mnemonic=='bx' or i.mnemonic.startswith('pop') and 'pc' in i.op_str: exits.add(depth); continue
            if i.mnemonic in ('b','b.w'):
                t=i.operands[-1].imm
                if t in native|external_tails: exits.add(depth); continue
                todo.append((t,depth)); continue
            if conditional_branch(i.mnemonic): todo.append((i.operands[-1].imm,depth))
            todo.append((pc+i.size,depth))
        assert exits=={0},(name,exits)
        funcs[name]=dict(max_local_stack_bytes=maximum,exit_sp_deltas=sorted(exits))
    masks=[]
    for i in insns.values():
        if i.mnemonic!='cpsid': continue
        todo=[(i.address+i.size,frozenset())]; paths=[]
        while todo:
            pc,path=todo.pop(); assert pc not in path; path=path|{pc}; j=insns[pc]
            assert j.mnemonic not in ('bl','blx','bx','pop','pop.w')
            if j.mnemonic=='msr' and j.op_str.startswith('primask,'): paths.append(len(path)); continue
            if j.mnemonic in ('b','b.w'): todo.append((j.operands[-1].imm,path)); continue
            if conditional_branch(j.mnemonic): todo.append((j.operands[-1].imm,path))
            todo.append((pc+j.size,path))
        masks.append(max(paths))
    report=dict(scope='LOCAL_CODE_PASS; readonly MSC storage policy over native queue/worker/USB and synthetic boundaries',
        production_integrated=False,code_bytes=len(code),code_sha256=hashlib.sha256(code).hexdigest(),
        msc_variant_bytes=len(variant),msc_variant_sha256=hashlib.sha256(variant).hexdigest(),
        additional_synthetic_ram_bytes=storage.STATE_SIZE,combined_synthetic_ram_bytes=inherited['combined_synthetic_ram_bytes']+storage.STATE_SIZE,
        functions=funcs,max_forced_mask_instructions=max(masks),forced_mask_sections=len(masks),masked_calls_or_loops=False,
        emulator_overlays=overlays,inherited_msc_variant=inherited,
        limits='Local frames only; lower flash is RAM, wake/yield are RTOS boundaries. Only pinned readonly table and READ10/CSW/CBW cancellation proved. Real flash/SPI/RTOS/NVIC/cache/cycle/full boot/RAM/init and complete class/power graphs remain open.')
    (out/'storage-code.txt').write_text('\n'.join(f'{i.address:08x} {i.bytes.hex():12} {i.mnemonic} {i.op_str}' for i in insns.values()),encoding='utf-8')
    (out/'storage-code-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


if __name__=='__main__': print(json.dumps(audit(sys.argv[1]),indent=2))
