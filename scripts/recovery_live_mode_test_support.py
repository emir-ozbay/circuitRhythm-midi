"""Native boot objects and vtable input calls; no startup object/store seeds.

Input is injected at the constructed controller's pad/button interface. The
adapter preserves the interrupted Main CPU context after the native callback
returns; it does not emulate GPIO scanning or claim event-queue timing.
"""
import hashlib,struct
from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_READ,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
from recovery_fpu_test_support import FPUStartup,FP_REGS
from recovery_worker_test_support import SAVED_REGS
from recovery_dsp_test_support import ScriptedDSPPeer,mailbox_script
from recovery_input_test_support import MAIN_LOOP,MAIN_INPUT_READY
import midi_recovery_patch as fixed
import seq_Patch as seq

PROJECT_BYTES=0x29484
PROJECT_IO=(0x08037B8C,0x08037BD6,0x08037ED0,0x08047288,0x080472E2,
            0x0804113A,0x080411D8,0x08041906)
TIMER_OBJECT=0x20000370
TIMER_EVENTS=(0x08046DDE,0x08046E2A,0x0805CE48,0x0805CE28)


class UnsupportedDWTClock(RuntimeError):pass


class LiveModeStartup(FPUStartup):
    def __init__(self,image,*,sample_status=(),**options):
        super().__init__(image,**options)
        self.sample_status=tuple(sample_status)
        assert all(isinstance(v,int) and 0<=v<0x1000000 for v in self.sample_status)
        self.sample_status_reads=[]
        self.u.mem_map(0xE0001000,4096)
        self.dwt_reads=0
        self.u.hook_add(UC_HOOK_MEM_READ,self._dwt_read,begin=0xE0001004,end=0xE0001007)
        self.u.hook_add(UC_HOOK_MEM_WRITE,self._dwt_write,begin=0xE0001000,end=0xE0001007)

    def _dwt_read(self,u,kind,address,size,value,_):
        assert address==0xE0001004 and size==4
        if self.read(0xE0001000)&1:raise UnsupportedDWTClock('enabled CYCCNT timing is not modeled')
        self.dwt_reads+=1

    def _dwt_write(self,u,kind,address,size,value,_):
        assert size==4 and address in (0xE0001000,0xE0001004)
        if address==0xE0001000 and value&1:raise UnsupportedDWTClock('cannot enable an unmodeled cycle clock')

    def _wire_response(self,rc,n,data):
        if (rc&0x400 and self.command and self.command['caller']==0x08031296
                and self.read_register==dict(bank=0,register=0x802F)
                and len(self.sample_status_reads)<len(self.sample_status)):
            assert n==3 and data==bytes.fromhex('400000') and self.selector=='80802f'
            payload=self.sample_status[len(self.sample_status_reads)].to_bytes(3,'big')
            return payload,'explicit_sample_status',None
        return super()._wire_response(rc,n,data)

    def complete_spi_dma(self,**options):
        event=super().complete_spi_dma(**options)
        if event['meaning']=='explicit_sample_status':
            self.sample_status_reads.append(dict(bank=0,register=0x802F,
                reply=self.sample_status[len(self.sample_status_reads)].to_bytes(3,'big').hex()))
        return event


def boot_session(image,*,sample_status=()):
    h=LiveModeStartup(image,peer_policy='ready',dsp_peer=ScriptedDSPPeer(mailbox_script()),sample_status=sample_status)
    h.main_setup().start_tasks().checkpoint().start_input().checkpoint(MAIN_INPUT_READY,budget=800000).start_spi()
    for _ in range(8):
        pc=h.run(h.u.reg_read(UC_ARM_REG_PC),MAIN_LOOP,budget=2000000)
        if pc==MAIN_LOOP:
            assert not h.invalid
            return LiveModeSession(h,image)
    raise AssertionError('native Main loop not reached')


