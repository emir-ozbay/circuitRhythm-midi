"""EMULATION ONLY: preserve unsubmitted MIDI software debt across USB epochs.

The historical default requires idle staging. Optional staging=True also
retains native MAIN CPU-formatted bytes and an owned partial SysEx cursor,
consuming MAIN only after endpoint submission acquires a new TX ticket.
RX FIFO/parser/ledger and immutable software TX readers survive; hardware
still uses the full disable/ACK/drain/flush barrier. Ambiguous in-flight TX,
raw ALT mode and partial parser/held input do not receive staged carry.
"""
from capstone import Cs,CS_ARCH_ARM,CS_MODE_THUMB,CS_MODE_MCLASS
import midi_usb_task_prototype as task
import midi_usb_session_prototype as session
import midi_usb_lifecycle_prototype as life
import midi_usb_ledger_prototype as ledger
import midi_sysex_retry_prototype as retry
import midi_recovery_prototype as recovery
import midi_usb_control_prototype as control
import seq_Patch as seq
from thumb_asm import (Asm,adds_imm8,b,b_cond_w,b_w,bl,bx_lr,cmp_imm,cmp_reg,
    ldr_imm,ldr_w,ldr_sp,ldrb_imm,ldrb_w,ldrh_imm,mov_reg,movs_imm,pop,push,raw,
    str_imm,str_w,strb_imm,strh_imm,tst_reg)

CODE_BASE,STATE_BASE,STATE_SIZE=0x0807CC00,0x20048520,128
MAGIC=0x31595243
ACTIVE,BUSY,GENERATION,SEALS,RESUMES,RESUME_PENDING,REJECTED=4,8,12,16,20,24,28
FLUSH_BUSY=32  # staging=True only; default code generation is unchanged


def sites(staging=False):
    sc,ss=session.arm_code();_,lc=life.arm_code();rc,rp=recovery.arm_code()
    md=Cs(CS_ARCH_ARM,CS_MODE_THUMB|CS_MODE_MCLASS);md.detail=True
    candidates=[i.address-6 for i in md.disasm(sc[ss['step_flushed']-session.CODE_BASE:ss['seal_fail']-session.CODE_BASE],ss['step_flushed'])
                if i.mnemonic=='bl' and i.operands[0].imm==ss['ss_native_080401ac']]
    assert len(candidates)==1
    p=candidates[0];expected=sc[p-session.CODE_BASE:p-session.CODE_BASE+10]
    assert expected==movs_imm(0,1)+str_imm(0,4,session.BUSY)+ldr_imm(0,4,session.TX_PORT)+bl(p+6,ss['ss_native_080401ac'])
    resume=ss[f"ss_native_{lc['cl_resume']:08x}"]
    result={ss['ss_quiet']:(sc[ss['ss_quiet']-session.CODE_BASE:ss['ss_quiet']-session.CODE_BASE+6],'cy_quiet'),
            ss['ss_step']:(sc[ss['ss_step']-session.CODE_BASE:ss['ss_step']-session.CODE_BASE+6],'cy_step'),
            p:(expected,'cy_seal'),resume:(sc[resume-session.CODE_BASE:resume-session.CODE_BASE+6],'cy_resume'),
            rp['rp_poll']:(rc[rp['rp_poll']-recovery.CODE_BASE:rp['rp_poll']-recovery.CODE_BASE+6],'cy_poll')}
    if staging:result[0x0802B498]=(bytes.fromhex('38b50446'),'cy_flush')
    return result


