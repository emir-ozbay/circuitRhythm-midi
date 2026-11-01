"""Native mode5 pages,microstep bits,empty-step lifecycle and LED RAM.

Only reset-created objects and controller callbacks are used;no page,store,
project or ownership RAM seeds/repairs. Native Main consumes finite peer input.
"""
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1
from inspect_ui import load_image,BASE
from recovery_live_mode_test_support import PROJECT_BYTES
from recovery_uart_test_support import NativeUARTPeer
import seq_Patch as seq


def exercise_native_microstep(s,*,tracks=tuple(range(8)),progress=None):
    h=s.h;u=h.u;initial=s.snapshot();count=0;cycles=0
    uart=NativeUARTPeer(s,txe_credits=65536)
    routes=[];mapping=[];cases=[];edits=[];leds=[];pages=[];guards=[];preserved=[];idle=[];all_masks=[]
    stock=load_image()
    assert s.image[0x08056F0C-BASE:0x080571BC-BASE]==stock[0x08056F0C-BASE:0x080571BC-BASE]
    def observe(uc,pc,size,_):
        routes.append(dict(input=s.active_input,view=uc.reg_read(UC_ARM_REG_R0),pad=uc.reg_read(UC_ARM_REG_R1)))
    u.hook_add(UC_HOOK_CODE,observe,begin=0x08056F7C,end=0x08056F7C)
    def raw():return bytes(u.mem_read(s.raw,PROJECT_BYTES))
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
    def enter():
        for _ in range(2):
            if s.snapshot()['grid_mode']==5:break
            button(11)
        assert s.snapshot()['grid_mode']==5
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
        a=s.snapshot()['step_owners'][track]
        assert a['held']==a['held_bits']==1<<step,(track,step,a)
    def led(v,mask):
        data=bytes(u.mem_read(h.read(h.read(v+4)),32))
        palette=[int.from_bytes(stock[0x08062AB0-BASE+i:0x08062AB0-BASE+i+2],'little') for i in (0x42,0x44)]
        expected=b''.join(palette[0 if mask&(1<<i) else 1].to_bytes(2,'little') for i in range(6))+bytes(20)
        assert data==expected,(mask,data.hex(),expected.hex())
        return data
    def render(v,sv,page,track,mode,mask):
        before=raw();s._invoke(0x0804DD1C,(s.grid,0,0,0),label='native_microstep_compositor')
        top=bytes(u.mem_read(h.read(h.read(sv+4))+page*32,32));bottom=led(v,mask)
        assert bytes(u.mem_read(h.read(h.read(s.grid+4)),64))==top+bottom
        assert raw()==before
        leds.append(dict(mode=mode,track=track,page=page,mask=mask,top=top.hex(),bottom=bottom.hex()))
    def press_micro(v,track,step,local):
        offset=0x2E4+track*0x5140+8*step;before=raw();record=before[offset:offset+8]
        n=len(routes);pad(16+local);after=raw();outside(before,after,offset)
        assert routes[n:]==[dict(input=f'pad_down:{16+local}',view=v,pad=local)]
        old=record[2];assert 0<=old<64
        if local>=6:expected=record;new=old
        else:
            new=old^(1<<local)
            if not new:expected=bytes.fromhex('0006000007ff0000')
            elif not old:expected=bytes((s.value(h.read(v+0x24))&255,6,new,96,7,255,0,0))
            else:
                expected=bytearray(record);expected[2]=new;expected=bytes(expected)
        assert after[offset:offset+8]==expected,(track,step,local,record.hex(),after[offset:offset+8].hex(),expected.hex())
        led(v,new)
        edits.append(dict(mode=s.snapshot()['mode'],track=track,step=step,local=local,before=record.hex(),after=expected.hex()))
        return new
    def normalize(v,track,step):
        mask=raw()[0x2E4+track*0x5140+8*step+2]
        for bit in range(6):
            if mask&(1<<bit):press_micro(v,track,step,bit)
        assert raw()[0x2E4+track*0x5140+8*step+2]==0
    for enabled in (0,1):
        if s.snapshot()['mode']!=enabled:
            service();row=s.shortcut();assert row['after']['mode']==enabled
            assert row['before']['raw_sha256']==row['after']['raw_sha256']
        for track in tracks:
            button(track);enter()
            v=h.read(s.grid+0xDC+4*track);sv=h.read(s.grid+0x74+4*track);ps=h.read(sv+0x60)
            assert h.read(v)==0x08067FBC and h.read(h.read(v))==0x08056F7D
            assert h.read(v+0xC)==h.read(sv+0xC) and h.read(v+0x10)==h.read(sv+0x10)
            assert h.read(v+0x14)==h.read(sv+0x18)
            for page in (0,1):
                if s.value(ps)!=page:select_page(ps,page,track)
                for p in range(16):
                    step=16*page+p;before=raw();event('pad_down',p);owner(track,step)
                    event('pad_up',p);after=raw();outside(before,after,0x2E4+track*0x5140+8*step)
                    assert not s.snapshot()['step_owners'][track]['held_bits']
                    mapping.append(dict(mode=enabled,track=track,page=page,pad=p,step=step))
                # First endpoint plain,last endpoint with Shift. Both page
                # boundaries,including step32,retain the same six-bit layout.
                for p,shift in ((0,0),(15,1)):
                    step=16*page+p;event('pad_down',p);owner(track,step)
                    normalize(v,track,step)
                    if shift:event('button_down',27)
                    plan=list(range(6))+list(range(5,-1,-1))+[i for i in range(6) for _ in range(2)]
                    masks=[0]
                    if track==0 and page==0 and p==0:
                        prev=0;gray=[]
                        for i in range(1,64):
                            current=i^(i>>1);gray.append((prev^current).bit_length()-1);prev=current
                        gray.append(prev.bit_length()-1);plan=gray+plan
                    rendered=set()
                    for bit in plan:
                        mask=press_micro(v,track,step,bit);owner(track,step);masks.append(mask)
                        if mask in (0,63) and mask not in rendered:
                            render(v,sv,page,track,enabled,mask);rendered.add(mask)
                    assert rendered=={0,63}
                    assert masks[-1]==0
                    if track==0 and page==0 and p==0:
                        assert set(masks)==set(range(64));all_masks.append(dict(mode=enabled,masks=sorted(set(masks))))
                    for local in range(6,16):assert press_micro(v,track,step,local)==0
                    if shift:event('button_up',27)
                    # Reserved pad30 owns a physical bit but no extra step.
                    event('pad_down',30);before=raw();row=s.shortcut()
                    assert row['after']['mode']==enabled and row['after']['held_pads']==((1<<p)|(1<<30))
                    assert raw()==before;owner(track,step)
                    event('pad_up',30);event('pad_up',p)
                    assert not s.snapshot()['step_owners'][track]['held_bits'] and s.snapshot()['held_pads']==0
                    guards.append(dict(mode=enabled,track=track,page=page,pad=p))
                    cases.append(dict(mode=enabled,track=track,page=page,pad=p,step=step,shift=shift,masks=masks))
                # Existing non-default velocity/gate must survive nonzero XOR.
                button(10);event('pad_down',0);pad(30);event('pad_up',0)
                button(11);event('pad_down',0);pad(30);pad(31);event('pad_up',0);enter()
                step=page*16;event('pad_down',0);offset=0x2E4+track*0x5140+8*step
                record=raw()[offset:offset+8];assert record[1]==96 and record[3]==120
                mask=record[2]
                # Velocity creates an inactive step with its default bit0.
                assert mask==1
                assert press_micro(v,track,step,1)==3
                assert press_micro(v,track,step,1)==1
                assert raw()[offset:offset+8]==record
                event('pad_up',0)
                preserved.append(dict(mode=enabled,track=track,page=page,before=record.hex(),after=raw()[offset:offset+8].hex()))
                # Stopped stock mode also edits its latched selected step
                # without a held top pad;C0 remains empty in this path.
                assert not s.snapshot()['step_owners'][track]['held_bits']
                assert press_micro(v,track,step,1)==3
                assert press_micro(v,track,step,1)==1
                idle.append(dict(mode=enabled,track=track,page=page,step=step))
                if progress:progress(dict(mode=enabled,track=track,page=page,cases=len(cases),top_mappings=len(mapping),edits=len(edits)))
    button(8);service();final=s.snapshot()
    assert not s.io and not h.invalid and h.validate_stacks()
    assert final['mode']==1 and final['shift']==final['transport']==final['held_pads']==0
    assert all(not (a['held']|a['held_bits']) for a in final['step_owners'])
    for k in ('raw','project','metadata_sha256','heap','allocations','nor_mutations'):assert initial[k]==final[k],k
    assert bytes(u.mem_read(BASE,len(s.image)))==s.image
    return dict(initial=initial,final=final,tracks=list(tracks),top_mapping=mapping,cases=cases,edits=edits,leds=leds,
        page_events=pages,held_guards=guards,preserved_parameters=preserved,idle_edits=idle,all_masks=all_masks,
        routes=routes,inputs=s.inputs,main_cycles=cycles,sample_status_inputs=h.sample_status_reads,project_io=s.io,
        midi_faults=bytes(u.mem_read(seq.SEQ_STATE_ADDR+0x78,3)).hex(),uart=uart.report(),
        stock_microstep_code_identical=True,firmware_instruction_stubs=False,startup_objects_seeded=False,physical_test=False,
        scope='Native reset/controller mode5,Gate11 toggle,page21,all16 top mappings,six XOR microstep bits and ten reserved bottom pads. Page endpoints plain/Shift,mask0 deletion/default recreation,all64 masks in both runtime modes,non-default velocity120/gate96 preservation,stopped latched-step edits,physical-held mode rejection and LED RAM. Only selected8B step may change;finite DSP/TXE/native Main/IRQ service,no FIFO/fault/ownership repair. No GPIO/input queue,physical LEDs/MIDI,elapsed time,running transport or full scheduling proof. Existing strict SPI,NOR/ADC/USB,disabled-DWT/non-nested FPU limits remain.')
