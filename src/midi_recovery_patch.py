"""Integrated Off/Stop candidate profile;offline build only,not a hardware GO.

Reuses the tested bounded recovery core with a checked832B heap reservation,
native port constructor registration and actual flash vtable bindings. The
base Phase1 profile remains byte-identical. Recovery quarantines new musical
sends after a fault until reboot;it does not implement USB session recovery.
"""
import struct
import seq_Patch as seq
import midi_recovery_prototype as recovery
import midi_accepted_tx_patch as accepted
import flash_query_patch as flash_query
import midi_dense_stop_patch as dense_stop
import project_load_recovery_patch as load_guard
from patch_firmware import PatchHunk
from thumb_asm import Asm,b_w,b_cond_w,bl,bx_lr,cmp_imm,cmp_reg,ldr_imm,ldrb_imm,ldrh_imm,mov_reg,movs_imm,movw,movt,pop,push,raw,str_imm,strb_imm,strb_w,strh_imm

CORE_BASE,GLUE_BASE=0x0807D400,0x0807E400
STATE_SIZE=recovery.STATE_SIZE
STATE_BASE=seq.SEQ_STATE_ADDR-STATE_SIZE
VTABLE=0x08068AA8
CTOR=0x0804016C
CTOR_ENTRY=bytes.fromhex('38b50446')
PARENT_CLEAR_CALL=0x08068A32
PARENT_CLEAR_EXPECTED=bytes.fromhex('c0f7c5fe')
USB_FLUSH=0x0802B498
USB_FLUSH_EXPECTED=bytes.fromhex('38b50446')
USB_NO_CREDIT=0x080268CC
USB_NO_CREDIT_EXPECTED=bytes.fromhex('71bc7047')
FLUSH_BUSY=11 # unused byte in the existing zero-initialized USB recovery entry
OPTIONS=dict(extra_reserved_bytes=STATE_SIZE,extra_state_magic=recovery.MAGIC,allocator_fail_stop=True)


def seq_code():return seq.arm_code(**OPTIONS)


