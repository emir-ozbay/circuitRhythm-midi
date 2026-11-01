"""Bounded output service between stock player flushes;no fault clearing.

Eight stock gate slots on each of eight players can produce64 Offs plus
Stop in one controller callback. Service the registered native router once
after each stock flush,so healthy drivers need not wait for the next Main
iteration. Stalled drivers retain the existing deferred debt/quarantine.
"""
from patch_firmware import PatchHunk
from thumb_asm import Asm,bl,blx_reg,b_cond_w,cmp_imm,cmp_reg,ldr_imm,ldrb_imm,mov_reg,movs_imm,pop,push,raw,tst_reg
import midi_recovery_prototype as recovery

SITE=0x080552FE
EXPECTED=bytes.fromhex('90470020') # blx r2;movs r0,0
CODE_BASE=0x0807FE40
NATIVE_FLUSH=0x0804AED9
NATIVE_POLL=0x080297DE
GLOBAL_ROUTER=0x20006F04


def arm_code(state):
    a=Asm(CODE_BASE);E=a.emit
    def bc(condition):E(b_cond_w,'return',condition)
    def ram(r,size):
        E(movs_imm,1,3);E(tst_reg,r,1);bc('ne')
        a.imm32(1,0x20000000);E(cmp_reg,r,1);bc('lo')
        a.imm32(1,state-size);E(cmp_reg,r,1);bc('hi')
    a.label('flush_then_service');E(push,[4,5,6],lr=True);E(mov_reg,4,2)
    E(blx_reg,2) # original virtual flush,with original argument registers
    a.imm32(1,NATIVE_FLUSH);E(cmp_reg,4,1);bc('ne')
    for system in ('eff30581','eff31081','eff31181'): # IPSR,PRIMASK,BASEPRI
        E(raw,bytes.fromhex(system));E(cmp_imm,1,0);bc('ne')
    a.imm32(0,GLOBAL_ROUTER);E(ldr_imm,0,0);ram(0,0x1C)
    a.imm32(5,state);E(ldr_imm,1,5);a.imm32(2,recovery.MAGIC)
    E(cmp_reg,1,2);bc('ne')
    E(ldrb_imm,1,0,0x18);E(cmp_imm,1,3);bc('ne')
    E(ldr_imm,6,0,0x14);ram(6,12)
    for n in range(3):
        a.imm32(5,state+recovery.HEADER_SIZE+n*recovery.ENTRY_SIZE)
        E(ldr_imm,1,5);E(cmp_imm,1,0);bc('eq')
        E(ldr_imm,2,6,4*n);E(cmp_reg,1,2);bc('ne')
    a.label('service');E(bl,NATIVE_POLL)
    a.label('return');E(movs_imm,0,0);E(pop,[4,5,6],pc=True)
    code,labels=a.assemble();code+=b'\x00\xbf'*(-len(code)%4//2)
    assert CODE_BASE%4==0 and CODE_BASE+len(code)<=0x08080000
    return code,labels


def build_patches(state):
    code,_=arm_code(state)
    return [PatchHunk(SITE,EXPECTED,bl(SITE,CODE_BASE),'dense_stop_player_flush_service'),
            PatchHunk(CODE_BASE,b'\xff'*len(code),code,'dense_stop_bounded_output_service')]
