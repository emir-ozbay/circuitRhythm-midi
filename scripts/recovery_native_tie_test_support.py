"""Native Projects Load + SyncAll + Mutate + IRQ66 playback of step byte6 tie.

Stock5706 UI step editors write0 to step byte6(tie),while stock Load(37B8C ->
4113A ->37E3C ->48932 SyncAll ->54AB0) reads byte6 bit0 from external NOR project
files into view+0x20 words16..23,Pattern Settings Mutate(Shift+Duplicate,573AC)
shuffles full8B step records preserving byte6,and player prepare/commit(4AEEE/
4AFBC/4B0D4) suppresses same-pitch retrigger across15->16 and31->0 boundaries.
"""
from collections import Counter
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import *
from inspect_ui import BASE,load_image
from recovery_live_mode_test_support import PROJECT_BYTES
from recovery_uart_test_support import NativeUARTPeer
from recovery_playback_test_support import decode_midi
import seq_Patch as seq


TRACK_SPECS=(
    # (steps_and_gates_and_pitches, tied_steps)
    (((15,6,72),(16,6,72)),(15,)),                 # t0: 15->16 same-pitch tie, gate6
    (((15,6,72),(16,6,72)),()),                    # t1: 15->16 untied same-pitch control
    (((0,6,72),(31,6,72)),(31,)),                  # t2: 31->0 wrap same-pitch tie, gate6
    (((0,6,72),(31,6,72)),()),                     # t3: 31->0 wrap untied same-pitch control
    (((15,6,72),(16,95,72)),(15,)),                # t4: 15->16 same-pitch tie into gate95
    (((0,6,74),(31,6,72)),(31,)),                  # t5: 31->0 diff-pitch tie (60->62), gate6
    (((0,96,74),(31,96,72)),(31,)),                # t6: 31->0 diff-pitch tie (60->62), gate96 dual Stop
    (((15,6,72),(16,6,72),(17,6,72)),(15,16)),     # t7: 15->16->17 chain tie, gate6
)


