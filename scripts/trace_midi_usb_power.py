"""Pinned native suspend, wake, state save/restore and ungate evidence."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from capstone import Cs,CS_ARCH_ARM,CS_MODE_THUMB,CS_MODE_MCLASS
from inspect_ui import load_image
import midi_usb_power_prototype as power


def trace(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True);b=load_image();base=0x08010000
    md=Cs(CS_ARCH_ARM,CS_MODE_THUMB|CS_MODE_MCLASS);md.detail=True
    for p,e in power.GATES.items():assert b[p-base:p-base+len(e)]==e
    refs={x:[] for x in (0x0802C7E6,0x0802C802,0x0804279E,0x080427AE,0x0802C9F8)}
    for off in range(0,len(b)-3,2):
        if b[off+1]&0xF8!=0xF0:continue
        for i in md.disasm(b[off:off+4],base+off,count=1):
            if i.mnemonic in ('bl','b.w') and i.operands[0].imm in refs:refs[i.operands[0].imm].append(i.address)
    assert refs[0x0802C7E6]==[0x08042CD0,0x08042D12] and refs[0x0802C802]==[0x08042CB0]
    windows=[]
    for p,n in ((0x08042C80,0x96),(0x0802C7E6,0x24),(0x0804279E,0x1C),(0x0802C9F8,0x74)):
        raw=b[p-base:p-base+n]
        (out/f'stock-{p:08x}.txt').write_text('\n'.join(f'{i.address:08x} {i.bytes.hex():12} {i.mnemonic} {i.op_str}' for i in md.disasm(raw,p)),encoding='utf-8')
        windows.append(dict(address=hex(p),bytes=n,sha256=hashlib.sha256(raw).hexdigest()))
    r=dict(scope='Stock byte/disassembly/direct-call evidence; not full indirect/power graph',direct_refs={hex(k):[hex(x) for x in v] for k,v in refs.items()},
        native_suspend='GINT11 with DSTS+808 bit0 ->2C7E6 ->4279E: controller+275 saves+274, +274=4; USB+E00 bit0 set immediately, without reader cancellation.',
        native_wake='GINT31 before GINT11 in native IRQ: clears DCTL bit0 then2C802->427AE copies saved state without ownership checks. New preflight makes WAKE/RESET win.',
        native_ungate='2C9F8(handle,0) clears USB+E00 bit0 then427AE; low-power handle+20hex may also change system registers, so only0 is admitted.',
        experiment='Freeze prior to native completion claims, wait common barrier, native4279E then generation-checked atomic clock-stop. Wake ungates before normal IRQ; reset suppresses automatic config replay.',
        limits='Synthetic clock/MMIO/ACK/ticks/NVIC/RTOS/flash. LPM27, system deep stop, DMA, remote wake policy, actual PHY wake reachability, task wiring/boot/RAM/init and silicon timing unproven.',windows=windows)
    (out/'power-contract.json').write_text(json.dumps(r,indent=2),encoding='utf-8');return r


if __name__=='__main__':print(json.dumps(trace(sys.argv[1]),indent=2))
