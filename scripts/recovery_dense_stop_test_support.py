"""UI-programmed long gates/distinct notes,native IRQ/Main and64-voice Stop.

The optional before-output input adapter preserves CPU context at25870. It
does not restore RAM,skip a Main instruction,seed ownership or clear queues.
"""
import struct
from collections import Counter
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import *
from recovery_input_test_support import MAIN_LOOP
from recovery_fpu_test_support import FP_REGS
from recovery_worker_test_support import SAVED_REGS
from recovery_live_mode_test_support import PROJECT_BYTES
from recovery_uart_test_support import NativeUARTPeer
from recovery_playback_test_support import decode_midi
from inspect_ui import BASE
import midi_recovery_patch as fixed
import midi_recovery_prototype as rp
import seq_Patch as seq
import midi_dense_stop_patch as dense

AFTER_TIMER=0x08025870


def phase_input(s,kind,identifier):
    """Controller button callback at a named,unmasked Main CODE boundary."""
    h=s.h;u=h.u;assert u.reg_read(UC_ARM_REG_PC)==AFTER_TIMER
    assert kind in ('button_down','button_up') and h.task_by_tcb[h.running_tcb]['name']=='Main'
    assert not u.reg_read(UC_ARM_REG_PRIMASK) and not u.reg_read(UC_ARM_REG_BASEPRI)
    context=u.context_save();tcb=h.running_tcb;sp=u.reg_read(UC_ARM_REG_PSP)
    bank=tuple(u.reg_read(r) for r in SAVED_REGS);high=tuple(u.reg_read(r) for r in FP_REGS[16:])
    invalid=len(h.invalid);before=s.snapshot();s.active_input=f'before_output:{kind}:{identifier}'
    target=h.read(h.read(s.ctrl)+(8 if kind=='button_down' else 12))&~1
    for reg,value in zip((UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3),(s.ctrl,identifier,0,0)):u.reg_write(reg,value)
    u.reg_write(UC_ARM_REG_LR,AFTER_TIMER|1)
    try:
        assert h.run(target,AFTER_TIMER,budget=2000000)==AFTER_TIMER
        assert h.running_tcb==tcb and u.reg_read(UC_ARM_REG_PSP)==sp
        assert tuple(u.reg_read(r) for r in SAVED_REGS)==bank
        assert tuple(u.reg_read(r) for r in FP_REGS[16:])==high
        assert not u.reg_read(UC_ARM_REG_PRIMASK) and not u.reg_read(UC_ARM_REG_BASEPRI)
        assert len(h.invalid)==invalid and h.validate_stacks()
        row=dict(kind=kind,id=identifier,target=target,boundary=AFTER_TIMER,before=before,after=s.snapshot())
        u.context_restore(context);s.inputs.append(row);return row
    finally:s.active_input=None


