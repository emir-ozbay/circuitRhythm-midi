"""Non-nested Cortex-M4F frame shim over the native DSP/media boot harness.

Native VFP arithmetic and PendSV S16-S31 save/restore execute in Unicorn.
This layer supplies hardware exception stacking/unstacking and lazy low-FP
materialization. It is not cycle/NVIC/fault/nesting or auxiliary DSP emulation.
Default WorkerStartup still rejects FP. No firmware instructions are replaced.
Frame contract: Arm DAI0298A, figure1/sections2-3 (see accompanying report).
"""
import struct
from dataclasses import dataclass
from capstone import Cs,CS_ARCH_ARM,CS_MODE_THUMB,CS_MODE_MCLASS
from unicorn.arm_const import *
from recovery_dsp_test_support import DSPStartup
from recovery_worker_test_support import FRAME_REGS,SAVED_REGS,PENDSV,ICSR,BasicFrameOnly
from recovery_spi_test_support import IRQS
from recovery_input_test_support import ADC_IRQ,ADC_VECTOR,DMA as ADC_DMA,STREAM as ADC_STREAM
from recovery_media_test_support import DMA as NOR_DMA,QSPI
from recovery_boot_test_support import STOP

FPCCR,FPCAR,FPDSCR,CPACR = 0xE000EF34,0xE000EF38,0xE000EF3C,0xE000ED88
FP_REGS = tuple(globals()[f'UC_ARM_REG_S{i}'] for i in range(32))
IT_MASK=0x0600FC00


class UnsupportedFPContext(RuntimeError):pass


@dataclass
class ExceptionFrame:
    address: int
    sp: int
    core: list
    low: tuple
    fpscr: int
    extended: bool
    lazy: bool
    materialized: bool = False

    @property
    def size(self):return 104 if self.extended else 32

    @property
    def exc_return(self):return 0xFFFFFFED if self.extended else 0xFFFFFFFD


