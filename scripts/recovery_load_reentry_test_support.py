"""Characterize stock re-entry after a native short read, without RAM repair.

First prove Projects pad requests are rejected in quarantine. A separately
labeled direct native backend call then probes complete-read/apply boundaries;
it bypasses the UI dispatcher and is NOT a user-accessible recovery solution.
The final UI controls run only after that native backend has finished.
"""
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_SP
from inspect_ui import BASE,load_image
from recovery_live_mode_test_support import PROJECT_BYTES
from recovery_load_test_support import exercise_load
import seq_Patch as seq


def exercise_load_reentry(s,timer,mode,*,progress=None):
    setup=exercise_load(s,timer,mode,progress=progress)
    h=s.h;u=h.u;uart=s.load_uart
    stage='quarantined_ui';cycles=0;events=[];reads=[];current_read=None;rejections=[]
    def raw():return bytes(u.mem_read(s.raw,PROJECT_BYTES))
    def state():
        return dict(**s.snapshot(),taint=u.mem_read(seq.SEQ_STATE_ADDR+seq.OFF_PROJECT_TAINTED,1)[0],
            active_view=s.value(h.read(s.ctrl+0x14)),page=u.mem_read(s.projects+0x36,1)[0],
            active_slot=s.value(h.read(s.project+0x44),11)&255,
            controller_project_flags=s.value(h.read(s.ctrl+0x8C)),
            bridge_callback=h.read(h.read(s.project+0x64)))
    def aliases():
        players=s.objects(0x08068D24)
        return dict(recorders=[h.read(r+0x50) for r in s.recorders],players=[h.read(r+0x50) for r in players])
    initial_aliases=aliases()
    assert h.read(s.ctrl+0x8C)==h.read(s.project+0x4C)
    assert len(initial_aliases['players'])==8
    expected=sorted(s.raw+0x2E4+t*0x5140 for t in range(8))
    assert sorted(initial_aliases['recorders'])==expected
    assert sorted(initial_aliases['players'])==expected
    def update():
        if progress:progress(dict(stage=stage,mode=mode,cycles=cycles,total_cycles=cycles+setup['cycles'],state=state()))
    s.reentry_debug=dict(events=events,reads=reads,rejections=rejections,setup=setup)
    stock=load_image()
    for lo,hi in ((0x080385C8,0x080386DC),(0x0804F080,0x0804F16C),
                  (0x08037B8C,0x08038798),(0x0803D7FE,0x0803D85A)):
        assert s.image[lo-BASE:hi-BASE]==stock[lo-BASE:hi-BASE]
    def observe(uc,pc,size,_):
        nonlocal current_read
        regs=[uc.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)]
        row=dict(stage=stage,cycle=cycles,pc=pc,regs=regs,state=state())
        if pc==0x0804113A and regs[2]==s.raw:
            assert regs[1]==0 and regs[3]==PROJECT_BYTES and current_read is None
            current_read=dict(stage=stage,requested=regs[3],count_ptr=h.read(uc.reg_read(UC_ARM_REG_SP)))
            reads.append(current_read)
        elif pc==0x0802AE32 and current_read is not None:
            current_read.update(status=regs[0],count=h.read(current_read['count_ptr']),state=state())
            current_read=None
        events.append(row)
    hooks=[u.hook_add(UC_HOOK_CODE,observe,begin=pc,end=pc) for pc in
        (0x0803D7FE,0x0803D814,0x0803D858,0x0804F080,0x0804F09E,0x080385CA,0x080386D6,0x08037B8C,0x08037BD6,
         0x0804113A,0x0802AE32,0x08037E3C,0x080379B2,0x08037E7E,0x08038798,
         0x08037C84,0x08032DB2,0x08041906)]
    def cycle():
        nonlocal cycles
        uart.service();timer.deliver();s.cycle(budget=2000000);uart.service();cycles+=1
        assert not h.invalid and bytes(u.mem_read(seq.SEQ_STATE_ADDR+seq.OFF_MIDI_CONTEXT_FAULT,3))==bytes(3)
        assert state()['transport']==0 and state()['taint']==1
        if cycles%32==0:update()
    def completed():
        for _ in range(256):
            cycle()
            if state()['phase']==0:
                for _ in range(8):cycle()
                return
        raise AssertionError(('native retry did not complete',stage,state()))
    def button(n):s.input('button_down',n);s.input('button_up',n)
    def pad(n):s.input('pad_down',n);s.input('pad_up',n)
    def reject_mode():
        before=state();s.shortcut();after=state()
        assert after['mode']==mode and after['taint']==1
        for key in ('raw_sha256','metadata_sha256','io_count','nor_mutations','phase','project_flags'):
            assert before[key]==after[key],(key,before,after)
        rejections.append(dict(stage=stage,before=before,after=after))
    # Actual controller button/pad interface, not a project backend adapter.
    initial=state();assert initial['phase']==2 and initial['bridge_callback']==0
    button(26);assert state()['active_view']==6 and state()['page']==0
    opened=state();ui_attempts=[]
    for slot in (1,2):
        before=state();start=len(events);pad(slot)
        for _ in range(16):cycle()
        after=state();observed=events[start:]
        assert [e['pc'] for e in observed]==[0x0803D7FE,0x0803D814,0x0803D858]
        assert observed[1]['regs'][2]&2 and after['controller_project_flags']==3
        for key in ('raw_sha256','metadata_sha256','io_count','nor_mutations','phase','project_flags','active_slot','taint'):
            assert before[key]==after[key],(key,before,after)
        ui_attempts.append(dict(slot=slot,before=before,after=after,events=observed))
    reject_mode();update()
    # A second diagnostic boundary bypasses only the controller pad guard.
    # It confirms phase2 rejection in the underlying native Projects action.
    stage='diagnostic_projects_view';view_attempts=[]
    for slot in (1,2):
        before=state();start=len(events)
        s._invoke(0x0804F09E,(s.projects,slot,96,0),label=stage,budget=2000000)
        after=state();observed=events[start:]
        dispatch=[e for e in observed if e['pc']==0x080385CA]
        assert len(dispatch)==1 and dispatch[0]['regs'][1]==h.read(s.project+0x38)
        assert dispatch[0]['regs'][2]==slot+64
        assert sum(e['pc']==0x080386D6 for e in observed)==1
        assert not any(e['pc'] in (0x08037B8C,0x08037C84,0x0804113A,0x08032DB2) for e in observed)
        for key in ('raw_sha256','metadata_sha256','io_count','nor_mutations','phase','project_flags','active_slot','taint'):
            assert before[key]==after[key],(key,before,after)
        view_attempts.append(dict(slot=slot,before=before,after=after,events=observed))
    # Boundary experiment: the UI cannot reach this call while phase==2.
    # Invoke the native backend as an explicit diagnostic input, no RAM fix.
    stage='diagnostic_backend_full_reload';start=len(events);update()
    s._invoke(0x08037B8C,(s.project,1,0,0),label=stage,budget=2000000)
    completed();restored=state();restore_events=events[start:]
    assert [(r['status'],r['count']) for r in reads]==[(0,PROJECT_BYTES)]
    assert restored['raw_sha256']==setup['saved']['raw_sha256']
    assert restored['phase']==restored['project_flags']==0 and restored['taint']==1
    assert sum(e['pc']==0x080379B2 for e in restore_events)==1
    assert sum(e['pc']==0x08037E3C for e in restore_events)==1
    # Stock successful-read bridge/apply has no explicit Close in this window.
    # Do not infer a leak or file retirement from its application idle flag.
    assert not any(e['pc']==0x08041906 for e in restore_events)
    assert not any(e['pc']==0x08032DB2 for e in restore_events)
    assert aliases()==initial_aliases
    reject_mode()
    # Native UI controls after full native replacement: saved Load and empty New.
    # They establish reachability at phase0, not quarantine recovery.
    stage='ui_full_reload';start=len(events);update()
    assert state()['active_view']==6
    pad(1);completed();ui_loaded=state();load_events=events[start:]
    assert len(reads)==2 and reads[-1]['status']==0 and reads[-1]['count']==PROJECT_BYTES
    assert ui_loaded['raw_sha256']==setup['saved']['raw_sha256']
    assert sum(e['pc']==0x08037B8C for e in load_events)==1
    assert sum(e['pc']==0x08037E3C for e in load_events)==1
    assert not any(e['pc']==0x080386D6 for e in load_events)
    reject_mode()
    stage='ui_new_empty_slot';start=len(events);update()
    pad(2);completed();created=state();new_events=events[start:]
    assert len(reads)==2 # empty-slot New takes the native timer/defaults route
    assert sum(e['pc']==0x08037C84 for e in new_events)==1
    assert sum(e['pc']==0x08032DB2 for e in new_events)==1
    assert sum(e['pc']==0x08037E3C for e in new_events)==1
    assert not any(e['pc']==0x080386D6 for e in new_events)
    assert created['active_slot']==2 and created['phase']==created['project_flags']==0
    assert created['taint']==1 and aliases()==initial_aliases
    reject_mode();final=state()
    assert final['heap']==initial['heap'] and final['allocations']==initial['allocations']
    assert final['nor_mutations']==initial['nor_mutations']
    # Setup telemetry is a snapshot, not the reused peer's growing IRQ list.
    assert len(setup['uart']['interrupts'])==setup['uart']['used_credits']
    assert len(uart.interrupts)==uart.report()['used_credits']
    assert h.validate_stacks() and bytes(u.mem_read(BASE,len(s.image)))==s.image
    assert current_read is None
    for hook in hooks:u.hook_del(hook)
    update()
    return dict(mode=mode,setup=setup,initial=initial,projects_opened=opened,ui_rejected=ui_attempts,
        diagnostic_view_rejected=view_attempts,
        diagnostic_backend_restored=restored,ui_loaded=ui_loaded,ui_created=created,final=final,
        read_results=reads,events=events,aliases=initial_aliases,rejected_shortcuts=rejections,
        cycles=cycles,total_cycles=cycles+setup['cycles'],timer_events=len(timer.events),uart=uart.report(),
        diagnostic_backend_bypasses_ui_dispatch=True,ui_quarantine_recovery=False,taint_cleared=False,
        diagnostic_backend_explicit_close_observed=False,
        application_ram_repaired=False,firmware_instruction_stubs=False,physical_test=False,
        model_scope=__doc__,hardware_release='NO-GO')
