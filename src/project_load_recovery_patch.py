"""Close-confirmed stock Load/New recovery; no raw rollback or forged idle.

Only a stopped, unheld Projects pad may retry after a matching native Close.
Only its successful read/New callback and complete native apply clear taint.
"""
from patch_firmware import PatchHunk
from thumb_asm import (Asm,b_w,b_cond_w,bl,cmp_imm,cmp_reg,ldr_imm,ldr_w,ldr_reg,
    ldr_sp,ldrb_w,ldrh_imm,mov_reg,movs_imm,movw,movt,pop,push,raw,str_imm,
    strb_w,tst_reg,adds_imm8,subs_imm8,ands_reg,lsls_imm,lsrs_imm,adds_reg,
    sub_sp_imm,add_sp_imm)
import seq_Patch as seq
SITE=0x080472A8;EXPECTED=bytes.fromhex('10b5039a')
PAD_SITE=0x0803D7FE;PAD_EXPECTED=bytes.fromhex('70b50646')
RELEASE_SITE=0x0803D896;RELEASE_EXPECTED=bytes.fromhex('38b50446')
NEW_SITE=0x08037C84;NEW_EXPECTED=bytes.fromhex('10b50c46')
APPLY_SITE=0x08037E3C;APPLY_EXPECTED=bytes.fromhex('f8b50446')
BUTTON_SITE=0x0803D8FC;BUTTON_EXPECTED=bytes.fromhex('40f0ca81')
BUTTON_CONTINUE=0x0803D900;BUTTON_REJECT=0x0803DC94
CODE_BASE=0x0807C000;CODE_LIMIT=0x0807D400
PROJECT_LOAD_VTABLE=0x08066FA0;PROJECT_VTABLE=0x08066F64;CONTROLLER_VTABLE=0x080672E4
NATIVE_CLOSE=0x080460C8;NATIVE_LOAD=0x08037B8C
READ_WORD=0x0803FC58;PAD_DOWN=0x08051B7A;PAD_UP=0x08051BB8
# Inactive historical close bookkeeping; no additional reserved RAM.
OWNER=0x44;DESCRIPTOR=0x48;EPOCH=0x54;SLOT=0x58;BRIDGE=0x5C
HELD=seq.OFF_PROJECT_RECOVERY_HELD;STAGE=seq.OFF_PROJECT_RECOVERY_STAGE
CLEAN=0;CLOSING=1;READY=2;RETRY=3;READ_OK=4;NEW_OK=5;DEAD=6
HOOKS=((SITE,EXPECTED,'read_result'),(PAD_SITE,PAD_EXPECTED,'pad'),
       (RELEASE_SITE,RELEASE_EXPECTED,'release'),(NEW_SITE,NEW_EXPECTED,'new'),
       (APPLY_SITE,APPLY_EXPECTED,'apply'),(BUTTON_SITE,BUTTON_EXPECTED,'button_busy'))

