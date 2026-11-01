"""Native reset/main/task allocation trace over explicit peripheral models.

RCC acknowledges immediately. QSPI has scripted ID bytes, no flash media.
SDIO sends CMD0 and times out every response command (no responding card).
Native IRQ adapters execute as calls over saved CPU contexts, not NVIC/exception
entry. No firmware instruction, allocator result, task or heap pointer is seeded.
"""
import struct
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
from recovery_boot_test_support import NativeStartup, MAIN, STOP
import seq_Patch as seq

SCHEDULER = 0x08025430
MAIN_WORKER = 0x0802C23A
RCC = 0x40023800
QSPI = 0xA0001000
SDIO = 0x40012C00


class MainStartup(NativeStartup):
    def __init__(self, image, *, clock_ack=True, qspi_complete=True):
        super().__init__(image)
        self.startup()
        self.static_heap_current = self.read(seq.HEAP_CUR_PTR)
        self.u.mem_map(0xE0042000, 0x1000)  # native DBGMCU watchdog setup
        self.u.mem_map(QSPI, 0x1000)
        self.clock_ack, self.qspi_complete = clock_ack, qspi_complete
        self.tasks, self.commands, self.sdio_commands, self.events = [], [], [], []
        self.qspi_data_index = self.ticks = self.qspi_irqs = self.sdio_irqs = 0
        self.reason = self.skip = None
        self.in_service = False
        self.next_tick = self.instructions+256
        self.stage = 'main'
        self.task_min_sp = None
        self.u.hook_add(UC_HOOK_MEM_READ, self._rcc, begin=RCC, end=RCC+11)
        self.u.hook_add(UC_HOOK_MEM_WRITE, self._qwrite, begin=QSPI, end=QSPI+0x33)
        self.u.hook_add(UC_HOOK_MEM_READ, self._qread, begin=QSPI+0x20, end=QSPI+0x23)
        self.u.hook_add(UC_HOOK_CODE, self._code)

    def _rcc(self, u, kind, address, size, value, _):
        if not self.clock_ack:
            return
        value = int.from_bytes(u.mem_read(address, size), 'little')
        if address == RCC:
            for on, ready in ((0, 1), (16, 17), (24, 25), (28, 29)):
                value = value | (1 << ready) if value & (1 << on) else value & ~(1 << ready)
        if address == RCC+8:
            value = (value & ~12) | ((value & 3) << 2)
        u.mem_write(address, value.to_bytes(size, 'little'))

    def _qwrite(self, u, kind, address, size, value, _):
        if address == QSPI+0x14:
            self.commands.append(value)
            self.qspi_data_index = 0
        if address == QSPI+0xC:
            self.word(QSPI+8, self.read(QSPI+8) & ~value)

    def _qread(self, u, kind, address, size, value, _):
        opcode = self.commands[-1] & 255 if self.commands else 0
        data = bytes.fromhex('ef4018') if opcode in (0x9F, 0xAF) else bytes(16)
        value = data[self.qspi_data_index % len(data)]
        self.qspi_data_index += 1
        u.mem_write(address, value.to_bytes(size, 'little'))

    def _code(self, u, pc, size, _):
        if self.in_service:
            return
        if self.stage == 'task':
            self.task_min_sp = min(self.task_min_sp, u.reg_read(UC_ARM_REG_SP))
        if pc == 0x08024BF0:
            sp, name = u.reg_read(UC_ARM_REG_SP), u.reg_read(UC_ARM_REG_R1)
            self.tasks.append(dict(entry=u.reg_read(UC_ARM_REG_R0),
                name=bytes(u.mem_read(name, 32)).split(b'\0')[0].decode('ascii'),
                words=u.reg_read(UC_ARM_REG_R2), argument=u.reg_read(UC_ARM_REG_R3),
                priority=self.read(sp), output=self.read(sp+4)))
        if self.skip == pc:
            self.skip = None
            return
        if (self.qspi_complete and pc in (0x08041C2E, 0x08041C68)
                and self.read(QSPI) & 0xA0000):
            self.reason = 'qspi'
        elif pc in (0x08024914, 0x08023BB6):
            self.reason = 'sdio'
        elif (pc in (0x08024068, 0x08024138) and self.instructions >= self.next_tick and self.read(0xE000E010) & 1
                and not u.reg_read(UC_ARM_REG_PRIMASK)):
            self.reason = 'tick'
        else:
            return
        u.emu_stop()

    def _service(self, pc):
        context = self.u.context_save()
        reason = self.reason
        self.in_service = True
        # Task IRQ adapters use MSP. This omits architectural exception entry,
        # stacked hardware/FPU frames, priorities, nesting and real timing.
        self.u.reg_write(UC_ARM_REG_CONTROL, 0)
        if reason == 'qspi':
            self.word(QSPI+8, 0xA)
            result = self.call(0x080645E0)
            self.qspi_irqs += 1
        elif reason == 'sdio':
            command = self.read(SDIO+0xC) & 63
            self.sdio_commands.append(command)
            self.word(SDIO+0x34, 0x80 if command == 0 else 4)
            result = self.call(0x08064762)
            self.sdio_irqs += 1
            self.skip = pc
        else:
            result = self.call(0x08066BD0)
            self.ticks += 1
            self.next_tick = self.instructions+256
            self.skip = pc
        assert result['pc'] == STOP and result['error'] is None, result
        self.events.append(dict(kind=reason, interrupted_pc=pc))
        self.u.context_restore(context)
        self.in_service = False

    def run(self, start, end, *, budget=600000):
        pc, before = start, self.instructions
        for _ in range(4096):
            remaining = budget-(self.instructions-before)
            if remaining <= 0:
                break
            self.reason = None
            self.u.emu_start(pc | 1, end, count=remaining)
            pc = self.u.reg_read(UC_ARM_REG_PC)
            if pc == end or self.reason is None:
                break
            self._service(pc)
        return self.u.reg_read(UC_ARM_REG_PC)

    def main_setup(self):
        assert self.run(MAIN, SCHEDULER) == SCHEDULER, list(map(hex, self.trace))
        for task in self.tasks:
            task['tcb'] = self.read(task['output'])
            task['stack'] = self.read(task['tcb']+0x30)
            task['saved_sp'] = self.read(task['tcb'])
            task['frame'] = list(struct.unpack('<17I', self.u.mem_read(task['saved_sp'], 68)))
        self.setup_heap_current = self.read(seq.HEAP_CUR_PTR)
        self.setup_min_sp = self.min_sp
        return self

    def first_main_task(self):
        task = next(t for t in self.tasks if t['name'] == 'Main')
        frame = task['frame']
        assert frame[8] == 0xFFFFFFFD and frame[15] == task['entry'] & ~1 and frame[16] == 0x01000000
        # Rotate the actual native ready list to Main. No fabricated TCB or
        # current-task RAM store; interrupt scheduling itself is not modeled.
        self.selection_steps = []
        self.in_service = True
        for _ in range(len(self.tasks)+1):
            current = self.read(self.read(0x08025CB8))
            self.selection_steps.append(current)
            if current == task['tcb']:
                break
            result = self.call(0x08024F84)
            assert result['pc'] == STOP and result['error'] is None, result
        self.in_service = False
        assert self.read(self.read(0x08025CB8)) == task['tcb']
        for reg, value in zip((UC_ARM_REG_R4, UC_ARM_REG_R5, UC_ARM_REG_R6, UC_ARM_REG_R7,
                               UC_ARM_REG_R8, UC_ARM_REG_R9, UC_ARM_REG_R10, UC_ARM_REG_R11), frame[:8]):
            self.u.reg_write(reg, value)
        for reg, value in zip((UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3,
                               UC_ARM_REG_R12, UC_ARM_REG_LR), frame[9:15]):
            self.u.reg_write(reg, value)
        self.u.reg_write(UC_ARM_REG_MSP, self.initial_sp)
        self.u.reg_write(UC_ARM_REG_PSP, task['saved_sp']+68)
        self.u.reg_write(UC_ARM_REG_CONTROL, 2)
        self.u.reg_write(UC_ARM_REG_XPSR, frame[16])
        self.task_min_sp = self.u.reg_read(UC_ARM_REG_SP)
        self.stage = 'task'
        assert self.run(task['entry'], MAIN_WORKER, budget=10000) == MAIN_WORKER
        return self
