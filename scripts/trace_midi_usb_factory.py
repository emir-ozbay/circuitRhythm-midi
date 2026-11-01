"""Pinned factory list-clear order, native caller ABI, stop/init/start evidence."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from inspect_ui import load_image
from capstone import Cs,CS_ARCH_ARM,CS_MODE_THUMB,CS_MODE_MCLASS
import midi_usb_factory_prototype as factory


def trace(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True);b=load_image();base=0x08010000
    md=Cs(CS_ARCH_ARM,CS_MODE_THUMB|CS_MODE_MCLASS);md.detail=True
    for p,e in factory.GATES.items():assert b[p-base:p-base+len(e)]==e
    refs=[]
    for off in range(0,len(b)-3,2):
        if b[off+1]&0xF8!=0xF0:continue
        for i in md.disasm(b[off:off+4],base+off,count=1):
            if i.mnemonic in ('bl','b.w') and i.operands[0].imm==0x080432A8:refs.append(i.address)
    assert refs==[0x0802CB2E,0x08035838]
    constants=[int.from_bytes(b[p-base:p-base+4],'little') for p in (0x0803583C,0x08035840)]
    assert set(constants)=={1,0x101}
    for p,n in ((0x08040A30,0x48),(0x08040AFE,0x3A),(0x080432A8,0x60),(0x0802CB18,0x1A),
                (0x08035814,0x30),(0x08042544,0x40),(0x080428D4,0x46),(0x0804291A,0x24),(0x0802C82A,0x6A)):
        (out/f'stock-{p:08x}.txt').write_text('\n'.join(f'{i.address:08x} {i.bytes.hex():12} {i.mnemonic} {i.op_str}' for i in md.disasm(b[p-base:p-base+n],p)),encoding='utf-8')
    r=dict(scope='Pinned stock bytes/direct calls/disassembly; no complete indirect/caller/boot proof',direct_callers=[hex(x) for x in refs],
        caller_constants=constants,
        unsafe_order='40A40 clears root class pointers and40A44 count before40A48->40B44->40B7E deinit. Old classes can therefore miss teardown.',
        factory='432A8 reads argument bytes0/1,builds MIDI200000F0 and optional MSC200000FC at root200000D0. Upper16 bits ignored;2CB18 initializes only low two stack bytes.',
        mode_map={'0':'0','1':'1','2':'3','3':'2'},
        native_graph='Old-list mc barrier/deinit first;then native432A8->40A30 stop/init->40AFE class add/deinit->40B1C descriptor/start.427FC HAL init is an explicit boundary.',
        timing='Native3ms stop/start and200ms factory waits run against synthetic24068 ticks. NVIC/clock register memory is mapped, not IRQ/cycle/silicon modeled.',
        remaining='MSC-only/zero lists unsupported;full Packs UI/project operations,power,indirect callers,RTOS task wiring,boot/RAM/init/timing remain open.')
    (out/'factory-contract.json').write_text(json.dumps(r,indent=2),encoding='utf-8');return r


if __name__=='__main__':print(json.dumps(trace(sys.argv[1]),indent=2))
