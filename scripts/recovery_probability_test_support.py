"""Native mode6 probability pages,creation,parameter preservation and Mutate.

Reset-created objects/controller callbacks only. No project,store,page or
ownership seeds or repairs;native Main uses finite DSP/UART peer inputs.
"""
from collections import Counter
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1
from inspect_ui import load_image,BASE
from recovery_live_mode_test_support import PROJECT_BYTES
from recovery_uart_test_support import NativeUARTPeer
import seq_Patch as seq


def exercise_native_probability(s,*,tracks=tuple(range(8)),progress=None):
    h=s.h;u=h.u;initial=s.snapshot();count=0;cycles=0
    uart=NativeUARTPeer(s,txe_credits=65536)
    routes=[];mapping=[];cases=[];edits=[];leds=[];pages=[];guards=[];preserved=[];idle=[];mutations=[]
    stock=load_image()
    assert s.image[0x0805746C-BASE:0x080576DC-BASE]==stock[0x0805746C-BASE:0x080576DC-BASE]
    def observe(uc,pc,size,_):
        routes.append(dict(input=s.active_input,view=uc.reg_read(UC_ARM_REG_R0),pad=uc.reg_read(UC_ARM_REG_R1)))
    u.hook_add(UC_HOOK_CODE,observe,begin=0x080574C4,end=0x080574C4)
    def raw():return bytes(u.mem_read(s.raw,PROJECT_BYTES))
    def owners():return [(a['held'],a['held_bits']) for a in s.snapshot()['step_owners']]
    def service():
        nonlocal cycles
        uart.service();s.cycle(budget=2000000);cycles+=1;uart.service()
    def event(kind,i):
        nonlocal count
        row=s.input(kind,i);count+=1
        if count%16==0:service()
        assert row['after']['transport']==0
        assert bytes(u.mem_read(seq.SEQ_STATE_ADDR+seq.OFF_MIDI_CONTEXT_FAULT,3))==bytes(3)
        return row
    def button(i):
        row=event('button_down',i);event('button_up',i);return row
    def pad(i):event('pad_down',i);event('pad_up',i)
    def enter(mode,button_id):
        for _ in range(2):
            if s.snapshot()['grid_mode']==mode:break
            button(button_id)
        assert s.snapshot()['grid_mode']==mode
    def outside(before,after,offset):
        assert before[:offset]==after[:offset] and before[offset+8:]==after[offset+8:]
    def select_page(ps,page,track):
        before=raw();old=s.value(ps);button(21);after=raw()
        assert old!=page and s.value(ps)==page
        delta=[i for i,(a,b) in enumerate(zip(before,after)) if a!=b]
        if delta:
            end=0x2E4+track*0x5140+0x100
            assert delta==[end] and before[end]==15 and after[end]==31
        pages.append(dict(track=track,before=old,after=page,raw_offsets=delta))
    def owner(track,step):
        assert owners()[track]==(1<<step,1<<step),(track,step,owners()[track])
    def color(index):return int.from_bytes(stock[0x08062AB0-BASE+index*2:0x08062AB0-BASE+index*2+2],'little')
    def led(v,record):
        data=bytes(u.mem_read(h.read(h.read(v+4)),32))
        values=[color(45+i) if record[3] and i<=record[4] else color(0) for i in range(8)]+[0]*8
        expected=b''.join(n.to_bytes(2,'little') for n in values)
        assert data==expected,(record.hex(),data.hex(),expected.hex())
        return data
    def render(v,sv,page,track,mode,record):
        before=raw();s._invoke(0x0804DD1C,(s.grid,0,0,0),label='native_probability_compositor')
        top=bytes(u.mem_read(h.read(h.read(sv+4))+page*32,32));bottom=led(v,record)
        assert bytes(u.mem_read(h.read(h.read(s.grid+4)),64))==top+bottom and raw()==before
        leds.append(dict(mode=mode,track=track,page=page,probability=record[4],top=top.hex(),bottom=bottom.hex()))
    def press_probability(v,track,step,local):
        offset=0x2E4+track*0x5140+8*step;before=raw();record=before[offset:offset+8]
        n=len(routes);old_owners=owners();physical=s.snapshot()['held_pads']
        row=event('pad_down',16+local)
        assert row['after']['held_pads']==physical|(1<<(16+local))
        event('pad_up',16+local);after=raw();outside(before,after,offset)
        assert owners()==old_owners and s.snapshot()['held_pads']==physical
        assert routes[n:]==[dict(input=f'pad_down:{16+local}',view=v,pad=local)]
        if local>=8:expected=record
        else:
            expected=bytearray(record if record[3] else bytes((s.value(h.read(v+0x18))&255,6,1,96,7,255,0,0)))
            expected[4]=local;expected=bytes(expected)
        assert after[offset:offset+8]==expected,(track,step,local,record.hex(),after[offset:offset+8].hex(),expected.hex())
        led(v,expected)
        edits.append(dict(mode=s.snapshot()['mode'],track=track,step=step,local=local,before=record.hex(),after=expected.hex()))
        return expected
    def clear_step(track,step,p):
        # Existing native mode5 is the normal UI path for deleting all
        # microsteps;this prepares an empty step without host RAM seeds.
        enter(5,11);event('pad_down',p);owner(track,step)
        offset=0x2E4+track*0x5140+8*step;before=raw();mask=before[offset+2]
        if mask:
            for bit in range(6):
                if mask&(1<<bit):pad(16+bit)
        else:pad(16);pad(16)
        event('pad_up',p);after=raw();outside(before,after,offset)
        assert after[offset:offset+8]==bytes.fromhex('0006000007ff0000')
        enter(6,12)
    for enabled in (0,1):
        if s.snapshot()['mode']!=enabled:
            service();row=s.shortcut();assert row['after']['mode']==enabled
            assert row['before']['raw_sha256']==row['after']['raw_sha256']
        for track in tracks:
            button(track);enter(6,12)
            v=h.read(s.grid+0x11C+4*track);sv=h.read(s.grid+0x74+4*track);ps=h.read(sv+0x60);bundle=h.read(v+0xC)
            assert h.read(v)==0x08067E6C and h.read(h.read(v))==0x080574C5
            assert h.read(bundle)==h.read(sv+0xC) and h.read(bundle+4)==h.read(sv+0x10)
            assert h.read(bundle+0xC)==h.read(sv+0x18) and h.read(v+0x10)==h.read(s.ctrl+0x18)
            for page in (0,1):
                if s.value(ps)!=page:select_page(ps,page,track)
                for p in range(16):
                    step=16*page+p;before=raw();event('pad_down',p);owner(track,step)
                    event('pad_up',p);outside(before,raw(),0x2E4+track*0x5140+8*step)
                    assert owners()[track]==(0,0)
                    mapping.append(dict(mode=enabled,track=track,page=page,pad=p,step=step))
                for p,shift in ((0,0),(15,1)):
                    step=16*page+p;offset=0x2E4+track*0x5140+8*step
                    clear_step(track,step,p);event('pad_down',p);owner(track,step)
                    if shift:event('button_down',27)
                    values=[];rendered=set()
                    for local in list(range(8))+list(range(7,-1,-1))+[0,7]:
                        record=press_probability(v,track,step,local);owner(track,step);values.append(record[4])
                        if local in (0,7) and local not in rendered:
                            render(v,sv,page,track,enabled,record);rendered.add(local)
                    assert set(values)==set(range(8))
                    for local in range(8,16):press_probability(v,track,step,local)
                    if shift:event('button_up',27)
                    event('pad_down',30);before=raw();row=s.shortcut()
                    assert row['after']['mode']==enabled and row['after']['held_pads']==((1<<p)|(1<<30))
                    assert raw()==before;owner(track,step)
                    event('pad_up',30);event('pad_up',p)
                    assert owners()[track]==(0,0) and s.snapshot()['held_pads']==0
                    guards.append(dict(mode=enabled,track=track,page=page,pad=p))
                    cases.append(dict(mode=enabled,track=track,page=page,pad=p,step=step,shift=shift,values=values))
                # Enrich one step using native editors,including two
                # microstep bits,then ensure probability only changes byte4.
                button(10);event('pad_down',0);pad(30);event('pad_up',0)
                button(11);event('pad_down',0);pad(30);pad(31);event('pad_up',0)
                enter(5,11);event('pad_down',0);pad(21);event('pad_up',0);enter(6,12)
                step=page*16;offset=0x2E4+track*0x5140+8*step
                event('pad_down',0);record=raw()[offset:offset+8]
                assert record[1:4]==bytes((96,33,120)),record.hex()
                for local in range(8):press_probability(v,track,step,local)
                assert raw()[offset:offset+8]==record
                event('pad_up',0)
                preserved.append(dict(mode=enabled,track=track,page=page,record=record.hex()))
                # Stopped native view edits the latched selected step with
                # no top pad held;leave probability3 for the Mutate check.
                assert owners()[track]==(0,0)
                for local in (3,7,3):press_probability(v,track,step,local)
                idle.append(dict(mode=enabled,track=track,page=page,step=step))
                # Extend prior Mutate evidence with non-default probability,
                # microstep,gate and velocity in the same8B record.
                before=raw();base=0x2E4+track*0x5140
                records=[before[base+8*i:base+8*i+8] for i in range(32)]
                assert any(r[2]==33 and r[4]==3 and r[1]==96 and r[3]==120 for r in records)
                event('button_down',27);button(24);event('button_up',27);service();after=raw()
                result=[after[base+8*i:base+8*i+8] for i in range(32)]
                assert before[:base]==after[:base] and before[base+256:]==after[base+256:]
                assert Counter(records)==Counter(result)
                mutations.append(dict(mode=enabled,track=track,page=page,changed=records!=result,before=[r.hex() for r in records],after=[r.hex() for r in result]))
                if progress:progress(dict(mode=enabled,track=track,page=page,cases=len(cases),top_mappings=len(mapping),edits=len(edits),mutations=len(mutations)))
            # A random shuffle may legitimately reproduce its input. Require
            # observed movement per track/mode across its two page trials.
            assert any(m['changed'] for m in mutations[-2:])
    button(8);service();final=s.snapshot()
    assert not s.io and not h.invalid and h.validate_stacks()
    assert final['mode']==1 and final['shift']==final['transport']==final['held_pads']==0
    assert all(not (a['held']|a['held_bits']) for a in final['step_owners'])
    for k in ('raw','project','metadata_sha256','heap','allocations','nor_mutations'):assert initial[k]==final[k],k
    assert bytes(u.mem_read(BASE,len(s.image)))==s.image
    return dict(initial=initial,final=final,tracks=list(tracks),top_mapping=mapping,cases=cases,edits=edits,leds=leds,
        page_events=pages,held_guards=guards,preserved_parameters=preserved,idle_edits=idle,rich_mutations=mutations,
        routes=routes,inputs=s.inputs,main_cycles=cycles,sample_status_inputs=h.sample_status_reads,project_io=s.io,
        midi_faults=bytes(u.mem_read(seq.SEQ_STATE_ADDR+0x78,3)).hex(),uart=uart.report(),
        stock_probability_code_identical=True,firmware_instruction_stubs=False,startup_objects_seeded=False,physical_test=False,
        scope='Native reset/controller mode6,PatternSettings12 toggle,page21,512 top mappings,eight probability values/eight reserved pads. Empty-step creation,endpoint plain/Shift,non-default velocity120/gate96/microstep33 preservation,stopped latched-step edits,physical mode rejection and128 LED composites. Probability changes only selected8B step;active steps only byte4.32 Mutate cases preserve full8B record multisets with varied probability/microstep/gate/velocity;only target256B may change. Sample-flip/automation values remain default. Finite DSP/TXE/native Main/IRQ service,no RAM repair. No GPIO/input queue,physical LEDs/MIDI,random probability statistics,elapsed time or running playback proof. Existing strict SPI,NOR/ADC/USB,disabled-DWT/non-nested FPU limits remain.')
