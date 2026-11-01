"""Pinned main/worker/direct-caller graph; no complete scheduler claim."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from capstone import Cs,CS_ARCH_ARM,CS_MODE_THUMB,CS_MODE_MCLASS
from inspect_ui import load_image
import midi_usb_task_prototype as task


def trace(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True);b=load_image();base=0x08010000
    md=Cs(CS_ARCH_ARM,CS_MODE_THUMB|CS_MODE_MCLASS);md.detail=True
    assert b[task.MAIN_CALL-base:task.MAIN_CALL-base+4]==task.GATES[task.MAIN_CALL]
    refs={x:[] for x in (0x08027624,0x0802C278)}
    for off in range(0,len(b)-3,2):
        if b[off+1]&0xF8!=0xF0:continue
        for i in md.disasm(b[off:off+4],base+off,count=1):
            if i.mnemonic in ('bl','b.w') and i.operands[0].imm in refs:refs[i.operands[0].imm].append(i.address)
    assert refs=={0x08027624:[0x0802587C,0x0802DE92,0x08053E78],0x0802C278:[0x080648A6,0x080648B0]}
    assert int.from_bytes(b[0x080648C8-base:0x080648C8-base+4],'little')==0x20006E60
    windows=[]
    for p,n in ((0x08025870,0x10),(0x08027624,0x50),(0x08064874,0x60),(0x0802C23A,0x3C),(0x0802DE90,0xA),(0x08053E6C,0x1C)):
        raw=b[p-base:p-base+n]
        (out/f'stock-{p:08x}.txt').write_text('\n'.join(f'{i.address:08x} {i.bytes.hex():12} {i.mnemonic} {i.op_str}' for i in md.disasm(raw,p)),encoding='utf-8')
        windows.append(dict(address=hex(p),bytes=n,sha256=hashlib.sha256(raw).hexdigest()))
    r=dict(scope='Pinned bytes/direct refs and bounded native main/worker spans',direct_refs={hex(k):[hex(x) for x in v] for k,v in refs.items()},
        native_order='25870 router global20006F04 ->297DE output;25878->29ABC USB/DIN input;2587C->27624 MSC.',
        replacement='Only2587C:one sr_service,one pw_service,then zero/one original27624 through storage/MSC gates. No service in IRQ/masked/reentrant or active worker/read ownership.',
        worker='READ65128->2C23A drain->24138 modeled task switch->native648AE..648B8 loop->2C278 queue worker. No Python ready/drain clearing; return/wait edge remains a boundary.',
        unwired='2DE92 event callback and53E78 loop also call27624. No safe task-context/full-owner proof for these callers; not patched.',
        unresolved='Frozen cl_poll cannot discharge retained ledger debt;ss_quiet requires debt/queued TX empty before close.64 live main passes including wake still do not recover in the negative test.',windows=windows)
    (out/'task-contract.json').write_text(json.dumps(r,indent=2),encoding='utf-8');return r


if __name__=='__main__':print(json.dumps(trace(sys.argv[1]),indent=2))
