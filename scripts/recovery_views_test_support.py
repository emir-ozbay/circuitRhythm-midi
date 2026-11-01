"""Native Velocity/Gate pages, parameter edits and LED composition after boot.

No project, store, page or ownership RAM is seeded. Only the existing Main
callback adapter injects controller inputs; peripheral/timing limits still apply.
"""
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1
from recovery_live_mode_test_support import PROJECT_BYTES
from inspect_ui import load_image,BASE
import seq_Patch as seq
from recovery_uart_test_support import NativeUARTPeer

VIEW_BUTTONS={2:10,3:11}
PARAM_OFFSETS={2:0x9C,3:0xBC}
PARAM_HANDLERS={2:0x08056ABA,3:0x08056D54}


def exercise_native_views(s,*,tracks=tuple(range(8)),progress=None):
    h=s.h;u=h.u;initial=s.snapshot();routes=[];cases=[];top_mapping=[];length_extensions=[]
    input_count=0;main_cycles=0
    uart=NativeUARTPeer(s,txe_credits=131072)
    assert initial['mode']==initial['grid_mode']==0
    stock=load_image()
    # Native parameter handlers and observers are byte-identical to stock.
    assert s.image[0x08056A00-BASE:0x08056F80-BASE]==stock[0x08056A00-BASE:0x08056F80-BASE]
    def route(uc,pc,size,_):
        routes.append(dict(input=s.active_input,pc=pc,view=uc.reg_read(UC_ARM_REG_R0),pad=uc.reg_read(UC_ARM_REG_R1)))
    for pc in PARAM_HANDLERS.values():u.hook_add(UC_HOOK_CODE,route,begin=pc,end=pc)
    def service_main():
        nonlocal main_cycles
        uart.service()
        s.cycle(budget=2000000);main_cycles+=1
        uart.service()
    def input_event(*args,**kwargs):
        nonlocal input_count
        row=s.input(*args,**kwargs);input_count+=1
        # Thousands of callback injections without Main artificially starve
        # the real output consumer. Run the native loop, never clear queues.
        if input_count%16==0:service_main()
        assert bytes(u.mem_read(seq.SEQ_STATE_ADDR+seq.OFF_MIDI_CONTEXT_FAULT,3))==bytes(3),('MIDI guard fault',input_count)
        return row
    def button(identifier):
        row=input_event('button_down',identifier);input_event('button_up',identifier)
        return row
    def raw():return bytes(u.mem_read(s.raw,PROJECT_BYTES))
    def unchanged_outside(before,after,offset):
        assert before[:offset]==after[:offset] and before[offset+8:]==after[offset+8:]
    def render(bottom):
        before=s.snapshot()
        s._invoke(0x0804DD1C,(s.grid,0,0,0),label='native_grid_compositor')
        source=bytes(u.mem_read(h.read(h.read(bottom+4)),32))
        result=bytes(u.mem_read(h.read(h.read(s.grid+4))+32,32))
        assert result==source
        after=s.snapshot()
        for field in ('raw_sha256','metadata_sha256','heap','allocations','nor_mutations','io_count'):
            assert before[field]==after[field],field
        return result.hex()
    for enabled in (0,1):
        if s.snapshot()['mode']!=enabled:
            service_main()
            row=s.shortcut();assert row['after']['mode']==enabled
            assert row['before']['raw_sha256']==row['after']['raw_sha256']
        for track in tracks:
            button(track);assert s.value(h.read(s.grid+0x25C))==track
            view=h.read(s.grid+0x74+4*track);page_store=h.read(view+0x60)
            for gm in (2,3):
                button(VIEW_BUTTONS[gm]);assert s.snapshot()['grid_mode']==gm
                bottom=h.read(s.grid+PARAM_OFFSETS[gm]+4*track)
                assert h.read(h.read(bottom))==PARAM_HANDLERS[gm]|1
                for page in (0,1):
                    if s.value(page_store)!=page:
                        before=raw();button(21);after=raw()
                        delta=[i for i,(a,b) in enumerate(zip(before,after)) if a!=b]
                        if delta:
                            # Stock4BA82..4BA98 extends an initial16-step
                            # pattern on its first second-page request.
                            end=0x2E4+track*0x5140+0x100
                            assert delta==[end] and before[end]==15 and after[end]==31,(track,delta)
                            length_extensions.append(dict(mode=enabled,track=track,view_mode=gm,offset=end,before=15,after=31))
                    assert s.value(page_store)==page,(enabled,track,gm,page,s.value(page_store),s.snapshot())
                    # All sixteen top pads must address the selected half.
                    for pad in range(16):
                        step=page*16+pad;before=raw();row=input_event('pad_down',pad)
                        owner=row['after']['step_owners'][track]
                        assert owner['held']==owner['held_bits']==1<<step,(enabled,track,gm,page,pad,owner)
                        input_event('pad_up',pad)
                        after=raw();offset=0x2E4+track*0x5140+step*8
                        unchanged_outside(before,after,offset)
                        assert not s.snapshot()['step_owners'][track]['held_bits']
                        top_mapping.append(dict(mode=enabled,track=track,view_mode=gm,page=page,pad=pad,step=step))
                    # Endpoints exercise both page boundaries, including step32.
                    for pad in (0,15):
                        step=page*16+pad;offset=0x2E4+track*0x5140+step*8
                        if gm==3:
                            # Top-pad toggle coverage can leave a step empty.
                            # Gate deliberately refuses empty steps; create it
                            # through native Velocity input, never a RAM seed.
                            button(10);input_event('pad_down',pad)
                            input_event('pad_down',16);input_event('pad_up',16);input_event('pad_up',pad)
                            button(11)
                            assert s.value(page_store)==page and s.snapshot()['grid_mode']==3
                        input_event('pad_down',pad)
                        # Velocity view creates an inactive step natively;
                        # the following Gate pass reuses those edited steps.
                        values=[];leds=[]
                        plan=list(range(16)) if gm==2 else [14,15]+list(range(16))+[15]*6
                        for index,local in enumerate(plan):
                            before=raw();start=len(routes)
                            input_event('pad_down',16+local);input_event('pad_up',16+local)
                            after=raw();unchanged_outside(before,after,offset)
                            assert routes[start:]==[dict(input=f'pad_down:{16+local}',pc=PARAM_HANDLERS[gm],view=bottom,pad=local)]
                            value=after[offset+(3 if gm==2 else 1)]
                            if gm==2:expected=min(8*(local+1),127)
                            elif index==0:expected=None  # prime an unknown previous cell
                            elif index<18:expected=6*(local+1)
                            else:expected=(95,94,93,92,91,96)[index-18]
                            if expected is not None:assert value==expected,(enabled,track,gm,page,pad,local,index,value,expected)
                            values.append(value)
                            if (gm==2 and local in (0,15)) or (gm==3 and index in (2,17)):
                                leds.append(render(bottom))
                        assert len(leds)==2 and leds[0]!=leds[1],(gm,leds)
                        input_event('pad_up',pad)
                        owner=s.snapshot()['step_owners'][track]
                        assert owner['held']==owner['held_bits']==0
                        cases.append(dict(mode=enabled,track=track,view_mode=gm,page=page,step=step,
                            bottom=bottom,values=values,low_high_leds=leds))
                        if progress is not None:progress(dict(cases=len(cases),top_mappings=len(top_mapping),mode=enabled,track=track,view_mode=gm,page=page))
    # Return to the main32-pad screen: page button may retain its stock store,
    # while effective step addressing stays locked to the full grid.
    button(8);assert s.snapshot()['grid_mode']==0
    final=s.snapshot()
    assert final['mode']==1 and not s.io and not h.invalid and h.validate_stacks()
    for field in ('raw','project','metadata_sha256','heap','allocations','nor_mutations'):
        assert initial[field]==final[field],field
    assert bytes(u.mem_read(BASE,len(s.image)))==s.image
    assert all(not (v['held']|v['held_bits']) for v in final['step_owners'])
    return dict(initial=initial,final=final,tracks=list(tracks),top_mapping=top_mapping,cases=cases,
        routes=routes,inputs=s.inputs,project_io=s.io,voice_calls=s.voices,length_extensions=length_extensions,
        main_cycles=main_cycles,sample_status_inputs=h.sample_status_reads,midi_faults=bytes(u.mem_read(seq.SEQ_STATE_ADDR+0x78,3)).hex(),
        uart=uart.report(),
        firmware_instruction_stubs=False,startup_objects_seeded=False,physical_test=False,
        stock_parameter_code_identical=True,
        scope='Native reset objects/controller button10/11/21,pad callbacks,native parameter stores/raw aliases and32B bottom LED composition. Native Main runs after each16 UI inputs and before mode commit;finite explicit802F zero inputs,no queue/fault clearing. No GPIO/event queue,elapsed-time,actual LEDs,physical device or full transport/MIDI proof. Existing finite DSP/NOR/ADC/USB/disabled-DWT/non-nested FPU assumptions remain.')
