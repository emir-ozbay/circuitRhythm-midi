"""Native boot/Save/Load over NOR,with one explicit lower-read count limit.

Fault input: at stock411BE,cap the native file object's read request to741B.
Native FatFs copies real saved bytes and returns its count;411C4..CC compares
that count with the original169092B request and produces short-read4. This is
an injected lower-read boundary,not a physical EOF/SD fault reproduction.
No returned status,project byte,owner,phase,taint,queue or fault is host-written.
"""
import hashlib
from copy import deepcopy
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import *
from recovery_live_mode_test_support import PROJECT_BYTES
from recovery_uart_test_support import NativeUARTPeer
from inspect_ui import BASE,load_image
import seq_Patch as seq
import project_load_recovery_patch as guard
import midi_recovery_patch as fixed
from thumb_asm import b_w


def exercise_load(s,timer,mode,*,progress=None):
    h=s.h;u=h.u;uart=NativeUARTPeer(s,txe_credits=8192)
    s.load_uart=uart # retain the same finite peripheral peer for continuation tests
    initial=s.snapshot();stage='save';events=[];reads=[];clips=[];rejects=[];cycles=0
    current_read=None
    def raw():return bytes(u.mem_read(s.raw,PROJECT_BYTES))
    def taint():return u.mem_read(seq.SEQ_STATE_ADDR+seq.OFF_PROJECT_TAINTED,1)[0]
    def state():return dict(**s.snapshot(),taint=taint())
    def update():
        if progress:progress(dict(stage=stage,mode=mode,cycles=cycles,state=state()))
    s.load_debug=dict(events=events,reads=reads,clips=clips,rejects=rejects)
    stock=load_image()
    _,recovery_labels=guard.arm_code(fixed.seq_code()[1]['c_seq_state'],fixed.STATE_BASE)
    for lo,hi in ((0x08037B8C,0x08038798),(0x0804113A,0x080411D8),(0x080472AC,0x080472BC)):
        expected=bytearray(stock[lo-BASE:hi-BASE])
        for site,original,name in guard.HOOKS:
            if lo<=site<hi:
                assert stock[site-BASE:site-BASE+4]==original
                expected[site-lo:site-lo+4]=b_w(site,recovery_labels[name])
        assert s.image[lo-BASE:hi-BASE]==expected
    def observe(uc,pc,size,_):
        nonlocal current_read
        regs=[uc.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)]
        event=dict(stage=stage,pc=pc,regs=regs,task=h.task_by_tcb[h.running_tcb]['name'],cycle=cycles)
        if pc==0x0804113A and regs[2]==s.raw:
            assert regs[1]==0 and regs[3]==PROJECT_BYTES
            current_read=dict(stage=stage,descriptor=bytes(u.mem_read(regs[0],12)).hex(),target=regs[2],requested=regs[3],count_ptr=h.read(uc.reg_read(UC_ARM_REG_SP)))
            reads.append(current_read)
        elif pc==0x080411BE and stage=='short_read' and regs[1]==s.raw:
            assert regs[2]==PROJECT_BYTES and not clips
            clips.append(dict(pc=pc,requested=PROJECT_BYTES,supplied=741,target=regs[1]))
            uc.reg_write(UC_ARM_REG_R2,741) # explicit fault input BEFORE native read
        elif pc==0x0802AE32 and current_read is not None:
            current_read.update(status=regs[0],count=h.read(current_read['count_ptr']),
                raw_sha256=hashlib.sha256(raw()).hexdigest(),step0=raw()[0x2E4:0x2EC].hex())
            current_read=None
        if pc in (0x08037E3C,0x08037DD0,guard.SITE):event['state']=state()
        events.append(event)
    hooks=[]
    for pc in (0x0804113A,0x080411BE,0x0802AE32,0x08037E3C,0x08037DD0,
               0x080381C8,0x080381D6,0x08041906,guard.SITE):
        hooks.append(u.hook_add(UC_HOOK_CODE,observe,begin=pc,end=pc))
    def cycle():
        nonlocal cycles
        uart.service();timer.deliver();s.cycle(budget=2000000);uart.service();cycles+=1
        assert not h.invalid and bytes(u.mem_read(seq.SEQ_STATE_ADDR+seq.OFF_MIDI_CONTEXT_FAULT,3))==bytes(3)
        if cycles%32==0:update()
    def completed():
        for _ in range(256):
            cycle()
            if s.snapshot()['phase']==0:
                for _ in range(8):cycle() # let the native queued Close retire too
                return
        raise AssertionError(('native operation did not complete',stage,state()))
    def shortcut(expected):
        before=state();row=s.shortcut();after=state()
        assert after['mode']==expected
        for key in ('raw_sha256','metadata_sha256','io_count','nor_mutations','heap','allocations','taint'):
            assert before[key]==after[key],(key,before[key],after[key])
        return row
    if mode:shortcut(mode)
    assert state()['transport']==state()['phase']==taint()==0
    update()
    # Native public backend entry;this setup does not claim Save-button UI.
    s._invoke(0x08037ED0,(s.project,1,0,0),label='native_Save_slot1',budget=2000000)
    completed();saved=raw();saved_state=state()
    assert any(e['pc']==0x080381D6 for e in events)
    assert any(e['pc']==0x08041906 for e in events)
    def edit():
        s.input('pad_down',0);s.input('pad_up',0)
        assert raw()[0x2E4]!=saved[0x2E4] and raw()[0x2E7]==96
        assert not state()['held_pads'] and all(not(x['held']|x['held_bits']) for x in state()['step_owners'])
    stage='complete_read';edit();edited_control=state();update()
    s._invoke(0x08037B8C,(s.project,1,0,0),label='native_Load_control',budget=2000000)
    completed();control=state()
    assert [(r['status'],r['count']) for r in reads]==[(0,PROJECT_BYTES)]
    assert raw()==saved and control['phase']==control['project_flags']==control['taint']==0
    assert sum(e['pc']==0x08037E3C for e in events)==1
    shortcut(1-mode);shortcut(mode) # full read leaves clean admission available
    stage='short_read';edit();before=raw();before_failure=state();update()
    start_io=len(s.io);start_events=len(events)
    s._invoke(0x08037B8C,(s.project,1,0,0),label='native_Load_short_read',budget=2000000)
    rejects.append(shortcut(mode)) # queued/running phase,prior to completion
    for _ in range(64):cycle()
    failed=state();after=raw();failure_events=events[start_events:]
    assert len(clips)==1 and [(r['status'],r['count']) for r in reads]==[(0,PROJECT_BYTES),(4,741)]
    assert after[:741]==saved[:741] and after[741:]==before[741:]
    assert after[0x2E4:0x2EC]==saved[0x2E4:0x2E5]+before[0x2E5:0x2EC]
    assert not any(e['pc'] in (0x08037E3C,0x080381C8,0x08037DD0) for e in failure_events)
    assert any(e['pc']==0x08041906 for e in failure_events)
    bridge=h.read(s.project+0x64);assert h.read(bridge)==0
    assert failed['phase']==2 and failed['project_flags']&3==3 and failed['taint']==1
    assert failed['transport']==0
    rejects.append(shortcut(mode))
    for _ in range(16):cycle()
    rejects.append(shortcut(mode));final=state()
    assert final['raw_sha256']==failed['raw_sha256'] and final['taint']==1
    assert final['heap']==initial['heap'] and final['allocations']==initial['allocations']
    assert h.validate_stacks() and bytes(u.mem_read(BASE,len(s.image)))==s.image
    update()
    # The completed one-shot fault must not affect a later native retry.
    # Removing hooks changes no application RAM, CPU state or queued work.
    assert current_read is None
    for hook in hooks:u.hook_del(hook)
    return dict(mode=mode,initial=initial,saved=saved_state,edited_control=edited_control,control=control,
        before_failure=before_failure,failed=failed,final=final,read_results=reads,fault_inputs=clips,
        events=events,rejected_shortcuts=rejects,io=list(s.io),failure_io=s.io[start_io:],
        changed_offsets=[i for i,(a,b) in enumerate(zip(before,after)) if a!=b],
        step0=dict(saved=saved[0x2E4:0x2EC].hex(),before=before[0x2E4:0x2EC].hex(),after=after[0x2E4:0x2EC].hex()),
        cycles=cycles,timer_events=len(timer.events),uart=deepcopy(uart.report()),raw_rollback=False,
        model_scope=__doc__,boot_objects_seeded=False,application_ram_repaired=False,
        firmware_instruction_stubs=False,physical_test=False,hardware_release='NO-GO')