def arm_code(base=CODE_BASE,state=STATE_BASE,staging=False):
    tc,ut=task.arm_code();sc,ss=session.arm_code();_,lc=life.arm_code();_,sq=seq.arm_code();_,rp=recovery.arm_code()
    hooks=sites(staging=staging);seal=next(p for p,(_,n) in hooks.items() if n=='cy_seal')
    resume=next(p for p,(_,n) in hooks.items() if n=='cy_resume')
    md=Cs(CS_ARCH_ARM,CS_MODE_THUMB|CS_MODE_MCLASS);md.detail=True
    callers=[i.address+4|1 for i in md.disasm(sc,session.CODE_BASE) if i.mnemonic=='bl' and i.operands[0].imm==resume]
    assert len(callers)==1;resume_lr=callers[0]
    if base!=CODE_BASE or state%4 or not task.STATE_BASE+task.STATE_SIZE<state<state+STATE_SIZE<=0x20048600:
        raise ValueError('Carry code/state exceeds registered bounds')
    if task.CODE_BASE+len(tc)>base:raise ValueError('Carry overlaps task code')
    a=Asm(base);E=a.emit
    def imm(r,v):a.imm32(r,v)
    def bc(l,c):E(b_cond_w,l,c)
    def field(o,r=0):E(ldr_imm,r,4,o)
    def put(o,r=0):E(str_imm,r,4,o)
    def mask():E(raw,bytes.fromhex('eff3108372b6'))
    def restore():E(raw,bytes.fromhex('83f31088'))
    def zero(p,o,fail,byte=False):
        E(ldrb_w if byte else ldr_w,0,p,o);E(cmp_imm,0,0);bc(fail,'ne')
    def main(fail):
        E(raw,bytes.fromhex('eff31080'));E(cmp_imm,0,0);bc(fail,'ne')
        E(raw,bytes.fromhex('eff30580'));E(cmp_imm,0,0);bc(fail,'ne')
        imm(4,state);field(0);imm(1,MAGIC);E(cmp_reg,0,1);bc(fail,'ne')

    # Physical quiescence eligibility is separate from logical queued debt.
    # Preserve all software bytes; do not relax in-progress owner checks.
    a.label('cy_stable');E(push,[3,4,5,6,7],lr=True);main('stable_no')
    E(bl,ss['ss_binding']);E(cmp_imm,0,1);bc('stable_no','ne')
    imm(5,life.STATE_BASE)
    for o in (life.BUSY,life.PUBLISHING):zero(5,o,'stable_no')
    E(ldr_imm,0,5,life.EPOCH);imm(1,0xFFFFFFFF);E(cmp_reg,0,1);bc('stable_no','eq')
    imm(5,retry.STATE_BASE)
    for o in (retry.BUSY,retry.PRODUCER_BUSY,retry.FAILED):zero(5,o,'stable_no',True)
    zero(5,retry.REQUEST,'stable_no')
    imm(5,ledger.STATE_BASE)
    for o in (ledger.BUSY,ledger.FAULT):zero(5,o,'stable_no')
    for n in range(3):
        imm(5,recovery.STATE_BASE+recovery.HEADER_SIZE+n*recovery.ENTRY_SIZE)
        zero(5,recovery.BUSY,'stable_no',True)
        if n==0:zero(5,recovery.FLAGS,'stable_no',True)
    imm(6,session.STATE_BASE);zero(6,session.TX_ACTIVE,'stable_no')
    if staging:
        zero(4,FLUSH_BUSY,'stable_no')
        E(bl,'cy_staging');E(cmp_imm,0,1);bc('stable_no','ne')
    if not staging:
        E(ldr_imm,5,6,session.DRIVER)
        E(ldrh_imm,0,5,18);E(cmp_imm,0,0);bc('stable_no','ne')
        zero(5,20,'stable_no',True)
        for off in (session.MAIN,session.ALT):
            E(ldr_imm,7,6,off);E(ldrh_imm,0,7);E(cmp_imm,0,0);bc('stable_no','ne')
        E(ldr_imm,0,5,24);E(ldr_imm,1,6,session.MAIN);E(cmp_reg,0,1);bc('stable_no','ne')
        E(ldr_imm,5,6,session.TX_COUNTER);E(ldrh_imm,0,5);E(ldrh_imm,1,5,2)
        E(cmp_imm,0,0);bc('stable_cursor_ok','eq');E(cmp_reg,0,1);bc('stable_no','ne')
        a.label('stable_cursor_ok')
    # A partial native parser or live musical input needs a separate policy.
    imm(5,life.STATE_BASE);E(ldr_imm,5,5,life.PARSER)
    zero(5,0,'stable_no',True);E(ldrb_imm,0,5,2);E(cmp_imm,0,1);bc('stable_no','hi')
    E(ldr_imm,0,5,12);E(bl,0x0802A37E);E(cmp_imm,0,0);bc('stable_no','ne')
    E(bl,sq['c_midi_inputs_idle']);E(cmp_imm,0,1);bc('stable_no','ne')
    E(movs_imm,0,1);E(pop,[3,4,5,6,7],pc=True)
    a.label('stable_no');E(movs_imm,0,0);E(pop,[3,4,5,6,7],pc=True)

    a.label('cy_quiet');E(push,[3,4,5],lr=True);E(bl,'cy_original_quiet')
    if staging:
        # ss_quiet does not inspect MAIN. A fully formatted short message can
        # leave zero logical debt yet still own unsent bytes; never clear it.
        E(cmp_imm,0,1);bc('quiet_check','ne')
        imm(1,session.STATE_BASE);E(ldr_imm,1,1,session.MAIN)
        E(ldrh_imm,0,1);E(cmp_imm,0,0);bc('quiet_ok','eq')
        a.label('quiet_check')
    else:
        E(cmp_imm,0,1);bc('quiet_ok','eq')
    main('quiet_no')
    imm(1,session.STATE_BASE);E(ldr_imm,0,1,session.PHASE)
    E(cmp_imm,0,session.CLOSING);bc('quiet_no','lo')
    E(cmp_imm,0,session.SEALED);bc('quiet_no','hi')
    E(bl,'cy_stable');E(cmp_imm,0,1);bc('quiet_no','ne')
    E(movs_imm,0,1);put(ACTIVE)
    a.label('quiet_ok');E(movs_imm,0,1);E(pop,[3,4,5],pc=True)
    a.label('quiet_no');E(movs_imm,0,0);E(pop,[3,4,5],pc=True)
    a.label('cy_original_quiet');E(raw,hooks[ss['ss_quiet']][0]);E(b_w,ss['ss_quiet']+6)

    # Separate retirement ownership from ss.BUSY: a native reset IRQ must be
    # allowed to invalidate the generation while main clears already-retired
    # HAL objects. The step entry still rejects recursive main service.
    a.label('cy_step');E(push,[3,4,5],lr=True);imm(4,state)
    field(0);imm(1,MAGIC);E(cmp_reg,0,1);bc('step_original','ne')
    field(BUSY);E(cmp_imm,0,1);bc('step_original','ne')
    E(movs_imm,0,1);E(pop,[3,4,5],pc=True)
    a.label('step_original');E(pop,[3,4,5],lr=True)
    a.label('cy_original_step');E(raw,hooks[ss['ss_step']][0]);E(b_w,ss['ss_step']+6)

    # A planned, fully owned close is not an unexpected driver failure.
    # Keep the USB port's FIFO/SEEN/FAULT bytes untouched while it is carried.
    # Other ports and genuine broken/OPEN driver faults retain the old path.
    a.label('cy_poll');E(push,[0,1,2,3,4,5,6],lr=True);imm(4,state)
    field(0,1);imm(2,MAGIC);E(cmp_reg,1,2);bc('poll_original','ne')
    if staging:
        imm(1,session.STATE_BASE);E(ldr_imm,2,1,session.TX_PORT);E(cmp_reg,0,2);bc('poll_original','ne')
        field(FLUSH_BUSY,2);E(cmp_imm,2,0);bc('poll_park','ne')
        # A retained full MAIN makes native402FC exit before its flush edge.
        # Submit retained bytes first on an OPEN poll, then continue natively.
        E(ldr_imm,0,1,session.DRIVER);E(bl,'cy_flush');E(ldr_sp,0,0)
    field(ACTIVE,1);E(cmp_imm,1,1);bc('poll_original','ne')
    imm(1,session.STATE_BASE);E(ldr_imm,2,1,session.TX_PORT);E(cmp_reg,0,2);bc('poll_original','ne')
    E(ldr_imm,0,1,session.PHASE);E(cmp_imm,0,session.CLOSING);bc('poll_original','lo')
    E(cmp_imm,0,session.SEALED);bc('poll_original','hi')
    a.label('poll_park');E(pop,[0,1,2,3,4,5,6],lr=True);E(movs_imm,0,1);E(bx_lr)
    a.label('poll_original');E(pop,[0,1,2,3,4,5,6],lr=True)
    a.label('cy_original_poll');E(raw,hooks[rp['rp_poll']][0]);E(b_w,rp['rp_poll']+6)

    # Entered from inside ss_step with its24-byte frame still on the stack.
    a.label('cy_seal');E(push,[3,4,5,6,7],lr=True);imm(4,state)
    field(0);imm(1,MAGIC);E(cmp_reg,0,1);bc('seal_original','ne')
    field(ACTIVE);E(cmp_imm,0,1);bc('seal_original','ne')
    field(BUSY);E(cmp_imm,0,0);bc('seal_denied','ne');E(movs_imm,0,1);put(BUSY)
    E(bl,'cy_stable');E(cmp_imm,0,1);bc('seal_wait','ne')
    imm(5,session.STATE_BASE);E(ldr_imm,0,5,session.BUSY);E(cmp_imm,0,0);bc('seal_wait','ne')
    imm(1,control.STATE_BASE);E(ldr_imm,7,1,control.REQUESTS)
    E(ldr_imm,6,5,session.USB_BASE)
    for reg,bits in ((session.IN_CTL,session.EPENA),(session.OUT_CTL,session.EPENA),(session.IN_INT,3),(session.OUT_INT,3),
                     (session.GRSTCTL,0x30),(session.GINTSTS,16)):
        E(ldr_w,0,6,reg);imm(1,bits);E(tst_reg,0,1);bc('seal_wait','ne')
    # Only HAL transfer objects are discarded. Software port/driver/payload,
    # RX FIFO, parser and ledger provenance remain byte-for-byte owned.
    # The native raw driver binds its endpoint; use the pinned controller chain.
    imm(1,life.STATE_BASE);E(ldr_imm,1,1,life.CONTROLLER);E(ldr_w,1,1,0x298)
    E(movs_imm,0,0)
    for desc in (0x3C+0x1C,0x1FC+0x1C):
        for o in (12,16,20,24):E(str_w,0,1,desc+o)
    a.label('cy_seal_commit');mask();imm(1,control.STATE_BASE);E(ldr_imm,0,1,control.REQUESTS);E(cmp_reg,0,7);bc('seal_race','ne')
    imm(1,life.STATE_BASE);E(ldr_imm,0,1,life.EPOCH);E(adds_imm8,0,1)
    E(str_imm,0,1,life.EPOCH);E(str_imm,0,5,session.EPOCH)
    E(movs_imm,0,life.CLOSED);E(str_imm,0,1,life.PHASE)
    E(ldr_imm,2,5,session.RX_ACTIVE);E(ldr_imm,1,5,session.CANCEL_RX);E(raw,bytes.fromhex('8918'))
    E(str_imm,1,5,session.CANCEL_RX);E(str_imm,0,5,session.RX_ACTIVE)
    E(ldr_imm,1,5,session.RX_PORT);E(strb_imm,0,1,28)
    E(movs_imm,0,session.SEALED);E(str_imm,0,5,session.PHASE)
    E(movs_imm,0,0);E(str_imm,0,5,session.BUSY);put(BUSY);put(RESUME_PENDING)
    field(SEALS);E(adds_imm8,0,1);put(SEALS);restore()
    E(pop,[3,4,5,6,7],lr=True);E(b_w,ss['step_ok'])
    a.label('seal_race');restore()
    a.label('seal_wait');imm(1,session.STATE_BASE);E(movs_imm,0,0);E(str_imm,0,1,session.BUSY)
    put(BUSY)
    a.label('seal_denied')
    E(pop,[3,4,5,6,7],lr=True);E(b_w,ss['step_wait'])
    a.label('seal_original');E(pop,[3,4,5,6,7],lr=True)
    a.label('cy_original_seal');E(movs_imm,0,1);E(str_imm,0,4,session.BUSY)
    E(ldr_imm,0,4,session.TX_PORT);E(bl,ss['ss_native_080401ac']);E(b_w,seal+10)

    a.label('cy_resume');E(push,[3,4,5,6,7],lr=True);imm(4,state)
    field(0);imm(1,MAGIC);E(cmp_reg,0,1);bc('resume_original','ne')
    field(ACTIVE);E(cmp_imm,0,1);bc('resume_original','ne')
    E(ldr_sp,0,20);imm(1,resume_lr);E(cmp_reg,0,1);bc('resume_no','ne')
    imm(1,control.STATE_BASE);E(ldr_imm,7,1,control.REQUESTS)
    E(bl,'cy_stable');E(cmp_imm,0,1);bc('resume_no','ne')
    imm(5,session.STATE_BASE);E(ldr_imm,0,5,session.PHASE);E(cmp_imm,0,session.SEALED);bc('resume_no','ne')
    imm(5,life.STATE_BASE);E(ldr_imm,0,5,life.CONTROLLER);E(ldrb_w,0,0,0x274);E(cmp_imm,0,3);bc('resume_no','ne')
    a.label('cy_resume_commit');mask()
    imm(1,control.STATE_BASE);E(ldr_imm,0,1,control.REQUESTS);E(cmp_reg,0,7);bc('resume_race','ne')
    E(ldr_imm,0,5,life.PHASE);E(cmp_imm,0,life.CLOSED);bc('resume_race','ne')
    E(movs_imm,0,life.ACTIVE);E(str_imm,0,5,life.PHASE);E(movs_imm,0,1);put(RESUME_PENDING)
    put(GENERATION,7);restore()
    E(movs_imm,0,0);E(pop,[3,4,5,6,7],pc=True)
    a.label('resume_race');restore()
    a.label('resume_no');E(movs_imm,0,1);E(pop,[3,4,5,6,7],pc=True)
    a.label('resume_original');E(pop,[3,4,5,6,7],lr=True)
    a.label('cy_original_resume');E(raw,hooks[resume][0]);E(b_w,resume+6)

    a.label('cy_task');E(push,[3,4,5,6,7],lr=True);E(bl,ut['ut_main']);E(mov_reg,6,0);imm(4,state)
    E(cmp_imm,6,0);bc('task_done','ne')
    field(0);imm(1,MAGIC);E(cmp_reg,0,1);bc('task_done','ne')
    field(RESUME_PENDING);E(cmp_imm,0,1);bc('task_done','ne')
    mask();imm(1,session.STATE_BASE);E(ldr_imm,0,1,session.PHASE);E(cmp_imm,0,session.OPEN);bc('task_unlock','ne')
    imm(1,life.STATE_BASE);E(ldr_imm,0,1,life.PHASE);E(cmp_imm,0,life.ACTIVE);bc('task_unlock','ne')
    field(GENERATION,2);imm(1,control.STATE_BASE);E(ldr_imm,0,1,control.REQUESTS);E(cmp_reg,0,2);bc('task_unlock','ne')
    E(movs_imm,0,0);put(ACTIVE);put(RESUME_PENDING);field(RESUMES);E(adds_imm8,0,1);put(RESUMES)
    a.label('task_unlock');restore()
    a.label('task_done');E(mov_reg,0,6);E(pop,[3,4,5,6,7],pc=True)

    if staging:
        # Read-only admission for native CPU-formatted MAIN bytes. ALT/raw
        # direct mode is separate. Partial SysEx cursors require the immutable
        # owned retry slot, not an arbitrary borrowed caller buffer.
        a.label('cy_staging');E(push,[3,4,5,6,7],lr=True);imm(6,session.STATE_BASE)
        E(ldr_imm,5,6,session.DRIVER)
        E(ldrh_imm,0,5,18);E(cmp_imm,0,0);bc('staging_no','ne')
        zero(5,20,'staging_no',True)
        for off in (16,30):
            E(ldrh_imm,0,5,off);E(cmp_imm,0,64);bc('staging_no','ne')
        E(ldr_imm,7,6,session.ALT);E(ldrh_imm,0,7);E(cmp_imm,0,0);bc('staging_no','ne')
        zero(7,4,'staging_no')
        E(ldr_imm,7,6,session.MAIN);E(ldr_imm,0,5,24);E(cmp_reg,0,7);bc('staging_no','ne')
        E(ldrh_imm,0,7);E(cmp_imm,0,64);bc('staging_no','hi')
        E(movs_imm,1,3);E(tst_reg,0,1);bc('staging_no','ne')
        E(ldr_imm,5,6,session.TX_COUNTER);E(ldrh_imm,0,5);E(ldrh_imm,1,5,2)
        E(cmp_reg,0,1);bc('staging_no','hi')
        E(cmp_imm,0,0);bc('staging_ok','eq');E(cmp_reg,0,1);bc('staging_ok','eq')
        imm(5,retry.STATE_BASE);E(ldrb_imm,0,5,retry.ACTIVE);E(cmp_imm,0,1);bc('staging_no','ne')
        E(ldrb_imm,0,5,retry.ACCEPTED);E(movs_imm,2,1);E(tst_reg,0,2);bc('staging_no','eq')
        E(ldr_imm,7,6,session.TX_PORT);E(ldr_imm,0,7,8)
        imm(2,retry.STATE_BASE+retry.PAYLOAD);E(cmp_reg,0,2);bc('staging_no','ne')
        E(ldr_imm,0,7,12);E(cmp_reg,0,1);bc('staging_no','ne')
        E(ldr_imm,0,5,retry.DESCRIPTOR+4);E(cmp_reg,0,1);bc('staging_no','ne')
        imm(2,retry.CAPACITY);E(cmp_reg,1,2);bc('staging_no','hi')
        a.label('staging_ok');E(movs_imm,0,1);E(pop,[3,4,5,6,7],pc=True)
        a.label('staging_no');E(movs_imm,0,0);E(pop,[3,4,5,6,7],pc=True)

        # Native2B498 clears MAIN even when raw2B3BC -> ss_tx_arm rejects a
        # close raced before submission. Call the asserted endpoint adapter
        # directly and consume MAIN only if a new immutable TX ticket exists.
        # Once admitted, any delivery uncertainty retains the old strict path.
        a.label('cy_flush');E(push,[3,4,5,6,7],lr=True);E(mov_reg,5,0)
        imm(4,session.STATE_BASE);field(session.DRIVER,1);E(cmp_reg,0,1);bc('flush_foreign','ne')
        field(0);imm(1,session.MAGIC);E(cmp_reg,0,1);bc('flush_done','ne')
        field(session.PHASE);E(cmp_imm,0,session.OPEN);bc('flush_done','ne')
        imm(1,life.STATE_BASE);E(ldr_imm,0,1,life.PHASE);E(cmp_imm,0,life.ACTIVE);bc('flush_done','ne')
        E(ldr_imm,6,5,24);E(ldrh_imm,2,6);E(cmp_imm,2,0);bc('flush_done','eq')
        # Limit this adapter to the MAIN/CPU mode; foreign/raw modes keep their
        # old OPEN path and cannot acquire staged carry admission.
        field(session.MAIN,0);E(cmp_reg,0,6);bc('flush_foreign','ne')
        E(ldrb_imm,0,5,20);E(cmp_imm,0,0);bc('flush_foreign','ne')
        E(raw,bytes.fromhex('eff31080'));E(cmp_imm,0,0);bc('flush_done','ne')
        E(raw,bytes.fromhex('eff30580'));E(cmp_imm,0,0);bc('flush_done','ne')
        imm(1,state);E(ldr_imm,0,1,FLUSH_BUSY);E(cmp_imm,0,0);bc('flush_done','ne')
        E(movs_imm,0,1);E(str_imm,0,1,FLUSH_BUSY)
        field(session.TX_TICKET,7);field(session.TX_ENDPOINT);E(ldr_imm,1,6,4)
        a.label('cy_flush_submit');E(bl,0x08026880)
        a.label('cy_flush_after_submit')
        field(session.TX_TICKET);E(cmp_reg,0,7);bc('flush_release','eq')
        E(movs_imm,0,0);E(strh_imm,0,6)
        a.label('flush_release');imm(1,state);E(movs_imm,0,0);E(str_imm,0,1,FLUSH_BUSY)
        a.label('flush_done');E(mov_reg,0,5);E(pop,[3,4,5,6,7],pc=True)
        a.label('flush_foreign');E(mov_reg,0,5);E(pop,[3,4,5,6,7],lr=True)
        a.label('cy_original_flush');E(raw,hooks[0x0802B498][0]);E(b_w,0x0802B49C)
    code,labels=a.assemble();code+=b'\x00\xbf'*(-len(code)%4//2)
    if base+len(code)>0x08080000:raise ValueError('Carry code exceeds application flash')
    return code,labels
