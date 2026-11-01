"""Pinned native initializer, object tables and class-parent evidence."""
import hashlib,json,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'src')]
from inspect_ui import load_image
from capstone import Cs,CS_ARCH_ARM,CS_MODE_THUMB,CS_MODE_MCLASS
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_THUMB,UC_MODE_MCLASS,UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC
import midi_usb_composite_prototype as composite


def trace(out):
    out=Path(out); out.mkdir(parents=True,exist_ok=True); data=load_image()
    md=Cs(CS_ARCH_ARM,CS_MODE_THUMB|CS_MODE_MCLASS)
    u=Uc(UC_ARCH_ARM,UC_MODE_THUMB|UC_MODE_MCLASS)
    u.mem_map(0x08000000,0x80000); u.mem_write(0x08010000,data)
    u.mem_map(0x20000000,0x50000); u.reg_write(UC_ARM_REG_SP,0x2004F000)
    u.reg_write(UC_ARM_REG_LR,0x0800E001); visited=[]
    u.hook_add(UC_HOOK_CODE,lambda u,p,n,d:visited.append(p),begin=0x0806668C,end=0x08066700)
    # This walks native static initializer records and executes constructors.
    # It is not just a scatter-copy, and is not full reset/boot/RTOS startup.
    u.emu_start(0x08068A55,0x0800E000,count=1000000)
    assert u.reg_read(UC_ARM_REG_PC)==0x0800E000 and visited
    def words(address,n): return struct.unpack('<'+'I'*n,u.mem_read(address,n*4))
    root=words(0x200000D0,8); midi=words(0x200000F0,3); msc=words(0x200000FC,3)
    assert root==(0,0x20005CC8,0,0,0,0,0,0)
    assert midi==(0x080676F4,0x200000C0,0x200000C8)
    assert msc==(0x08067730,0x08069784,0x0806978C)
    assert words(0x200000C0,4)==(0x20005F70,0,0x20005F94,0)
    assert words(0x08069784,4)==(0x20006100,0,0x20006124,0)
    assert words(midi[0],1)==(0x08068A2D,)
    assert words(msc[0],3)==(0x080661DD,0x080661EF,0x080661F9)
    for address,expected in composite.GATES.items():
        assert data[address-0x08010000:address-0x08010000+len(expected)]==expected
    calls={0x08068A32:0x080297C0,0x08068A36:0x08029AB0,
           0x080661E0:0x0802F00C,0x080661E6:0x0802EFC8,
           0x08040B72:0x080525B2,0x08040B96:0x0805261C}
    for address,target in calls.items():
        i=next(md.disasm(data[address-0x08010000:address-0x08010000+4],address))
        assert i.mnemonic=='bl' and int(i.op_str.lstrip('#'),16)==target
    for address,size in ((0x08068A2C,0x50),(0x0806668C,0x90),(0x080432A8,0x60),
                         (0x080297C0,0x1E),(0x08029AB0,0xC),(0x080661DC,0x1C),
                         (0x0802EFC8,0x4C),(0x08040A78,0xE2)):
        (out/f'stock-{address:08x}.txt').write_text('\n'.join(
            f'{i.address:08x} {i.bytes.hex():12} {i.mnemonic} {i.op_str}'
            for i in md.disasm(data[address-0x08010000:address-0x08010000+size],address)),encoding='utf-8')
    result=dict(scope='Pinned stock bytes + native static initializer walker in isolated Unicorn; no MMIO/full boot/device',
        image_sha256=hashlib.sha256(data).hexdigest(),native_endpoint_initializer_visits=len(visited),
        root=[hex(x) for x in root],midi=[hex(x) for x in midi],msc=[hex(x) for x in msc],
        calls={hex(k):hex(v) for k,v in calls.items()},
        midi_parent='68A2C executes all-port router clear297C0 then input rearm29AB0. DIN queues are affected by the stock parent.',
        msc_parent='661DC executes BOT reset2F00C then2EFC8: Init(LUN0) storage callback and31-byte OUT2 CBW arm.661EE resets BOT state.',
        descriptor='40B24 uses buffer200067E0. Native40A78 updates that same125-byte/3-interface composite header.',
        boundary='Experiment substitutes only storage Init callback with pinned native427D2 return0. No storage/media I/O or full BOT transfer proof.',
        terminology_correction='Earlier reports called68A54 scatter-load. It is a static-initializer record walker that also executes6668C endpoint constructors; not full boot.')
    (out/'composite-contract.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


if __name__=='__main__': print(json.dumps(trace(sys.argv[1]),indent=2))
