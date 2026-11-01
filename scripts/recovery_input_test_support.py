"""Native ADC DMA producer/consumer through Main's input-readiness branch.

Synthetic ADC values and factory calibration, not physical input/timing proof.
Only the two native DMA targets receive host sample writes. Native646E8/
27762 copy samples and publish pending; native265BA advances sampler state.
The IRQ adapter models a basic PSP frame and MSP call, then restores the saved
CPU context; exception return/NVIC arbitration and ADC conversion timing are
not emulated. Inherited worker/other peripheral model limits still apply.
"""
import struct
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_WRITE, UC_PROT_READ
from unicorn.arm_const import *
from recovery_boot_test_support import STOP
from recovery_worker_test_support import WorkerStartup, READY_GATE, SAVED_REGS

DMA = 0x40026400
STREAM = DMA+0x10
ADC_IRQ = 0x080646E8
ADC_VECTOR = 72
MAIN_INPUT_LOOP = 0x080257C8
MAIN_INPUT_READY = 0x0802582E
SPI_WAIT = 0x0802B66C
MAIN_LOOP = 0x08025864
CALIBRATION = 0x1FF0F44A  # literal read by native2BF08, not a measured value


class InputStartup(WorkerStartup):
    def __init__(self, image, *, sample=2048, calibration=1500):
        assert 0 <= sample <= 4095 and 0 < calibration <= 4095
        super().__init__(image)
        self.sample, self.calibration = sample, calibration
        self.input_enabled = False
        self.input_irq_enabled = True
        self.input_skip = False
        self.dma_transfers, self.input_irqs, self.ready_checks = [], [], []
        self.u.mem_map(CALIBRATION & ~4095, 4096)
        self.u.mem_write(CALIBRATION, struct.pack('<H', calibration))
        self.u.mem_protect(CALIBRATION & ~4095, 4096, UC_PROT_READ)
        # No global RAM-write hook: conditional STM/IT is sensitive in Unicorn.
        self.u.hook_add(UC_HOOK_MEM_WRITE, self._dma_clear, begin=DMA+8, end=DMA+11)
        self.u.hook_add(UC_HOOK_CODE, self._input_code)

    def _dma_clear(self, u, kind, address, size, value, _):
        assert address == DMA+8 and size == 4
        self.word(DMA, self.read(DMA) & ~value)  # DMA LIFCR write-one-to-clear

    def _input_code(self, u, pc, size, _):
        if not self.cooperative or self.in_service:
            return
        if pc == READY_GATE:
            self.ready_checks.append(self.readiness()['counters'])
        if pc != MAIN_INPUT_LOOP or not self.input_enabled or self.reason is not None:
            return
        if self.input_skip:
            self.input_skip = False
            return
        assert self.task_by_tcb[self.running_tcb]['name'] == 'Main'
        if not u.reg_read(UC_ARM_REG_PRIMASK) and not u.reg_read(UC_ARM_REG_BASEPRI):
            assert not u.reg_read(UC_ARM_REG_XPSR) & 0x0600FC00
            self.reason = 'input_dma'
            u.emu_stop()

    def _configuration(self):
        # Reject unsupported stream settings before any model write. Fields
        # include double buffer, halfword width, memory increment and TC IRQ.
        cr = self.read(STREAM)
        assert cr & ~(1 << 19) == 0x52C15, hex(cr)
        assert self.read(STREAM+4) == 96
        assert self.read(STREAM+8) == 0x40012308
        raw = self.read(0x20000338)  # embedded driver+4; global334 is NOT a pointer
        assert raw == self.read(0x080266B4)
        assert [self.read(STREAM+12), self.read(STREAM+16)] == [raw+0xC4, raw+0x184]
        assert self.read(0x08010000+4*ADC_VECTOR) == ADC_IRQ | 1
        return cr, raw, self.read(STREAM+12+(4 if cr & (1 << 19) else 0))

    def start_input(self):
        assert self.u.reg_read(UC_ARM_REG_PC) == READY_GATE
        self._configuration()
        self.input_enabled = True
        return self

    def complete_input_dma(self, *, deliver=True):
        cr, raw, target = self._configuration()
        payload = struct.pack('<96H', *([self.sample]*96))
        before = self.readiness()['counters']
        self.u.mem_write(target, payload)
        # A completed double-buffer transfer changes CT and reloads NDTR.
        # NDTR is already96 at these boundary-only observations.
        self.word(STREAM, cr ^ (1 << 19))
        self.word(DMA, self.read(DMA) | 32)
        event = dict(target=target, bytes=len(payload), ct_before=bool(cr & (1 << 19)),
                     counters_before=before, irq_delivered=deliver)
        self.dma_transfers.append(event)
        if deliver:
            self.deliver_input_irq()
            assert bytes(self.u.mem_read(raw+4, 192)) == payload
            assert self.readiness()['counters'] == before, 'IRQ must not advance consumer counters'
            assert not self.read(DMA) & 32
        event.update(counters_after=self.readiness()['counters'], pending=self.u.mem_read(raw+2, 1)[0])
        return event

    def deliver_input_irq(self):
        u = self.u
        assert self.cooperative and not self.in_service
        assert not u.reg_read(UC_ARM_REG_PRIMASK) and not u.reg_read(UC_ARM_REG_BASEPRI)
        assert not u.reg_read(UC_ARM_REG_CONTROL) & 4
        assert self.read(DMA) & 32 and self.read(STREAM) & 16
        context = u.context_save()
        pc, sp = u.reg_read(UC_ARM_REG_PC), u.reg_read(UC_ARM_REG_PSP)
        saved_regs = [u.reg_read(r) for r in SAVED_REGS]
        frame_sp, frame = self._hardware_frame(pc, sp)
        msp = u.reg_read(UC_ARM_REG_MSP)
        self.thread_min[self.running_tcb] = min(self.thread_min[self.running_tcb], frame_sp)
        self.in_service = True
        try:
            u.reg_write(UC_ARM_REG_PSP, frame_sp)
            u.reg_write(UC_ARM_REG_CONTROL, 0)
            u.reg_write(UC_ARM_REG_XPSR, (frame[7] & ~0x1FF) | ADC_VECTOR)
            # Native C IRQ body returns to STOP; this adapter restores context,
            # not an emulated architectural BX EXC_RETURN.
            result = self.call(ADC_IRQ)
            assert result['pc'] == STOP and result['error'] is None, result
            assert u.reg_read(UC_ARM_REG_MSP) == msp
            assert [u.reg_read(r) for r in SAVED_REGS] == saved_regs
            assert bytes(u.mem_read(frame_sp, 32)) == struct.pack('<8I', *frame)
            self.input_irqs.append(dict(handler=ADC_IRQ, exception=ADC_VECTOR,
                                        interrupted_pc=pc, frame_sp=frame_sp, msp=msp))
        finally:
            u.context_restore(context)
            self.in_service = False

    def _service(self, pc):
        if self.reason != 'input_dma':
            return super()._service(pc)
        self.complete_input_dma(deliver=self.input_irq_enabled)
        self.input_skip = True
