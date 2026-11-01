"""Finite TIM compare events,native IRQ66 and Main AppTimer consumption.

SR uses write-zero-to-clear semantics from before native Main setup. Explicit
compare events supply CNT/CC1IF;no autonomous time,NVIC arbitration or rate is
inferred. Debt,slots,callbacks,projects and firmware instructions are not seeded.
"""
import struct
from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_READ,UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_PC,UC_ARM_REG_PRIMASK,UC_ARM_REG_BASEPRI,UC_ARM_REG_R0,UC_ARM_REG_R3,UC_ARM_REG_LR,UC_ARM_REG_XPSR
from recovery_live_mode_test_support import LiveModeStartup,LiveModeSession,TIMER_OBJECT
from recovery_dsp_test_support import ScriptedDSPPeer,DSPRead,mailbox_script
from recovery_input_test_support import MAIN_LOOP,MAIN_INPUT_READY,STREAM,DMA

BASE=0x40000C00
VECTOR=66
HANDLER=0x08064698
MAIN_TIMER_OBJECT=0x20000358
UI_TIMER_OBJECT=0x20000364


class ExhaustedTimerCredits(RuntimeError):pass
class ExhaustedADCCredits(RuntimeError):pass


class TimerStartup(LiveModeStartup):
    def __init__(self,image,*,adc_scan=None,adc_frame_credits=0,**options):
        super().__init__(image,**options)
        self.adc_scan=tuple(adc_scan) if adc_scan is not None else None
        if self.adc_scan is not None:
            assert len(self.adc_scan)==3 and all(isinstance(v,int) and 0<=v<=4095 for v in self.adc_scan)
            assert isinstance(adc_frame_credits,int) and adc_frame_credits>0
        self.adc_frame_credits=adc_frame_credits;self.adc_initial_credits=adc_frame_credits

    def complete_input_dma(self,*,deliver=True):
        if self.adc_scan is None:return super().complete_input_dma(deliver=deliver)
        if not self.adc_frame_credits:raise ExhaustedADCCredits('finite ADC frame input exhausted')
        cr,raw,target=self._configuration();before=self.readiness()['counters']
        payload=struct.pack('<96H',*(self.adc_scan*32));self.adc_frame_credits-=1
        # Only the native DMA destination receives raw input. Native646E8/
        # 27762 copies it;265BA/2BEF4 performs calibration and publication.
        self.u.mem_write(target,payload)
        self.word(STREAM,cr^(1<<19));self.word(DMA,self.read(DMA)|32)
        event=dict(target=target,bytes=len(payload),ct_before=bool(cr&(1<<19)),
            counters_before=before,irq_delivered=deliver,adc_scan=list(self.adc_scan))
        self.dma_transfers.append(event)
        if deliver:
            self.deliver_input_irq()
            assert bytes(self.u.mem_read(raw+4,192))==payload
            assert self.readiness()['counters']==before and not self.read(DMA)&32
        event.update(counters_after=self.readiness()['counters'],pending=self.u.mem_read(raw+2,1)[0])
        return event


class TimerLiveModeSession(LiveModeSession):
    def service_timer_ticks(self,count):
        raise AssertionError('direct synthetic timer debt is forbidden in this IRQ session')


