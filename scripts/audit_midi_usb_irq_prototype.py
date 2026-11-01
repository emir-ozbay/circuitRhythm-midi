"""Local bridge CFG/ABI/gate audit. Not a whole-device IRQ/DMA proof."""
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
import midi_usb_irq_prototype as irq
import midi_usb_session_prototype as session
import midi_usb_lifecycle_prototype as life
import midi_usb_ledger_prototype as ledger
import midi_sysex_retry_prototype as retry
import midi_recovery_prototype as recovery


def audit(out):
    out=Path(out); out.mkdir(parents=True,exist_ok=True)
    code,labels=irq.arm_code(); stock=load_image(); _,ss=session.arm_code()
    md=Cs(CS_ARCH_ARM,CS_MODE_THUMB|CS_MODE_MCLASS); md.detail=True
    insns={i.address:i for i in md.disasm(code,irq.CODE_BASE)}
    assert sum(i.size for i in insns.values())==len(code)
    targets={irq.NATIVE_IRQ:'ib_irq',0x080268D0:'ib_tx_callback',0x08026988:'ib_rx_callback',0x0805261C:'ib_disconnect'}
    overlays=[]
    for address,original in irq.GATES.items():
        assert stock[address-0x08010000:address-0x08010000+len(original)]==original
        assert 0x08010200<=address<address+len(original)<=0x08080000
        assert sum(i.size for i in md.disasm(original,address))==len(original)
        for other in overlays:
            p=int(other['address'],16); n=len(bytes.fromhex(other['expected']))
            assert address+len(original)<=p or p+n<=address
        replacement=b_w(address,labels[targets[address]])+b'\x00\xBF'*(len(original)//2-2)
        overlays.append(dict(address=hex(address),expected=original.hex(),replacement=replacement.hex()))
    # Only the native IRQ and disconnect trampolines execute copied prologues.
    tails={labels['ib_native_irq']+4:irq.NATIVE_IRQ+4,
           labels['ib_native_disconnect']+4:0x08052620}
    for name,address in (('ib_native_irq',irq.NATIVE_IRQ),('ib_native_disconnect',0x0805261C)):
        off=labels[name]-irq.CODE_BASE; assert code[off:off+4]==irq.GATES[address][:4]
    external={ss['ss_tx_done'],ss['ss_rx_done']}
    native_foreign={ss['ss_native_080268d0'],ss['ss_native_08026988']}
    for i in insns.values():
        if i.mnemonic in ('b','b.w','bl') or conditional_branch(i.mnemonic):
            t=i.operands[-1].imm
            assert t in insns or i.mnemonic=='bl' and t in external or t in native_foreign or tails.get(i.address)==t
        assert i.mnemonic not in ('blx','cpsid','cpsie')
    functions={}; starts={labels['ib_native_irq'],labels['ib_native_disconnect']}
    for name in ('ib_irq','ib_tx_callback','ib_rx_callback','ib_disconnect'):
        todo,seen,exits,maximum=[(labels[name],0)],set(),set(),0
        while todo:
            pc,depth=todo.pop()
            if pc in starts:
                exits.add(depth); continue
            if (pc,depth) in seen: continue
            seen.add((pc,depth)); assert len(seen)<5000
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
                if target in starts|native_foreign: exits.add(depth); continue
                todo.append((target,depth)); continue
            if conditional_branch(i.mnemonic): todo.append((i.operands[-1].imm,depth))
            todo.append((pc+i.size,depth))
        assert exits=={0},(name,exits)
        functions[name]=dict(max_local_stack_bytes=maximum,exit_sp_deltas=sorted(exits))
    report=dict(scope='LOCAL_CODE_PASS; synchronous native CPU-FIFO completion subset',
        production_integrated=False,code_bytes=len(code),code_sha256=hashlib.sha256(code).hexdigest(),
        additional_synthetic_ram_bytes=irq.STATE_SIZE,
        combined_synthetic_ram_bytes=irq.STATE_SIZE+session.STATE_SIZE+life.STATE_SIZE+ledger.STATE_SIZE+retry.REQUEST_STATE_SIZE+recovery.STATE_SIZE,
        functions=functions,forced_irq_mask=False,emulator_overlays=overlays,
        native_irq_local_frame_bytes=64,bridge_plus_native_irq_local_bytes=88,
        limits='Native64B IRQ frame + bridge24B excludes callees and exception frame. No complete NVIC/cache/DMA/timing proof; reset/control/DMA IRQs fail closed.')
    (out/'irq-code.txt').write_text('\n'.join(f'{i.address:08x} {i.bytes.hex():12} {i.mnemonic} {i.op_str}' for i in insns.values()),encoding='utf-8')
    (out/'irq-code-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


if __name__=='__main__': print(json.dumps(audit(sys.argv[1] if len(sys.argv)>1 else ROOT/'logs/usb-irq-audit'),indent=2))
