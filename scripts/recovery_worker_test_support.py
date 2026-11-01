"""Native port/SVC/PendSV and Storage handshake with basic-frame CPU shim.

No task/ready/driver state or completion value is supplied by this model.
The shim stacks/un-stacks architectural basic frames; native port, handler,
selector, notification and worker code runs. Four priority bits and IRQ/wake
delivery at controlled boundaries are model assumptions, not NVIC/timing proof.
Thread FP/coprocessor instructions are rejected before execution.
"""
import struct
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
from recovery_main_test_support import MainStartup, SCHEDULER

ICSR = 0xE000ED04
PENDSV = 0x08025C10
SVC = 0x08025C6C
READY_GATE = 0x08026596
MAIN_AFTER_FIRST_DRAIN = 0x08026F72
FRAME_REGS = (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2,
              UC_ARM_REG_R3, UC_ARM_REG_R12, UC_ARM_REG_LR)
SAVED_REGS = (UC_ARM_REG_R4, UC_ARM_REG_R5, UC_ARM_REG_R6, UC_ARM_REG_R7,
              UC_ARM_REG_R8, UC_ARM_REG_R9, UC_ARM_REG_R10, UC_ARM_REG_R11)


class BasicFrameOnly(RuntimeError):
    pass


class WorkerStartup(MainStartup):
    def __init__(self, image):
        self.cooperative = False
        super().__init__(image)
        self.minimum_msp = self.min_sp
        self.dispatch_enabled = self.wake_enabled = True
        self.switches, self.requests, self.completions, self.worker_calls = [], [], [], []
        self.thread_min, self.fp_opcode = {}, {}
        self.pending_pendsv = False
        self.wfi_wakes = 0
        self.stop_reason = None
        self.u.hook_add(UC_HOOK_CODE, self._observe_thread)
        # This exact register is written by STR, not conditional STM. Avoid a
        # global memory callback (see the prior Unicorn IT/STM negative).
        self.u.hook_add(UC_HOOK_MEM_WRITE, self._icsr_write, begin=ICSR, end=ICSR+3)

    def _icsr_write(self, u, kind, address, size, value, _):
        if value & 0x10000000:
            self.pending_pendsv = True
        elif value & 0x08000000:
            self.pending_pendsv = False

    def _current(self):
        return self.read(self.current_pointer)

    def _bounds(self, tcb, address, size):
        task = self.task_by_tcb[tcb]
        assert task['stack'] <= address <= address+size <= task['stack']+4*task['words'], (task['name'], hex(address), size)

    def _hardware_frame(self, pc, sp):
        psr = self.u.reg_read(UC_ARM_REG_XPSR)
        frame_sp = (sp-32) & ~7
        if self.cooperative:
            self._bounds(self.running_tcb, frame_sp-36, sp-(frame_sp-36))
        else:
            assert sp == self.initial_sp and frame_sp == self.initial_sp-32
        psr = (psr & ~512) | (512 if sp & 4 else 0)
        frame = [self.u.reg_read(r) for r in FRAME_REGS] + [pc, psr]
        self.u.mem_write(frame_sp, struct.pack('<8I', *frame))
        return frame_sp, frame

    def _restore_frame(self):
        u = self.u
        assert u.reg_read(UC_ARM_REG_LR) == 0xFFFFFFFD, 'only Thread/PSP/basic return is supported'
        task = self._current()
        incoming = u.reg_read(UC_ARM_REG_PSP)
        self._bounds(task, incoming, 32)
        frame = list(struct.unpack('<8I', u.mem_read(incoming, 32)))
        assert frame[7] & 0x01000000 and not frame[7] & 0x1FF
        assert 0x08010200 <= frame[6] < 0x08080000
        after = incoming+32+(4 if frame[7] & 512 else 0)
        self._bounds(task, incoming, after-incoming)
        for reg, value in zip(FRAME_REGS, frame[:6]):
            u.reg_write(reg, value)
        u.reg_write(UC_ARM_REG_PSP, after)
        u.reg_write(UC_ARM_REG_CONTROL, 2)
        u.reg_write(UC_ARM_REG_XPSR, frame[7] & ~512)
        u.reg_write(UC_ARM_REG_PC, frame[6])
        self.running_tcb = task
        self.thread_min[task] = min(self.thread_min.get(task, 0xFFFFFFFF), incoming-36)
        return incoming, frame

    def start_tasks(self):
        self.task_by_tcb = {t['tcb']: t for t in self.tasks}
        self.current_pointer = self.read(0x08025CB8)
        self.critical_pointer = self.read(0x08025568)+4
        self.critical_before = self.read(self.critical_pointer)
        priority = self.read(0x0802556C)

        def priority_read(u, kind, address, size, value, _):
            u.mem_write(address, bytes([u.mem_read(address, 1)[0] & 0xF0]))

        self.u.hook_add(UC_HOOK_MEM_READ, priority_read, begin=priority, end=priority)
        assert self.run(SCHEDULER, 0x08025CA6) == 0x08025CA6
        assert self.read(self.critical_pointer) == 0
        assert self.read(0xE000ED08) == 0x08010000
        # Model SVC exception entry after the real vPortStartFirstTask reset
        # of MSP/CONTROL. Its old MSP frame remains when returning on PSP.
        sp = self.u.reg_read(UC_ARM_REG_MSP)
        assert sp == self.initial_sp
        self.svc_msp, self.svc_frame = self._hardware_frame(0x08025CA8, sp)
        self.u.reg_write(UC_ARM_REG_MSP, self.svc_msp)
        psr = self.u.reg_read(UC_ARM_REG_XPSR)
        self.u.reg_write(UC_ARM_REG_XPSR, (psr & ~0x1FF) | 11)
        self.u.reg_write(UC_ARM_REG_LR, 0xFFFFFFF9)
        self.in_service = True
        self.u.emu_start(SVC | 1, 0x08025C86, count=50000)
        assert self.u.reg_read(UC_ARM_REG_PC) == 0x08025C86
        self._restore_frame()
        self.in_service = False
        self.cooperative = True
        self.pending_pendsv = bool(self.read(ICSR) & 0x10000000)
        self.stage = 'task'
        self.task_min_sp = self.u.reg_read(UC_ARM_REG_SP)
        self.port_heap = self.read(0x20002B58)
        return self

    def _observe_thread(self, u, pc, size, _):
        self.minimum_msp = min(self.minimum_msp, u.reg_read(UC_ARM_REG_MSP))
        if not self.cooperative or self.in_service:
            return
        task = self.running_tcb
        self.thread_min[task] = min(self.thread_min.get(task, 0xFFFFFFFF), u.reg_read(UC_ARM_REG_SP))
        if pc not in self.fp_opcode:
            # Thumb coprocessor/VFP groups EC..EF/FC..FF. Reject instead of
            # silently omitting FP register or extended-frame ownership.
            first = int.from_bytes(u.mem_read(pc, 2), 'little')
            self.fp_opcode[pc] = (first & 0xEC00) == 0xEC00
        if self.fp_opcode[pc]:
            raise BasicFrameOnly(f'Thread FP/coprocessor instruction at {pc:#x}')
        if pc == 0x0802C23A:
            driver = u.reg_read(UC_ARM_REG_R0)
            self.requests.append(dict(task=task, driver=driver, flag_before=self.read(driver+0x10)))
        elif pc == 0x0802C274:
            driver = u.reg_read(UC_ARM_REG_R4)
            self.completions.append(dict(task=task, driver=driver, flag_after=self.read(driver+0x10)))
        elif pc == 0x0802C278:
            self.worker_calls.append(dict(task=task, driver=u.reg_read(UC_ARM_REG_R0)))
        # Delivery is deferred out of IT and away from observation entrypoints
        # so replaying a stopped instruction cannot double-count a request.
        if (self.dispatch_enabled and self.reason is None and self.pending_pendsv
                and not u.reg_read(UC_ARM_REG_PRIMASK) and not u.reg_read(UC_ARM_REG_BASEPRI)
                and not u.reg_read(UC_ARM_REG_XPSR) & 0x0600FC00
                and pc not in (0x08025A98, 0x08024BF0, 0x08068A6A, 0x0802C23A, 0x0802C274, 0x0802C278)):
            self.reason = 'pendsv'
            u.emu_stop()

    def _service(self, pc):
        if self.reason != 'pendsv':
            return super()._service(pc)
        u = self.u
        old = self._current()
        assert old == self.running_tcb
        assert not u.reg_read(UC_ARM_REG_CONTROL) & 4, 'extended FP frame is not modeled'
        saved_regs = [u.reg_read(r) for r in SAVED_REGS]
        frame_sp, frame = self._hardware_frame(pc, u.reg_read(UC_ARM_REG_PSP))
        self._bounds(old, frame_sp-36, 68)
        u.reg_write(UC_ARM_REG_PSP, frame_sp)
        u.reg_write(UC_ARM_REG_CONTROL, 0)
        u.reg_write(UC_ARM_REG_XPSR, (frame[7] & ~0x1FF) | 14)
        u.reg_write(UC_ARM_REG_LR, 0xFFFFFFFD)
        self.in_service = True
        u.emu_start(PENDSV | 1, 0x08025C6A, count=50000)
        assert u.reg_read(UC_ARM_REG_PC) == 0x08025C6A
        saved = self.read(old)
        self._bounds(old, saved, 68)
        actual_saved = list(struct.unpack('<9I', u.mem_read(saved, 36)))
        assert actual_saved == saved_regs+[0xFFFFFFFD]
        assert list(struct.unpack('<8I', u.mem_read(saved+36, 32))) == frame
        self.thread_min[old] = min(self.thread_min[old], saved)
        new = self._current()
        incoming_saved = list(struct.unpack('<9I', u.mem_read(self.read(new), 36)))
        assert [u.reg_read(r) for r in SAVED_REGS] == incoming_saved[:8]
        incoming, incoming_frame = self._restore_frame()
        self.word(ICSR, self.read(ICSR) & ~0x10000000)
        self.pending_pendsv = False
        self.switches.append(dict(old=old, new=new, interrupted_pc=pc, resume=incoming_frame[6],
                                  saved_sp=saved, hardware_sp=frame_sp, incoming_sp=incoming))
        self.in_service = False

    def run(self, start, end, *, budget=600000):
        pc, before = start, self.instructions
        for _ in range(12000):
            remaining = budget-(self.instructions-before)
            if remaining <= 0:
                self.stop_reason = 'budget'
                break
            self.reason = None
            self.u.emu_start(pc | 1, end, count=remaining)
            pc = self.u.reg_read(UC_ARM_REG_PC)
            if pc == end:
                self.stop_reason = 'checkpoint'
                break
            if self.cooperative and pc == 0x08025A28 and self.reason is None:
                if not self.wake_enabled:
                    self.stop_reason = 'wfi'
                    break
                # Unicorn yields after executing the native WFI. A modeled
                # timer wake resumes at its following instruction, not at WFI.
                self.reason = 'tick'
                self.wfi_wakes += 1
            if self.reason is None:
                self.stop_reason = 'unhandled_stop'
                break
            self._service(pc)
            # PendSV restores a different thread; resume that PC, not the
            # interrupted caller's local PC used for ordinary IRQ adapters.
            pc = self.u.reg_read(UC_ARM_REG_PC)
        else:
            self.stop_reason = 'event_budget'
        return self.u.reg_read(UC_ARM_REG_PC)

    def checkpoint(self, address=READY_GATE, *, budget=600000):
        assert self.run(self.u.reg_read(UC_ARM_REG_PC), address, budget=budget) == address, (self.stop_reason, list(map(hex, self.trace)))
        return self

    def validate_stacks(self):
        for tcb, minimum in self.thread_min.items():
            self._bounds(tcb, minimum, 0)
            task = self.task_by_tcb[tcb]
            assert bytes(self.u.mem_read(task['stack'], 16)) == b'\xA5'*16
        return True

    def readiness(self):
        root = self.read(0x080266B0)  # literal of native26596
        objects = [self.read(root+0x10), self.read(self.read(root+0x18)), self.read(root+0x24)]
        return dict(root=root, objects=objects,
                    counters=[int.from_bytes(self.u.mem_read(p+0x2A, 2), 'little') for p in objects])