def exercise_native_tie(s,timer,*,progress=None):
    h=s.h;u=h.u;initial=s.snapshot();uart=NativeUARTPeer(s,txe_credits=65536)
    players=sorted(s.objects(0x08068D24),key=lambda p:h.read(p+0x50));assert len(players)==8
    sync_objs=sorted(s.objects(0x080696A0),key=lambda o:h.read(o+4));assert len(sync_objs)==8
    views=[h.read(s.grid+0x74+4*t) for t in range(8)]
    count=cycles=tick=0;mode=None;trace=[];program=[];runs=[];mutations=[];last_commit={};prep={}
    sync_calls=[]
    stock=load_image()
    for lo,hi in ((0x0804ADA4,0x0804B214),(0x08054AB0,0x08054B22),(0x080573AC,0x0805746C)):
        assert s.image[lo-BASE:hi-BASE]==stock[lo-BASE:hi-BASE]
    def raw():return bytes(u.mem_read(s.raw,PROJECT_BYTES))
    def fault():return bytes(u.mem_read(seq.SEQ_STATE_ADDR+seq.OFF_MIDI_CONTEXT_FAULT,3)).hex()
    def active(p):
        node=u.mem_read(p+0x8A,1)[0];seen=[]
        while node!=255:
            assert node<8 and node not in seen;seen.append(node);node=u.mem_read(p+0x78+2*node,1)[0]
        return seen
    def tie_store_bits(t):
        store20=h.read(sync_objs[t]+0x20);bits=[]
        for step in range(32):
            word=s.value(store20,16+(step>>2))
            if (word>>(8*(step&3)))&1:bits.append(step)
        return tuple(bits)
    def observe(uc,pc,size,_):
        p=uc.reg_read(UC_ARM_REG_R0)
        if pc==0x08054AB0:
            sync_calls.append(dict(view=p,cycle=cycles,input=s.active_input))
            return
        row=dict(pc=pc,mode=mode,tick=tick,input=s.active_input,r0=p,r1=uc.reg_read(UC_ARM_REG_R1),
            r2=uc.reg_read(UC_ARM_REG_R2),r3=uc.reg_read(UC_ARM_REG_R3),caller=uc.reg_read(UC_ARM_REG_LR))
        if pc==0x0804AEEE and p in players:prep[p]=(row['r1'],row['r2'],row['r3'])
        if pc==0x0804AFBC and p in players:last_commit[p]=(row['r1'],row['r2'],row['r3'])
        row['prepare']=prep.get(p);row['commit']=last_commit.get(p);trace.append(row)
    for pc in (0x0804AEEE,0x0804AFBC,0x0804B0D4,0x0804B170,0x0804AED8,0x08054AB0):
        u.hook_add(UC_HOOK_CODE,observe,begin=pc,end=pc)
    def service():
        nonlocal cycles
        uart.service();s.cycle(budget=2000000);cycles+=1;uart.service();assert fault()=='000000'
    def completed():
        for _ in range(256):
            uart.service();timer.deliver();service()
            if s.snapshot()['phase']==0:
                for _ in range(8):uart.service();timer.deliver();service()
                return
        raise AssertionError('native project I/O did not complete')
    def event(kind,i):
        nonlocal count
        row=s.input(kind,i);count+=1
        if count%64==0 and s.snapshot()['held_pads']==0:service()
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
    s.shortcut();assert s.snapshot()['mode']==1
    for t,(steps,tied) in enumerate(TRACK_SPECS):
        button(t);ps=h.read(views[t]+0x60);enter(4,12);page(ps,1);pad(15);pad(23);pad(28)
        for step,gate,pitch in steps:
            enter(2,10);page(ps,step//16);event('pad_down',step%16);pad(27);event('pad_up',step%16)
            enter(3,11);page(ps,step//16);event('pad_down',step%16)
            pad(30);pad(31)
            if gate==95:pad(31)
            elif gate==6:pad(16)
            event('pad_up',step%16)
            if pitch!=72:
                assert pitch==74
                enter(1,9);page(ps,step//16);event('pad_down',step%16);pad(25);event('pad_up',step%16)
        assert tie_store_bits(t)==()
        program.append(dict(track=t,steps=list(steps),tied=list(tied)))
        if progress:progress(dict(stage='program',track=t))
    button(8)
    for _ in range(4):service()
    # Save programmed project to slot1 on external NOR flash medium.
    s._invoke(0x08037ED0,(s.project,1,0,0),label='native_Save_slot1',budget=2000000)
    completed();saved_untied=raw()
    # Prepare external NOR flash slot1 project file with step byte6 tie=1 on
    # the external SparseNOR medium (zero host writes to MCU RAM).
    nor=s.h.medium.data;patched_nor_offsets=[]
    file_pos=nor.find(saved_untied)
    assert file_pos>=0 and nor.find(saved_untied,file_pos+1)==-1,file_pos
    for t,(steps,tied) in enumerate(TRACK_SPECS):
        for step in tied:
            off=file_pos+0x2E4+t*0x5140+8*step+6
            assert nor[off]==0
            nor[off]=1
            patched_nor_offsets.append(dict(track=t,step=step,nor_offset=off))
        assert tie_store_bits(t)==()
    # Native UI Projects(button26) + pad1(Load slot1) reads external NOR via
    # QSPI DMA + FatFs into s.raw and runs 08037E3C -> 08048932(SyncAll) -> 08054AB0.
    sync_before=len(sync_calls)
    button(26);assert (s.value(h.read(s.ctrl+0x14))&0xFF)==6
    pad(1);completed()
    button(8);assert (s.value(h.read(s.ctrl+0x14))&0xFF)==0 and s.snapshot()['grid_mode']==0
    assert len(sync_calls)>=sync_before+8
    loaded=raw()
    for t,(steps,tied) in enumerate(TRACK_SPECS):
        assert tie_store_bits(t)==tied,(t,tie_store_bits(t),tied)
        for step,gate,pitch in steps:
            rec=loaded[0x2E4+t*0x5140+8*step:0x2E4+t*0x5140+8*(step+1)]
            assert rec==bytes((pitch,gate,1,96,7,255,1 if step in tied else 0,0)),(t,step,rec.hex())
    for enabled in (0,1):
        mode=enabled
        if s.snapshot()['mode']!=enabled:
            row=s.shortcut();assert row['after']['mode']==enabled and raw()==loaded
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
                if threshold==97:
                    assert counts[0]==counts[1]==counts[4]==counts[7]==1,(threshold,counts)
                else:
                    assert counts[2]==counts[3]==counts[5]==1 and counts[6]==2,(threshold,counts)
                boundaries.append(dict(threshold=threshold,commits=len(commits),counts=counts,tick=tick))
            if progress and len(commits)//48!=reported and commits:
                progress(dict(stage='play',mode=mode,commits=len(commits),step=commits[-1]['r2'],tick=tick))
                reported=len(commits)//48
            if len(commits)>=385:break
        else:raise AssertionError('two complete32-step passes not reached')
        assert 385<=len(commits)<=387 and [(e['r1'],e['r2'],e['r3']) for e in commits]==[(0,(i//6)%32,i%6) for i in range(len(commits))]
        stop_live=[len(active(p)) for p in players]
        assert stop_live==[0,0,1,1,0,1,2,0],stop_live
        stop=len(trace);button(17);assert s.snapshot()['transport']==0
        assert not any(active(p) for p in players)
        for _ in range(8):service()
        stream=[bytes(p['bytes'][a:]) for p,a in zip(uart.ports,wire)];assert stream[0]==stream[1]
        messages=decode_midi(stream[0]);notes=[m for m in messages if len(m)==3]
        held=set();counts=Counter()
        for m in notes:
            assert m[1] in (60,62) and m[2]==(96 if m[0]&0xF0==0x90 else 0),m
            track=m[0]&15;key=(track,m[1]);counts[(track,m[0]&0xF0)]+=1
            if m[0]&0xF0==0x90:assert key not in held;held.add(key)
            else:assert key in held;held.remove(key)
        assert not held and messages[0]==[0xFA] and messages[-1]==[0xFC]
        assert sum(m==[0xFC] for m in messages)==1 and sum(m==[0xF8] for m in messages)==129
        expected_ons={0:2,1:4,2:3,3:5,4:2,5:5,6:5,7:2}
        expected_natural={0:2,1:4,2:2,3:4,4:2,5:4,6:3,7:2}
        expiry=[]
        for t in range(8):
            want=expected_ons[t]
            assert counts[t,0x90]==counts[t,0x80]==want,(t,counts)
            ons=[e for e in trace[start:stop] if e['pc']==0x0804B0D4 and e['r0']==players[t]]
            # Note: 0804B0D4 is entered for every active step, but when player+0x138
            # tie suppression bit is set, 0804B0D4 skips vtable+0 Note On emission!
            # So counts[t,0x90] is the exact emitted Note On count, whereas len(ons)
            # is the total step triggers (4 for t0, 4 for t2, 4 for t4, 6 for t7).
            offs=[e for e in trace[start:] if e['pc']==0x0804B170 and e['r0']==players[t]]
            natural=[e for e in offs if e['caller'] in (0x0804AF9F,0x0804B1B7)]
            stopped=[e for e in offs if e['caller']==0x0804AEE5]
            assert len(natural)==expected_natural[t],(t,len(natural),expected_natural[t],offs)
            assert len(stopped)==stop_live[t] and len(natural)+len(stopped)==want,(t,offs)
            expiry.append(dict(track=t,emitted_ons=counts[t,0x90],step_triggers=len(ons),natural=len(natural),stopped=len(stopped)))
        assert raw()==loaded and fault()=='000000'
        runs.append(dict(mode=mode,messages=messages,live_before_stop=stop_live,commits=len(commits),boundaries=boundaries,expiry=expiry))
        if progress:progress(dict(stage='complete',mode=mode,notes=len(notes)))
    # Verify Pattern Settings Mutate (Shift+Duplicate, 080573AC) preserves full
    # 8-byte step records including byte6==1 tie bits in both modes, then reload slot1.
    for enabled in (0,1):
        if s.snapshot()['mode']!=enabled:
            row=s.shortcut();assert row['after']['mode']==enabled
        button(7);enter(4,12)
        before=raw();offset=0x2E4+7*0x5140
        records=[before[offset+8*i:offset+8*i+8] for i in range(32)]
        assert sum(r[6]==1 for r in records)==2
        event('button_down',27);button(24);event('button_up',27);service()
        after=raw()
        result=[after[offset+8*i:offset+8*i+8] for i in range(32)]
        assert Counter(records)==Counter(result) and sum(r[6]==1 for r in result)==2
        assert len( tie_store_bits(7) )==2
        mutations.append(dict(mode=enabled,track=7,tied_steps_after=list(tie_store_bits(7))))
    button(8);button(26);pad(1);completed();button(8);service()
    assert raw()==loaded
    for t,(_,tied) in enumerate(TRACK_SPECS):assert tie_store_bits(t)==tied
    final=s.snapshot()
    for key in ('raw','project','heap','allocations'):assert initial[key]==final[key],key
    assert not h.invalid and h.validate_stacks() and bytes(u.mem_read(BASE,len(s.image)))==s.image
    return dict(initial=initial,final=final,program=program,patched_nor_offsets=patched_nor_offsets,
        sync_all_calls=len(sync_calls),runs=runs,mutations=mutations,uart=uart.report(),timer_peer=timer.report(),
        main_cycles=cycles,timer_events=tick,midi_faults=fault(),project_io=s.io,
        application_ram_repaired=False,boot_objects_seeded=False,firmware_instruction_stubs=False,physical_test=False,
        scope='Native UI Projects Load(37B8C ->4113A ->37E3C ->48932 SyncAll ->54AB0) of external NOR slot1 project containing step byte6 tie=1 records;live view+0x20 words16..23 population;Pattern Settings Shift+Duplicate Mutate(573AC) preserving8B tied records;native IRQ66/Main playback and Stop across15->16,31->0 and15->16->17 boundaries in both modes.')
