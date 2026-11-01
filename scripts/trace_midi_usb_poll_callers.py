"""Pinned MSC direct callers and transfer-view callback provenance; bounded CFG."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from capstone import Cs,CS_ARCH_ARM,CS_MODE_THUMB,CS_MODE_MCLASS
from inspect_ui import load_image


def trace(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True);image=load_image();base=0x08010000
    md=Cs(CS_ARCH_ARM,CS_MODE_THUMB|CS_MODE_MCLASS);md.detail=True
    def word(p):return int.from_bytes(image[p-base:p-base+4],'little')
    refs=[]
    for offset in range(0,len(image)-3,2):
        if image[offset+1]&0xF8!=0xF0:continue
        for i in md.disasm(image[offset:offset+4],base+offset,count=1):
            if i.mnemonic in ('bl','b.w') and i.operands[0].imm==0x08027624:refs.append(i.address)
    assert refs==[0x0802587C,0x0802DE92,0x08053E78]
    assert word(0x0802DEE0)==0x08069628 and word(0x0802DEE4)==0x0802DE91
    assert word(0x08069628)==0x08025653
    assert image[0x08043B58-base:0x08043B5A-base]==bytes.fromhex('ae61')
    assert image[0x08043FA0-base:0x08043FAC-base]==bytes.fromhex('b06918b10268002113689847')
    windows=[]
    for start,end in ((0x080273A8,0x080273AE),(0x0802DE90,0x0802DEDC),(0x08025652,0x08025660),
                      (0x08043B2C,0x08043B8C),(0x08043F84,0x08043FB4),(0x08053E24,0x08053E8C),
                      (0x08027624,0x08027678)):
        raw=image[start-base:end-base]
        (out/f'stock-{start:08x}.txt').write_text('\n'.join(
            f'{i.address:08x} {i.bytes.hex():12} {i.mnemonic} {i.op_str}' for i in md.disasm(raw,start)),encoding='utf-8')
        windows.append(dict(address=hex(start),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
    r=dict(scope='Pinned direct call scan + native constructor/callback/dispatch slice; no complete UI/RTOS/boot graph',
        direct_poll_callers=[hex(p) for p in refs],
        callback_provenance=['273A8 constructor calls2DE9A','2DE9A allocates8B callback;vtable69628/function2DE91',
            '43B2C stores callback at view+48','43FA0..43FAC invokes view+48->vtable[0]',
            'Native25652 adapter loads function at+4,passes context','2DE90 callback calls27624 and always returns0'],
        guards='27624 ->storage sd_poll(TX/SCSI/IO ownership) ->MSC mc_poll(main context,OPEN/op0,TASK_BUSY). Guarded reject0 is not a progress/completion acknowledgement.',
        cancellation='mc_service also waits TASK_BUSY/ARM_BUSY/IRQ_ACTIVE and storage quiet policy before endpoint/reader release. Tests inject callback/task service inside native worker/IRQ/factory/poll ownership.',
        progress_limit='This callback only polls MSC. It does not replace coordinated main retry/power service;callback-only pending MIDI debt/power request cannot progress.',
        other_caller='53E78 single BL leaf has the same guards in tests;surrounding53E24 loop/storage/UI owner graph is not executed or closed.',
        model='Synthetic view/callback binding;native43FA0 dispatch slice/25652 adapter/2DE90/MSC/READ worker/HAL/IRQ execute. Full43E1C transfer handler,actual object creation lifetime,RTOS scheduling and real PHY/flash/UART timing remain open.',
        windows=windows)
    (out/'poll-callers-contract.json').write_text(json.dumps(r,indent=2),encoding='utf-8');return r


if __name__=='__main__':print(json.dumps(trace(sys.argv[1]),indent=2))
