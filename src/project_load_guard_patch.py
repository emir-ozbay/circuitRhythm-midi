"""Contain failed stock project reads before their result is discarded.

This is NOT rollback. A failed read can already have changed live aliases.
Keep the stock running phase/flags, latch boot-lifetime project taint, retire
the bridge callback and queue native Close. No success apply is fabricated.
Other read clients and successful reads keep the stock bridge behavior.
"""
from patch_firmware import PatchHunk
from thumb_asm import (Asm,b_w,b_cond_w,bl,cmp_imm,cmp_reg,ldr_imm,ldr_sp,
                       movs_imm,pop,push,raw,str_imm,strb_w,tst_reg)
import seq_Patch as seq

SITE=0x080472A8
EXPECTED=bytes.fromhex('10b5039a')
CODE_BASE=0x0807C000
PROJECT_LOAD_VTABLE=0x08066FA0
NATIVE_CLOSE=0x080460C8


def arm_code(seq_state,ram_limit):
    a=Asm(CODE_BASE);E=a.emit
    def fallback(cond):E(b_cond_w,'native',cond)
    def ram(reg,size):
        E(movs_imm,1,3);E(tst_reg,reg,1);fallback('ne')
        a.imm32(1,0x20000000);E(cmp_reg,reg,1);fallback('lo')
        a.imm32(1,ram_limit-size);E(cmp_reg,reg,1);fallback('hi')
    a.label('read_result');E(push,[0,1,2,3,4,5,6],lr=True)
    E(cmp_imm,2,0);fallback('eq')
    # Native2B064 supplies userdata as argument6 at entry SP+4.
    E(ldr_sp,4,36);ram(4,4);E(ldr_imm,5,4);ram(5,12)
    E(ldr_imm,1,5);a.imm32(2,PROJECT_LOAD_VTABLE);E(cmp_reg,1,2);fallback('ne')
    # Native project Load writes P+14;the callback receiver is P+0C.
    E(ldr_imm,1,5,8);E(ldr_sp,2,12);E(cmp_reg,1,2);fallback('ne')
    E(bl,seq_state);E(cmp_imm,0,0);E(b_cond_w,'retire','eq')
    E(movs_imm,1,1);E(strb_w,1,0,seq.OFF_PROJECT_TAINTED)
    a.label('retire');E(movs_imm,1,0);E(str_imm,1,4)
    E(ldr_sp,0,0);E(movs_imm,2,0);E(bl,NATIVE_CLOSE)
    E(pop,[0,1,2,3,4,5,6],pc=True)
    a.label('native');E(pop,[0,1,2,3,4,5,6],lr=True)
    E(raw,EXPECTED);E(b_w,SITE+4)
    code,labels=a.assemble();code+=b'\x00\xbf'*(-len(code)%4//2)
    assert CODE_BASE%4==0 and CODE_BASE+len(code)<=0x0807D400
    return code,labels


def build_patches(seq_state,ram_limit):
    code,_=arm_code(seq_state,ram_limit)
    return [PatchHunk(SITE,EXPECTED,b_w(SITE,CODE_BASE),'project_load_error_containment'),
            PatchHunk(CODE_BASE,b'\xff'*len(code),code,'project_load_error_code')]