def arm_code(seq_state,ram_limit):
    a=Asm(CODE_BASE);E=a.emit;fixups=[]
    def bc(label,condition):E(b_cond_w,label,condition)
    def ram(reg,size,fail,tmp=1):
        assert reg!=tmp
        E(movs_imm,tmp,3);E(tst_reg,reg,tmp);bc(fail,'ne')
        a.imm32(tmp,0x20000000);E(cmp_reg,reg,tmp);bc(fail,'lo')
        a.imm32(tmp,ram_limit-size);E(cmp_reg,reg,tmp);bc(fail,'hi')
    def ptr(reg,label):
        name='ptr_'+str(len(fixups));a.label(name);a.imm32(reg,0);fixups.append((name,reg,label))
    def context(fail):
        for code in ('eff30581','eff31081','eff31181'):
            E(raw,bytes.fromhex(code));E(cmp_imm,1,0);bc(fail,'ne')
    def read(obj,offset,index,fail):
        E(ldr_w,0,obj,offset);E(movs_imm,1,index);E(bl,'word')
        E(cmp_imm,1,1);bc(fail,'ne')
    def byte0():E(movs_imm,1,255);E(ands_reg,0,1)
    def stage(value):E(movs_imm,1,value);E(strb_w,1,6,STAGE)
    def return32():E(pop,[0,1,2,3,4,5,6],pc=True)
    def native32(label,expected,site):
        a.label(label);E(pop,[0,1,2,3,4,5,6],lr=True);E(raw,expected);E(b_w,site+4)

    a.label('read_result');E(push,[0,1,2,3,4,5,6],lr=True)
    E(ldr_sp,4,36);ram(4,4,'read_native');E(ldr_imm,5,4);ram(5,12,'read_native')
    E(ldr_imm,1,5);a.imm32(2,PROJECT_LOAD_VTABLE);E(cmp_reg,1,2);bc('read_native','ne')
    E(ldr_imm,1,5,8);E(ldr_sp,2,12);E(cmp_reg,1,2);bc('read_native','ne')
    E(subs_imm8,5,12);ram(5,0xE4,'read_native')
    E(bl,seq_state);E(cmp_imm,0,0);bc('read_no_state','eq');E(mov_reg,6,0)
    E(ldr_sp,0,8);E(cmp_imm,0,0);bc('read_failed','ne')
    E(ldrb_w,0,6,seq.OFF_PROJECT_TAINTED);E(cmp_imm,0,0);bc('read_native','eq')
    E(ldr_imm,0,6,OWNER);E(cmp_reg,0,5);bc('read_failed','ne')
    E(ldr_imm,0,6,BRIDGE);E(cmp_reg,0,4);bc('read_failed','ne')
    E(ldrb_w,0,6,STAGE);E(cmp_imm,0,RETRY);bc('read_failed','ne')
    E(mov_reg,0,5);E(bl,'operation_matches');E(cmp_imm,0,1);bc('read_failed','ne')
    stage(READ_OK);E(b_w,'read_native')
    a.label('read_failed');E(movs_imm,1,1);E(strb_w,1,6,seq.OFF_PROJECT_TAINTED)
    E(str_imm,5,6,OWNER);E(str_imm,4,6,BRIDGE)
    E(ldr_sp,0,0);ram(0,12,'read_dead')
    for off in (0,4,8):E(ldr_imm,1,0,off);E(str_imm,1,6,DESCRIPTOR+off)
    E(ldr_imm,2,6,EPOCH);E(adds_imm8,2,1);bc('read_dead','eq');E(str_imm,2,6,EPOCH)
    stage(CLOSING);E(movs_imm,1,0);E(str_imm,1,4)
    ptr(1,'close_done');E(bl,NATIVE_CLOSE);E(cmp_imm,0,0);bc('read_exit','eq')
    a.label('read_dead');stage(DEAD);E(movs_imm,1,0);E(str_imm,1,4)
    a.label('read_exit');return32()
    a.label('read_no_state');E(ldr_sp,0,8);E(cmp_imm,0,0);bc('read_native','eq')
    E(movs_imm,1,0);E(str_imm,1,4);E(movs_imm,2,0);E(ldr_sp,0,0);E(bl,NATIVE_CLOSE);return32()
    native32('read_native',EXPECTED,SITE)

    # Native2B064 supplies descriptor/result and arg6 cookie at entry SP+4.
    a.label('close_done');E(push,[0,1,2,3,4,5,6],lr=True);context('close_exit')
    E(bl,seq_state);E(cmp_imm,0,0);bc('close_exit','eq');E(mov_reg,6,0)
    E(ldrb_w,0,6,STAGE);E(cmp_imm,0,CLOSING);bc('close_exit','ne')
    E(ldrb_w,0,6,seq.OFF_PROJECT_TAINTED);E(cmp_imm,0,1);bc('close_exit','ne')
    E(ldr_sp,0,36);E(ldr_imm,1,6,EPOCH);E(cmp_reg,0,1);bc('close_exit','ne')
    E(ldr_sp,4,0);ram(4,12,'close_exit')
    for off in (0,4,8):
        E(ldr_imm,0,4,off);E(ldr_imm,1,6,DESCRIPTOR+off);E(cmp_reg,0,1);bc('close_exit','ne')
    E(ldr_sp,0,8);E(cmp_imm,0,0);bc('close_failed','ne')
    stage(READY);E(b_w,'close_exit')
    a.label('close_failed');stage(DEAD)
    a.label('close_exit');return32()

    a.label('pad');E(push,[0,1,2,3,4,5,6],lr=True)
    E(bl,seq_state);E(cmp_imm,0,0);bc('pad_native','eq');E(mov_reg,6,0)
    E(ldrb_w,0,6,seq.OFF_PROJECT_TAINTED);E(cmp_imm,0,0);bc('pad_native','eq')
    context('pad_exit');E(raw,bytes.fromhex('72b6')) # checked unmasked thread; serialize admission
    E(ldr_sp,0,0);E(ldr_sp,1,4);E(bl,'admit');E(cmp_imm,0,0);bc('pad_unlock','eq')
    E(mov_reg,4,0);E(mov_reg,5,1)
    E(ldr_sp,0,0);E(adds_imm8,0,0x9C);E(ldr_sp,1,4);E(bl,PAD_DOWN)
    E(cmp_imm,0,0);bc('pad_unlock','ne')
    E(ldr_sp,0,0);E(str_imm,0,6,HELD);E(str_imm,5,6,SLOT);stage(RETRY)
    E(raw,bytes.fromhex('62b6')) # native I/O runs outside the serialized section
    E(mov_reg,0,4);E(mov_reg,1,5);E(movs_imm,2,1);E(bl,NATIVE_LOAD)
    E(b_w,'pad_exit')
    a.label('pad_unlock');E(raw,bytes.fromhex('62b6'))
    a.label('pad_exit');return32()
    native32('pad_native',PAD_EXPECTED,PAD_SITE)

    # Retire actual native pad ownership on physical release, including busy.
    a.label('release');E(push,[0,1,2,3,4,5,6],lr=True)
    E(bl,seq_state);E(cmp_imm,0,0);bc('release_native','eq');E(mov_reg,6,0)
    context('release_native');E(ldr_sp,4,0);E(ldr_sp,5,4)
    ram(4,0xA0,'release_native');E(cmp_imm,5,32);bc('release_native','hs')
    E(ldr_imm,0,4);a.imm32(1,CONTROLLER_VTABLE);E(cmp_reg,0,1);bc('release_native','ne')
    E(ldr_imm,0,6,HELD);E(cmp_reg,0,4);bc('release_busy_projects','ne')
    E(ldr_imm,0,6,SLOT);E(movs_imm,1,31);E(ands_reg,0,1)
    E(cmp_reg,0,5);bc('release_busy_projects','ne');E(mov_reg,1,5)
    E(mov_reg,0,4);E(adds_imm8,0,0x9C);E(bl,PAD_UP)
    E(movs_imm,0,0);E(str_imm,0,6,HELD);return32()
    # Original stock Load also sets controller ownership before going busy.
    # Do not drop its real pad-up while waiting for an eventual read failure.
    a.label('release_busy_projects');read(4,0x14,0,'release_native');byte0()
    E(cmp_imm,0,6);bc('release_native','ne')
    read(4,0x8C,0,'release_native');E(movs_imm,1,2);E(tst_reg,0,1);bc('release_native','eq')
    E(mov_reg,1,5);E(mov_reg,0,4);E(adds_imm8,0,0x9C);E(bl,PAD_UP);return32()
    native32('release_native',RELEASE_EXPECTED,RELEASE_SITE)

    a.label('new');E(push,[0,1,2,3,4,5,6],lr=True)
    E(bl,seq_state);E(cmp_imm,0,0);bc('new_native','eq');E(mov_reg,6,0)
    E(ldrb_w,0,6,seq.OFF_PROJECT_TAINTED);E(cmp_imm,0,0);bc('new_native','eq')
    E(ldr_sp,5,4);E(ldr_imm,0,6,OWNER);E(cmp_reg,0,5);bc('new_exit','ne')
    E(ldrb_w,0,6,STAGE);E(cmp_imm,0,RETRY);bc('new_exit','ne')
    E(mov_reg,0,5);E(bl,'operation_matches');E(cmp_imm,0,1);bc('new_exit','ne')
    stage(NEW_OK);E(b_w,'new_native')
    a.label('new_exit');return32()
    native32('new_native',NEW_EXPECTED,NEW_SITE)

    a.label('apply');E(push,[4,5,6],lr=True);E(mov_reg,5,0)
    E(bl,seq_state);E(cmp_imm,0,0);bc('apply_stock','eq');E(mov_reg,6,0)
    E(ldrb_w,0,6,seq.OFF_PROJECT_TAINTED);E(cmp_imm,0,0);bc('apply_stock','eq')
    E(ldr_imm,0,6,OWNER);E(cmp_reg,0,5);bc('apply_exit','ne')
    E(ldrb_w,4,6,STAGE);E(cmp_imm,4,READ_OK);bc('apply_authorized','eq')
    E(cmp_imm,4,NEW_OK);bc('apply_exit','ne')
    a.label('apply_authorized');context('apply_exit')
    E(mov_reg,0,5);E(bl,'operation_matches');E(cmp_imm,0,1);bc('apply_exit','ne')
    E(mov_reg,0,5);E(bl,'apply_native')
    a.label('apply_return')
    E(ldrb_w,0,6,STAGE);E(cmp_reg,0,4);bc('apply_exit','ne')
    read(5,0x48,1,'apply_exit');byte0();E(cmp_imm,0,0);bc('apply_exit','ne')
    read(5,0x4C,0,'apply_exit');E(movs_imm,1,3);E(tst_reg,0,1);bc('apply_exit','ne')
    read(5,0x44,11,'apply_exit');byte0();E(ldr_imm,1,6,SLOT);E(cmp_reg,0,1);bc('apply_exit','ne')
    stage(CLEAN);E(movs_imm,1,0);E(str_imm,1,6,OWNER);E(str_imm,1,6,BRIDGE)
    E(strb_w,1,6,seq.OFF_PROJECT_TAINTED);E(b_w,'apply_exit')
    a.label('apply_stock');E(mov_reg,0,5);E(bl,'apply_native')
    a.label('apply_exit');E(pop,[4,5,6],pc=True)
    a.label('apply_native');E(raw,APPLY_EXPECTED);E(b_w,APPLY_SITE+4)

    # The stock busy-button BNE also blocks Projects Up/Down. Keep its EQ
    # path exactly; only Close-confirmed stopped/unheld recovery may admit
    # buttons19/20 to the original controller/Projects handler. No fake idle.
    a.label('button_busy');bc('button_stock','eq')
    E(push,[0,1,2,3,4,5,6],lr=True)
    E(cmp_imm,5,19);bc('button_check','eq')
    E(cmp_imm,5,20);bc('button_blocked','ne')
    a.label('button_check');context('button_blocked')
    E(bl,seq_state);E(cmp_imm,0,0);bc('button_blocked','eq');E(mov_reg,6,0)
    E(ldrb_w,0,6,seq.OFF_PROJECT_TAINTED);E(cmp_imm,0,1);bc('button_blocked','ne')
    E(raw,bytes.fromhex('72b6'))
    E(mov_reg,0,4);E(movs_imm,1,0);E(bl,'admit');E(cmp_imm,0,0)
    E(raw,bytes.fromhex('62b6'));bc('button_blocked','eq')
    E(pop,[0,1,2,3,4,5,6],lr=True)
    a.label('button_stock');E(b_w,BUTTON_CONTINUE)
    a.label('button_blocked');E(pop,[0,1,2,3,4,5,6],lr=True);E(b_w,BUTTON_REJECT)

    # Checked active-bank read: return r0=value,r1=valid.
    a.label('word');E(push,[4],lr=True);E(mov_reg,4,1);ram(0,20,'word_no')
    E(ldrb_w,1,0,0);E(cmp_reg,1,4);bc('word_no','ls');E(cmp_imm,1,32);bc('word_no','hi')
    E(mov_reg,1,4);E(bl,READ_WORD);ram(0,4,'word_no')
    E(ldr_imm,0,0);E(movs_imm,1,1);E(pop,[4],pc=True)
    a.label('word_no');E(movs_imm,0,0);E(movs_imm,1,0);E(pop,[4],pc=True)
    a.label('operation_matches');E(push,[4],lr=True);E(mov_reg,4,0)
    ram(4,0xE4,'op_no');read(4,0x48,0,'op_no')
    E(mov_reg,2,0);E(movs_imm,1,255);E(ands_reg,2,1);E(cmp_imm,2,4);bc('op_no','ne')
    E(lsrs_imm,0,0,8);byte0();a.imm32(1,seq.SEQ_STATE_ADDR+SLOT);E(ldr_imm,1,1)
    E(cmp_reg,0,1);bc('op_no','ne');E(movs_imm,0,1);E(pop,[4],pc=True)
    a.label('op_no');E(movs_imm,0,0);E(pop,[4],pc=True)

    # Read-only admission, bounded by four RX contexts/eight tracks/32 bits.
    a.label('admit');E(push,[4,5,6,7],lr=True);E(sub_sp_imm,4)
    E(mov_reg,4,0);E(mov_reg,5,1);a.imm32(6,seq.SEQ_STATE_ADDR)
    E(cmp_imm,5,32);bc('admit_no','hs')
    ram(4,0x1E0,'admit_no');E(ldr_imm,0,4);a.imm32(1,CONTROLLER_VTABLE);E(cmp_reg,0,1);bc('admit_no','ne')
    E(ldrb_w,0,6,STAGE);E(cmp_imm,0,READY);bc('admit_no','ne')
    E(ldr_imm,0,6,HELD);E(cmp_imm,0,0);bc('admit_no','ne')
    E(ldr_w,0,4,0x9C);E(cmp_imm,0,0);bc('admit_no','ne')
    E(ldr_imm,7,6,OWNER);ram(7,0xE4,'admit_no')
    E(ldr_imm,0,7);a.imm32(1,PROJECT_VTABLE);E(cmp_reg,0,1);bc('admit_no','ne')
    E(ldr_imm,0,7,0x64);E(ldr_imm,1,6,BRIDGE);E(cmp_reg,0,1);bc('admit_no','ne')
    ram(0,4,'admit_no');E(ldr_imm,0,0);E(cmp_imm,0,0);bc('admit_no','ne')
    for off,want in ((0xC,0),(0x14,6),(0x18,0)):
        read(4,off,0,'admit_no');byte0();E(cmp_imm,0,want);bc('admit_no','ne')
    read(7,0x48,1,'admit_no');byte0();E(cmp_imm,0,2);bc('admit_no','ne')
    read(7,0x4C,0,'admit_no');E(movs_imm,1,3);E(ands_reg,0,1);E(cmp_imm,0,3);bc('admit_no','ne')
    E(ldr_imm,7,4,0x50);ram(7,0x38,'admit_no');E(ldr_imm,2,6,OWNER)
    for left,right in ((0x20,0x44),(0x28,0x48)):
        E(ldr_imm,0,7,left);E(ldr_imm,1,2,right);E(cmp_reg,0,1);bc('admit_no','ne')
    read(7,0x24,0,'admit_no');E(movs_imm,1,8);E(tst_reg,0,1);bc('admit_no','eq')
    for off in (0x18,0x1C,0x2C):
        read(7,off,0,'admit_no');byte0();E(cmp_imm,0,0);bc('admit_no','ne')
    E(ldrb_w,0,7,0x36);E(cmp_imm,0,1);bc('admit_no','hi')
    E(lsls_imm,0,0,5);E(adds_reg,5,5,0)
    for off in (seq.OFF_MIDI_CONTEXT_FAULT,seq.OFF_MIDI_ACTIVE_CALLS,seq.OFF_MIDI_TX_FAULT):
        E(ldrb_w,0,6,off);E(cmp_imm,0,0);bc('admit_no','ne')
    E(movs_imm,7,seq.OFF_MIDI_RECEIVERS)
    a.label('rx_owner');E(ldr_reg,0,6,7);E(cmp_imm,0,0);bc('rx_next','eq')
    ram(0,0x114,'admit_no');E(adds_imm8,0,0x74);E(movs_imm,3,40)
    a.label('rx_word');E(ldr_imm,1,0);E(cmp_imm,1,0);bc('admit_no','ne')
    E(adds_imm8,0,4);E(subs_imm8,3,1);bc('rx_word','ne')
    a.label('rx_next');E(adds_imm8,7,4);E(cmp_imm,7,0x78);bc('rx_owner','ne')
    E(mov_reg,7,4);E(adds_imm8,7,0xE0);E(adds_imm8,7,0xE0);E(movs_imm,6,8)
    a.label('notes');read(7,0,0,'admit_no');E(cmp_imm,0,0);bc('admit_no','ne')
    E(adds_imm8,7,4);E(subs_imm8,6,1);bc('notes','ne')
    E(ldr_imm,7,4,0x3C);ram(7,0x26C,'admit_no');E(ldr_w,0,7,0x228);E(cmp_imm,0,0);bc('admit_no','ne')
    E(adds_imm8,7,0x74);E(movs_imm,6,8)
    a.label('views');E(ldr_imm,0,7);E(cmp_imm,0,0);bc('view_next','eq')
    ram(0,0xC4,'admit_no');E(ldr_w,1,0,0xC0);E(cmp_imm,1,0);bc('admit_no','ne')
    E(adds_imm8,0,0x74);E(movs_imm,3,32)
    a.label('held_bits');E(ldrh_imm,1,0);E(movs_imm,2,8);E(tst_reg,1,2);bc('admit_no','ne')
    E(adds_imm8,0,2);E(subs_imm8,3,1);bc('held_bits','ne')
    a.label('view_next');E(adds_imm8,7,4);E(subs_imm8,6,1);bc('views','ne')
    a.imm32(0,seq.SEQ_STATE_ADDR+OWNER);E(ldr_imm,0,0);E(mov_reg,1,5);E(b_w,'admit_exit')
    a.label('admit_no');E(movs_imm,0,0)
    a.label('admit_exit');E(add_sp_imm,4);E(pop,[4,5,6,7],pc=True)
    code,labels=a.assemble();code=bytearray(code)
    for name,reg,label in fixups:
        value=labels[label]|1;off=labels[name]-CODE_BASE
        code[off:off+8]=movw(reg,value&65535)+movt(reg,value>>16)
    code=bytes(code);code+=b'\x00\xbf'*(-len(code)%4//2)
    assert CODE_BASE%4==0 and CODE_BASE+len(code)<=CODE_LIMIT
    return code,labels

def build_patches(seq_state,ram_limit):
    code,labels=arm_code(seq_state,ram_limit)
    return [*(PatchHunk(site,expected,b_w(site,labels[name]),'project_recovery_'+name)
              for site,expected,name in HOOKS),
            PatchHunk(CODE_BASE,b'\xff'*len(code),code,'project_load_error_code')]
