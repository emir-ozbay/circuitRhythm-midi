"""Pinned native IRQ/submit/completion wiring and partial initialization."""
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'src')]
from inspect_ui import load_image
from capstone import Cs,CS_ARCH_ARM,CS_MODE_THUMB,CS_MODE_MCLASS


def trace(out):
    out=Path(out); out.mkdir(parents=True,exist_ok=True)
    data=load_image(); base=0x08010000; md=Cs(CS_ARCH_ARM,CS_MODE_THUMB|CS_MODE_MCLASS)
    expected={0x0804293E:[0x080646D2],0x080526C8:[0x08040C56],
              0x0805268E:[0x08040C32],0x08040C46:[0x0802AB4A],0x08040C22:[0x0802AB3E]}
    actual={key:[] for key in expected}
    for offset in range(0,len(data)-3,2):
        if data[offset+1]&0xF8!=0xF0: continue
        for i in md.disasm(data[offset:offset+4],base+offset,count=1):
            if i.mnemonic in ('bl','b.w'):
                target=int(i.op_str.lstrip('#'),16)
                if target in actual: actual[target].append(i.address)
    assert actual==expected
    def word(address): return int.from_bytes(data[address-base:address-base+4],'little')
    assert word(0x08067780)==0x0802AB37 and word(0x08067784)==0x0802AB43
    assert word(0x0802AB74)==0x20006F20
    assert word(0x080647E0)==word(0x0802CA60)==0x200054B4
    assert word(0x0802CA54)==0x40040000
    assert data[0x1c852:0x1c854]==bytes.fromhex('2361')  # handle+10 = r3=0
    windows=[(0x080646D0,6),(0x0804293E,0x5BE),(0x080532E0,0x6A),
             (0x080531A6,0x3E),(0x0802C78C,0x32),(0x08042614,0x136),
             (0x0802AB36,0x18),(0x08040C22,0x48),(0x0805268E,0x7E),
             (0x0802C82A,0x68),(0x08042FD8,0x88),(0x08052F52,0x188)]
    evidence=[]
    for address,size in windows:
        raw=data[address-base:address-base+size]
        (out/f'stock-{address:08x}.txt').write_text('\n'.join(
            f'{i.address:08x} {i.bytes.hex():12} {i.mnemonic} {i.op_str}' for i in md.disasm(raw,address)),encoding='utf-8')
        evidence.append(dict(address=hex(address),bytes=size,sha256=hashlib.sha256(raw).hexdigest()))
    report=dict(scope='Pinned direct refs/table/literal/byte evidence, not a complete indirect graph',
        direct_refs={hex(k):[hex(x) for x in v] for k,v in actual.items()},
        rx_chain='4293E ->2C798 ->42614 ->2AB42 ->40C46 ->526C8 ->26988',
        tx_chain='4293E ->2C7AC ->42690 ->2AB36 ->40C22 ->5268E ->268E0 ->268D0',
        ordering='OUT completion loop precedes RXFLVL CPU FIFO copy531CC in the same native IRQ. Deferred publication waits until IRQ return and RXFLVL empty.',
        initialization='Native2C82A..2C862 prefix assigns HAL handle200054B4,USBx40040000,6 endpoints and handle+10=0 CPU FIFO mode; partial prefix only, before hardware init427FC.',
        ownership_limit='Native XFRC has no generation. IRQ-entry job snapshot is valid only under cancellation barrier + synchronous callback ownership. Injected stale XFRC after a broken barrier is indistinguishable.',
        remaining='Control/reset/disconnect recovery, full boot/OOM/NVIC/cache/cycles and exact silicon/barrier semantics remain release gates.',windows=evidence)
    (out/'irq-contract.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


if __name__=='__main__': print(json.dumps(trace(sys.argv[1] if len(sys.argv)>1 else ROOT/'logs/usb-irq-contract'),indent=2))
