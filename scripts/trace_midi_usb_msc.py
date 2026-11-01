"""Pinned BOT reset, consumer task, counter and endpoint close evidence."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from capstone import Cs,CS_ARCH_ARM,CS_MODE_THUMB,CS_MODE_MCLASS
from inspect_ui import load_image
import midi_usb_msc_prototype as msc


def trace(out):
    out=Path(out); out.mkdir(parents=True,exist_ok=True); b=load_image(); base=0x08010000
    md=Cs(CS_ARCH_ARM,CS_MODE_THUMB|CS_MODE_MCLASS); md.detail=True
    for address,expected in msc.GATES.items(): assert b[address-base:address-base+len(expected)]==expected
    calls={0x0806624E:0x0802EFF8,0x0802764A:0x0802F014,0x0802766E:0x0802F04A,
           0x0802EFF4:0x0802C9D4,0x0802F008:0x0802C9D4,0x08042FD2:0x08052EDC}
    for address,target in calls.items():
        i=next(md.disasm(b[address-base:address-base+4],address))
        assert i.mnemonic in ('bl','b.w') and i.operands[0].imm==target
    for address,value in ((0x0802F168,msc.BOT),(0x0802F174,msc.CBW),(0x08027674,0x20006E68)):
        assert int.from_bytes(b[address-base:address-base+4],'little')==value
    ranges=[(0x080661F8,0xBA),(0x0802EFF8,0x16A),(0x08027624,0x54),
            (0x08052EDC,0x70),(0x080531CC,0x18),(0x08023CEA,0x26),(0x0802CA6C,0x22)]
    windows=[]
    for address,n in ranges:
        raw=b[address-base:address-base+n]
        (out/f'stock-{address:08x}.txt').write_text('\n'.join(f'{i.address:08x} {i.bytes.hex():12} {i.mnemonic} {i.op_str}' for i in md.disasm(raw,address)),encoding='utf-8')
        windows.append(dict(address=hex(address),bytes=n,sha256=hashlib.sha256(raw).hexdigest()))
    report=dict(scope='Pinned bytes/direct calls/disassembly; not complete storage/IRQ reachability',
        calls={hex(k):hex(v) for k,v in calls.items()},windows=windows,
        reset='MSC class request0xFF ->661F8/6624E ->2EFF8 resets BOT state/status then arms OUT2(31B) without a cancellation barrier.',
        task='27624 polls native MSC IN/OUT ready counters then2F014/2F04A. The OUT handler turns a31B CBW into458D0 SCSI dispatch. Task entry and handler gates freeze it before media work.',
        close='52EDC masks endpoint IRQ and AND-clears CTL bits; it does not wait for EPDIS/ACK. Deferred native close occurs only after the new modeled barrier.',
        counter='26988(count0 endpoint) ->23CEA atomic ready increment, with capacity byte at endpoint+29. Clear only byte+28, preserve capacity.',
        cpu_copy='531CC rounds byte count up to full words and copies without bounds checks. The experiment guards the32B-padded CBW object; bad<=64B packets drain to private scratch and fail closed.',
        limits='No media I/O, active SCSI command cancellation, real USB/DMA/cache/NVIC/timing or complete boot/task graph proof.')
    (out/'msc-contract.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


if __name__=='__main__': print(json.dumps(trace(sys.argv[1]),indent=2))
