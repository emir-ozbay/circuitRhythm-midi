"""Native Pattern Settings pages, Shift endpoints, sync/direction and Mutate.

Reset-created objects and real controller callbacks;no project/store/page or
ownership seeds. Native Main and finite UART/DSP peripheral inputs are used.
"""
from collections import Counter
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1
from inspect_ui import load_image,BASE
from recovery_live_mode_test_support import PROJECT_BYTES
from recovery_uart_test_support import NativeUARTPeer
import seq_Patch as seq


def exercise_native_pattern_settings(s,*,tracks=tuple(range(8)),progress=None):
    h=s.h;u=h.u;initial=s.snapshot();count=0;cycles=0
    uart=NativeUARTPeer(s,txe_credits=65536)
    routes=[];upper=[];bottom=[];leds=[];page_events=[];mutations=[];guards=[]
    stock=load_image()
    assert s.image[0x080571BC-BASE:0x0805746C-BASE]==stock[0x080571BC-BASE:0x0805746C-BASE]
    def observe(uc,pc,size,_):
        routes.append(dict(input=s.active_input,view=uc.reg_read(UC_ARM_REG_R0),pad=uc.reg_read(UC_ARM_REG_R1)))
    u.hook_add(UC_HOOK_CODE,observe,begin=0x08057218,end=0x08057218)
    def raw():return bytes(u.mem_read(s.raw,PROJECT_BYTES))
    def color(offset):return int.from_bytes(stock[0x08062AB0-BASE+offset:0x08062AB0-BASE+offset+2],'little')
    def bottom_led(v,settings):
        values=[int.from_bytes(u.mem_read(h.read(h.read(v+4))+2*i,2),'little') for i in range(32)]
        assert values[16:24]==[color(0xD8 if 23-i==s.value(settings,1) else 0xDA) for i in range(16,24)]
        assert values[24:28]==[0]*4
        assert values[28:32]==[color(0xDC if i-28==s.value(settings,2) else 0xDE) for i in range(28,32)]
    def service():
        nonlocal cycles
        uart.service();s.cycle(budget=2000000);cycles+=1;uart.service()
    def event(kind,i):
        nonlocal count
        row=s.input(kind,i);count+=1
        if count%16==0:service()
        assert row['after']['transport']==0,'unexpected transport start'
        assert bytes(u.mem_read(seq.SEQ_STATE_ADDR+seq.OFF_MIDI_CONTEXT_FAULT,3))==bytes(3)
        return row
    def button(i):
        row=event('button_down',i);event('button_up',i);return row
    def pad(i):event('pad_down',i);event('pad_up',i)
    def enter():
        if s.snapshot()['grid_mode']!=4:button(12)
        assert s.snapshot()['grid_mode']==4 and s.snapshot()['shift']==0
    def unchanged_except(before,after,offset,value):
        expected=bytearray(before);expected[offset]=value
        assert after==bytes(expected),('unexpected raw write',offset,value,
            [(i,a,b) for i,(a,b) in enumerate(zip(before,after)) if a!=b])
    def set_page(ps,page,track):
        before=raw();old=s.value(ps);assert old in (0,1) and old!=page
        button(21);after=raw();assert s.value(ps)==page
        delta=[i for i,(a,b) in enumerate(zip(before,after)) if a!=b]
        if delta:
            end=0x2E4+track*0x5140+0x100
            assert delta==[end] and before[end]<16 and after[end]==31
        page_events.append(dict(track=track,before=old,after=page,raw_offsets=delta))
    def render(v,mode,track,page,shift):
        before=s.snapshot();s._invoke(0x0804DD1C,(s.grid,0,0,0),label='native_pattern_settings_compositor')
        src=h.read(h.read(v+4));dst=h.read(h.read(s.grid+4))
        data=bytes(u.mem_read(src,64));assert bytes(u.mem_read(dst,64))==data
        selected=(s.value(h.read(v+0xC))>>(8*shift))&255
        assert selected//16==page and int.from_bytes(data[(selected%16)*2:(selected%16)*2+2],'little')==color(0xE0)
        assert before['raw_sha256']==s.snapshot()['raw_sha256']
        leds.append(dict(mode=mode,track=track,page=page,shift=shift,source=src,leds=data.hex()))
    for enabled in (0,1):
        if s.snapshot()['mode']!=enabled:
            service();row=s.shortcut();assert row['after']['mode']==enabled
            assert row['before']['raw_sha256']==row['after']['raw_sha256']
        for track in tracks:
            button(track);enter()
            v=h.read(s.grid+0xFC+4*track);sv=h.read(s.grid+0x74+4*track)
            ps=h.read(v+0x18);settings=h.read(v+0xC);header=0x2E4+track*0x5140+0x100
            assert h.read(v)==0x08067EA4 and h.read(h.read(v))==0x08057219
            assert h.read(v+0x10)==h.read(s.ctrl+0xC) and ps==h.read(sv+0x60)
            assert h.read(v+0x14)==sv
            for page in (0,1):
                if s.value(ps)!=page:set_page(ps,page,track)
                for shift in (0,1):
                    if shift:event('button_down',27)
                    for p in range(16):
                        before=raw();n=len(routes);pad(p);after=raw();step=16*page+p
                        unchanged_except(before,after,header+shift,step)
                        assert routes[n:]==[dict(input=f'pad_down:{p}',view=v,pad=p)]
                        bottom_led(v,settings)
                        assert (s.value(settings)>>(8*shift))&255==step
                        assert s.snapshot()['held_pads']==0
                        assert all(not (a['held']|a['held_bits']) for a in s.snapshot()['step_owners'])
                        upper.append(dict(mode=enabled,track=track,page=page,shift=shift,pad=p,step=step,offset=header+shift))
                    render(v,enabled,track,page,shift)
                    # All bottom pads,including four reserved blank pads.
                    for p in range(16,32):
                        before=raw();n=len(routes);pad(p);after=raw()
                        if p<24:
                            expected=23-p;unchanged_except(before,after,header+2,expected)
                            assert s.value(settings,1)==expected
                        elif p>=28:
                            expected=p-28;unchanged_except(before,after,header+3,expected)
                            assert s.value(settings,2)==expected
                        else:expected=None;assert before==after
                        assert routes[n:]==[dict(input=f'pad_down:{p}',view=v,pad=p)]
                        bottom_led(v,settings)
                        bottom.append(dict(mode=enabled,track=track,page=page,shift=shift,pad=p,value=expected))
                    if shift:event('button_up',27)
                # A physical owner in this non-step view still blocks mode
                # admission,including a reserved blank pad.
                for p in (0,24):
                    event('pad_down',p);before=raw();row=s.shortcut()
                    assert row['after']['mode']==enabled and row['after']['held_pads']==1<<p
                    assert raw()==before
                    event('pad_up',p);assert s.snapshot()['held_pads']==0
                    guards.append(dict(mode=enabled,track=track,page=page,pad=p))
                if progress:progress(dict(mode=enabled,track=track,page=page,upper=len(upper),bottom=len(bottom),mutations=len(mutations)))
            # Set a full32-step range using native endpoint inputs. Create
            # distinct active records through Velocity/Gate,never RAM writes.
            if s.value(ps)!=0:set_page(ps,0,track)
            event('button_down',27);pad(0);event('button_up',27)
            set_page(ps,1,track);pad(15)
            for page in (0,1):
                if s.value(ps)!=page:set_page(ps,page,track)
                button(10);assert s.snapshot()['grid_mode']==2
                for p in (0,3,7,11,15):
                    event('pad_down',p);pad(16+p);event('pad_up',p)
                button(11);assert s.snapshot()['grid_mode']==3
                for p in (0,15):
                    event('pad_down',p);pad(16+(p//3));event('pad_up',p)
                enter()
            # Restore default playback parameters;Start0/End31 remains.
            pad(20);pad(28)
            for page in (0,1):
                if s.value(ps)!=page:set_page(ps,page,track)
                before=raw();offset=0x2E4+track*0x5140
                records=[before[offset+8*i:offset+8*i+8] for i in range(32)]
                assert len(set(records))>=6
                event('button_down',27);button(24);event('button_up',27)
                service();after=raw()
                assert before[:offset]==after[:offset] and before[offset+256:]==after[offset+256:]
                result=[after[offset+8*i:offset+8*i+8] for i in range(32)]
                assert Counter(records)==Counter(result),'Mutate lost or altered a step record'
                assert before!=after,'nontrivial native Mutate did not move records'
                assert s.snapshot()['transport']==0 and s.snapshot()['grid_mode']==4
                mutations.append(dict(mode=enabled,track=track,page=page,before=[r.hex() for r in records],after=[r.hex() for r in result]))
    button(8);service();final=s.snapshot()
    assert not s.io and not h.invalid and h.validate_stacks()
    assert final['mode']==1 and final['shift']==final['transport']==final['held_pads']==0
    for k in ('raw','project','metadata_sha256','heap','allocations','nor_mutations'):assert initial[k]==final[k],k
    assert bytes(u.mem_read(BASE,len(s.image)))==s.image
    return dict(initial=initial,final=final,tracks=list(tracks),upper=upper,bottom=bottom,leds=leds,
        page_events=page_events,mutations=mutations,held_guards=guards,routes=routes,inputs=s.inputs,
        main_cycles=cycles,sample_status_inputs=h.sample_status_reads,project_io=s.io,
        midi_faults=bytes(u.mem_read(seq.SEQ_STATE_ADDR+0x78,3)).hex(),uart=uart.report(),
        stock_pattern_settings_code_identical=True,firmware_instruction_stubs=False,startup_objects_seeded=False,physical_test=False,
        scope='Native reset/controller mode4 button12,page21,all32 physical pads with and without Shift;exact4 parameter bytes,shared page,64B LED composition,held mode rejection and Shift27+Duplicate24 Mutate on nontrivial32-step records. Full8B step multisets preserved;only selected pattern first256B may change. Default automation/sample-flip data is not enriched here. Native Main with finite DSP/TXE/native IRQ inputs,no queue/fault repair. No GPIO/input queue,physical LEDs/MIDI,elapsed-time,random distribution or transport-playback proof. Existing strict SPI,NOR/ADC/USB,disabled-DWT/non-nested FPU limits remain.')
