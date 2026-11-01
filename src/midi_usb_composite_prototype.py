"""EMULATION ONLY: defer a bound MIDI+MSC class list and retain DIN queues.

Only quiescent MSC configuration is supported. No production RAM reservation,
storage driver, task wiring, real controller cancellation or device access.
"""
import midi_usb_control_prototype as control
import midi_usb_session_prototype as session
from thumb_asm import (Asm, adds_imm8, b_cond_w, b_w, bl, bx_lr, cmp_imm,
                       cmp_reg, ldr_imm, ldr_sp, ldr_w, ldrb_w, mov_reg,
                       movs_imm, pop, push, raw, str_imm, tst_reg)

CODE_BASE, STATE_BASE, STATE_SIZE = 0x0807A400, 0x20047D80, 96
MAGIC = 0x31435855
ROOT, MIDI, MSC, CONTROLLER, ROUTER = 4, 8, 12, 16, 20
PENDING, RUNNING, GENERATION, CURRENT, ERRORS, SKIPPED, STARTS = 24,28,32,36,40,44,48
GATES = {0x08040B5A: bytes.fromhex('f8b50446'),
         0x080525B2: control.GATES[0x080525B2],
         0x080297C0: bytes.fromhex('38b50446'),
         0x0802C928: control.GATES[0x0802C928]}