class FPUStartup(DSPStartup):
    def __init__(self,image,**options):
        self.fp_decoder=Cs(CS_ARCH_ARM,CS_MODE_THUMB|CS_MODE_MCLASS)
        self.fp_instructions={}
        self.lazy_frame=None
        self.fp_events=[]
        self.exception_events=[]
        super().__init__(image,**options)

    @staticmethod
    def _condition_passes(psr):
        it=((psr>>25)&3)|((psr>>8)&0xFC)
        if not it:return True
        cond=it>>4
        n,z,c,v=(bool(psr&(1<<bit)) for bit in (31,30,29,28))
        values=(z,c,n,v,c and not z,n==v,n==v and not z,True)
        result=values[cond>>1]
        return not result if cond&1 and cond!=15 else result

    def _fp_before(self,u,pc):
        if pc in self.fp_opcode and not self.fp_opcode[pc] and pc not in self.fp_instructions:return
        first=int.from_bytes(u.mem_read(pc,2),'little')
        if first&0xEC00!=0xEC00:
            self.fp_opcode[pc]=False
            return
        if pc not in self.fp_instructions:
            ins=next(self.fp_decoder.disasm(bytes(u.mem_read(pc,4)),pc),None)
            # CP10/11 VFP instructions only; do not admit arbitrary coprocessors
            # or double-precision arithmetic unsupported by the physical M4F.
            assert ins is not None
            allowed=ins.mnemonic.startswith(('vpush','vpop','vldr','vstr','vldm','vstm','vmov','vmrs','vmsr',
                'vcvt','vadd','vsub','vmul','vdiv','vmla','vmls','vneg','vabs','vsqrt','vcmp','vcmpe','vnmla','vnmls','vnmul','vfma','vfms','vfnma','vfnms'))
            if not allowed or '.f64' in ins.mnemonic:
                raise BasicFrameOnly(f'Unsupported FP/coprocessor at {pc:#x}: {ins.mnemonic}')
            self.fp_instructions[pc]=(ins.mnemonic,ins.op_str)
        self.fp_opcode[pc]=False  # only this opt-in subclass admits validated VFP
        if not self._condition_passes(u.reg_read(UC_ARM_REG_XPSR)):return
        if self.read(CPACR)&0xF00000!=0xF00000:
            raise UnsupportedFPContext('CP10/CP11 must be enabled by native firmware')
        if not self.read(FPCCR)&0x80000000:
            raise UnsupportedFPContext('manual FP context preservation is not modeled')
        if self.lazy_frame is not None:
            self._materialize(self.lazy_frame)
        self.fp_events.append(dict(pc=pc,in_service=self.in_service,instruction=self.fp_instructions[pc][0]))

    def _observe_thread(self,u,pc,size,data):
        self._fp_before(u,pc)
        return super()._observe_thread(u,pc,size,data)

    def _make_frame(self,pc,sp,*,reserve_software=False):
        u=self.u
        extended=bool(u.reg_read(UC_ARM_REG_CONTROL)&4)
        if self.lazy_frame is not None or self.read(FPCCR)&1:
            raise UnsupportedFPContext('nested/lazy exception ownership is not modeled')
        if extended and (self.read(CPACR)&0xF00000!=0xF00000 or not self.read(FPCCR)&0x80000000):
            raise UnsupportedFPContext('invalid automatic FP context configuration')
        size=104 if extended else 32
        address=(sp-size)&~7
        software=36+(64 if extended else 0) if reserve_software else 0
        if self.cooperative:self._bounds(self.running_tcb,address-software,sp-address+software)
        else:assert not extended and sp==self.initial_sp
        psr=u.reg_read(UC_ARM_REG_XPSR)
        assert psr&0x01000000 and not psr&0x1FF,hex(psr)
        psr=(psr&~512)|(512 if sp&4 else 0)
        core=[u.reg_read(r) for r in FRAME_REGS]+[pc,psr]
        frame=ExceptionFrame(address,sp,core,tuple(u.reg_read(r) for r in FP_REGS[:16]),
                             u.reg_read(UC_ARM_REG_FPSCR),extended,bool(extended and self.read(FPCCR)&0x40000000))
        u.mem_write(address,struct.pack('<8I',*core))
        if extended:
            self.word(FPCAR,address+32)
            if frame.lazy:
                self.lazy_frame=frame
                self.word(FPCCR,self.read(FPCCR)|1)
            else:self._materialize(frame)
        return frame

    def _materialize(self,frame):
        assert frame.extended and not frame.materialized
        self.u.mem_write(frame.address+32,struct.pack('<17I',*frame.low,frame.fpscr))
        frame.materialized=True
        self.word(FPCCR,self.read(FPCCR)&~1)
        if self.lazy_frame is frame:self.lazy_frame=None

    def _hardware_frame(self,pc,sp):
        # Initial SVC uses the unchanged basic frame contract.
        frame=self._make_frame(pc,sp,reserve_software=self.cooperative)
        return frame.address,frame.core

    def _restore_frame(self):
        u=self.u;code=u.reg_read(UC_ARM_REG_LR)
        assert code in (0xFFFFFFFD,0xFFFFFFED),hex(code)
        extended=not bool(code&16);size=104 if extended else 32
        task=self._current();incoming=u.reg_read(UC_ARM_REG_PSP)
        self._bounds(task,incoming,size)
        core=list(struct.unpack('<8I',u.mem_read(incoming,32)))
        assert core[7]&0x01000000 and not core[7]&0x1FF
        assert 0x08010200<=core[6]<0x08080000
        assert self.lazy_frame is None,'outgoing FP context must materialize before task switch'
        if extended:
            values=struct.unpack('<17I',u.mem_read(incoming+32,68))
            for r,value in zip(FP_REGS[:16],values[:16]):u.reg_write(r,value)
            u.reg_write(UC_ARM_REG_FPSCR,values[16])
        after=incoming+size+(4 if core[7]&512 else 0)
        self._bounds(task,incoming,after-incoming)
        for r,value in zip(FRAME_REGS,core[:6]):u.reg_write(r,value)
        u.reg_write(UC_ARM_REG_PSP,after)
        u.reg_write(UC_ARM_REG_CONTROL,2|(4 if extended else 0))
        u.reg_write(UC_ARM_REG_XPSR,core[7]&~512)
        u.reg_write(UC_ARM_REG_PC,core[6]|1)
        self.running_tcb=task
        self.thread_min[task]=min(self.thread_min.get(task,0xFFFFFFFF),incoming-36-(64 if extended else 0))
        return incoming,core

    def _irq_call(self,handler,vector):
        u=self.u
        assert self.cooperative and not self.in_service
        assert not u.reg_read(UC_ARM_REG_PRIMASK)
        assert not u.reg_read(UC_ARM_REG_XPSR)&IT_MASK
        context=u.context_save();msp=u.reg_read(UC_ARM_REG_MSP)
        bank=tuple(u.reg_read(r) for r in SAVED_REGS)
        fp=tuple(u.reg_read(r) for r in FP_REGS)+(u.reg_read(UC_ARM_REG_FPSCR),)
        frame=self._make_frame(u.reg_read(UC_ARM_REG_PC),u.reg_read(UC_ARM_REG_PSP))
        self.thread_min[self.running_tcb]=min(self.thread_min[self.running_tcb],frame.address)
        self.in_service=True
        try:
            u.reg_write(UC_ARM_REG_PSP,frame.address)
            u.reg_write(UC_ARM_REG_CONTROL,0)
            u.reg_write(UC_ARM_REG_XPSR,(frame.core[7]&~(0x1FF|IT_MASK|512))|vector)
            result=self.call(handler)
            assert result['pc']==STOP and result['error'] is None,result
            assert u.reg_read(UC_ARM_REG_MSP)==msp
            assert tuple(u.reg_read(r) for r in SAVED_REGS)==bank
            assert tuple(u.reg_read(r) for r in FP_REGS[16:])==fp[16:32]
            assert bytes(u.mem_read(frame.address,32))==struct.pack('<8I',*frame.core)
            if frame.extended and frame.materialized:
                values=struct.unpack('<17I',u.mem_read(frame.address+32,68))
                assert values==frame.low+(frame.fpscr,)
                for r,value in zip(FP_REGS[:16],values[:16]):u.reg_write(r,value)
                u.reg_write(UC_ARM_REG_FPSCR,values[16])
            elif frame.extended:
                assert self.lazy_frame is frame and tuple(u.reg_read(r) for r in FP_REGS[:16])==frame.low
                assert u.reg_read(UC_ARM_REG_FPSCR)==frame.fpscr
                self.lazy_frame=None;self.word(FPCCR,self.read(FPCCR)&~1)
            for r,value in zip(FRAME_REGS,frame.core[:6]):u.reg_write(r,value)
            u.reg_write(UC_ARM_REG_PSP,frame.sp)
            u.reg_write(UC_ARM_REG_CONTROL,2|(4 if frame.extended else 0))
            u.reg_write(UC_ARM_REG_XPSR,frame.core[7]&~512)
            u.reg_write(UC_ARM_REG_PC,frame.core[6]|1)
            if frame.extended:assert tuple(u.reg_read(r) for r in FP_REGS)+(u.reg_read(UC_ARM_REG_FPSCR),)==fp
            event=dict(handler=handler,exception=vector,frame_sp=frame.address,extended=frame.extended,
                       lazy=frame.lazy,materialized=frame.materialized)
            self.exception_events.append(event)
            return event
        except BaseException:
            u.context_restore(context)
            raise
        finally:self.in_service=False

    def deliver_spi_irq(self,direction):
        handler,vector,status,flag=IRQS[direction]
        assert self.read(status)&flag and not self.u.reg_read(UC_ARM_REG_BASEPRI)
        event=self._irq_call(handler,vector)
        assert not self.read(status)&flag
        self.spi_irqs.append(dict(direction=direction,**event))

    def deliver_input_irq(self):
        assert self.read(ADC_DMA)&32 and self.read(ADC_STREAM)&16
        assert not self.u.reg_read(UC_ARM_REG_BASEPRI)
        event=self._irq_call(ADC_IRQ,ADC_VECTOR)
        assert not self.read(ADC_DMA)&32
        self.input_irqs.append(event)

    def _dma_irq(self):
        if not self.cooperative:return super()._dma_irq()
        assert self.read(0x08010000+86*4)==0x080645EF
        self._irq_call(0x080645EE,86)
        assert not self.read(NOR_DMA+4)&(1<<27)
        self.qspi_dma_irqs.append(dict(handler=0x080645EE))

    def _qspi_irq(self,pc):
        if not self.cooperative:return super()._qspi_irq(pc)
        self.word(QSPI+8,8 if pc==0x08041C68 else 2)
        self._irq_call(0x080645E0,108)

    def _service(self,pc):
        if not self.cooperative:return super()._service(pc)
        if self.reason=='pendsv':return self._switch(pc)
        if self.reason not in ('tick','sdio'):return super()._service(pc)
        reason=self.reason
        if reason=='sdio':
            command=self.read(0x40012C0C)&63;self.sdio_commands.append(command)
            self.word(0x40012C34,0x80 if command==0 else 4)
            self._irq_call(0x08064762,65);self.sdio_irqs+=1
        else:
            self._irq_call(0x08066BD0,15);self.ticks+=1;self.next_tick=self.instructions+256
        self.skip=pc;self.events.append(dict(kind=reason,interrupted_pc=pc))

    def _switch(self,pc):
        u=self.u;old=self._current();assert old==self.running_tcb
        saved=tuple(u.reg_read(r) for r in SAVED_REGS)
        high=tuple(u.reg_read(r) for r in FP_REGS[16:])
        frame=self._make_frame(pc,u.reg_read(UC_ARM_REG_PSP),reserve_software=True)
        u.reg_write(UC_ARM_REG_PSP,frame.address)
        u.reg_write(UC_ARM_REG_CONTROL,0)
        u.reg_write(UC_ARM_REG_XPSR,(frame.core[7]&~(0x1FF|IT_MASK|512))|14)
        u.reg_write(UC_ARM_REG_LR,frame.exc_return)
        self.in_service=True
        try:
            u.emu_start(PENDSV|1,0x08025C6A,count=50000)
            assert u.reg_read(UC_ARM_REG_PC)==0x08025C6A
            address=self.read(old);software=36+(64 if frame.extended else 0)
            self._bounds(old,address,software+frame.size)
            assert tuple(struct.unpack('<9I',u.mem_read(address,36)))==saved+(frame.exc_return,)
            assert address+software==frame.address
            assert bytes(u.mem_read(frame.address,32))==struct.pack('<8I',*frame.core)
            if frame.extended:
                assert frame.materialized and self.lazy_frame is None
                assert struct.unpack('<16I',u.mem_read(address+36,64))==high
                assert struct.unpack('<17I',u.mem_read(frame.address+32,68))==frame.low+(frame.fpscr,)
            new=self._current();incoming_saved=self.read(new)
            incoming=struct.unpack('<9I',u.mem_read(incoming_saved,36))
            assert tuple(u.reg_read(r) for r in SAVED_REGS)==incoming[:8]
            if not incoming[8]&16:
                assert tuple(u.reg_read(r) for r in FP_REGS[16:])==struct.unpack('<16I',u.mem_read(incoming_saved+36,64))
            incoming_sp,incoming_frame=self._restore_frame()
            self.word(ICSR,self.read(ICSR)&~0x10000000);self.pending_pendsv=False
            self.thread_min[old]=min(self.thread_min[old],address)
            self.switches.append(dict(old=old,new=new,interrupted_pc=pc,resume=incoming_frame[6],
                saved_sp=address,hardware_sp=frame.address,incoming_sp=incoming_sp,
                outgoing_extended=frame.extended,incoming_extended=not bool(incoming[8]&16),
                lazy=frame.lazy,materialized=frame.materialized))
        finally:self.in_service=False