class LiveModeSession:
    def __init__(self,h,image):
        self.h,self.image=h,image
        self.labels=fixed.seq_code()[1]
        self.inputs=[];self.io=[];self.guards=[];self.voices=[];self.timer_events=[]
        self.active_input=None
        self.ctrl=self.unique(0x080672E4)
        self.project=self.unique(0x08066F64)
        self.grid=h.read(self.ctrl+0x3C);self.projects=h.read(self.ctrl+0x50)
        self.raw=h.read(self.project+0x14)
        assert h.read(self.projects+0x20)==h.read(self.project+0x44)
        assert h.read(self.projects+0x28)==h.read(self.project+0x48)
        assert h.read(self.projects+0x24)!=h.read(self.project+0x4C)
        self.recorders=self.objects(0x08067864)
        assert len(self.recorders)==8
        assert sorted(h.read(r+0x50) for r in self.recorders)==[self.raw+0x2E4+t*0x5140 for t in range(8)]
        assert 0x20006F60<=self.raw<self.raw+PROJECT_BYTES<=h.read(seq.HEAP_CUR_PTR)
        assert bytes(h.u.mem_read(0x08010000,len(image)))==image
        for pc in PROJECT_IO+TIMER_EVENTS+(self.labels['c_mode_can_switch'],seq.STOCK_SAMPLE_FORCE_OFF):
            h.u.hook_add(UC_HOOK_CODE,self._observe,begin=pc,end=pc)

    def objects(self,vtable):
        stop=self.h.read(seq.HEAP_CUR_PTR)
        data=bytes(self.h.u.mem_read(0x20006F60,stop-0x20006F60))
        word=vtable.to_bytes(4,'little')
        return [0x20006F60+i for i in range(0,len(data)-3,4) if data[i:i+4]==word]

    def unique(self,vtable):
        objects=self.objects(vtable)
        assert len(objects)==1,(hex(vtable),list(map(hex,objects)))
        return objects[0]

    def store_address(self,obj,index=0):
        # Exact native3FC58 per-word active-bank selector, not one bank/array.
        assert 0x20000000<=obj<self.h.read(seq.HEAP_CUR_PTR)-20
        assert 0<=index<(self.h.read(obj)&255)
        bank=(self.h.read(obj+4)>>index)&1
        target=self.h.read(obj+12+4*bank)+4*index
        assert 0x20000000<=target<target+4<=self.h.read(seq.HEAP_CUR_PTR)
        return target

    def value(self,obj,index=0):return self.h.read(self.store_address(obj,index))

    def store_digest(self,obj):
        h=self.h;count=h.read(obj)&255
        assert 0<count<=32
        data=bytes(h.u.mem_read(obj,20))
        for bank in (12,16):data+=bytes(h.u.mem_read(h.read(obj+bank),count*4))
        return hashlib.sha256(data).hexdigest()

    def timer_state(self,index):
        assert index in (3,6)
        h=self.h;slot=h.read(TIMER_OBJECT+8)+28*index
        assert 0x20006F60<=slot<slot+28<=h.read(seq.HEAP_CUR_PTR)
        return dict(id=index,period=h.read(slot),remaining=h.read(slot+4),
            active=h.u.mem_read(slot+8,1)[0],callback=h.read(slot+12),argument=h.read(slot+16))

    def snapshot(self):
        h=self.h
        return dict(mode=h.u.mem_read(seq.SEQ_STATE_ADDR+4,1)[0],ctrl=self.ctrl,project=self.project,
            raw=self.raw,raw_sha256=hashlib.sha256(h.u.mem_read(self.raw,PROJECT_BYTES)).hexdigest(),
            grid=self.grid,grid_mode=h.u.mem_read(self.grid+0x264,1)[0],
            shift=self.value(h.read(self.ctrl+12)),transport=self.value(h.read(self.ctrl+0x18)),
            ready=self.value(h.read(self.projects+0x24)),phase=self.value(h.read(self.projects+0x28),1),
            project_flags=self.value(h.read(self.project+0x4C)),
            metadata_sha256=self.store_digest(h.read(self.projects+0x20)),
            held_pads=h.read(self.grid+0x228),note_owners=[self.value(h.read(self.ctrl+0x1C0+4*t)) for t in range(8)],
            step_owners=[dict(view=h.read(self.grid+0x74+4*t),
                pending=h.read(h.read(self.grid+0x74+4*t)+0xB8),held=h.read(h.read(self.grid+0x74+4*t)+0xC0),
                held_bits=sum((bool(int.from_bytes(h.u.mem_read(h.read(self.grid+0x74+4*t)+0x74+2*i,2),'little')&8)<<i) for i in range(32))) for t in range(8)],
            allocations=len(h.allocations),heap=h.read(seq.HEAP_CUR_PTR),nor_mutations=len(h.medium.mutations),
            io_count=len(self.io),min_msp=h.minimum_msp,task_min=dict(h.thread_min))

    def _observe(self,u,pc,size,_):
        h=self.h
        row=dict(input=self.active_input,pc=pc,task=h.task_by_tcb[h.running_tcb]['name'],
            r0=u.reg_read(UC_ARM_REG_R0),r1=u.reg_read(UC_ARM_REG_R1),caller=u.reg_read(UC_ARM_REG_LR),
            primask=u.reg_read(UC_ARM_REG_PRIMASK))
        if pc in TIMER_EVENTS:self.timer_events.append(row)
        elif pc in PROJECT_IO:self.io.append(row)
        elif pc==self.labels['c_mode_can_switch']:
            row['state']=self.snapshot();self.guards.append(row)
        else:self.voices.append(row)

    def input(self,kind,identifier,velocity=96,*,budget=600000):
        assert kind in ('button_down','button_up','pad_down','pad_up')
        slot={'pad_down':0,'pad_up':4,'button_down':8,'button_up':12}[kind]
        target=self.h.read(self.h.read(self.ctrl)+slot)&~1
        row=self._invoke(target,(self.ctrl,identifier,velocity if kind=='pad_down' else 0,0),
                         label=f'{kind}:{identifier}',budget=budget)
        row.update(kind=kind,id=identifier);self.inputs.append(row)
        return row

    def _invoke(self,target,args,*,label,budget=600000):
        """Call adapter at a Main boundary; only CPU context is restored."""
        h=self.h;u=h.u
        assert u.reg_read(UC_ARM_REG_PC)==MAIN_LOOP
        assert h.task_by_tcb[h.running_tcb]['name']=='Main'
        assert not u.reg_read(UC_ARM_REG_PRIMASK) and not u.reg_read(UC_ARM_REG_BASEPRI)
        context=u.context_save();tcb=h.running_tcb;sp=u.reg_read(UC_ARM_REG_PSP)
        invalid_before=len(h.invalid)
        bank=tuple(u.reg_read(r) for r in SAVED_REGS)
        high=tuple(u.reg_read(r) for r in FP_REGS[16:])
        before=self.snapshot()
        self.active_input=label
        for reg,value in zip((UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3),args):u.reg_write(reg,value)
        u.reg_write(UC_ARM_REG_LR,MAIN_LOOP|1)
        try:
            pc=h.run(target,MAIN_LOOP,budget=budget)
            assert pc==MAIN_LOOP,(hex(pc),h.stop_reason,list(map(hex,h.trace)))
            assert h.running_tcb==tcb and u.reg_read(UC_ARM_REG_PSP)==sp
            assert tuple(u.reg_read(r) for r in SAVED_REGS)==bank
            assert tuple(u.reg_read(r) for r in FP_REGS[16:])==high
            assert not u.reg_read(UC_ARM_REG_PRIMASK) and not u.reg_read(UC_ARM_REG_BASEPRI)
            assert h.validate_stacks() and len(h.invalid)==invalid_before
            after=self.snapshot()
            row=dict(target=target,before=before,after=after)
            # Input-call adapter only; native IRQs use the frame shim normally.
            u.context_restore(context)
            return row
        finally:self.active_input=None

    def service_timer_ticks(self,count):
        """Explicit synthetic tick debt, then native2677A countdown/dispatch.

        No elapsed time is inferred. Other armed native timers also run.
        The native timer slot, callback and view ownership are never seeded.
        """
        assert isinstance(count,int) and 1<=count<=255
        debt=self.h.read(TIMER_OBJECT+4)+10
        assert self.h.u.mem_read(debt,1)==b'\x00'
        self.h.u.mem_write(debt,bytes([count]))
        # Native2677A consumes exactly one pending tick per call, not the
        # entire pending byte. Preserve that native debit/countdown behavior.
        for index in range(count):
            row=self._invoke(0x0802677A,(TIMER_OBJECT,0,0,0),label=f'synthetic_timer_ticks:{count}:{index}')
        assert self.h.u.mem_read(debt,1)==b'\x00'
        return row

    def cycle(self,*,budget=600000):
        # Leave the endpoint first; do not mistake an immediate checkpoint for
        # execution of a full native Main iteration.
        h=self.h
        h.checkpoint(0x08025870,budget=budget)
        h.checkpoint(MAIN_LOOP,budget=budget)
        return self.snapshot()

    def shortcut(self):
        self.input('button_down',27)
        row=self.input('button_down',18)
        self.input('button_up',18);self.input('button_up',27)
        return row


