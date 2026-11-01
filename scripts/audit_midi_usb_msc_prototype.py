"""Local branch/stack/mask/relocation audit for the CBW-only cancel layer."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from capstone import Cs,CS_ARCH_ARM,CS_MODE_THUMB,CS_MODE_MCLASS
from audit_midi_recovery_prototype import conditional_branch
from audit_midi_usb_composite_prototype import audit as prior_audit
from inspect_ui import load_image
from thumb_asm import b_w
import midi_usb_msc_prototype as msc
import midi_usb_control_prototype as control
import midi_usb_composite_prototype as composite
import midi_usb_irq_prototype as irq
import midi_usb_session_prototype as session


def audit(out,storage_hooks=None,class_hooks=None):
    out=Path(out); out.mkdir(parents=True,exist_ok=True)
    opts={} if storage_hooks is None else dict(storage_policy=storage_hooks[0],storage_finalize=storage_hooks[1])
    if class_hooks is not None:opts.update(class_policy=class_hooks[0],config_ready=class_hooks[1])
    code,labels=msc.arm_code(**opts); _,cc=control.arm_code(); _,xc=composite.arm_code()
    _,ib=irq.arm_code(); _,ss=session.arm_code(); stock=load_image()
    inherited=prior_audit(out/'composite')
    md=Cs(CS_ARCH_ARM,CS_MODE_THUMB|CS_MODE_MCLASS); md.detail=True
    insns={i.address:i for i in md.disasm(code,msc.CODE_BASE)}
    assert sum(i.size for i in insns.values())==len(code)
    targets={0x08040B5A:'mc_init_list',0x08040B7E:'mc_deinit_list',0x0804293E:'mc_irq',
             0x08026988:'mc_rx_callback',0x0802C9D4:'mc_rx_lower',0x0802EFF8:'mc_bot_reset',
             0x08027624:'mc_poll',0x0802F014:'mc_bot_0802f014',0x0802F04A:'mc_bot_0802f04a',0x080531CC:'mc_fifo_read'}
    overlays=[]
    for address,original in msc.GATES.items():
        assert stock[address-0x08010000:address-0x08010000+len(original)]==original
        assert sum(i.size for i in md.disasm(original,address))==len(original)
        assert 0x08010200<=address<address+len(original)<=0x08080000
        patch=b_w(address,labels[targets[address]])+b'\x00\xBF'*(len(original)//2-2)
        overlays.append(dict(address=hex(address),expected_stock=original.hex(),replacement=patch.hex()))
    for address,(expected,label) in msc.generated_gates().items():
        overlays.append(dict(address=hex(address),expected_generated=expected.hex(),
                             replacement=(b_w(address,labels[label])+b'\x00\xBF'*(len(expected)//2-2)).hex()))
    for index,o in enumerate(overlays):
        p=int(o['address'],16); n=len(bytes.fromhex(o['replacement']))
        for other in overlays[:index]:
            q=int(other['address'],16); k=len(bytes.fromhex(other['replacement']))
            assert p+n<=q or q+k<=p
    tails={}; native=set()
    for name,address,expected in (('mc_native_deinit',0x08040B7E,msc.GATES[0x08040B7E]),
            ('mc_native_fifo',0x080531CC,msc.GATES[0x080531CC]),
            ('mc_bot_0802f014_native',0x0802F014,msc.GATES[0x0802F014]),
            ('mc_bot_0802f04a_native',0x0802F04A,msc.GATES[0x0802F04A]),
            ('mc_native_request',cc['cc_request'],msc.generated_gates()[cc['cc_request']][0]),
            ('mc_native_service',cc['cc_service'],msc.generated_gates()[cc['cc_service']][0])):
        p=labels[name]; native.add(p)
        assert code[p-msc.CODE_BASE:p-msc.CODE_BASE+len(expected)]==expected
        tails[p+len(expected)]=address+len(expected)
    native|={labels['mc_native_poll'],labels['mc_native_bot_reset']}
    tails[labels['mc_native_poll']+6]=0x0802762A
    tails[labels['mc_native_bot_reset']+10]=0x0802EFFC
    relocated=list(md.disasm(code[labels['mc_native_bot_reset']-msc.CODE_BASE:labels['mc_native_bot_reset']-msc.CODE_BASE+10],labels['mc_native_bot_reset']))
    assert [i.mnemonic for i in relocated]==['movw','movt','movs']
    assert relocated[0].operands[1].imm==msc.BOT&0xFFFF and relocated[1].operands[1].imm==msc.BOT>>16
    assert stock[0x0802F168-0x08010000:0x0802F168-0x08010000+4]==msc.BOT.to_bytes(4,'little')
    external_calls={cc['cc_init'],cc['cc_request'],cc['cc_rx_submit'],cc['cc_irq'],
                    ss['ss_step'],ss['ss_resume'],ss['ss_native_08026988'],0x0802EF5A}
    if storage_hooks is not None: external_calls.update(storage_hooks)
    if class_hooks is not None: external_calls.update(class_hooks)
    external_tails={xc['xc_init_list'],cc['cc_rx_submit'],cc['cc_irq'],ib['ib_rx_callback']}
    for i in insns.values():
        assert i.mnemonic!='blx'
        if i.mnemonic in ('b','b.w','bl') or conditional_branch(i.mnemonic):
            t=i.operands[-1].imm
            assert t in insns or t in external_tails or i.mnemonic=='bl' and t in external_calls or tails.get(i.address)==t,(hex(i.address),hex(t))
    funcs={}
    for name in set(targets.values())|{'mc_cc_request','mc_service','mc_step'}:
        todo,seen,exits,maximum=[(labels[name],0)],set(),set(),0
        while todo:
            pc,depth=todo.pop()
            if pc in native: exits.add(depth); continue
            if (pc,depth) in seen: continue
            seen.add((pc,depth)); assert len(seen)<8000
            i=insns[pc]
            if i.mnemonic.startswith('push'): depth-=4*len(i.operands)
            if i.mnemonic.startswith('pop'): depth+=4*len(i.operands)
            maximum=max(maximum,-depth)
            if i.mnemonic=='bl': assert depth%8==0,(name,hex(pc),depth)
            if i.mnemonic=='bx' or i.mnemonic.startswith('pop') and 'pc' in i.op_str:
                exits.add(depth); continue
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
    # The one suppressed native notification has an exact generated return PC.
    call=next(md.disasm(control.arm_code()[0][cc['cc_deinit']-control.CODE_BASE+50:cc['cc_deinit']-control.CODE_BASE+54],cc['cc_deinit']+50))
    assert call.mnemonic=='bl' and call.operands[0].imm==cc['cc_request']
    report=dict(scope='LOCAL_CODE_PASS; CBW receive cancellation under synthetic MMIO contract',production_integrated=False,
        code_bytes=len(code),code_sha256=hashlib.sha256(code).hexdigest(),additional_synthetic_ram_bytes=msc.STATE_SIZE,
        combined_synthetic_ram_bytes=inherited['combined_synthetic_ram_bytes']+msc.STATE_SIZE,functions=funcs,
        max_forced_mask_instructions=max(masks),forced_mask_sections=len(masks),masked_calls_or_loops=False,
        emulator_overlays=overlays,inherited_composite=inherited,
        limits='Local frames only. CBW awaiting/partly received/pre-command only. Active storage/data/TX commands retain closed state. CPU-FIFO<=64B guard; no DMA, full scheduler, boot/RAM/init/OOM, NVIC/cache/cycle or silicon cancellation proof.')
    (out/'msc-code.txt').write_text('\n'.join(f'{i.address:08x} {i.bytes.hex():12} {i.mnemonic} {i.op_str}' for i in insns.values()),encoding='utf-8')
    (out/'msc-code-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


if __name__=='__main__': print(json.dumps(audit(sys.argv[1]),indent=2))
