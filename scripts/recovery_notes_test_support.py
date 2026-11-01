"""Native Note1/7 routing, retained key ownership and emitted UART bytes.

Uses reset-created objects and controller callbacks. No page/keymap/ownership,
project bytes, MIDI queues or fault flags are seeded or repaired by the host.
"""
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1
from inspect_ui import load_image,BASE
from recovery_live_mode_test_support import PROJECT_BYTES
from recovery_uart_test_support import NativeUARTPeer
import seq_Patch as seq
import midi_recovery_patch as fixed
import midi_recovery_prototype as rp


def exercise_native_notes(s,*,tracks=tuple(range(8)),progress=None):
    h=s.h;u=h.u;initial=s.snapshot();routes=[];keys=[];mapping=[];retained=[];edits=[];pages=[];entries=[];leds=[];defaults=[];cancelled=[];page_buttons=[]
    count=0;cycles=0;uart=NativeUARTPeer(s,txe_credits=131072)
    stock=load_image()
    assert s.image[0x0805D7A0-BASE:0x0805E380-BASE]==stock[0x0805D7A0-BASE:0x0805E380-BASE]
    def route(uc,pc,size,_):
        routes.append(dict(input=s.active_input,pc=pc,view=uc.reg_read(UC_ARM_REG_R0),pad=uc.reg_read(UC_ARM_REG_R1)))
    u.hook_add(UC_HOOK_CODE,route,begin=0x0805D7A0,end=0x0805D7A0)
    def raw():return bytes(u.mem_read(s.raw,PROJECT_BYTES))
    def held(v):return bytes(u.mem_read(v+0x54,32))
    def service():
        nonlocal cycles
        uart.service();s.cycle(budget=2000000);cycles+=1;uart.service()
    def pending():
        # Read-only equivalent of stock2A37E; ring indices are never changed.
        counts=[]
        for i in range(3):
            port=h.read(fixed.STATE_BASE+rp.HEADER_SIZE+i*rp.ENTRY_SIZE);q=h.read(port+4)
            cap=int.from_bytes(u.mem_read(q+4,2),'little')
            a=int.from_bytes(u.mem_read(q+6,2),'little');b=int.from_bytes(u.mem_read(q+8,2),'little')
            assert 0<=a<cap and 0<=b<cap
            counts.append((a-b)%cap)
        return counts
    def settle():
        for _ in range(4):
            service()
            if not any(pending()):return
        raise AssertionError(('native MIDI ring did not drain',pending()))
    def event(kind,pad):
        nonlocal count
        row=s.input(kind,pad);count+=1
        if count%16==0:service()
        assert bytes(u.mem_read(seq.SEQ_STATE_ADDR+seq.OFF_MIDI_CONTEXT_FAULT,3))==bytes(3),('fault',count)
        return row
    def button(i):
        row=event('button_down',i);event('button_up',i);return row
    def note1():
        before=raw()
        for _ in range(2):
            if s.snapshot()['grid_mode']==1:break
            button(9)
        assert s.snapshot()['grid_mode']==1
        after=raw();delta=[dict(offset=i,before=a,after=b) for i,(a,b) in enumerate(zip(before,after)) if a!=b]
        if delta:entries.append(delta)  # stock Note entry may enable pitch mode
    def select_page(ps,page,track,gm):
        before=raw();button(21);after=raw()
        assert s.value(ps)==page
        delta=[i for i,(a,b) in enumerate(zip(before,after)) if a!=b]
        if delta:
            end=0x2E4+track*0x5140+0x100
            assert delta==[end] and before[end]==15 and after[end]==31
            pages.append(dict(track=track,offset=end,before=15,after=31))
        page_buttons.append(dict(track=track,view_mode=gm,page=page))
    def key(v,pad):
        km=h.read(v+0x4C);window=s.value(h.read(v+0x48));stride=u.mem_read(km+0x19C,1)[0]
        index=(pad+(5-window)*stride*8)&255
        assert index<128
        return u.mem_read(km+8+index,1)[0]
    def mark():return [len(p['bytes']) for p in uart.ports]
    def wire(start,expected):
        settle()
        got=[bytes(p['bytes'][start[i]:]) for i,p in enumerate(uart.ports)]
        assert got==[bytes(expected)]*2,('wire',got,bytes(expected))
        return [b.hex() for b in got]
    def render(v,sv,gm,page):
        before=s.snapshot();window=s.value(h.read(v+0x48));km=h.read(v+0x4C)
        offset=((5-window)*u.mem_read(km+0x19C,1)[0]*8)&127
        source=h.read(h.read(v+4))+offset*2
        top=(h.read(h.read(sv+4))+page*32) if gm==1 else source
        s._invoke(0x0804DD1C,(s.grid,0,0,0),label='native_note_compositor')
        dest=h.read(h.read(s.grid+4));result=bytes(u.mem_read(dest,64))
        assert result[:32]==bytes(u.mem_read(top,32))
        assert result[32:]==bytes(u.mem_read(source+32,32))
        assert before['raw_sha256']==s.snapshot()['raw_sha256']
        return dict(view_mode=gm,page=page,top_source=top,bottom_source=source+32,leds=result.hex())
    for enabled in (0,1):
        if s.snapshot()['mode']!=enabled:
            settle();row=s.shortcut();assert row['after']['mode']==enabled
            assert row['before']['raw_sha256']==row['after']['raw_sha256']
        for track in tracks:
            button(track);assert s.value(h.read(s.grid+0x25C))==track
            note1();v=h.read(s.grid+0x54+track*4);sv=h.read(s.grid+0x74+track*4);ps=h.read(sv+0x60)
            assert h.read(h.read(v))==0x0805D7A1
            for page in (0,1):
                note1()
                if s.value(ps)!=page:
                    select_page(ps,page,track,1)
                assert s.value(ps)==page
                for pad in range(16):
                    step=page*16+pad;before=raw();row=event('pad_down',pad)
                    owner=row['after']['step_owners'][track]
                    assert owner['held']==owner['held_bits']==1<<step,(track,page,pad,owner)
                    event('pad_up',pad);after=raw();off=0x2E4+track*0x5140+8*step
                    assert before[:off]==after[:off] and before[off+8:]==after[off+8:]
                    mapping.append(dict(mode=enabled,track=track,page=page,pad=pad,step=step))
                # Stock pitch writer and same-pitch toggle at both page endpoints.
                for pad in (0,15):
                    step=page*16+pad;off=0x2E4+track*0x5140+8*step
                    event('pad_down',pad);values=[]
                    for kp in (24,24,25):
                        before=raw();old=before[off];pitch=key(v,kp)
                        event('pad_down',kp);event('pad_up',kp);after=raw()
                        assert before[:off]==after[:off] and before[off+8:]==after[off+8:]
                        assert after[off]==(0 if old==pitch else pitch),(old,pitch,after[off:off+8].hex())
                        values.append(after[off:off+8].hex())
                    event('pad_up',pad)
                    edits.append(dict(mode=enabled,track=track,page=page,step=step,values=values))
                for gm in (1,7):
                    if s.snapshot()['grid_mode']!=gm:button(9)
                    assert s.snapshot()['grid_mode']==gm and s.value(ps)==page
                    if gm==7:
                        select_page(ps,1-page,track,gm);select_page(ps,page,track,gm)
                    settle();start=mark();expected=bytearray()
                    for pad in range(16 if gm==1 else 0,32):
                        pitch=key(v,pad);start_route=len(routes);before=raw()
                        event('pad_down',pad)
                        assert routes[start_route:]==[dict(input=f'pad_down:{pad}',pc=0x0805D7A0,view=v,pad=pad)]
                        owners=held(v);assert owners[pad]==pitch and sum(bool(b) for b in owners)==bool(pitch)
                        assert s.snapshot()['held_pads']==1<<pad
                        event('pad_up',pad);assert held(v)==bytes(32) and s.snapshot()['held_pads']==0
                        # Stock5D85E updates the default-note store when no
                        # step is held. Its project serialization is one byte.
                        after=raw();expected_raw=bytearray(before);default=0x28CF4+track
                        if pitch:expected_raw[default]=pitch
                        assert after==bytes(expected_raw),('default note',track,gm,page,pad,
                            [(i,a,b) for i,(a,b) in enumerate(zip(before,after)) if a!=b])
                        assert s.value(h.read(v+0x34))==after[default]
                        if before!=after:defaults.append(dict(track=track,offset=default,before=before[default],after=after[default]))
                        if pitch:expected+=bytes((0x90|track,pitch-12,96,0x80|track,pitch-12,0))
                        keys.append(dict(mode=enabled,track=track,view_mode=gm,page=page,pad=pad,raw_note=pitch))
                    wire(start,expected)
                    leds.append(dict(mode=enabled,track=track,**render(v,sv,gm,page)))
                # Same NoteView keeps bottom notes across1<->7. The physical
                # bit must remain, both to route release and reject mode commit.
                for old,new in ((7,1),(1,7)):
                    assert s.snapshot()['grid_mode']==old
                    settle();start=mark();pitch=key(v,24)
                    event('pad_down',24);before=raw();button(9)
                    assert s.snapshot()['grid_mode']==new
                    assert held(v)[24]==pitch and s.snapshot()['held_pads']==1<<24
                    row=s.shortcut();assert row['after']['mode']==enabled
                    assert held(v)[24]==pitch and s.snapshot()['held_pads']==1<<24
                    event('pad_up',24);assert held(v)==bytes(32) and s.snapshot()['held_pads']==0
                    got=wire(start,(0x90|track,pitch-12,96,0x80|track,pitch-12,0))
                    assert raw()==before
                    retained.append(dict(mode=enabled,track=track,page=page,old=old,new=new,raw_note=pitch,wire=got))
                if progress:progress(dict(track=track,mode=enabled,page=page,keys=len(keys),retained=len(retained),edits=len(edits)))
            # Native4DAAC must still retire changed subviews and top Note7
            # pads. A later physical release must not emit a second Note Off.
            for trigger in ('view','track','top_note7'):
                note1()
                if trigger=='top_note7':button(9)
                pad=8 if trigger=='top_note7' else 24
                settle();start=mark();pitch=key(v,pad)
                event('pad_down',pad);before=raw()
                if trigger=='view':button(10)
                elif trigger=='track':button((track+1)%8)
                else:button(9)
                assert held(v)==bytes(32) and s.snapshot()['held_pads']==0,(trigger,held(v).hex(),s.snapshot()['held_pads'])
                event('pad_up',pad)
                got=wire(start,(0x90|track,pitch-12,96,0x80|track,pitch-12,0))
                assert raw()==before
                cancelled.append(dict(mode=enabled,track=track,trigger=trigger,pad=pad,wire=got))
                if trigger=='track':button(track)
    button(8);settle();final=s.snapshot()
    assert not s.io and not h.invalid and h.validate_stacks()
    for field in ('raw','project','metadata_sha256','heap','allocations','nor_mutations'):assert initial[field]==final[field],field
    assert all(not (a['held']|a['held_bits']) for a in final['step_owners'])
    assert all(held(h.read(s.grid+0x54+4*t))==bytes(32) for t in range(8))
    assert final['held_pads']==0 and bytes(u.mem_read(BASE,len(s.image)))==s.image
    return dict(initial=initial,final=final,tracks=list(tracks),keys=keys,top_mapping=mapping,retained=retained,pitch_edits=edits,
        leds=leds,entry_changes=entries,default_note_changes=defaults,length_extensions=pages,page_buttons=page_buttons,cancelled=cancelled,routes=routes,inputs=s.inputs,main_cycles=cycles,
        sample_status_inputs=h.sample_status_reads,midi_faults=bytes(u.mem_read(seq.SEQ_STATE_ADDR+0x78,3)).hex(),uart=uart.report(),
        project_io=s.io,guards=s.guards,firmware_instruction_stubs=False,startup_objects_seeded=False,physical_test=False,
        stock_note_code_identical=True,scope='Native boot/controller Note1/7,page21,step ownership,pitch edit,keymap/blank keys,NoteView held bytes and64B LED RAM. Same-view ownership survives1<->7;held mode toggle rejects;release emits exactly one UART On/Off per key through native Main/IRQ53/54 with finite DSP/TXE inputs. No RAM repair,GPIO scan,event-queue,elapsed-time,physical LED/MIDI/RX or complete transport proof. Existing strict SPI,NOR/ADC/USB,disabled-DWT,non-nested FPU limits remain.')
