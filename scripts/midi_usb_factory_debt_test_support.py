"""A second checked emulator-only injection cave; no production patch/API."""
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_PRIMASK,UC_ARM_REG_PC
from thumb_asm import Asm,b_w,bl,pop,push,raw,str_imm


def inject_second(h,pc,calls):
    # The inherited helper owns71000..71100 and permits one installation.
    # Keep that executed trampoline intact while adding a later race edge.
    address,results=0x08071100,0x20004AA0
    a=Asm(address);a.emit(push,list(range(13)),lr=True)
    a.emit(raw,bytes.fromhex('eff30084'));a.emit(push,[4,5])
    for n,(target,args) in enumerate(calls):
        assert 0x08010200<=target<0x08080000 and target%2==0
        for r,value in enumerate(args):a.imm32(r,value)
        a.emit(bl,target);a.imm32(3,results+n*4);a.emit(str_imm,0,3)
    a.emit(pop,[4,5]);a.emit(raw,bytes.fromhex('84f3008c'))
    a.emit(pop,list(range(13)),lr=True);a.emit(b_w,pc)
    code,_=a.assemble();assert len(code)<=256 and address%4==0
    assert 0x08010200<=address<address+len(code)<=0x08080000
    assert all(address+len(code)<=o['address'] or o['address']+len(o['replacement'])<=address for o in h.recovery.overlays)
    offset=address-0x08010000
    assert h.ss.flash[offset:offset+256]==bytes(256)
    assert h.u.mem_read(address,256)==bytes(256)
    h.u.mem_write(address,code);h.u.ctl_remove_cache(address,address+256)
    expected=bytearray(h.ss.flash);expected[offset:offset+len(code)]=code;h.ss.flash=bytes(expected)
    injected=[]
    def inject(u,p,n,d):
        if injected:return
        h.assertEqual(u.reg_read(UC_ARM_REG_PRIMASK),0)
        injected.append(p);u.reg_write(UC_ARM_REG_PC,address|1)
    h.u.hook_add(UC_HOOK_CODE,inject,begin=pc,end=pc)
    return injected,lambda:[h.read(results+n*4) for n in range(len(calls))]
