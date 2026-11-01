"""Reset-created sequencer players driven by finite synthetic AppTimer debt.

Only controller callbacks and native2677A/Main/IRQ service are invoked. Timer
debt is an explicit test input,not elapsed time or a hardware timer model.
No player,project,store,LED,ownership,FIFO or instruction is seeded/repaired.
"""
import struct
from collections import Counter
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_LR
from inspect_ui import BASE,load_image
from recovery_live_mode_test_support import PROJECT_BYTES
from recovery_uart_test_support import NativeUARTPeer
import seq_Patch as seq
import midi_dense_stop_patch as dense
from thumb_asm import bl


def decode_midi(data):
    """Decode this bounded channel/realtime stream,including running status."""
    status=None;pending=[];messages=[]
    for byte in data:
        if byte>=0xF8:messages.append([byte]);continue
        if byte&0x80:
            assert not pending and 0x80<=byte<0xF0,('unexpected MIDI status',byte,pending)
            status=byte;continue
        assert status is not None
        pending.append(byte)
        needed=1 if status&0xF0 in (0xC0,0xD0) else 2
        if len(pending)==needed:messages.append([status,*pending]);pending=[]
    assert not pending
    return messages


def exercise_native_playback(s,*,progress=None,timer_peer=None):
    h=s.h;u=h.u;initial=s.snapshot();cycles=0;tick=0;enabled=None
    uart=NativeUARTPeer(s,txe_credits=65536)
    players=sorted(s.objects(0x08068D24),key=lambda p:h.read(p+0x50))
    assert len(players)==8
    views=[h.read(s.grid+0x74+4*t) for t in range(8)]
    stock=load_image()
    for lo,hi in ((0x0804ADA4,0x0804B1D0),(0x08055008,dense.SITE),(dense.SITE+4,0x0805552C)):
        assert s.image[lo-BASE:hi-BASE]==stock[lo-BASE:hi-BASE]
    assert stock[dense.SITE-BASE:dense.SITE-BASE+4]==dense.EXPECTED
    assert s.image[dense.SITE-BASE:dense.SITE-BASE+4]==bl(dense.SITE,dense.CODE_BASE)
    for t,(p,v) in enumerate(zip(players,views)):
        assert h.read(p+0x50)==s.raw+0x2E4+t*0x5140
        assert h.read(p+8)==h.read(v+0x1C)
    trace=[];leds=[];runs=[];guards=[];program=[];timer_inputs=[];page_events=[]
    def observe(uc,pc,size,_):
        r0=uc.reg_read(UC_ARM_REG_R0)
        trace.append(dict(mode=enabled,tick=tick,input=s.active_input,pc=pc,r0=r0,
            r1=uc.reg_read(UC_ARM_REG_R1),r2=uc.reg_read(UC_ARM_REG_R2),
            r3=uc.reg_read(UC_ARM_REG_R3),caller=uc.reg_read(UC_ARM_REG_LR)))
    for pc in (0x0804AEEE,0x0804AFBC,0x0804AED8,0x080552F6):
        u.hook_add(UC_HOOK_CODE,observe,begin=pc,end=pc)
    def raw():return bytes(u.mem_read(s.raw,PROJECT_BYTES))
    def fault():return bytes(u.mem_read(seq.SEQ_STATE_ADDR+seq.OFF_MIDI_CONTEXT_FAULT,3)).hex()
    def service():
        nonlocal cycles
        uart.service();s.cycle(budget=2000000);cycles+=1;uart.service()
        assert fault()=='000000'
    def event(kind,i):
        row=s.input(kind,i);assert fault()=='000000';return row
    def button(i):
        row=event('button_down',i);event('button_up',i);return row
    def pad(i):event('pad_down',i);event('pad_up',i)
    def active(p):
        node=u.mem_read(p+0x8A,1)[0];result=[]
        while node!=255:
            assert node<8 and node not in [n['node'] for n in result]
            result.append(dict(node=node,note=u.mem_read(p+0x8E+4*node,1)[0]))
            node=u.mem_read(p+0x78+2*node,1)[0]
        return result
    def mode(value):
        if s.snapshot()['mode']!=value:
            service();row=s.shortcut();assert row['after']['mode']==value
            assert row['before']['raw_sha256']==row['after']['raw_sha256']
            service()
    def render(track,step,*,stopped=False):
        button(track);v=views[track];page=s.value(h.read(v+0x60))
        s._invoke(0x0804DD1C,(s.grid,0,0,0),label='native_playback_compositor')
        flags=list(struct.unpack('<32H',u.mem_read(v+0x74,64)))
        # Native5D458/5D290 uses bit6 for the running player cursor. Bit0
        # follows a different recorder/edit-time store and is not this clock.
        assert [i for i,x in enumerate(flags) if x&64]==([] if stopped else [step])
        expected=[1 if i==step and not stopped else 24 if i in (0,15,16,31) else 25 for i in range(32)]
        source=bytes(u.mem_read(h.read(h.read(v+4)),64))
        assert list(struct.unpack('<32H',source))==expected,(enabled,track,step,flags,source.hex())
        data=bytes(u.mem_read(h.read(h.read(s.grid+4)),64))
        if enabled:
            # The auxiliary view's remembered page may stay1. Main view's
            # effective offset is0 without erasing that stock page selection.
            assert data==source
        else:
            assert page in (0,1) and data[:32]==source[page*32:page*32+32]
            bottom=h.read(s.grid+0x14+4*track)
            assert data[32:]==bytes(u.mem_read(h.read(h.read(bottom+4)),32))
        leds.append(dict(mode=enabled,track=track,step=step,stopped=stopped,page=page,effective_page=0 if enabled else page,
            flags=flags,source=source.hex(),grid=data.hex()))
    # Program a32-step sparse pattern on all8 tracks exclusively through UI.
    assert initial['mode']==initial['transport']==initial['held_pads']==0
    mode(1)
    for t in range(8):
        button(t)
        for _ in range(2):
            if s.snapshot()['grid_mode']==4:break
            button(12)
        assert s.snapshot()['grid_mode']==4
        if s.value(h.read(views[t]+0x60))!=1:button(21)
        pad(15);button(8)
        assert s.snapshot()['grid_mode']==0
        base=0x2E4+t*0x5140
        assert raw()[base+0x100:base+0x104]==bytes((31,0,3,0))
        assert all(raw()[base+8*i+3]==0 for i in range(32))
        for i in (0,15,16,31):pad(i)
        records=[raw()[base+8*i:base+8*i+8] for i in range(32)]
        assert [i for i,r in enumerate(records) if r[3]]==[0,15,16,31]
        assert all(records[i]==bytes.fromhex('4806016007ff0000') for i in (0,15,16,31))
        program.append(dict(track=t,records=[r.hex() for r in records]))
        service()
    programmed=raw();programmed_sha=s.snapshot()['raw_sha256']
    for enabled in (0,1):
        mode(enabled);assert raw()==programmed
        wire_start=[len(p['bytes']) for p in uart.ports];start=len(trace);tick=0
        assert all(not active(p) for p in players)
        row=button(17);assert row['after']['transport']==1;service()
        seen=[]
        for block in range(400):
            n=1 if block==0 else 16
            tick+=n;timer_inputs.append(dict(mode=enabled,count=n,total=tick))
            if timer_peer is None:
                # Legacy synthetic debt path remains a separate evidence tier.
                s.service_timer_ticks(n);service()
            else:
                assert timer_peer.s is s and timer_peer.debt()==0
                timer_peer.deliver(n)
                assert timer_peer.debt()==n
                for remaining in range(n-1,-1,-1):
                    service();assert timer_peer.debt()==remaining
            commits=[e for e in trace[start:] if e['pc']==0x0804AFBC and e['r0']==players[0] and e['r3']==0]
            steps=[e['r2'] for e in commits]
            assert steps==list(range(min(32,len(steps))))+([0] if len(steps)==33 else []),steps
            if len(steps)>len(seen):
                assert len(steps)==len(seen)+1
                step=steps[-1]
                for t in range(8):render(t,step)
                seen=steps
                assert raw()==programmed
                if step==16:
                    before=s.snapshot();r=s.shortcut();assert r['after']['mode']==enabled
                    assert before['raw_sha256']==r['after']['raw_sha256']
                    guards.append(dict(mode=enabled,transport=1,step=step))
                if enabled and step in (15,16):
                    saved_page=s.value(h.read(views[7]+0x60))
                    button(21)
                    new_page=s.value(h.read(views[7]+0x60))
                    assert new_page in (0,1) and raw()==programmed
                    s._invoke(0x0804DD1C,(s.grid,0,0,0),label='native_running_page_compositor')
                    source=bytes(u.mem_read(h.read(h.read(views[7]+4)),64))
                    assert bytes(u.mem_read(h.read(h.read(s.grid+4)),64))==source
                    page_events.append(dict(step=step,before=saved_page,after=new_page,effective_offset=0,grid=source.hex()))
                if progress:progress(dict(mode=enabled,timer_debt=tick,steps=seen,leds=len(leds),main_cycles=cycles))
                if len(seen)==33:break
        else:raise AssertionError('32-step wrap not reached within6400 finite timer inputs')
        live=[active(p) for p in players];assert all(len(a)==1 and a[0]['note']==72 for a in live),live
        stop_start=len(trace);row=button(17);assert row['after']['transport']==0;service()
        assert all(not active(p) for p in players)
        for t in range(8):render(t,0,stopped=True)
        stop=trace[stop_start:]
        assert [e['r0'] for e in stop if e['pc']==0x0804AED8]==players
        assert [e['r0'] for e in stop if e['pc']==0x080552F6]==players
        streams=[bytes(p['bytes'][a:]) for p,a in zip(uart.ports,wire_start)]
        assert streams[0]==streams[1]
        messages=decode_midi(streams[0]);notes=[m for m in messages if len(m)==3]
        counts=Counter(tuple(m) for m in notes)
        assert counts==Counter({(0x90|t,60,96):5 for t in range(8)})+Counter({(0x80|t,60,0):5 for t in range(8)}),counts
        held=set()
        for m in messages:
            if len(m)!=3:continue
            key=(m[0]&15,m[1])
            if m[0]&0xF0==0x90:assert key not in held;held.add(key)
            else:assert m[0]&0xF0==0x80 and key in held;held.remove(key)
        assert not held and messages[0]==[0xFA] and messages[-1]==[0xFC]
        assert sum(m==[0xF8] for m in messages)==193
        for t,p in enumerate(players):
            events=[e for e in trace[start:stop_start] if e['pc']==0x0804AFBC and e['r0']==p]
            assert [(e['r1'],e['r2'],e['r3']) for e in events]==[(0,i//6%32,i%6) for i in range(193)]
        assert all(not (a['held']|a['held_bits']) for a in s.snapshot()['step_owners'])
        assert raw()==programmed
        runs.append(dict(mode=enabled,timer_debt=tick,steps=seen,live_before_stop=live,
            native_stop_flushes=8,uart_messages=messages,clock_count=sum(m==[0xF8] for m in messages),
            note_ons=40,note_offs=40,raw_sha256=s.snapshot()['raw_sha256']))
    final=s.snapshot()
    assert final['transport']==final['held_pads']==final['shift']==0
    assert not s.io and not h.invalid and h.validate_stacks() and fault()=='000000'
    for k in ('raw','project','metadata_sha256','heap','allocations','nor_mutations'):assert initial[k]==final[k],k
    assert bytes(u.mem_read(BASE,len(s.image)))==s.image
    return dict(initial=initial,final=final,players=players,tracks=list(range(8)),program=program,
        programmed_raw_sha256=programmed_sha,runs=runs,leds=leds,held_guards=guards,trace=trace,
        timer_inputs=timer_inputs,timer_events=s.timer_events,page_events=page_events,inputs=s.inputs,main_cycles=cycles,
        sample_status_inputs=h.sample_status_reads,uart=uart.report(),project_io=s.io,midi_faults=fault(),
        timer_peer=timer_peer.report() if timer_peer is not None else None,
        firmware_instruction_stubs=False,startup_objects_seeded=False,physical_test=False,
        scope=('Finite native TIM compare/IRQ66/Main358/slot11/2B750/application370 chain;direct synthetic debt adapter forbidden. ' if timer_peer is not None else 'Finite direct synthetic AppTimer debt invokes2677A and installed callbacks. ')+
        'One native reset,8 constructed players,both runtime modes,UI-programmed32-step patterns.193 ordered microstep commits per player/mode,1..32..1 live bit6 cursor and LED RAM composites,Normal stock bottom layout,Sequencer effective page0,running mode rejection,native Stop with8 live notes,40 matched UART On/Off and193 Clock per mode/port. No RAM repair,FIFO clearing,GPIO/event queue,autonomous elapsed time,NVIC arbitration,USB RX/baud/DSP execution/physical MIDI timing. Existing strict SPI,NOR/ADC/USB,disabled-DWT/non-nested FPU limits remain.')
