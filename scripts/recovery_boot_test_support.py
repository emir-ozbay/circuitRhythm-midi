"""Native reset through static initialization, with passive MMIO RAM only.

No heap pointers/state/objects or instruction replacements are supplied. Stop
before native main's hardware setup. RCC/SCS reads return the last RAM write;
this is not a clock, NVIC, peripheral, RTOS or complete boot model.
"""
import collections
import struct
from unicorn import (Uc, UcError, UC_ARCH_ARM, UC_MODE_THUMB, UC_MODE_MCLASS,
                     UC_HOOK_CODE, UC_HOOK_MEM_WRITE, UC_HOOK_MEM_INVALID)
from unicorn.arm_const import (UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_PC,
                               UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_PRIMASK)
import seq_Patch as seq
import midi_recovery_patch as fixed

MAIN = 0x08025688
STOP = 0x0800E000


class NativeStartup:
    def __init__(self, image, fill=0xA5):
        self.u = u = Uc(UC_ARCH_ARM, UC_MODE_THUMB | UC_MODE_MCLASS)
        u.mem_map(0x08000000, 0x80000)
        u.mem_write(0x08010000, image)
        u.mem_map(0x20000000, 0x50000)
        u.mem_write(0x20000000, bytes([fill])*0x50000)
        u.mem_map(0x40000000, 0x40000)  # passive RCC and peripheral address RAM
        u.mem_map(0xE000E000, 0x2000)  # passive SCS; no exceptions synthesized
        self.initial_sp, self.reset = struct.unpack_from('<II', image)
        u.reg_write(UC_ARM_REG_SP, self.initial_sp)
        self.trace = collections.deque(maxlen=24)
        self.allocations, self.heap_writes, self.reserved_writes = [], [], []
        self.initializer_records = []
        self.invalid = []
        self.instructions = self.masked = 0
        self.min_sp = self.initial_sp
        self.first_allocation_state = None
        # Keep register reads at code boundaries. Unicorn2.1.4 M-class can
        # corrupt ITSTATE when a write callback fires for conditional STM;
        # the write hooks below must cover only the two watched state ranges.
        observed = dict(pc=self.reset & ~1, masked=0, snapshot_pending=False)

        def code(u, pc, size, _):
            observed['pc'] = pc
            observed['masked'] = u.reg_read(UC_ARM_REG_PRIMASK)
            if observed['snapshot_pending'] and self.first_allocation_state is None:
                self.first_allocation_state = bytes(u.mem_read(fixed.STATE_BASE, 1088))
                observed['snapshot_pending'] = False
            self.trace.append(pc)
            self.instructions += 1
            self.masked += bool(observed['masked'])
            self.min_sp = min(self.min_sp, u.reg_read(UC_ARM_REG_SP))
            if pc == 0x08068A6A:
                self.initializer_records.append(dict(record=u.reg_read(UC_ARM_REG_R0)-4,
                                                     handler=u.reg_read(UC_ARM_REG_R1)))
            if pc == seq.STOCK_ALLOCATOR_ADDR:
                self.allocations.append(dict(size=u.reg_read(UC_ARM_REG_R0),
                    current=self.read(seq.HEAP_CUR_PTR), limit=self.read(seq.HEAP_LIMIT_PTR)))

        def write(u, kind, address, size, value, _):
            event = dict(pc=observed['pc'], address=address,
                         size=size, value=value, masked=observed['masked'])
            if seq.HEAP_LIMIT_PTR <= address < seq.HEAP_CUR_PTR+4:
                self.heap_writes.append(event)
            if fixed.STATE_BASE <= address < seq.HEAP_LIMIT:
                self.reserved_writes.append(event)
            # Read at the next instruction boundary, after the first bump;
            # the bump itself touches only heap_cur, not reserved state.
            if address == seq.HEAP_CUR_PTR and size == 4 and self.first_allocation_state is None:
                observed['snapshot_pending'] = True

        def invalid(u, kind, address, size, value, _):
            self.invalid.append(dict(pc=observed['pc'], kind=kind,
                                     address=address, size=size))
            return False

        u.hook_add(UC_HOOK_CODE, code)
        u.hook_add(UC_HOOK_MEM_WRITE, write,
                   begin=seq.HEAP_LIMIT_PTR, end=seq.HEAP_CUR_PTR+3)
        u.hook_add(UC_HOOK_MEM_WRITE, write,
                   begin=fixed.STATE_BASE, end=seq.HEAP_LIMIT-1)
        u.hook_add(UC_HOOK_MEM_INVALID, invalid)

    def read(self, address):
        return int.from_bytes(self.u.mem_read(address, 4), 'little')

    def word(self, address, value):
        self.u.mem_write(address, struct.pack('<I', value))

    def startup(self):
        self.u.emu_start(self.reset, MAIN, count=500000)
        assert self.u.reg_read(UC_ARM_REG_PC) == MAIN, list(map(hex, self.trace))
        return self

    def call(self, address, *args, budget=20000):
        from unicorn.arm_const import UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3
        for reg, value in zip((UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3), args):
            self.u.reg_write(reg, value)
        self.u.reg_write(UC_ARM_REG_LR, STOP | 1)
        error = None
        try:
            self.u.emu_start(address | 1, STOP, count=budget)
        except UcError as exc:
            error = str(exc)
        return dict(pc=self.u.reg_read(UC_ARM_REG_PC), result=self.u.reg_read(UC_ARM_REG_R0),
                    primask=self.u.reg_read(UC_ARM_REG_PRIMASK), error=error)

    def oom_constructor(self, available=0):
        # Re-run the actual native USB endpoint initializer with an exhausted
        # bump heap. Existing objects stay at their native startup addresses.
        self.word(seq.HEAP_CUR_PTR, self.read(seq.HEAP_LIMIT_PTR)-available)
        return self.call(0x0806668C)
