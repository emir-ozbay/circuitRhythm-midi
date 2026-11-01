"""Live native microstep/probability edits,with read-only player decisions.

Only controller callbacks and finite IRQ/Main/peripheral inputs are supplied.
The player's native PRNG/state is observed,never seeded or overridden.
"""
from collections import Counter
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import *
from inspect_ui import BASE,load_image
from recovery_live_mode_test_support import PROJECT_BYTES
from recovery_uart_test_support import NativeUARTPeer
from recovery_playback_test_support import decode_midi
import seq_Patch as seq
import midi_recovery_patch as fixed
import midi_recovery_prototype as rp


def exercise_running_edits(s,timer,*,progress=None):
    h=s.h;u=h.u;initial=s.snapshot();uart=NativeUARTPeer(s,txe_credits=65536)
    players=sorted(s.objects(0x08068D24),key=lambda p:h.read(p+0x50));assert len(players)==8
    views=[h.read(s.grid+0x74+4*t) for t in range(8)]
    trace=[];edits=[];guards=[];runs=[];program=[];midi_offs=[];counts={p:0 for p in players};prepared={};current={}
    mode=None;stage='program';tick=cycles=inputs=0;preparing=None
    s.running_edit_debug=dict(trace=trace,edits=edits,guards=guards,runs=runs,program=program,midi_offs=midi_offs)
    stock=load_image()
    for lo,hi in ((0x0804ADA4,0x0804B214),(0x08056F0C,0x080571BC),(0x0805746C,0x080576DC)):
        assert s.image[lo-BASE:hi-BASE]==stock[lo-BASE:hi-BASE]
    def raw():return bytes(u.mem_read(s.raw,PROJECT_BYTES))
    def offset(t,step):return 0x2E4+t*0x5140+8*step
    def record(t,step):return bytes(u.mem_read(s.raw+offset(t,step),8))
    def fault():return bytes(u.mem_read(seq.SEQ_STATE_ADDR+seq.OFF_MIDI_CONTEXT_FAULT,3)).hex()
    def active(p):
        n=u.mem_read(p+0x8A,1)[0];slots=[];notes=[]
        while n!=255:
            assert n<8 and n not in slots;slots.append(n);notes.append(u.mem_read(p+0x8E+4*n,1)[0]);n=u.mem_read(p+0x78+2*n,1)[0]
        return sorted(notes)
    def active_all():return [active(p) for p in players]
    def observe(uc,pc,size,_):
        nonlocal preparing
        p=uc.reg_read(UC_ARM_REG_R0)
        if pc==0x08031FC6:
            identifier=uc.reg_read(UC_ARM_REG_R1);pitch=uc.reg_read(UC_ARM_REG_R2)
            if u.mem_read(p+0x18,1)[0]&1:
                channel=u.mem_read(h.read(p+0xC)+((identifier-16)&255),1)[0]
                notes=active(players[channel]) if channel<8 else []
                row=dict(mode=mode,stage=stage,tick=tick,input=s.active_input,channel=channel,pitch=pitch,player_notes=notes)
                midi_offs.append(row)
                if stage in ('micro33_5','probability','delete_recreate'):
                    assert pitch+12 not in notes,('UI prematurely released an active player note',row)
            return
        if pc==0x0804AF1A:
            assert preparing is not None
            row=preparing
            assert uc.reg_read(UC_ARM_REG_R1)==row['record'][4]
            assert uc.reg_read(UC_ARM_REG_R2)&7==row['threshold']
            row['native_compare_seen']=True;return
        if p not in players:return
        row=dict(pc=pc,mode=mode,stage=stage,tick=tick,input=s.active_input,player=p,
            r1=uc.reg_read(UC_ARM_REG_R1),r2=uc.reg_read(UC_ARM_REG_R2),r3=uc.reg_read(UC_ARM_REG_R3),caller=uc.reg_read(UC_ARM_REG_LR))
        if pc==0x0804AEEE and row['r3']<6:
            data=bytes(u.mem_read(h.read(p+0x50)+row['r1']*0xA28+row['r2']*8,8))
            threshold=u.mem_read(p+4,1)[0]&7
            row.update(record=list(data),threshold=threshold,
                expected=bool(data[2]&(1<<row['r3'])) and data[4]>=threshold,native_compare_seen=False)
            slot=(p,row['r1'],row['r2'],row['r3']);assert slot not in prepared
            prepared[slot]=row;preparing=row
        elif pc==0x0804AFBC:
            q=prepared.pop((p,row['r1'],row['r2'],row['r3']))
            row.update(key=(mode,p,counts[p]),record=q['record'],threshold=q['threshold'],expected=q['expected'],native_compare_seen=q['native_compare_seen'])
            if row['record'][2]:assert row['native_compare_seen']
            current[p]=row;counts[p]+=1
        elif pc==0x0804B0D4:
            row['key']=current[p]['key'];row['position']=(current[p]['r1'],current[p]['r2'],current[p]['r3'])
            assert row['r1']==(current[p]['record'][0] or 48) and row['r2']==current[p]['record'][3]
        trace.append(row)
    for pc in (0x0804AEEE,0x0804AF1A,0x0804AFBC,0x0804B0D4,0x0804B170,0x0804AED8,0x08031FC6):u.hook_add(UC_HOOK_CODE,observe,begin=pc,end=pc)
    def queues():
        rows=[]
        for n in range(3):
            e=fixed.STATE_BASE+rp.HEADER_SIZE+n*rp.ENTRY_SIZE;p=h.read(e);q=h.read(p+4)
            cap=int.from_bytes(u.mem_read(q+4,2),'little');head=int.from_bytes(u.mem_read(q+6,2),'little');tail=int.from_bytes(u.mem_read(q+8,2),'little')
            rows.append(dict(bytes=(head-tail)%cap,flags=u.mem_read(e+rp.FLAGS,1)[0],deferred=int.from_bytes(u.mem_read(e+rp.COUNT,2),'little')))
        return rows
    def service():
        nonlocal cycles
        uart.service();s.cycle(budget=2000000);cycles+=1;uart.service();assert fault()=='000000'
    def settle():
        for _ in range(16):
            service()
            if all(not(r['bytes'] or r['flags'] or r['deferred']) for r in queues()):return
        raise AssertionError(('closing queues did not drain',queues()))
    def event(kind,i):
        nonlocal inputs
        row=s.input(kind,i);inputs+=1
        if inputs%16==0:service()
        assert fault()=='000000';return row
    def button(i):row=event('button_down',i);event('button_up',i);return row
    def pad(i):event('pad_down',i);event('pad_up',i)
    def enter(gm,key):
        for _ in range(2):
            if s.snapshot()['grid_mode']==gm:return
            button(key)
        assert s.snapshot()['grid_mode']==gm
    def page(t,want):
        ps=h.read(views[t]+0x60)
        if s.value(ps)!=want:button(21)
        assert s.value(ps)==want
    def select(t,step,gm):button(t);enter(gm,11 if gm in (3,5) else 12 if gm==6 else 9);page(t,step//16)
    def held(t,step):
        a=s.snapshot()['step_owners'][t];assert a['held']==a['held_bits']==1<<step,(t,step,a)
    def edit(t,step,gm,local,*,hold=True,reject_mode=False):
        before_select=active_all();select(t,step,gm);assert active_all()==before_select
        v=h.read(s.grid+(0xDC if gm==5 else 0x11C)+4*t)
        if hold:event('pad_down',step%16);held(t,step)
        before=raw();old=record(t,step);voices=active_all();pos=counts.copy();pad(16+local);after=raw()
        off=offset(t,step);assert before[:off]==after[:off] and before[off+8:]==after[off+8:]
        if not hold or local>=(6 if gm==5 else 8):want=old
        elif gm==6:
            want=bytearray(old);assert old[3];want[4]=local;want=bytes(want)
        else:
            mask=old[2]^(1<<local)
            if not mask:want=bytes.fromhex('0006000007ff0000')
            elif not old[2]:want=bytes((s.value(h.read(v+0x24))&255,6,mask,96,7,255,0,0))
            else:want=bytearray(old);want[2]=mask;want=bytes(want)
        assert record(t,step)==want,(mode,t,step,gm,local,hold,old.hex(),record(t,step).hex(),want.hex())
        assert active_all()==voices and counts==pos,('live edit advanced/cut player',t,step,gm,local)
        if hold:
            held(t,step)
            if reject_mode:
                row=s.shortcut();assert row['after']['mode']==mode and raw()==after;held(t,step)
                guards.append(dict(mode=mode,track=t,step=step,view=gm))
            event('pad_up',step%16)
            a=s.snapshot()['step_owners'][t];assert not(a['held'] or a['held_bits'])
        edits.append(dict(mode=mode,stage=stage,track=t,step=step,view=gm,local=local,held=hold,before=old.hex(),after=want.hex(),voices=voices))
    def set_pitch(t,step,pitch=None):
        # Pressing the already assigned key is the stock note toggle,not
        # an idempotent setter;do not erase/recreate the step unnecessarily.
        if pitch is not None and record(t,step)[0]==pitch:return pitch
        before=active_all();button(t);enter(1,9);page(t,step//16);v=h.read(s.grid+0x54+4*t);km=h.read(v+0x4C)
        window=s.value(h.read(v+0x48));stride=u.mem_read(km+0x19C,1)[0];keys=[]
        for key in range(16,32):
            idx=(key+(5-window)*stride*8)&255;assert idx<128
            n=u.mem_read(km+8+idx,1)[0]
            if n and (n==pitch if pitch is not None else n!=72):keys.append((key,n))
        assert keys,(t,step,pitch);key,note=keys[0]
        event('pad_down',step%16);pad(key);event('pad_up',step%16);assert record(t,step)[0]==note
        assert active_all()==before
        return note
    def gate96(t,step):
        select(t,step,3);before=active_all();event('pad_down',step%16);pad(30);pad(31);event('pad_up',step%16)
        assert record(t,step)[1]==96 and active_all()==before
    def advance(predicate,label,limit=2400):
        nonlocal tick
        for n in range(limit):
            uart.service();timer.deliver();tick+=1;service()
            if predicate():
                if progress:progress(dict(stage=label,mode=mode,tick=tick,commits=counts[players[0]]))
                return
        raise AssertionError(('finite IRQ stage not reached',label,tick,current.get(players[0])))
    if progress:progress(dict(stage='boot_complete'))
    s.shortcut();assert s.snapshot()['mode']==1
    for t in range(8):
        button(t);enter(4,12);page(t,0);event('button_down',27);pad(15);event('button_up',27);page(t,1);pad(0);pad(23);pad(28)
        for step in (15,16):
            button(10);assert s.snapshot()['grid_mode']==2;page(t,step//16)
            event('pad_down',step%16);pad(27);event('pad_up',step%16);gate96(t,step)
        pitch=set_pitch(t,16)
        assert record(t,15)==bytes((72,96,1,96,7,255,0,0)) and record(t,16)==bytes((pitch,96,1,96,7,255,0,0))
        header=raw()[offset(t,0)+0x100:offset(t,0)+0x104];assert header==bytes((16,15,0,0)),header.hex()
        program.append(dict(track=t,second_pitch=pitch,header=header.hex()))
        if progress:progress(dict(stage='program',track=t))
    enter(0,8);settle();programmed=raw()
    for enabled in (0,1):
        mode=enabled;stage='reset_parameters'
        if enabled:
            for t in range(8):
                select(t,15,5);event('pad_down',15);pad(20);pad(16);event('pad_up',15)
                gate96(t,15);set_pitch(t,15,72)
                select(t,16,5);event('pad_down',0);pad(18);event('pad_up',0)
                select(t,16,6);event('pad_down',0);pad(23);event('pad_up',0)
            assert raw()==programmed
        enter(0,8);settle()
        if s.snapshot()['mode']!=mode:row=s.shortcut();assert row['after']['mode']==mode and raw()==programmed
        start=len(trace);edit_start=len(edits);wire=[len(p['bytes']) for p in uart.ports]
        start_count=counts.copy();stage='start';button(17);assert s.snapshot()['transport']==1
        advance(lambda:counts[players[0]]>=start_count[players[0]]+3,'first_step')
        assert active_all()==[[72]]*8
        stage='micro33_5'
        for t in range(8):
            for step,local in ((15,5),(16,2)):
                edit(t,step,5,local,hold=False);edit(t,step,5,local,reject_mode=True)
                edit(t,step,5,14)
        stage='late5';mark=len(trace)
        advance(lambda:(current[players[0]]['r2'],current[players[0]]['r3'])==(15,5),'late5')
        assert len([e for e in trace[mark:] if e['pc']==0x0804B0D4 and e['position']==(0,15,5)])==8
        stage='probability'
        for t in range(8):
            for step in (15,16):
                edit(t,step,6,0,hold=False)
                if step==15:edit(t,step,6,3);edit(t,step,6,7)
                else:edit(t,step,6,0)
                edit(t,step,6,8)
        trials=len(trace);stage='probability_trials'
        def covered():
            rows=[e for e in trace[trials:] if e['pc']==0x0804AFBC and e['r2']==16 and e['r3']==0]
            return {e['player'] for e in rows if not e['expected']}==set(players) and any(e['expected'] for e in rows)
        advance(covered,'natural_probability_accept_and_reject',limit=2400)
        trial_rows=[e for e in trace[trials:] if e['pc']==0x0804AFBC and e['r2']==16 and e['r3'] in (0,2)]
        assert all(e['record'][4]==0 for e in trial_rows)
        stage='reach_current_step'
        advance(lambda:(current[players[0]]['r2'],current[players[0]]['r3'])==(15,2),'current_step_15')
        stage='delete_recreate'
        for t in range(8):
            edit(t,15,5,0);edit(t,15,5,5);assert record(t,15)==bytes.fromhex('0006000007ff0000')
            edit(t,15,5,4);gate96(t,15);set_pitch(t,15,72)
            assert record(t,15)==bytes((72,96,16,96,7,255,0,0))
        stage='late4';mark=len(trace)
        advance(lambda:(current[players[0]]['r2'],current[players[0]]['r3'])==(15,5),'recreated_late4')
        assert len([e for e in trace[mark:] if e['pc']==0x0804B0D4 and e['position']==(0,15,4)])==8
        expected_raw=raw();live=active_all();stage='stop';button(17);assert not s.snapshot()['transport'] and not any(active_all());settle()
        assert raw()==expected_raw
        events=trace[start:];commits=[e for e in events if e['pc']==0x0804AFBC];ons=[e for e in events if e['pc']==0x0804B0D4]
        assert Counter(tuple(e['key']) for e in ons)==Counter(tuple(e['key']) for e in commits if e['expected'])
        stream=[bytes(p['bytes'][a:]) for p,a in zip(uart.ports,wire)];assert stream[0]==stream[1]
        messages=decode_midi(stream[0]);owners=set()
        for m in messages:
            if len(m)!=3 or m[0]&0xF0 not in (0x80,0x90):continue
            key=m[0]&15,m[1]
            if m[0]&0xF0==0x90 and m[2]:assert key not in owners;owners.add(key)
            else:assert key in owners;owners.remove(key)
        assert not owners and messages[0]==[0xFA] and messages[-1]==[0xFC] and sum(m==[0xFC] for m in messages)==1
        assert not s.snapshot()['held_pads'] and fault()=='000000'
        runs.append(dict(mode=mode,commits=len(commits),player_ons=len(ons),probability_trials=trial_rows,live_before_stop=live,
            queues=queues(),messages=messages,trace=events,edits=edits[edit_start:]))
        if progress:progress(dict(stage='complete',mode=mode,tick=tick,player_ons=len(ons)))
    final=s.snapshot()
    for k in ('raw','project','metadata_sha256','heap','allocations','nor_mutations'):assert initial[k]==final[k],k
    assert not s.io and not h.invalid and h.validate_stacks() and bytes(u.mem_read(BASE,len(s.image)))==s.image
    return dict(initial=initial,final=final,program=program,runs=runs,edits=edits,held_mode_guards=guards,trace=trace,midi_offs=midi_offs,
        main_cycles=cycles,timer_events=tick,timer_peer=timer.report(),uart=uart.report(),midi_faults=fault(),project_io=s.io,
        physical_test=False,scope='Native reset/controller live mode5/6 on all8 tracks/both pages/both runtime modes;native IRQ/Main,late microstep additions,deletion/recreation and read-only native probability decisions. No PRNG/project/owner/FIFO/fault/debt repair. No statistical probability claim,GPIO/full input queue,NVIC/nested IRQ,baud/tempo/jitter or physical delivery proof.')
