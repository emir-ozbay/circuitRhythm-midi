"""Pinned loader byte/disassembly contract; no device APIs."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from capstone import Cs,CS_ARCH_ARM,CS_MODE_THUMB,CS_MODE_MCLASS
from inspect_ui import load_image
from midi_usb_long_loop_test_support import PINS,BOUNDARIES


def trace(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True);image=load_image();base=0x08010000
    md=Cs(CS_ARCH_ARM,CS_MODE_THUMB|CS_MODE_MCLASS);md.detail=True
    windows=[]
    for (p,n),digest in PINS.items():
        raw=image[p-base:p-base+n];assert hashlib.sha256(raw).hexdigest()==digest
        (out/f'stock-{p:08x}.txt').write_text('\n'.join(f'{i.address:08x} {i.bytes.hex():12} {i.mnemonic} {i.op_str}' for i in md.disasm(raw,p)),encoding='utf-8')
        windows.append(dict(address=hex(p),bytes=n,sha256=digest))
    ins={i.address:i for i in md.disasm(image[0x53E24-0x10000:0x53E8C-0x10000],0x08053E24)}
    for p,target in ((0x08053E26,0x08040E28),(0x08053E6C,0x0803172E),(0x08053E74,0x08053E8C),(0x08053E78,0x08027624)):
        assert ins[p].mnemonic=='bl' and ins[p].operands[0].imm==target
    assert ins[0x08053E7C].op_str=='r5, #0x80' and ins[0x08053E7E].operands[0].imm==0x08053E60
    for p,b in BOUNDARIES.items():assert image[p-base:p-base+4]==bytes.fromhex(b)
    def word(p):return int.from_bytes(image[p-base:p-base+4],'little')
    assert [word(p) for p in (0x080540BC,0x080540C0,0x080540C4,0x080540C8)]==[0x20006F24,0x20000A8C,0x20003F94,0x20006AD8]
    assert word(0x0802EFC0)==0x20003F8C and word(0x0802EFC4)==0x20003F94 and word(0x08026DE4)==0x40003000
    r=dict(scope='Native53E24 full128-slot control loop and53E8C sample loader; bounded synthetic RAM evidence',
        native=['40E28/2745A already-selected pack fast path','53E24 progress/control loop128 slots',
                '3172E->26DD6 watchdog reload','53E8C sample loader +4603A read wrapper',
                '5B2B4/5B2A0/540D4 WAV checks/offset/length; REV16 double buffer',
                '53E78->27624 MSC; native SCSI/queued worker/USB HAL/IRQ under existing prototypes'],
        bindings={'sample_manager':'20006F24 -> synthetic allocator/vtable','progress_observer':'20000A8C -> synthetic UI/vtable',
                  'sample_buffers':['20003F94..20004794','20004794..20004F94'],
                  'header':'20006AD8..20006B18','msc_read_buffer':'40024000..40025000',
                  'media_semaphore':'20003F8C;native2EF6A/2EF98;27624 checks2EF5A'},
        model_boundaries={hex(p):b for p,b in BOUNDARIES.items()},
        model_limits=['File dispatcher45EB6 immediately copies RAM bytes,zero-fills short reads;no file-task scheduling,errors,ownership lifetime or custom filesystem.',
                      'Sample flash API records RAM writes;no real flash arbitration,bank/page timing or DMA.',
                      'Progress observer and sample allocator use synthetic vtables;full UI/allocator initialization/ownership not proved.',
                      'Earlier synthetic MIDI objects at4B00..5000 are rebound to asserted-free E000..E500;injection results E580. This is a test layout,not production RAM/init proof.',
                      'External bus checkpoints save/restore CPU and test-stack context;they do not call main service unless stated.',
                      'Loop-only MSC calls do not service MIDI retry/power;production and hardware release remain NO-GO.'],windows=windows)
    (out/'long-loop-contract.json').write_text(json.dumps(r,indent=2),encoding='utf-8');return r


if __name__=='__main__':print(json.dumps(trace(sys.argv[1]),indent=2))