def arm_code(base=CODE_BASE, state=STATE_BASE):
    cc_code, cc = control.arm_code()
    if (base % 4 or state % 4 or base < control.CODE_BASE + len(cc_code)
            or not 0x20047D44 <= state < state+STATE_SIZE <= 0x20047DFC):
        raise ValueError('Composite code/state overlaps or exceeds bounds')
    a=Asm(base); E=a.emit
    def imm(r,v): a.imm32(r,v)
    def bc(label,cond): E(b_cond_w,label,cond)
    def field(off,r=0): E(ldr_imm,r,4,off)
    def owned(fail):
        field(0); imm(1,MAGIC); E(cmp_reg,0,1); bc(fail,'ne')
        field(RUNNING); E(cmp_imm,0,1); bc(fail,'ne')
        imm(5,control.STATE_BASE); E(ldr_imm,0,5,control.INIT_BUSY)
        E(cmp_imm,0,1); bc(fail,'ne')
        field(GENERATION); E(ldr_imm,1,5,control.REQUESTS); E(cmp_reg,0,1); bc(fail,'ne')
        imm(5,session.STATE_BASE); E(ldr_imm,0,5,session.PHASE)
        E(cmp_imm,0,session.SEALED); bc(fail,'ne')
        for off in (session.TX_ACTIVE,session.RX_ACTIVE):
            E(ldr_imm,0,5,off); E(cmp_imm,0,0); bc(fail,'ne')
    def no(): E(movs_imm,0,1); E(pop,[3,4,5,6,7],pc=True)
    def native(name,address):
        a.label(name); E(raw,GATES[address]); E(b_w,address+len(GATES[address]))

    # Native EP0 calls40B5A once for the whole class list. Queue that request;
    # no MSC flush or BOT parent may run ahead of the MIDI cancellation barrier.
    a.label('xc_init_list')
    E(push,[3,4,5,6,7],lr=True); E(mov_reg,6,0); E(mov_reg,7,1); imm(4,state)
    field(ROOT,3); E(cmp_reg,6,3); bc('list_foreign','ne')
    field(CONTROLLER,3); E(cmp_reg,7,3); bc('list_foreign','ne')
    E(cmp_imm,2,1); bc('list_no','ne')
    field(0); imm(1,MAGIC); E(cmp_reg,0,1); bc('list_no','ne')
    E(ldrb_w,0,6,0); E(cmp_imm,0,2); bc('list_no','ne')
    for off,bound in ((8,MIDI),(12,MSC)):
        E(ldr_imm,0,6,off); field(bound,1); E(cmp_reg,0,1); bc('list_no','ne')
    E(ldr_imm,0,6,16); E(cmp_imm,0,0); bc('list_no','ne')
    imm(1,0x20006F20); E(ldr_imm,0,1); E(cmp_reg,0,6); bc('list_no','ne')
    field(RUNNING); E(cmp_imm,0,0); bc('list_no','ne')
    # An armed MSC CBW or endpoint completion is not a proved cancelled job.
    # Preserve it and reject reconfiguration until an external owner quiesces it.
    E(bl,'xc_msc_quiet'); E(cmp_imm,0,1); bc('list_no','ne')
    field(MIDI); E(mov_reg,1,7); E(movs_imm,2,1); E(bl,cc['cc_init'])
    E(cmp_imm,0,0); bc('list_no','ne')
    imm(5,control.STATE_BASE); E(ldr_imm,0,5,control.REQUESTS); E(str_imm,0,4,GENERATION)
    E(movs_imm,0,1); E(str_imm,0,4,PENDING)
    E(movs_imm,0,0); E(pop,[3,4,5,6,7],pc=True)
    a.label('list_no'); no()
    a.label('list_foreign'); E(mov_reg,0,6); E(mov_reg,1,7)
    E(pop,[3,4,5,6,7],lr=True); E(b_w,'xc_native_list')
    native('xc_native_list',0x08040B5A)

    # Replaces the generated cc_native_init entry, retaining its native fallback.
    a.label('xc_deferred_list')
    E(push,[3,4,5,6,7],lr=True); E(mov_reg,6,0); E(mov_reg,7,1); imm(4,state)
    field(MIDI,3); E(cmp_reg,6,3); bc('deferred_foreign','ne')
    field(CONTROLLER,3); E(cmp_reg,7,3); bc('deferred_foreign','ne')
    field(PENDING); E(cmp_imm,0,1); bc('deferred_no','ne')
    E(movs_imm,0,1); E(str_imm,0,4,RUNNING)
    owned('deferred_bad')
    E(bl,'xc_msc_quiet'); E(cmp_imm,0,1); bc('deferred_bad','ne')
    field(STARTS); E(adds_imm8,0,1); E(str_imm,0,4,STARTS)
    field(ROOT); field(CONTROLLER,1); E(movs_imm,2,1); E(bl,'xc_native_list')
    E(mov_reg,6,0); E(movs_imm,0,0); E(str_imm,0,4,RUNNING); E(str_imm,0,4,CURRENT)
    E(str_imm,0,4,PENDING); E(mov_reg,0,6); E(pop,[3,4,5,6,7],pc=True)
    a.label('deferred_bad'); E(movs_imm,0,0); E(str_imm,0,4,RUNNING)
    a.label('deferred_no'); E(movs_imm,0,1); E(str_imm,0,4,ERRORS); no()
    a.label('deferred_foreign'); E(mov_reg,0,6); E(mov_reg,1,7)
    E(pop,[3,4,5,6,7],lr=True); E(b_w,'xc_native_ctor')

    a.label('xc_init_class')
    E(push,[3,4,5,6,7],lr=True); E(mov_reg,6,0); E(mov_reg,7,1); imm(4,state)
    field(MIDI,3); E(cmp_reg,6,3); bc('class_bound','eq')
    field(MSC,3); E(cmp_reg,6,3); bc('class_foreign','ne')
    a.label('class_bound'); field(CONTROLLER,3); E(cmp_reg,7,3); bc('class_foreign','ne')
    owned('class_no'); E(str_imm,6,4,CURRENT)
    E(mov_reg,0,6); E(mov_reg,1,7); E(pop,[3,4,5,6,7],lr=True); E(b_w,'xc_native_ctor')
    a.label('class_no'); no()
    a.label('class_foreign'); E(mov_reg,0,6); E(mov_reg,1,7)
    E(pop,[3,4,5,6,7],lr=True); E(b_w,cc['cc_init'])
    native('xc_native_ctor',0x080525B2)

    # Real parent68A2C calls297C0, clearing USB and BOTH DIN queues. USB has
    # already been cleared by the sealed barrier. Preserve DIN and borrowed data.
    a.label('xc_clear_router')
    E(push,[3,4,5,6,7],lr=True); E(mov_reg,6,0); imm(4,state)
    field(RUNNING); E(cmp_imm,0,1); bc('clear_foreign','ne')
    owned('clear_no')
    field(ROUTER,3); E(cmp_reg,6,3); bc('clear_no','ne')
    E(ldr_sp,0,20); imm(1,0x08068A37); E(cmp_reg,0,1); bc('clear_no','ne')
    field(CURRENT); field(MIDI,1); E(cmp_reg,0,1); bc('clear_no','ne')
    imm(1,0x20006F04); E(ldr_imm,0,1); E(cmp_reg,0,6); bc('clear_no','ne')
    field(SKIPPED); E(adds_imm8,0,1); E(str_imm,0,4,SKIPPED)
    E(movs_imm,0,0); E(pop,[3,4,5,6,7],pc=True)
    a.label('clear_no'); no()
    a.label('clear_foreign'); E(mov_reg,0,6); E(pop,[3,4,5,6,7],lr=True)
    native('xc_native_clear',0x080297C0)

    # MSC's OUT2 constructor also flushes the shared RX FIFO. Suppress only
    # its owned sealed callsite; endpoint1 remains under the earlier guard.
    a.label('xc_flush')
    E(push,[3,4,5,6,7],lr=True); E(mov_reg,6,0); E(mov_reg,7,1); imm(4,state)
    E(cmp_imm,7,2); bc('flush_foreign','ne')
    field(CONTROLLER,3); E(cmp_reg,6,3); bc('flush_foreign','ne')
    field(RUNNING); E(cmp_imm,0,1); bc('flush_foreign','ne')
    owned('flush_no'); field(CURRENT); field(MSC,1); E(cmp_reg,0,1); bc('flush_no','ne')
    E(ldr_sp,0,20); imm(1,0x080525CB); E(cmp_reg,0,1); bc('flush_no','ne')
    imm(1,session.STATE_BASE); E(ldr_imm,0,1,session.RX_ACTIVE); E(cmp_imm,0,0); bc('flush_no','ne')
    E(movs_imm,0,0); E(pop,[3,4,5,6,7],pc=True)
    a.label('flush_no'); no()
    a.label('flush_foreign'); E(mov_reg,0,6); E(mov_reg,1,7)
    E(pop,[3,4,5,6,7],lr=True); E(b_w,cc['cc_flush'])

    a.label('xc_msc_quiet')
    field(CONTROLLER,0); E(ldr_w,0,0,0x298); E(ldr_imm,2,0)
    for reg,bits in ((0x940,session.EPENA),(0xB40,session.EPENA),(0x948,3),(0xB48,3)):
        E(ldr_w,0,2,reg); imm(1,bits); E(tst_reg,0,1); bc('msc_busy','ne')
    imm(1,0x20006DD4); E(ldrb_w,0,1,0x10); E(cmp_imm,0,0); bc('msc_busy','ne')
    E(movs_imm,0,1); E(bx_lr)
    a.label('msc_busy'); E(movs_imm,0,0); E(bx_lr)
    code,labels=a.assemble()
    if base+len(code)>0x08080000: raise ValueError('Composite code exceeds application flash')
    return code,labels