def exercise_dense_stop(s,timer,*,mode=0,before_output=True,progress=None):
    h=s.h;u=h.u;initial=s.snapshot();uart=NativeUARTPeer(s,txe_credits=65536)
    cycles=0;tick=0;count=0;trace=[];program=[];growth=[];drains=[]
    players=sorted(s.objects(0x08068D24),key=lambda p:h.read(p+0x50));assert len(players)==8
    views=[h.read(s.grid+0x74+4*t) for t in range(8)]
    def raw():return bytes(u.mem_read(s.raw,PROJECT_BYTES))
    def faults():return bytes(u.mem_read(seq.SEQ_STATE_ADDR+seq.OFF_MIDI_CONTEXT_FAULT,3)).hex()
    dense_labels=dense.arm_code(fixed.STATE_BASE)[1]
    def observe(uc,pc,size,_):
        trace.append(dict(pc=pc,tick=tick,r0=uc.reg_read(UC_ARM_REG_R0),r1=uc.reg_read(UC_ARM_REG_R1),
            r2=uc.reg_read(UC_ARM_REG_R2),r3=uc.reg_read(UC_ARM_REG_R3),caller=uc.reg_read(UC_ARM_REG_LR),
            primask=uc.reg_read(UC_ARM_REG_PRIMASK),basepri=uc.reg_read(UC_ARM_REG_BASEPRI),
            ipsr=uc.reg_read(UC_ARM_REG_IPSR),sp=uc.reg_read(UC_ARM_REG_SP)))
    for pc in (0x0804AEEE,0x0804AFBC,0x0804AED8,0x080552F6,dense.CODE_BASE,dense_labels['service']):u.hook_add(UC_HOOK_CODE,observe,begin=pc,end=pc)
    def midi_state():
        result=[]
        for n in range(3):
            entry=fixed.STATE_BASE+rp.HEADER_SIZE+n*rp.ENTRY_SIZE;port=h.read(entry);q=h.read(port+4)
            cap=int.from_bytes(u.mem_read(q+4,2),'little');head=int.from_bytes(u.mem_read(q+6,2),'little');tail=int.from_bytes(u.mem_read(q+8,2),'little')
            assert 0<=head<cap and 0<=tail<cap
            result.append(dict(port=port,fifo_bytes=(head-tail)%cap,
                flags=u.mem_read(entry+rp.FLAGS,1)[0],deferred=int.from_bytes(u.mem_read(entry+rp.COUNT,2),'little')))
        return result
    def service():
        nonlocal cycles
        uart.service();s.cycle(budget=2000000);cycles+=1;uart.service()
    def settle():
        for _ in range(32):
            service();state=midi_state();drains.append(state)
            if all(not (r['fifo_bytes'] or r['deferred'] or r['flags']&rp.STOP_PENDING) for r in state):return
        raise AssertionError(('MIDI closing debt did not drain',midi_state()))
    def event(kind,i):
        nonlocal count
        row=s.input(kind,i);count+=1
        if count%16==0:service()
        assert faults()=='000000';return row
    def button(i):
        row=event('button_down',i);event('button_up',i);return row
    def pad(i):event('pad_down',i);event('pad_up',i)
    def enter(gm,button_id):
        for _ in range(2):
            if s.snapshot()['grid_mode']==gm:break
            button(button_id)
        assert s.snapshot()['grid_mode']==gm
    def active(p):
        node=u.mem_read(p+0x8A,1)[0];result=[]
        while node!=255:
            assert node<8 and node not in [a['slot'] for a in result]
            result.append(dict(slot=node,note=u.mem_read(p+0x8E+4*node,1)[0]))
            node=u.mem_read(p+0x78+2*node,1)[0]
        return result
    assert initial['mode']==initial['transport']==initial['held_pads']==0
    s.shortcut();assert s.snapshot()['mode']==1
    for t in range(8):
        button(t);enter(4,12);ps=h.read(views[t]+0x60)
        if s.value(ps)!=1:button(21)
        pad(15);enter(2,10)
        if s.value(ps):button(21)
        for i in range(8):
            event('pad_down',i);pad(27);event('pad_up',i)
        enter(1,9);v=h.read(s.grid+0x54+4*t);km=h.read(v+0x4C);window=s.value(h.read(v+0x48));stride=u.mem_read(km+0x19C,1)[0]
        keys=[]
        for kp in range(16,32):
            index=(kp+(5-window)*stride*8)&255;assert index<128
            pitch=u.mem_read(km+8+index,1)[0]
            if pitch and pitch!=72 and pitch not in [p for _,p in keys]:keys.append((kp,pitch))
        assert len(keys)>=8
        for i,(kp,pitch) in enumerate(keys[:8]):
            event('pad_down',i);pad(kp);event('pad_up',i)
            record=raw()[0x2E4+t*0x5140+8*i:0x2E4+t*0x5140+8*i+8]
            assert record[0]==pitch and record[3]==96,(t,i,record.hex(),pitch)
        enter(3,11)
        for i in range(8):
            event('pad_down',i);pad(30);pad(31);event('pad_up',i)
        records=[raw()[0x2E4+t*0x5140+8*i:0x2E4+t*0x5140+8*i+8] for i in range(32)]
        assert [i for i,r in enumerate(records) if r[3]]==list(range(8))
        assert all(r==bytes((pitch,96,1,96,7,255,0,0)) for r,(_,pitch) in zip(records[:8],keys[:8])),[r.hex() for r in records[:8]]
        program.append(dict(track=t,keys=keys[:8],records=[r.hex() for r in records]))
        if progress:progress(dict(stage='program',track=t,mode=mode,before_output=before_output))
    button(8);settle()
    if not mode:
        row=s.shortcut();assert row['after']['mode']==0
        settle()
    programmed=raw();snapshot=s.snapshot();wire_start=[len(p['bytes']) for p in uart.ports]
    assert all(not active(p) for p in players) and faults()=='000000'
    button(17);assert s.snapshot()['transport']==1
    start=len(trace);last=-1
    for _ in range(1600):
        assert timer.debt()==0;uart.service();timer.deliver();tick+=1
        h.checkpoint(AFTER_TIMER,budget=2000000)
        assert timer.debt()==0
        commits=[e for e in trace[start:] if e['pc']==0x0804AFBC and e['r0']==players[0] and e['r3']==0]
        if len(commits)>last+1:
            step=commits[-1]['r2'];assert step==last+1
            voices=[active(p) for p in players]
            assert all(len(a)==step+1 for a in voices),(step,voices)
            for t,a in enumerate(voices):assert {x['note'] for x in a}=={pitch for _,pitch in program[t]['keys'][:step+1]}
            growth.append(dict(step=step,tick=tick,counts=[len(a) for a in voices]));last=step
            if progress:progress(dict(stage='play',mode=mode,step=step,voices=sum(len(a) for a in voices),tick=tick,before_output=before_output))
        if last==7:
            if not before_output:
                h.checkpoint(MAIN_LOOP,budget=2000000);cycles+=1;uart.service()
            break
        h.checkpoint(MAIN_LOOP,budget=2000000);cycles+=1;uart.service()
        assert faults()=='000000' and raw()==programmed
    else:raise AssertionError('eight concurrent voices/player not reached')
    live=[active(p) for p in players];assert sum(map(len,live))==64
    before_stop=midi_state();stop_start=len(trace)
    if before_output:
        down=phase_input(s,'button_down',17);phase_input(s,'button_up',17)
    else:
        down=s.input('button_down',17);s.input('button_up',17)
    after_stop=midi_state();assert down['after']['transport']==0
    assert all(not active(p) for p in players)
    if before_output:
        h.checkpoint(MAIN_LOOP,budget=2000000);cycles+=1;uart.service()
    settle();stop_trace=trace[stop_start:]
    assert [e['r0'] for e in stop_trace if e['pc']==0x0804AED8]==players
    assert [e['r0'] for e in stop_trace if e['pc']==0x080552F6]==players
    assert [e['r0'] for e in stop_trace if e['pc']==dense.CODE_BASE]==players
    serviced=[e for e in stop_trace if e['pc']==dense_labels['service']]
    assert len(serviced)==8 and all(e['r0']==h.read(dense.GLOBAL_ROUTER) and not (e['primask'] or e['basepri'] or e['ipsr'] or e['sp']%8) for e in serviced)
    streams=[bytes(p['bytes'][a:]) for p,a in zip(uart.ports,wire_start)];assert streams[0]==streams[1]
    messages=decode_midi(streams[0]);notes=[m for m in messages if len(m)==3]
    expected=Counter((status|t,pitch-12,velocity) for t,row in enumerate(program) for _,pitch in row['keys'] for status,velocity in ((0x90,96),(0x80,0)))
    assert Counter(map(tuple,notes))==expected,Counter(map(tuple,notes))
    held=set()
    for m in notes:
        key=(m[0]&15,m[1])
        if m[0]&0xF0==0x90:assert key not in held;held.add(key)
        else:assert key in held;held.remove(key)
    assert not held and messages[0]==[0xFA] and messages[-1]==[0xFC]
    assert sum(m==[0xFC] for m in messages)==1 and sum(m==[0xF8] for m in messages)==43
    closing=s.snapshot();assert raw()==programmed and closing['transport']==closing['held_pads']==0
    assert faults()=='000000' and all(not r['flags'] for r in midi_state())
    closing_state=midi_state()
    # Prove usable runtime state after closing,without repairing the fault or
    # transport RAM. Dirty project edits survive the two mode commits.
    roundtrips=[]
    for target in (1-mode,mode):
        row=s.shortcut();assert row['after']['mode']==target and raw()==programmed
        roundtrips.append(row)
    restart_wire=[len(p['bytes']) for p in uart.ports];restart_trace=len(trace)
    button(17);assert s.snapshot()['transport']==1
    restart_ticks=0
    for _ in range(128):
        uart.service();timer.deliver();tick+=1;restart_ticks+=1
        s.cycle(budget=2000000);cycles+=1;uart.service()
        if all(len(active(p))==1 for p in players):break
    else:raise AssertionError('healthy Stop prevented native restart')
    assert faults()=='000000'
    button(17);assert s.snapshot()['transport']==0;settle()
    restart_streams=[bytes(p['bytes'][a:]) for p,a in zip(uart.ports,restart_wire)]
    assert restart_streams[0]==restart_streams[1]
    restart_messages=decode_midi(restart_streams[0])
    expected_restart=Counter((status|t,row['keys'][0][1]-12,velocity) for t,row in enumerate(program) for status,velocity in ((0x90,96),(0x80,0)))
    assert Counter(tuple(m) for m in restart_messages if len(m)==3)==expected_restart
    assert restart_messages[0]==[0xFA] and restart_messages[-1]==[0xFC]
    assert sum(m==[0xFA] for m in restart_messages)==sum(m==[0xFC] for m in restart_messages)==1
    assert not any(active(p) for p in players) and faults()=='000000'
    final=s.snapshot();assert raw()==programmed
    for key in ('raw','project','metadata_sha256','heap','allocations','nor_mutations'):assert initial[key]==final[key],key
    assert not s.io and not h.invalid and h.validate_stacks() and bytes(u.mem_read(BASE,len(s.image)))==s.image
    for p in players:
        events=[e for e in trace[start:stop_start] if e['pc']==0x0804AFBC and e['r0']==p]
        assert [(e['r1'],e['r2'],e['r3']) for e in events]==[(0,i//6,i%6) for i in range(43)]
    return dict(initial=initial,programmed=snapshot,final=final,mode=mode,before_output=before_output,program=program,
        growth=growth,live_before_stop=live,before_stop=before_stop,after_stop=after_stop,closing=closing,settled=closing_state,drains=drains,
        restart=dict(roundtrips=roundtrips,ticks=restart_ticks,messages=restart_messages,trace=trace[restart_trace:],settled=midi_state()),
        stop_input=down,stop_services=serviced,trace=trace,inputs=s.inputs,messages=messages,uart=uart.report(),timer_peer=timer.report(),
        main_cycles=cycles,timer_events=tick,midi_faults=faults(),project_io=s.io,physical_test=False,
        scope='Native reset objects,UI-programmed distinct notes/gate96,eight concurrent stock gate slots per track,64 total. Finite native IRQ/Main time;normal or25870 before-output Stop adapter. Both dirty runtime mode commits and native Play/8 On/Stop/8 Off restart follow64-voice closing. Native queues/recovery/driver IRQs only;no FIFO/fault/ownership/RAM repair;no physical timing/delivery claim.')