class NativeTimerPeer:
    def __init__(self,h,*,compare_credits):
        assert isinstance(compare_credits,int) and compare_credits>0
        self.h=h;self.s=None;self.initial_credits=compare_credits;self.remaining=compare_credits
        self.flags=h.read(BASE+0x10);assert self.flags==0,'install timer peer before native Main setup'
        self.pending_status=False;self.status_writes=[];self.software_events=[]
        self.events=[];self.writes=[];self.consumers=[];self.dispatches=[];self.record_idle_reads=[];self.battery_results=[];self.writer=None;self.event_active=False
        h.u.hook_add(UC_HOOK_MEM_WRITE,self._mmio_write,begin=BASE+0x10,end=BASE+0x17)
        h.u.hook_add(UC_HOOK_MEM_READ,self._status_read,begin=BASE+0x10,end=BASE+0x13)

    def _mmio_write(self,u,kind,address,size,value,_):
        # No CPU register reads in a write hook (Unicorn M-class ITSTATE).
        assert size==4
        if address==BASE+0x10:
            old=self.flags;self.flags&=value;self.pending_status=True
            self.status_writes.append(dict(value=value,before=old,after=self.flags))
        else:
            assert address==BASE+0x14 and value&~3==0,('unsupported TIM software event',hex(value))
            self.flags|=value&3;self.pending_status=True;self.software_events.append(value)

    def _status_read(self,u,kind,address,size,value,_):
        assert address==BASE+0x10 and size==4
        self._flush_status()

    def _flush_status(self):
        if self.pending_status:
            self.h.word(BASE+0x10,self.flags);self.pending_status=False

    def bind(self,s):
        h=self.h;assert self.s is None and s.h is h
        self._flush_status();self.s=s;self.driver=h.read(TIMER_OBJECT+4)
        assert self.driver==0x200001D0 and h.read(self.driver+4)==BASE
        assert h.read(MAIN_TIMER_OBJECT+4)==self.driver
        slot=h.read(MAIN_TIMER_OBJECT+8)+28*11
        assert h.read(slot)==1 and h.u.mem_read(slot+8,1)[0]==2 and h.read(slot+12)==0x0802B751
        assert int.from_bytes(s.image[VECTOR*4:VECTOR*4+4],'little')==HANDLER|1
        assert h.read(BASE)&1 and h.read(BASE+0x0C)&2 and self.flags==0
        self.step=int.from_bytes(h.u.mem_read(self.driver+8,2),'little')
        self.cap=h.u.mem_read(self.driver+11,1)[0]
        assert self.step==10 and self.cap==254 and self.debt()==0
        self.initial_registers={hex(o):h.read(BASE+o) for o in (0,4,8,0xC,0x10,0x18,0x20,0x24,0x28,0x2C,0x34)}
        h.u.hook_add(UC_HOOK_MEM_WRITE,self._debt_write,begin=self.driver+10,end=self.driver+10)
        for pc in (0x0802677A,0x0802679E,0x08064846,0x0802B750,0x080644E2,0x0802D8DA):
            h.u.hook_add(UC_HOOK_CODE,self._observe,begin=pc,end=pc)
        return self

    def debt(self):return self.h.u.mem_read(self.driver+10,1)[0]

    def _observe(self,u,pc,size,_):
        if pc==0x0802677A:
            obj=u.reg_read(UC_ARM_REG_R0);caller=u.reg_read(UC_ARM_REG_LR)
            if obj==UI_TIMER_OBJECT:
                assert caller==0x0802595D
                return
            assert obj==MAIN_TIMER_OBJECT and caller==0x08025871,'timer debt must be consumed by native Main'
            self.consumers.append(dict(object=obj,caller=caller,debt=self.debt()))
        elif pc==0x0802D8DA:
            value=u.reg_read(UC_ARM_REG_R0)
            assert 12<value<=100,'this workload supplies a charged-battery ADC scenario'
            self.battery_results.append(value)
        elif pc==0x080644E2:
            assert u.reg_read(UC_ARM_REG_R0)==0xFFFF,'this workload supplies recording-idle DSP status'
            self.record_idle_reads.append(dict(result=0xFFFF,debt=self.debt()))
        elif pc==0x0802B750:
            assert self.h.task_by_tcb[self.h.running_tcb]['name']=='Main'
            assert u.reg_read(UC_ARM_REG_LR)==0x080267DD
            self.dispatches.append(dict(caller=u.reg_read(UC_ARM_REG_LR),debt=self.debt()))
        else:
            if u.reg_read(UC_ARM_REG_R3)!=self.driver+10:
                assert pc==0x0802679E  # unrelated UI timer uses its own driver
                self.writer=None;return
            self.writer=dict(pc=pc,exception=u.reg_read(UC_ARM_REG_XPSR)&511)
            assert self.writer['exception']==(VECTOR if pc==0x08064846 else 0)

    def _debt_write(self,u,kind,address,size,value,_):
        assert address==self.driver+10 and size==1 and self.writer is not None
        old=self.debt();pc=self.writer['pc']
        assert value==old+(1 if pc==0x08064846 else -1)
        assert 0<=value<=self.cap
        self.writes.append(dict(**self.writer,before=old,after=value))
        self.writer=None

    def _at_main(self):
        h=self.h;u=h.u
        assert self.s is not None and not h.in_service and u.reg_read(UC_ARM_REG_PC)==MAIN_LOOP
        assert not u.reg_read(UC_ARM_REG_PRIMASK) and not u.reg_read(UC_ARM_REG_BASEPRI)
        assert h.task_by_tcb[h.running_tcb]['name']=='Main'

    def deliver(self,count=1):
        assert isinstance(count,int) and count>0
        self._at_main()
        if count>self.remaining:raise ExhaustedTimerCredits('finite compare-event input exhausted')
        assert count<=254 and not self.event_active
        h=self.h
        for _ in range(count):
            assert h.read(BASE)&1 and h.read(BASE+0x0C)&2 and self.flags==0
            old=self.debt();compare=h.read(BASE+0x34)
            assert compare<=h.read(BASE+0x2C)
            h.word(BASE+0x24,compare)  # finite peripheral CNT input,not firmware RAM
            self.flags|=2;h.word(BASE+0x10,self.flags);self.remaining-=1
            self.event_active=True
            try:frame=h._irq_call(HANDLER,VECTOR)
            finally:self.event_active=False
            self._flush_status()
            assert self.flags==h.read(BASE+0x10)==0
            assert self.debt()==min(self.cap,old+1)
            assert h.read(BASE+0x34)==(compare+self.step)&0xFFFFFFFF
            self.events.append(dict(cnt=compare,ccr1=h.read(BASE+0x34),before=old,after=self.debt(),frame=frame))

    def spurious(self):
        self._at_main();assert self.flags==0
        before=self.debt();compare=self.h.read(BASE+0x34);n=len(self.writes)
        self.h._irq_call(HANDLER,VECTOR);self._flush_status()
        assert self.debt()==before and self.h.read(BASE+0x34)==compare and len(self.writes)==n

    def report(self):
        return dict(initial_credits=self.initial_credits,used_credits=self.initial_credits-self.remaining,
            driver=self.driver,mmio=BASE,vector=VECTOR,handler=HANDLER,initial_registers=self.initial_registers,
            status_writes=self.status_writes,software_events=self.software_events,events=self.events,
            native_debt_writes=self.writes,main_consumers=self.consumers,application_dispatches=self.dispatches,
            recording_idle_results=self.record_idle_reads,dsp_inputs=self.h.dsp_peer.reads,
            battery_results=self.battery_results,adc_scan=self.h.adc_scan,adc_dma_inputs=self.h.dma_transfers,
            adc_initial_credits=self.h.adc_initial_credits,adc_used_credits=self.h.adc_initial_credits-self.h.adc_frame_credits,
            scope='Finite CNT/CC1IF events,SR W0C/EGR model,native IRQ66 via existing non-nested FPU frame shim. Main2677A/object358 consumes debt;its slot11 calls2B750 to dispatch higher timer370 without a second debt debit. No host debt writes,direct2677A adapter,autonomous time,NVIC arbitration,baud/tempo/jitter or physical timing proof.')


def boot_timer_session(image,*,sample_status=(),compare_credits,record_status=(),adc_scan=None,adc_frame_credits=0):
    reads=mailbox_script()+[DSPRead(0x371D5,v) for v in record_status]
    h=TimerStartup(image,peer_policy='ready',dsp_peer=ScriptedDSPPeer(reads),sample_status=sample_status,
        adc_scan=adc_scan,adc_frame_credits=adc_frame_credits)
    peer=NativeTimerPeer(h,compare_credits=compare_credits)
    h.main_setup().start_tasks().checkpoint().start_input().checkpoint(MAIN_INPUT_READY,budget=800000).start_spi()
    for _ in range(8):
        pc=h.run(h.u.reg_read(UC_ARM_REG_PC),MAIN_LOOP,budget=2000000)
        if pc==MAIN_LOOP:
            assert not h.invalid
            s=TimerLiveModeSession(h,image);return s,peer.bind(s)
    raise AssertionError('native Main loop not reached')
