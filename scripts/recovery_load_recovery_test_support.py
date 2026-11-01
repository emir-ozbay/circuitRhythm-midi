"""Native reset/failed Load/Close-bound UI retry; no application RAM repairs."""
import hashlib
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import *
from recovery_load_test_support import exercise_load
from recovery_live_mode_test_support import PROJECT_BYTES
from inspect_ui import BASE
import midi_recovery_patch as fixed
import project_load_recovery_patch as guard
import seq_Patch as seq

def exercise_load_recovery(s,timer,mode,*,progress=None):
    h=s.h;u=h.u;stage='setup';cycles=0;events=[];clips=[];reads=[];current=None;armed=False
    _,g=guard.arm_code(s.labels['c_seq_state'],fixed.STATE_BASE)
    def aliases():
        return dict(recorders=[h.read(r+0x50) for r in s.recorders],
                    players=[h.read(r+0x50) for r in s.objects(0x08068D24)])
    initial_aliases=aliases();expected=sorted(s.raw+0x2E4+t*0x5140 for t in range(8))
    assert sorted(initial_aliases['recorders'])==sorted(initial_aliases['players'])==expected
    def state():
        return dict(**s.snapshot(),taint=u.mem_read(seq.ST+seq.OFF_PROJECT_TAINTED,1)[0],
            recovery_stage=u.mem_read(seq.ST+guard.STAGE,1)[0],epoch=h.read(seq.ST+guard.EPOCH),
            recovery_held=h.read(seq.ST+guard.HELD),controller_pads=h.read(s.ctrl+0x9C),
            active_view=s.value(h.read(s.ctrl+0x14)),active_slot=s.value(h.read(s.project+0x44),11)&255,
            page=u.mem_read(s.projects+0x36,1)[0])
    def observe(uc,pc,size,_):
        nonlocal current,armed
        regs=[uc.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)]
        row=dict(stage=stage,cycle=cycles,pc=pc,regs=regs,state=state(),sp=uc.reg_read(UC_ARM_REG_SP),primask=uc.reg_read(UC_ARM_REG_PRIMASK))
        if pc==0x0804113A and regs[2]==s.raw:
            current=dict(stage=stage,count_ptr=h.read(uc.reg_read(UC_ARM_REG_SP)),requested=regs[3]);reads.append(current)
        elif pc==0x080411BE and armed and regs[1]==s.raw:
            assert regs[2]==PROJECT_BYTES
            uc.reg_write(UC_ARM_REG_R2,741);armed=False;clips.append(dict(stage=stage,request=PROJECT_BYTES,supplied=741))
        elif pc==0x0802AE32 and current is not None:
            current.update(status=regs[0],count=h.read(current['count_ptr']));current=None
        if pc==g['close_done']:row['cookie']=h.read(uc.reg_read(UC_ARM_REG_SP)+4)
        if pc in (g['close_done'],guard.NATIVE_CLOSE):row['descriptor']=bytes(u.mem_read(regs[0],12)).hex()
        events.append(row)
    hooks=[u.hook_add(UC_HOOK_CODE,observe,begin=pc,end=pc) for pc in
        (0x0804113A,0x080411BE,0x0802AE32,0x08041906,0x08041916,guard.SITE,
         g['close_done'],guard.NATIVE_CLOSE,guard.NEW_SITE,guard.APPLY_SITE,g['apply_return'],g['apply_exit'],guard.NATIVE_LOAD,
         0x08032DB2,0x080378C6,0x08037E7E,0x08038798)]
    s.reentry_debug=dict(events=events,reads=reads,clips=clips)
    setup=exercise_load(s,timer,mode,progress=progress);uart=s.load_uart
    initial=state();assert initial['taint']==1 and initial['recovery_stage']==guard.READY and initial['epoch']==1
    def update():
        if progress:progress(dict(stage=stage,mode=mode,cycles=cycles,total_cycles=setup['cycles']+cycles,state=state()))
    def cycle():
        nonlocal cycles
        uart.service();timer.deliver();s.cycle(budget=2000000);uart.service();cycles+=1
        assert not h.invalid and bytes(u.mem_read(seq.ST+seq.OFF_MIDI_CONTEXT_FAULT,3))==bytes(3)
        if cycles%32==0:update()
    def until(expected):
        for _ in range(256):
            cycle()
            if state()['recovery_stage']==expected:
                for _ in range(8):cycle()
                return
        raise AssertionError((stage,state()))
    def button(n):s.input('button_down',n);s.input('button_up',n)
    def pad(n):s.input('pad_down',n);s.input('pad_up',n)
    def mode_check(expected):
        before=state();s.shortcut();after=state();assert after['mode']==expected
        for key in ('raw_sha256','metadata_sha256','io_count','nor_mutations','recovery_stage','taint'):
            assert before[key]==after[key],(key,before,after)
    stage='ready_rejections';button(26);assert state()['active_view']==6
    before=state();s.input('button_down',27);pad(1);s.input('button_up',27)
    assert state()['io_count']==before['io_count'] and state()['raw_sha256']==before['raw_sha256']
    mode_check(mode)
    stage='ui_retry_short_read';armed=True;update();pad(1)
    assert state()['recovery_stage']==guard.RETRY and state()['recovery_held']==state()['controller_pads']==0
    mode_check(mode);until(guard.READY);failed_again=state()
    assert not armed and failed_again['epoch']==2 and failed_again['taint']==1
    assert failed_again['phase']==2 and failed_again['project_flags']&3==3
    assert [(r['status'],r['count']) for r in reads if r['stage']==stage]==[(4,741)]
    assert not any(e['pc']==guard.APPLY_SITE and e['stage']==stage for e in events)
    mode_check(mode)
    stage='ui_full_retry_held';update();s.input('pad_down',1)
    assert state()['recovery_held']==s.ctrl and state()['controller_pads']==2
    until(guard.CLEAN);restored_held=state()
    assert restored_held['taint']==restored_held['phase']==restored_held['project_flags']==0
    assert restored_held['raw_sha256']==setup['saved']['raw_sha256']
    assert aliases()==initial_aliases
    assert [(r['status'],r['count']) for r in reads if r['stage']==stage]==[(0,PROJECT_BYTES)]
    mode_check(mode) # actual pad still held, even though native apply finished
    s.input('pad_up',1);assert state()['recovery_held']==state()['controller_pads']==0
    mode_check(1-mode);mode_check(mode)
    stage='stock_ui_short_read';armed=True;update();pad(1)
    assert state()['controller_pads']==0 # physical release survives stock busy
    until(guard.READY);assert state()['epoch']==3 and state()['taint']==1 and not armed
    assert [(r['status'],r['count']) for r in reads if r['stage']==stage]==[(4,741)]
    stage='ui_new_page1';button(19);assert state()['page']==1;update();start_reads=len(reads)
    pad(1);until(guard.CLEAN);created=state()
    assert len(reads)==start_reads and created['active_slot']==33
    assert created['taint']==created['phase']==created['project_flags']==created['recovery_held']==created['controller_pads']==0
    assert created['raw_sha256']==setup['saved']['raw_sha256']
    assert aliases()==initial_aliases
    mode_check(1-mode);mode_check(mode);final=state()
    assert final['heap']==initial['heap'] and final['allocations']==initial['allocations']
    assert final['nor_mutations']==initial['nor_mutations']
    close_events=[e for e in events if e['pc']==g['close_done']]
    assert [e['cookie'] for e in close_events]==[1,2,3]
    assert all(e['regs'][2]==0 and e['state']['recovery_stage']==guard.CLOSING for e in close_events)
    queued=[e for e in events if e['pc']==guard.NATIVE_CLOSE]
    assert len(queued)==3
    for q,c in zip(queued,close_events):
        assert q['regs'][1]==g['close_done']|1 and q['regs'][2]==c['cookie']
        assert q['descriptor']==c['descriptor']
        assert q['sp']%8==c['sp']%8==0 and q['primask']==c['primask']==0
    for st in ('ui_full_retry_held','ui_new_page1'):
        apply=[e for e in events if e['stage']==st and e['pc']==guard.APPLY_SITE]
        done=[e for e in events if e['stage']==st and e['pc']==g['apply_exit']]
        assert len(apply)==len(done)==1 and apply[0]['state']['taint']==1 and done[0]['state']['taint']==0
        for pc in (0x08037E7E,0x08038798,g['apply_return']):
            rows=[e for e in events if e['stage']==st and e['pc']==pc]
            assert len(rows)==1 and rows[0]['state']['taint']==1
    for st,slot in (('ui_retry_short_read',1),('ui_full_retry_held',1),('stock_ui_short_read',1),('ui_new_page1',33)):
        loads=[e for e in events if e['stage']==st and e['pc']==guard.NATIVE_LOAD]
        assert len(loads)==1 and loads[0]['regs'][:3]==[s.project,slot,1] and loads[0]['primask']==0
    for pc in (guard.NEW_SITE,0x08032DB2,0x080378C6):
        assert len([e for e in events if e['stage']=='ui_new_page1' and e['pc']==pc])==1
    assert len(setup['uart']['interrupts'])==setup['uart']['used_credits']
    assert h.validate_stacks() and bytes(u.mem_read(BASE,len(s.image)))==s.image
    for hook in hooks:u.hook_del(hook)
    update()
    return dict(mode=mode,setup=setup,initial=initial,failed_again=failed_again,restored_held=restored_held,
        created=created,final=final,events=events,reads=reads,fault_inputs=clips,aliases=initial_aliases,
        cycles=cycles,total_cycles=setup['cycles']+cycles,timer_events=len(timer.events),uart=uart.report(),
        application_ram_repaired=False,firmware_instruction_stubs=False,ui_recovery=True,
        fault_scope='Three synthetic741B lower-read inputs per boot;native FatFs/count/status/Close. Not natural EOF or physical fault.',
        hardware_release='NO-GO')
