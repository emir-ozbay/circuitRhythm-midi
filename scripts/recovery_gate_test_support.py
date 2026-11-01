"""UI-programmed gate endpoints,finite native IRQ/Main,expiry and Stop.

This does not claim native UI creation of the separate step byte6 tie bit.
"""
from collections import Counter
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import *
from inspect_ui import BASE,load_image
from recovery_live_mode_test_support import PROJECT_BYTES
from recovery_uart_test_support import NativeUARTPeer
from recovery_playback_test_support import decode_midi
import seq_Patch as seq


def exercise_native_gates(s,timer,*,progress=None):
    h=s.h;u=h.u;initial=s.snapshot();uart=NativeUARTPeer(s,txe_credits=65536)
    players=sorted(s.objects(0x08068D24),key=lambda p:h.read(p+0x50));assert len(players)==8
    views=[h.read(s.grid+0x74+4*t) for t in range(8)]
    sources=(0,15,16,31,0,15,16,31);gates=(1,6,95,96,96,95,6,1)
    count=cycles=tick=0;mode=None;trace=[];program=[];runs=[];last_commit={};prep={}
    stock=load_image()
    for lo,hi in ((0x0804ADA4,0x0804B214),(0x08056D54,0x08056F00)):
        assert s.image[lo-BASE:hi-BASE]==stock[lo-BASE:hi-BASE]
    def raw():return bytes(u.mem_read(s.raw,PROJECT_BYTES))
    def fault():return bytes(u.mem_read(seq.SEQ_STATE_ADDR+seq.OFF_MIDI_CONTEXT_FAULT,3)).hex()
    def active(p):
        node=u.mem_read(p+0x8A,1)[0];seen=[]
        while node!=255:
            assert node<8 and node not in seen;seen.append(node);node=u.mem_read(p+0x78+2*node,1)[0]
        return seen
    def observe(uc,pc,size,_):
        p=uc.reg_read(UC_ARM_REG_R0)
        row=dict(pc=pc,mode=mode,tick=tick,input=s.active_input,r0=p,r1=uc.reg_read(UC_ARM_REG_R1),
            r2=uc.reg_read(UC_ARM_REG_R2),r3=uc.reg_read(UC_ARM_REG_R3),caller=uc.reg_read(UC_ARM_REG_LR))
        if pc==0x0804AEEE and p in players:prep[p]=(row['r1'],row['r2'],row['r3'])
        if pc==0x0804AFBC and p in players:last_commit[p]=(row['r1'],row['r2'],row['r3'])
        row['prepare']=prep.get(p);row['commit']=last_commit.get(p);trace.append(row)
    for pc in (0x0804AEEE,0x0804AFBC,0x0804B0D4,0x0804B170,0x0804AED8):u.hook_add(UC_HOOK_CODE,observe,begin=pc,end=pc)
    def service():
        nonlocal cycles
        uart.service();s.cycle(budget=2000000);cycles+=1;uart.service();assert fault()=='000000'
    def event(kind,i):
        nonlocal count
        row=s.input(kind,i);count+=1
        if count%16==0:service()
        assert fault()=='000000';return row
    def button(i):row=event('button_down',i);event('button_up',i);return row
    def pad(i):event('pad_down',i);event('pad_up',i)
    def enter(gm,key):
        for _ in range(2):
            if s.snapshot()['grid_mode']==gm:return
            button(key)
        assert s.snapshot()['grid_mode']==gm
    def page(ps,want):
        if s.value(ps)!=want:button(21)
        assert s.value(ps)==want
    # Use native fastest sync0 to cover two complete32-step passes with
    # fewer peripheral events. Gate endpoints are still native UI values.
    s.shortcut();assert s.snapshot()['mode']==1
    for t,(step,gate) in enumerate(zip(sources,gates)):
        button(t);ps=h.read(views[t]+0x60);enter(4,12);page(ps,1);pad(15);pad(23);pad(28)
        enter(2,10);page(ps,step//16);event('pad_down',step%16);pad(27);event('pad_up',step%16)
        enter(3,11);event('pad_down',step%16)
        pad(30);pad(31)
        if gate==95:pad(31)
        elif gate in (1,6):
            pad(16)
            if gate==1:
                for _ in range(5):pad(16)
        event('pad_up',step%16)
        records=[raw()[0x2E4+t*0x5140+8*i:0x2E4+t*0x5140+8*i+8] for i in range(32)]
        assert [i for i,r in enumerate(records) if r[3]]==[step]
        assert records[step]==bytes((72,gate,1,96,7,255,0,0)),(t,records[step].hex(),gate)
        header=raw()[0x2E4+t*0x5140+0x100:0x2E4+t*0x5140+0x104];assert header==bytes((31,0,0,0)),header.hex()
        program.append(dict(track=t,step=step,gate=gate,record=records[step].hex(),header=header.hex()))
        if progress:progress(dict(stage='program',track=t))
    button(8)
    for _ in range(4):service()
    programmed=raw()
    for enabled in (0,1):
        mode=enabled
        if s.snapshot()['mode']!=enabled:
            row=s.shortcut();assert row['after']['mode']==enabled and raw()==programmed
        for _ in range(4):service()
        assert not any(active(p) for p in players)
        wire=[len(p['bytes']) for p in uart.ports];start=len(trace);button(17)
        assert s.snapshot()['transport']==1;commits=[];boundaries=[];reported=-1
        for _ in range(5000):
            uart.service();timer.deliver();tick+=1;service()
            commits=[e for e in trace[start:] if e['pc']==0x0804AFBC and e['r0']==players[0]]
            threshold=(97,193)[len(boundaries)] if len(boundaries)<2 else None
            if threshold is not None and len(commits)>=threshold:
                counts=[len(active(p)) for p in players]
                assert len(commits)<threshold+3
                if threshold==97:assert counts[5]==1 # source15/gate95 is held across16/17
                else:assert counts[3]==1 # source31/gate96 is held across32/1
                boundaries.append(dict(threshold=threshold,commits=len(commits),counts=counts,tick=tick))
            if progress and len(commits)//48!=reported and commits:
                progress(dict(stage='play',mode=mode,commits=len(commits),step=commits[-1]['r2'],tick=tick))
                reported=len(commits)//48
            if len(commits)>=385:break
        else:raise AssertionError('two complete32-step passes not reached')
        # Fast sync0 has two clocks/step versus six microsteps/step. Stop
        # only at a full Main boundary,allowing its atomic three-commit batch.
        assert 385<=len(commits)<=387 and [(e['r1'],e['r2'],e['r3']) for e in commits]==[(0,(i//6)%32,i%6) for i in range(len(commits))]
        stop_live=[len(active(p)) for p in players];assert stop_live==[1,0,0,1,1,0,0,0],stop_live
        stop=len(trace);button(17);assert s.snapshot()['transport']==0
        assert not any(active(p) for p in players)
        for _ in range(8):service()
        stream=[bytes(p['bytes'][a:]) for p,a in zip(uart.ports,wire)];assert stream[0]==stream[1]
        messages=decode_midi(stream[0]);notes=[m for m in messages if len(m)==3]
        held=set();counts=Counter()
        for m in notes:
            assert m[1]==60 and m[2]==(96 if m[0]&0xF0==0x90 else 0),m
            track=m[0]&15;key=(track,m[1]);counts[(track,m[0]&0xF0)]+=1
            if m[0]&0xF0==0x90:assert key not in held;held.add(key)
            else:assert key in held;held.remove(key)
        assert not held and messages[0]==[0xFA] and messages[-1]==[0xFC]
        assert sum(m==[0xFC] for m in messages)==1 and sum(m==[0xF8] for m in messages)==129
        expiry=[]
        for t in range(8):
            want=3 if sources[t]==0 else 2
            assert counts[t,0x90]==counts[t,0x80]==want,(t,counts)
            ons=[e for e in trace[start:stop] if e['pc']==0x0804B0D4 and e['r0']==players[t]]
            assert len(ons)==want and all(e['commit'][1:]==(sources[t],0) for e in ons)
            offs=[e for e in trace[start:] if e['pc']==0x0804B170 and e['r0']==players[t]]
            natural=[e for e in offs if e['caller']==0x0804AF9F]
            stopped=[e for e in offs if e['caller']==0x0804AEE5]
            assert len(natural)==(1 if t==3 else 2),(t,offs)
            assert len(stopped)==stop_live[t] and len(natural)+len(stopped)==want,(t,offs)
            expiry.append(dict(track=t,natural=natural,stopped=stopped))
        assert raw()==programmed and fault()=='000000'
        runs.append(dict(mode=mode,messages=messages,live_before_stop=stop_live,trace=trace[start:],commits=len(commits),boundaries=boundaries,expiry=expiry))
        if progress:progress(dict(stage='complete',mode=mode,notes=len(notes)))
    final=s.snapshot()
    for key in ('raw','project','metadata_sha256','heap','allocations','nor_mutations'):assert initial[key]==final[key],key
    assert not s.io and not h.invalid and h.validate_stacks() and bytes(u.mem_read(BASE,len(s.image)))==s.image
    return dict(initial=initial,final=final,program=program,runs=runs,inputs=s.inputs,trace=trace,uart=uart.report(),timer_peer=timer.report(),
        main_cycles=cycles,timer_events=tick,midi_faults=fault(),project_io=s.io,physical_test=False,
        scope='Native reset/UI Gate1,6,95,96;fastest native sync0;two modes/two32-step passes. Natural gate expiry and Stop,matched DIN messages,finite native IRQ/Main. No tie bit creation,no project/FIFO/fault/owner/debt repair,no physical timing/delivery claim.')
