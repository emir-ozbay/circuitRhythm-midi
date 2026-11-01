"""Real stock request/result FIFOs and worker; OS wakeups and file API stubs.

Runs 45EB6 -> 2ACB8 -> 40DC4 and worker 2AD40 -> 419CC -> result FIFO.
File/OS boundaries are stubs; full project serialization and boot are omitted.
"""
import struct
import seq_Patch as seq
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_SP


class StorageQueueFixture:
    def __init__(self, h, base=0x20020000):
        self.h = h
        self.base = base
        self.worker, self.request_fifo = base, base + 0x1000
        self.result_fifo, self.packet = base + 0x3200, base + 0x5000
        self.bridge, self.callback, vt = base + 0x6000, base + 0x6100, base + 0x6200
        self.header, self.blob = base + 0x7000, base + 0x8000
        self.calls = []
        self.read_result = 0
        self.read_payload = None
        self.read_api_calls = 0
        self.boundary = 0x0800E940
        # Kernel event/semaphore operations only; no context switch is modeled.
        for address in (0x080240C0, 0x0802CA6C, 0x08023CEA):
            h.u.mem_write(address, bytes.fromhex('7047'))
        # File read/write/close APIs are the boundary.
        for address in (0x0804113A, 0x080411D8, 0x08041906):
            h.u.mem_write(address, bytes.fromhex('00207047'))
        def read_api(u, address, size, data):
            self.read_api_calls += 1
            requested = u.reg_read(UC_ARM_REG_R3)
            count_ptr = int.from_bytes(u.mem_read(u.reg_read(UC_ARM_REG_SP), 4), 'little')
            payload = self.read_payload
            if payload is not None:
                assert len(payload) <= requested
                u.mem_write(u.reg_read(UC_ARM_REG_R2), payload)
            count = requested if self.read_result == 0 else len(payload or b'')
            u.mem_write(count_ptr, struct.pack('<I', count))
        h.u.hook_add(UC_HOOK_CODE, read_api, begin=0x0804113A, end=0x0804113A)
        h.word(0x20006CA8, self.worker)
        self.fifo(self.request_fifo, base + 0x2000, 72, 2)
        h.word(self.worker + 0x14, self.request_fifo)
        h.u.mem_write(self.worker + 0x10, bytes([2, 2, 0, 1]))
        root, sender = base + 0x3000, base + 0x3100
        h.word(0x20006CA0, root)
        h.word(root + 4, sender)
        self.fifo(self.result_fifo, base + 0x4000, 36, 8)
        h.word(sender, self.result_fifo)
        h.word(sender + 4, base + 0x3300)
        h.word(sender + 8, 34)
        h.word(self.callback, vt)
        h.word(vt, self.boundary | 1)
        h.u.mem_write(self.boundary, bytes.fromhex('7047'))
        def completed(u, address, size, data):
            regs = tuple(u.reg_read(r) for r in (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3))
            self.calls.append((regs, bytes(u.mem_read(regs[1], 12))))
        h.u.hook_add(UC_HOOK_CODE, completed, begin=self.boundary, end=self.boundary)
        h.u.mem_write(self.header, struct.pack('<3I', 2, 7, 0))

    def fifo(self, obj, buf, item_size, count):
        self.h.word(obj, buf)
        self.h.u.mem_write(obj + 4, struct.pack('<4H', item_size * count + 1, 0, 0, item_size))

    def begin_project_save(self, slot=7):
        from phase1_test_support import ProjectTransitionFixture
        h = self.h
        project = ProjectTransitionFixture(h)
        self.callback = project.p + 0x10
        h.word(self.callback, self.base + 0x9000)
        h.word(self.base + 0x9000, 0x080381D7)
        h.word(project.p + 0x44, h.store(bytes(128)))
        h.word(project.p + 0x4C, h.store(bytes(4)))
        h.word(project.p + 0xFC, h.store(bytes(4)))
        h.word(project.p + 0x14, self.base + 0x9500)
        h.word(project.p + 0x6C, self.base + 0x9600)
        self.save_node = project.p + 0x180
        h.word(project.p + 0x3C, self.save_node)
        h.word(self.save_node, project.p)
        h.u.mem_write(seq.SEQ_STATE_ADDR + seq.OFF_PROJECT_DIRTY, b'\x01')
        h.call(0x08037ED0, project.p, slot, 0, end=0x08037F42)
        self.submit_save(slot)
        return project

    def begin_project_load(self, mode=0, project_kwargs=None, *, bypass_containment=False):
        """Default exercises the packaged guard. Explicit bypass is component-only.

        Bypass restores four stock bytes in emulator RAM for legacy read/Close
        bridge tests; those tests are NOT production Load acceptance evidence.
        """
        from phase1_test_support import ProjectTransitionFixture
        h = self.h
        project = ProjectTransitionFixture(h, **(project_kwargs or {}))
        self.callback = project.p + 0x0C
        h.word(self.callback, self.base + 0x9000)
        h.word(self.base + 0x9000, 0x080381C9)
        metadata = bytearray(128)
        metadata[44] = mode * 32
        target = 0 if mode else 32
        struct.pack_into('<I', metadata, 4 * (12 if target < 32 else 13), 1)
        self.meta = h.store(bytes(metadata))
        h.word(project.p + 0x44, self.meta)
        h.word(project.view + 0x20, self.meta)
        ready = h.store(bytes([8, 0, 0, 0]))
        h.word(project.p + 0x4C, ready)
        h.word(project.view + 0x24, ready)
        h.word(project.p + 0x64, self.bridge)
        h.word(project.p + 0x68, self.base + 0x9700)  # output-notification router, ports disabled
        h.word(project.p + 0x14, self.blob)
        h.word(project.p + 0x6C, self.base + 0x9600)
        h.word(project.ctrl + 0x0C, h.store(bytes([1, 0, 0, 0])))
        h.u.mem_write(seq.SEQ_STATE_ADDR + seq.OFF_SEQ_ENABLED, bytes([mode]))
        h.call(0x0803D8B8, project.ctrl, 18)
        # Real Load worker continuation builds a read request for an existing slot.
        if bypass_containment:
            saved = bytes(h.u.mem_read(0x08037BD6, 4))
            h.u.mem_write(0x08037BD6, bytes.fromhex('30b585b0'))
            try:
                h.call(0x08037BD6, project.p)
            finally:
                h.u.mem_write(0x08037BD6, saved)
        else:
            h.call(0x08037BD6, project.p)
        return project

    def submit_save(self, slot=7):
        h = self.h
        h.word(self.header + 4, slot)
        h.word(0x20040000, 44)
        h.word(0x20040004, self.callback)
        return h.call(0x080472E2, self.bridge, self.header, 0, self.blob)

    def submit_load(self, slot=7):
        h = self.h
        h.word(self.header + 4, slot)
        h.word(0x20040000, 44)
        h.word(0x20040004, self.callback)
        return h.call(0x08047288, self.bridge, self.header, 0, self.blob)

    def work(self, result=0, close_result=0, read_result=0):
        assert all(0 <= x <= 255 for x in (result, close_result, read_result))
        self.read_result = read_result
        self.h.u.mem_write(0x0804113A, bytes([read_result, 0x20, 0x70, 0x47]))
        self.h.u.mem_write(0x080411D8, bytes([result, 0x20, 0x70, 0x47]))
        self.h.u.mem_write(0x08041906, bytes([close_result, 0x20, 0x70, 0x47]))
        return self.h.call(0x0802AD40, self.worker)

    def deliver(self):
        h = self.h
        descriptor = self.packet + 0x100
        h.word(descriptor, 34)
        h.word(descriptor + 4, self.packet)
        if not h.call(0x08025B1A, self.result_fifo, descriptor):
            return False
        handler = int.from_bytes(h.u.mem_read(self.packet, 4), 'little')
        assert handler == 0x0802B065, hex(handler)
        h.call(handler & ~1, self.packet + 4)
        return True