def exercise_live_mode(s):
    """Assertions for one native boot lifetime; fault cases are labeled apart."""
    h=s.h;initial=s.snapshot();assert initial['ready']==14 and initial['phase']==initial['project_flags']==0
    assert initial['mode']==0
    def invariant(row,expected):
        before,after=row['before'],row['after']
        assert after['mode']==expected
        for field in ('project','raw','raw_sha256','metadata_sha256','heap','allocations','nor_mutations','io_count'):
            assert before[field]==after[field],(field,before[field],after[field])
    for expected in (1,0,1):invariant(s.shortcut(),expected)
    # Native bottom pad31 edits step32. No ownership or project object seed.
    row=s.input('pad_down',31);assert row['after']['held_pads']==1<<31
    invariant(s.shortcut(),1)
    row=s.input('pad_up',31);assert row['after']['held_pads']==0
    assert row['after']['raw_sha256']!=initial['raw_sha256']
    pending=s.snapshot();assert pending['step_owners'][0]['pending']==1<<31
    assert pending['step_owners'][0]['held']==pending['step_owners'][0]['held_bits']==0
    assert s.timer_state(6)['active']==s.timer_state(3)['active']==0
    invariant(s.shortcut(),0)  # completed click history is not live ownership
    assert s.snapshot()['step_owners'][0]['pending']==1<<31
    invariant(s.shortcut(),1)
    # Stock track change consumes cleanup hook without host-clearing masks.
    s.input('button_down',1);s.input('button_up',1)
    cleaned=s.snapshot()
    assert all(not (v['pending']|v['held']|v['held_bits']) for v in cleaned['step_owners'])
    invariant(s.shortcut(),0)
    edited=s.snapshot();assert edited['raw_sha256']!=initial['raw_sha256']
    fault_cases=[]
    for mode in (0,1):
        if s.snapshot()['mode']!=mode:invariant(s.shortcut(),mode)
        for label,obj,index,value in (
                ('transport_start',h.read(s.ctrl+0x18),0,1),
                ('transport_continue',h.read(s.ctrl+0x18),0,2),
                ('project_queued',h.read(s.projects+0x28),1,1),
                ('project_running',h.read(s.projects+0x28),1,2),
                ('note_owner_track7',h.read(s.ctrl+0x1C0+7*4),0,1)):
            address=s.store_address(obj,index);original=bytes(h.u.mem_read(address,4))
            h.word(address,value)  # explicit transient fault injection only
            try:
                row=s.shortcut();invariant(row,mode)
                fault_cases.append(dict(label=label,mode=mode,address=address,value=value))
            finally:h.u.mem_write(address,original)
    if s.snapshot()['mode']:invariant(s.shortcut(),0)
    # Re-enter the actual track0/grid0 graph; every pad edits only its own
    # eight-byte step. Each released click must allow both mode directions.
    s.input('button_down',0);s.input('button_up',0)
    invariant(s.shortcut(),1)
    pad_matrix=[]
    for pad in range(32):
        before=bytes(h.u.mem_read(s.raw,PROJECT_BYTES))
        row=s.input('pad_down',pad);owner=row['after']['step_owners'][0]
        assert row['after']['held_pads']==owner['held']==owner['held_bits']==1<<pad
        row=s.input('pad_up',pad);owner=row['after']['step_owners'][0]
        assert not (row['after']['held_pads']|owner['held']|owner['held_bits'])
        assert owner['pending']&(1<<pad) and not s.timer_state(6)['active']
        after=bytes(h.u.mem_read(s.raw,PROJECT_BYTES))
        delta=[i for i,(a,b) in enumerate(zip(before,after)) if a!=b]
        assert delta and all(0x2E4+8*pad<=i<0x2E4+8*(pad+1) for i in delta),(pad,delta)
        invariant(s.shortcut(),0);invariant(s.shortcut(),1)
        pad_matrix.append(dict(pad=pad,changed_raw_offsets=delta,released_owner=owner,timer6=s.timer_state(6)))
    # Long press: explicit synthetic tick debt drives the native timer's
    # countdown and registered callback. It is not elapsed-time/GPIO proof.
    before_long=s.snapshot();s.input('pad_down',31)
    assert s.timer_state(6)['period']==s.timer_state(6)['remaining']==300
    s.service_timer_ticks(255);s.service_timer_ticks(44)
    before_expiry=s.snapshot();assert s.timer_state(6)['remaining']==1
    assert before_expiry['step_owners'][0]['pending']&(1<<31)
    s.service_timer_ticks(1)
    expired=s.snapshot();assert not s.timer_state(6)['active']
    assert not expired['step_owners'][0]['pending']&(1<<31)
    assert expired['step_owners'][0]['held']==expired['step_owners'][0]['held_bits']==1<<31
    invariant(s.shortcut(),1)  # expiry cannot bypass live held ownership
    s.input('pad_up',31)
    released_long=s.snapshot()
    assert released_long['raw_sha256']==before_long['raw_sha256']
    assert not (released_long['held_pads']|released_long['step_owners'][0]['held']|released_long['step_owners'][0]['held_bits'])
    invariant(s.shortcut(),0)
    assert not s.io and not h.invalid and h.validate_stacks()
    assert bytes(h.u.mem_read(0x08010000,len(s.image)))==s.image
    final=s.snapshot()
    assert final['heap']==initial['heap'] and final['allocations']==initial['allocations']
    assert final['nor_mutations']==initial['nor_mutations']
    assert all(v['primask']==0 for v in s.voices)
    assert all(g['primask']==1 for g in s.guards)
    return dict(initial=initial,pending_after_native_pad_release=pending,after_native_track_cleanup=cleaned,
        edited=edited,final=final,inputs=s.inputs,guards=s.guards,voice_calls=s.voices,
        project_io=s.io,transient_fault_cases=fault_cases,pad_matrix=pad_matrix,
        timer_events=s.timer_events,long_press=dict(before=before_long,before_expiry=before_expiry,
            expired=expired,released=released_long,synthetic_timer_ticks=[255,44,1]),
        startup_objects_seeded=False,firmware_instruction_stubs=False,physical_input=False)
