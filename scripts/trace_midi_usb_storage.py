"""Native initializer table, readonly callback and queued read/drain evidence."""
import hashlib,json,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from inspect_ui import load_image
from capstone import Cs,CS_ARCH_ARM,CS_MODE_THUMB,CS_MODE_MCLASS
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_THUMB,UC_MODE_MCLASS
from unicorn.arm_const import UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC
import midi_usb_storage_prototype as storage


def trace(out):
    out=Path(out); out.mkdir(parents=True,exist_ok=True); b=load_image(); base=0x08010000
    u=Uc(UC_ARCH_ARM,UC_MODE_THUMB|UC_MODE_MCLASS); u.mem_map(0x08000000,0x80000);u.mem_write(base,b)
    u.mem_map(0x20000000,0x50000);u.reg_write(UC_ARM_REG_SP,0x2004F000);u.reg_write(UC_ARM_REG_LR,0x0800E001)
    u.emu_start(0x08068A55,0x0800E000,count=1000000); assert u.reg_read(UC_ARM_REG_PC)==0x0800E000
    ops=struct.unpack('<9I',u.mem_read(storage.OPS,36))
    assert int.from_bytes(u.mem_read(0x200038AC,4),'little')==storage.OPS
    assert ops==(0x080650D1,0x080650D5,0x080650E5,0x080650E9,0x08065129,0x08065195,0x08065251,0x08065255,0x08068BC0)
    assert b[0x080650E8-base:0x080650EC-base]==bytes.fromhex('01207047')
    vt=struct.unpack('<9I',u.mem_read(0x08068698,36)); assert vt[3]==0x0802C395 and vt[7]==0x0802C23B
    md=Cs(CS_ARCH_ARM,CS_MODE_THUMB|CS_MODE_MCLASS);md.detail=True
    for p,expected in storage.GATES.items(): assert b[p-base:p-base+len(expected)]==expected
    for p,n in ((0x080650D0,0x1C),(0x08065128,0x6C),(0x08045AD4,0x12),(0x08045B50,0x76),
                (0x08045BC6,0x56),(0x0802C394,0x34),(0x0802C23A,0x3C),(0x0802C278,0xEA),(0x08043264,0x22)):
        (out/f'stock-{p:08x}.txt').write_text('\n'.join(f'{i.address:08x} {i.bytes.hex():12} {i.mnemonic} {i.op_str}' for i in md.disasm(b[p-base:p-base+n],p)),encoding='utf-8')
    report=dict(scope='Pinned bytes/disassembly and isolated native static initializer; no full boot or devices',
        storage_global=hex(0x200038AC),ops=[hex(x) for x in ops],backend_vtable=[hex(x) for x in vt],
        readonly='650E8 always returns1. Native WRITE10 checks this callback at45C06 and rejects with DATA PROTECT, before65194 write. Factory43264 changes range descriptor, not this table.',
        read='65128 calls backend vtable+0C ->2C394:enqueue24B read descriptor2C1CC,then vtable+1C2C23A waits for2C278 worker to clear drain request. Lower flash is a separate boundary.',
        result='2C328 stores each worker result.2C394 returns the shared last status, but65128 ultimately returns0 and can hide read failure. New wrapper captures the matching read result at2C328 before later jobs overwrite the shared status.',
        ownership='40024000 is the4KB shared SCSI data buffer; CSW borrows20006DD4 for13B. New polling and submit gates prevent reuse until native completion or the cancellation barrier.',
        limits='Native readonly binding, constructor and worker proved locally. Complete rebinding/producer/RTOS/flash-driver/power/class/boot graphs and silicon cancellation unproven.')
    (out/'storage-contract.json').write_text(json.dumps(report,indent=2),encoding='utf-8');return report


if __name__=='__main__': print(json.dumps(trace(sys.argv[1]),indent=2))
