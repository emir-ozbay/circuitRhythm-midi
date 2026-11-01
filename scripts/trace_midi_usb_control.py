"""Pinned reset/EP0/configuration/SOF evidence. No physical peripherals."""
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'src')]
from inspect_ui import load_image
from capstone import Cs,CS_ARCH_ARM,CS_MODE_THUMB,CS_MODE_MCLASS
import midi_usb_control_prototype as control


def trace(out):
    out=Path(out); out.mkdir(parents=True,exist_ok=True)
    data=load_image(); base=0x08010000; md=Cs(CS_ARCH_ARM,CS_MODE_THUMB|CS_MODE_MCLASS)
    for address,expected in control.GATES.items():
        assert data[address-base:address-base+len(expected)]==expected
    calls={0x08040B72:0x080525B2,0x08040B96:0x0805261C,
           0x080525C6:0x0802C928,0x080525EC:0x0802C928,
           0x080525FE:0x080268D0,0x0805271A:0x080268EC,
           0x08044FE4:0x0804259A,0x08045024:0x08042584}
    for address,target in calls.items():
        ins=list(md.disasm(data[address-base:address-base+4],address,count=1))
        assert len(ins)==1 and ins[0].mnemonic=='bl' and int(ins[0].op_str.lstrip('#'),16)==target
    windows=[(0x08042D16,0xE0),(0x08042584,0x30),(0x080425A8,0x68),
             (0x08044F7C,0xB2),(0x08045018,0x2E),(0x08040B5A,0x48),
             (0x080525B2,0xB8),(0x0802C928,0x1C),(0x0804312C,0x2C),
             (0x08052E04,0x38),(0x080268EC,0x32),(0x080269AC,0x44)]
    evidence=[]
    for address,size in windows:
        raw=data[address-base:address-base+size]
        (out/f'stock-{address:08x}.txt').write_text('\n'.join(
            f'{i.address:08x} {i.bytes.hex():12} {i.mnemonic} {i.op_str}' for i in md.disasm(raw,address)),encoding='utf-8')
        evidence.append(dict(address=hex(address),bytes=size,sha256=hashlib.sha256(raw).hexdigest()))
    report=dict(scope='Pinned bytes/disassembly and selected callsites, not complete indirect reachability',
        calls={hex(k):hex(v) for k,v in calls.items()},
        setup_chain='IRQ4293E ->2C78C ->425A8 ->44DD8 ->42584/4259A ->2AB08/2AB14 ->40B5A/40B7E ->525B2/5261C',
        reset='Native USBRST branch flushes all TX FIFOs through52E04(fifo16), clears endpoint IRQs, restores EP0 masks and primes EP0 setup. ENUMDONE opens EP0 through2C7C6/4274C.',
        init_flush='Native525C6 flushes OUT1 through2C928/4312C/52E22, which is GLOBAL RX.525EC flushes IN81 via selected TX FIFO1. New guard skips only the bound OUT1 flush at verified525CB return PC during sealed deferred initialization.',
        bootstrap='Native525FE invokes268D0 to initialize availability. This is authorized only during sealed/no-owned-job constructor execution and is not counted as wire completion.',
        sof='Native5271A calls268EC, which can publish partial RX via2691E without26988. Control experiment suppresses bound SOF poll and arms one64B MTU job only when a66B ring record fits.',
        limits='Parent class notification uses a pinned native no-op boundary. Full descriptor/MSC/power-state/control graph, task wiring, silicon cancellation/NVIC/cache and timing remain unproven.',windows=evidence)
    (out/'control-contract.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


if __name__=='__main__': print(json.dumps(trace(sys.argv[1] if len(sys.argv)>1 else ROOT/'logs/usb-control-contract'),indent=2))