def arm_code():
    core,rp=recovery.arm_code(base=CORE_BASE,state=STATE_BASE)
    assert CORE_BASE%4==GLUE_BASE%4==STATE_BASE%4==0
    assert CORE_BASE+len(core)<=GLUE_BASE
    _,sq=seq_code();_,tg=accepted.arm_code(STATE_BASE,FLUSH_BUSY);a=Asm(GLUE_BASE);E=a.emit;fixups=[]
    def imm(r,v):a.imm32(r,v)
    def bc(name,condition):E(b_cond_w,name,condition)
    def ptr(r,label):
        name='pointer_'+str(len(fixups));a.label(name);imm(r,0);fixups.append((name,r,label))
    def ram(r,size,failure):
        E(movs_imm,1,3);E(raw,bytes.fromhex('0c42') if r==4 else bytes.fromhex('0d42') if r==5 else bytes.fromhex('0e42'))
        bc(failure,'ne');imm(1,0x20000000);E(cmp_reg,r,1);bc(failure,'lo')
        imm(1,STATE_BASE-size);E(cmp_reg,r,1);bc(failure,'hi')
    a.label('ip_ctor');E(push,[4],lr=True);E(mov_reg,4,0)
    E(bl,'ip_native_ctor');E(bl,'ip_register');E(mov_reg,0,4);E(pop,[4],pc=True)
    a.label('ip_native_ctor');E(raw,CTOR_ENTRY);E(b_w,CTOR+4)

    a.label('ip_register');E(push,[3,4,5,6,7],lr=True);E(mov_reg,4,0)
    E(bl,sq['c_seq_state']);E(cmp_imm,0,0);bc('register_no','eq')
    E(movs_imm,1,3);E(raw,bytes.fromhex('0c42')) # tst r4,r1
    bc('register_fault','ne');imm(1,0x20000000);E(cmp_reg,4,1);bc('register_fault','lo')
    imm(1,STATE_BASE-24);E(cmp_reg,4,1);bc('register_fault','hi')
    E(ldr_imm,1,4);imm(2,VTABLE);E(cmp_reg,1,2);bc('register_fault','ne')
    imm(5,STATE_BASE);E(ldr_imm,1,5);imm(2,recovery.MAGIC);E(cmp_reg,1,2);bc('register_fault','ne')
    E(raw,bytes.fromhex('eff31087 72b6')) # preserve PRIMASK,serialize port publication
    for n in range(3):
        imm(6,STATE_BASE+recovery.HEADER_SIZE+n*recovery.ENTRY_SIZE)
        E(ldr_imm,1,6);E(cmp_reg,1,4);bc('register_ok','eq')
        E(cmp_imm,1,0);bc('register_store','eq')
    E(raw,bytes.fromhex('87f31088'));E(b_w,'register_fault')
    a.label('register_store');E(str_imm,4,6)
    a.label('register_ok');E(raw,bytes.fromhex('87f31088'));E(movs_imm,0,1);E(pop,[3,4,5,6,7],pc=True)
    a.label('register_fault');imm(0,seq.SEQ_STATE_ADDR);E(movs_imm,1,1);E(strb_w,1,0,seq.OFF_MIDI_TX_FAULT)
    a.label('register_no');E(movs_imm,0,0);E(pop,[3,4,5,6,7],pc=True)

    # Keep the existing sticky mode-admission fault in sync with recovery's
    # quarantine,including driver-not-ready and nested-send failures.
    a.label('ip_latch');imm(0,STATE_BASE);E(ldr_imm,1,0);imm(2,recovery.MAGIC)
    E(cmp_reg,1,2);bc('latch_fault','ne')
    for n in range(3):
        imm(0,STATE_BASE+recovery.HEADER_SIZE+n*recovery.ENTRY_SIZE)
        E(ldrb_imm,1,0,recovery.FLAGS);E(movs_imm,2,recovery.FAULT);E(raw,bytes.fromhex('1142'))
        bc('latch_fault','ne')
    E(bx_lr)
    a.label('latch_fault');imm(0,seq.SEQ_STATE_ADDR);E(movs_imm,1,1);E(strb_w,1,0,seq.OFF_MIDI_TX_FAULT);E(bx_lr)
    for name,target in (('ip_send','rp_send'),('ip_poll','rp_poll'),('ip_sysex_send','rp_sysex_send'),('ip_sysex_pending','rp_sysex_pending')):
        a.label(name);E(push,[4,5],lr=True);E(raw,bytes.fromhex('81b0')) #16B frame incl alignment word
        if name=='ip_poll':
            E(mov_reg,4,0);E(bl,'ip_usb_preflush');E(mov_reg,0,4);E(bl,tg['tg_pause'])
            E(cmp_imm,0,0);bc('poll_closed','ne');E(mov_reg,0,4)
            E(bl,rp[target]);E(mov_reg,5,0);E(b_w,'poll_latch')
            a.label('poll_closed');E(movs_imm,5,1);a.label('poll_latch')
        else:E(bl,rp[target]);E(mov_reg,5,0)
        E(bl,'ip_latch');E(mov_reg,0,5)
        E(raw,bytes.fromhex('01b0'));E(pop,[4,5],pc=True)

    # Bind only the actual global boot router on first SysEx submission.
    a.label('ip_router');E(push,[0,1,2,3,4],lr=True)
    imm(3,0x20006F04);E(ldr_imm,3,3);E(cmp_reg,0,3);bc('router_no','ne')
    imm(3,STATE_BASE);E(ldr_imm,1,3);imm(2,recovery.MAGIC);E(cmp_reg,1,2);bc('router_no','ne')
    E(raw,bytes.fromhex('eff31084 72b6'))
    E(ldr_imm,1,3,recovery.ROUTER);E(cmp_imm,1,0);bc('router_store','eq')
    E(cmp_reg,1,0);bc('router_unlock_no','ne')
    a.label('router_store');E(str_imm,0,3,recovery.ROUTER);E(raw,bytes.fromhex('84f31088'))
    E(pop,[0,1,2,3,4],lr=True);E(b_w,rp['rp_sysex_route'])
    a.label('router_unlock_no');E(raw,bytes.fromhex('84f31088'))
    a.label('router_no');E(pop,[0,1,2,3,4],lr=True);E(movs_imm,0,1);E(bx_lr)

    # MIDI class re-init used to clear all output FIFOs/cursors here. Preserve
    # the registered boot router's software owners,including DIN and a busy
    # native worker. This read-only gate is specific to the actual parent BL;
    # ordinary router/port clears retain stock behavior. No hardware reader is
    # retired and no USB buffer,availability counter or epoch is modified.
    a.label('ip_parent_clear');E(push,[4,5,6],lr=True);E(mov_reg,4,0)
    E(mov_reg,1,14);imm(2,PARENT_CLEAR_CALL+5);E(cmp_reg,1,2);bc('parent_native','ne')
    imm(1,0x20006F04);E(ldr_imm,1,1);E(cmp_reg,4,1);bc('parent_native','ne')
    E(movs_imm,1,3);E(raw,bytes.fromhex('0c42'));bc('parent_native','ne')
    imm(1,0x20000000);E(cmp_reg,4,1);bc('parent_native','lo')
    imm(1,STATE_BASE-0x28);E(cmp_reg,4,1);bc('parent_native','hi')
    imm(0,STATE_BASE);E(ldr_imm,1,0);imm(2,recovery.MAGIC);E(cmp_reg,1,2);bc('parent_native','ne')
    E(ldrb_imm,1,4,0x18);E(cmp_imm,1,3);bc('parent_native','ne')
    E(ldr_imm,5,4,0x14);E(movs_imm,1,3);E(raw,bytes.fromhex('0d42'));bc('parent_native','ne')
    imm(1,0x20000000);E(cmp_reg,5,1);bc('parent_native','lo')
    imm(1,STATE_BASE-12);E(cmp_reg,5,1);bc('parent_native','hi')
    for n in range(3):
        imm(6,STATE_BASE+recovery.HEADER_SIZE+n*recovery.ENTRY_SIZE)
        E(ldr_imm,1,6);E(cmp_imm,1,0);bc('parent_native','eq')
        E(ldr_imm,2,5,n*4);E(cmp_reg,1,2);bc('parent_native','ne')
    E(mov_reg,0,4);E(pop,[4,5,6],pc=True)
    a.label('parent_native');E(mov_reg,0,4);E(pop,[4,5,6],lr=True);E(b_w,0x080297C0)
    a.label('parent_end')

    # Only the registered first (USB) output driver is eligible. No caller
    # pointer is dereferenced before the stored native port matches it.
    a.label('ip_usb_owner');imm(3,STATE_BASE);E(ldr_imm,1,3);imm(2,recovery.MAGIC)
    E(cmp_reg,1,2);bc('usb_owner_no','ne')
    E(ldr_imm,1,3,recovery.HEADER_SIZE);E(cmp_imm,1,0);bc('usb_owner_no','eq')
    E(ldr_imm,2,1,0x14);E(cmp_reg,0,2);bc('usb_owner_no','ne')
    imm(0,STATE_BASE+recovery.HEADER_SIZE);E(bx_lr)
    a.label('usb_owner_no');E(movs_imm,0,0);E(bx_lr)

    # A retained full MAIN otherwise makes native402FC return before flush.
    # Reuse the core port lease;do not run hardware submission in IRQ/masked
    # contexts. The normal core poll still owns all queue/deferred processing.
    a.label('ip_usb_preflush');E(push,[3,4,5],lr=True);E(mov_reg,4,0)
    E(raw,bytes.fromhex('eff30581'));E(cmp_imm,1,0);bc('preflush_return','ne') # IPSR
    imm(5,STATE_BASE);E(ldr_imm,1,5);imm(2,recovery.MAGIC);E(cmp_reg,1,2);bc('preflush_return','ne')
    E(ldr_imm,1,5,recovery.HEADER_SIZE);E(cmp_reg,4,1);bc('preflush_return','ne')
    imm(5,STATE_BASE+recovery.HEADER_SIZE);E(mov_reg,0,5);E(bl,rp['rp_begin'])
    E(cmp_imm,0,0);bc('preflush_return','eq')
    E(bl,tg['tg_service'])
    E(ldr_imm,0,4,0x14);E(ldrb_imm,1,0,0x14);E(cmp_imm,1,0);bc('preflush_release','ne')
    E(ldr_imm,1,0,8);E(ldr_imm,2,0,0x18);E(cmp_reg,1,2);bc('preflush_release','ne')
    E(bl,'ip_usb_flush')
    a.label('preflush_release');E(mov_reg,0,5);E(bl,rp['rp_end'])
    a.label('preflush_return');E(pop,[3,4,5],pc=True)

    a.label('ip_usb_flush');E(push,[3,4,5,6,7],lr=True);E(mov_reg,4,0)
    E(bl,'ip_usb_owner');E(cmp_imm,0,0);bc('flush_foreign','eq');E(mov_reg,7,0)
    E(bl,tg['tg_blocked']);E(cmp_imm,0,0);bc('flush_hold','ne')
    E(raw,bytes.fromhex('eff30581'));E(cmp_imm,1,0);bc('flush_hold','ne')
    E(raw,bytes.fromhex('eff31081'));E(cmp_imm,1,0);bc('flush_hold','ne')
    # Serialize only the flush owner byte;the native submit runs unmasked.
    E(raw,bytes.fromhex('eff31083 72b6'));E(ldrb_imm,1,7,FLUSH_BUSY);E(cmp_imm,1,0);bc('flush_busy','ne')
    E(movs_imm,1,1);E(strb_imm,1,7,FLUSH_BUSY);E(raw,bytes.fromhex('83f31088'))
    E(ldr_imm,0,4);imm(1,0x08068CA4);E(cmp_reg,0,1);bc('flush_release_hold','ne')
    E(ldr_imm,5,4,4);ram(5,8,'flush_release_hold')
    E(ldr_imm,0,5);imm(1,0x0806919C);E(cmp_reg,0,1);bc('flush_release_hold','ne')
    E(ldr_imm,6,5,4);ram(6,0x24,'flush_release_hold')
    E(ldrb_imm,0,6);E(cmp_imm,0,0x81);bc('flush_release_hold','ne')
    E(ldrh_imm,0,6,2);E(cmp_imm,0,64);bc('flush_release_hold','ne')
    E(ldr_imm,5,6,0x10);ram(5,0x29C,'flush_release_hold')
    E(mov_reg,0,4);E(bl,0x0802B4D8);E(cmp_imm,0,0);bc('flush_release_hold','eq')
    E(ldrb_imm,0,4,0x14);E(cmp_imm,0,0);bc('flush_release_native','ne')
    E(ldr_imm,5,4,8);ram(5,8,'flush_release_hold')
    E(ldr_imm,0,4,0x18);E(cmp_reg,0,5);bc('flush_release_native','ne')
    E(ldrh_imm,2,5);E(cmp_imm,2,0);bc('flush_release_hold','eq')
    E(cmp_imm,2,64);bc('flush_release_hold','hi')
    E(movs_imm,1,3);E(raw,bytes.fromhex('0a42'));bc('flush_release_hold','ne') # tst r2,r1
    E(ldr_imm,0,5,4);E(mov_reg,1,0);E(mov_reg,0,6)
    E(bl,tg['tg_prepare']);E(cmp_imm,0,0);bc('flush_release_hold','eq')
    E(ldr_imm,1,5,4);E(ldrh_imm,2,5);E(mov_reg,0,6)
    E(bl,0x08026880);a.label('usb_submit_return');E(bl,tg['tg_finish']);E(cmp_imm,0,0);bc('flush_release_hold','ne')
    E(ldr_imm,0,4,0x18);E(cmp_reg,0,5);bc('flush_release_hold','ne')
    E(movs_imm,0,0);E(strh_imm,0,5);E(movs_imm,4,1);E(b_w,'flush_release')
    a.label('flush_release_hold');E(movs_imm,4,0)
    a.label('flush_release');E(raw,bytes.fromhex('eff31083 72b6'));E(movs_imm,1,0);E(strb_imm,1,7,FLUSH_BUSY);E(raw,bytes.fromhex('83f31088'))
    E(mov_reg,0,4);E(pop,[3,4,5,6,7],pc=True)
    a.label('flush_busy');E(raw,bytes.fromhex('83f31088'))
    a.label('flush_hold');E(movs_imm,0,0);E(pop,[3,4,5,6,7],pc=True)
    a.label('flush_release_native');E(raw,bytes.fromhex('eff31083 72b6'));E(movs_imm,1,0);E(strb_imm,1,7,FLUSH_BUSY);E(raw,bytes.fromhex('83f31088'))
    a.label('flush_foreign');E(mov_reg,0,4);E(pop,[3,4,5,6,7],lr=True);E(b_w,'ip_native_usb_flush')
    a.label('ip_native_usb_flush');E(raw,USB_FLUSH_EXPECTED);E(b_w,USB_FLUSH+4)

    # Native26880's zero-credit branch normally has no R0 contract. Only our
    # pinned BL gets a nonzero rejection result;the native16B frame is retired
    # identically. Stock4301A/2C9B8 successful CPU submission returns zero.
    a.label('ip_usb_nocredit');E(mov_reg,1,14);ptr(2,'usb_submit_return');E(cmp_reg,1,2);bc('nocredit_native','ne')
    E(pop,[3,4,5,6]);E(movs_imm,0,1);E(bx_lr)
    a.label('nocredit_native');E(raw,USB_NO_CREDIT_EXPECTED)
    glue,labels=a.assemble();glue=bytearray(glue)
    for name,r,label in fixups:
        value=labels[label]|1;off=labels[name]-GLUE_BASE;glue[off:off+8]=movw(r,value&65535)+movt(r,value>>16)
    glue=bytes(glue);glue+=b'\x00\xbf'*(-len(glue)%4//2)
    assert GLUE_BASE+len(glue)<=accepted.CODE_BASE
    return core,rp,glue,labels


def build_patches():
    core,rp,glue,ip=arm_code()
    tx,tg=accepted.arm_code(STATE_BASE,FLUSH_BUSY)
    patches=seq.build_phase1_patches(**OPTIONS)
    patches.extend([
        PatchHunk(CTOR,CTOR_ENTRY,b_w(CTOR,ip['ip_ctor']),'recovery_native_port_registration'),
        PatchHunk(VTABLE+8,struct.pack('<I',0x080401FF),struct.pack('<I',ip['ip_send']|1),'recovery_short_send'),
        PatchHunk(VTABLE+12,struct.pack('<I',0x08040233),struct.pack('<I',ip['ip_sysex_send']|1),'recovery_sysex_send'),
        PatchHunk(VTABLE+16,struct.pack('<I',0x0804028D),struct.pack('<I',ip['ip_sysex_pending']|1),'recovery_sysex_pending'),
        PatchHunk(VTABLE+20,struct.pack('<I',0x080402B5),struct.pack('<I',ip['ip_poll']|1),'recovery_native_port_poll'),
        PatchHunk(recovery.NATIVE_ROUTER,recovery.ROUTER_PROLOGUE,b_w(recovery.NATIVE_ROUTER,ip['ip_router']),'recovery_router_owner'),
        PatchHunk(recovery.ROUTER_WAIT,recovery.ROUTER_WAIT_BYTES,b_w(recovery.ROUTER_WAIT,recovery.ROUTER_FAILURE),'recovery_router_bounded_wait'),
        PatchHunk(PARENT_CLEAR_CALL,PARENT_CLEAR_EXPECTED,bl(PARENT_CLEAR_CALL,ip['ip_parent_clear']),'recovery_parent_preserves_software_owners'),
        PatchHunk(USB_FLUSH,USB_FLUSH_EXPECTED,b_w(USB_FLUSH,ip['ip_usb_flush']),'recovery_usb_preserves_rejected_main'),
        PatchHunk(USB_NO_CREDIT,USB_NO_CREDIT_EXPECTED,b_w(USB_NO_CREDIT,ip['ip_usb_nocredit']),'recovery_usb_checked_no_credit_result'),
        PatchHunk(accepted.FULL,accepted.FULL_BYTES,b_w(accepted.FULL,tg['tg_full']),'recovery_usb_active_job_full'),
        PatchHunk(accepted.DONE_SITE,accepted.DONE_BYTES,b_w(accepted.DONE_SITE,tg['tg_done'])+b'\x00\xBF','recovery_usb_owned_completion'),
        PatchHunk(accepted.CLOSE_SITE,accepted.CLOSE_BYTES,b_w(accepted.CLOSE_SITE,tg['tg_close_gate']),'recovery_usb_close_freeze'),
        PatchHunk(accepted.IRQ_SITE,accepted.IRQ_BYTES,b_w(accepted.IRQ_SITE,tg['tg_irq']),'recovery_usb_reset_irq_freeze'),
        PatchHunk(accepted.INIT_SITE,accepted.INIT_BYTES,b_w(accepted.INIT_SITE,tg['tg_init']),'recovery_usb_deferred_class_init'),
        PatchHunk(accepted.RESET_SITE,accepted.RESET_BYTES,b_w(accepted.RESET_SITE,tg['tg_reset_branch']),'recovery_usb_late_reset_freeze'),
        PatchHunk(CORE_BASE,b'\xFF'*len(core),core,'integrated_recovery_core'),
        PatchHunk(GLUE_BASE,b'\xFF'*len(glue),glue,'integrated_recovery_glue'),
        PatchHunk(accepted.CODE_BASE,b'\xFF'*len(tx),tx,'integrated_accepted_tx_guard')])
    assert accepted.CODE_BASE+len(tx)<=flash_query.CODE_BASE
    patches.extend(flash_query.build_patches())
    assert flash_query.CODE_BASE+len(flash_query.arm_code())<=dense_stop.CODE_BASE
    patches.extend(dense_stop.build_patches(STATE_BASE))
    patches.extend(load_guard.build_patches(seq_code()[1]['c_seq_state'],STATE_BASE))
    return patches
