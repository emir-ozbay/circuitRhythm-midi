"""Synthetic project objects with real stock action dispatch and store operations.

Only the downstream storage-request endpoint and LED redraw are stubbed.
Completion injection is explicit: this fixture is NOT a storage roundtrip.
"""
from unicorn.arm_const import UC_ARM_REG_R4, UC_ARM_REG_R5
import seq_Patch as seq


class ProjectTransitionFixture:
    def __init__(self, h, ctrl=0x20004000, view=0x20004500, p=0x20007000):
        self.h, self.ctrl, self.view = h, ctrl, view
        self.p = p
        node, vt, worker, worker_vt, request = (p + 0x100, p + 0x200,
            p + 0x300, p + 0x400, p + 0x500)
        self.meta = h.store(bytes(64))
        self.phase = h.store(bytes(8))
        h.word(ctrl + 0x50, view)
        h.word(view + 0x0C, node)
        h.word(view + 0x20, self.meta)
        h.word(view + 0x24, h.store(bytes([8, 0, 0, 0])))
        h.word(view + 0x28, self.phase)
        h.word(p, vt); h.word(vt, 0x080385CB)
        h.word(node, p); h.word(p + 0x38, node)
        h.word(p + 0x44, self.meta); h.word(p + 0x48, self.phase)
        h.word(p + 0x84, h.store(bytes(4)))
        h.word(p + 0x5C, request); h.word(request, worker)
        h.word(worker, worker_vt); h.word(worker_vt, 0x0800E801)
        h.u.mem_write(0x0800E800, bytes.fromhex('00207047'))
        h.u.mem_write(0x0804F27E, bytes.fromhex('7047'))

    def finish(self):
        h = self.h
        state = seq.SEQ_STATE_ADDR
        assert h.u.mem_read(state + seq.OFF_TRANS_STATE, 1) == b'\x02'
        target = h.u.mem_read(state + seq.OFF_TRANS_TARGET_SLOT, 1)[0]
        for bank in (0x40, 0xC0):
            h.u.mem_write(self.meta + bank + 44, bytes([target]))
            h.u.mem_write(self.phase + bank, bytes(8))
        old4, old5 = h.u.reg_read(UC_ARM_REG_R4), h.u.reg_read(UC_ARM_REG_R5)
        h.u.reg_write(UC_ARM_REG_R4, self.p)
        h.u.reg_write(UC_ARM_REG_R5, target)
        h.call(h.labels['c_proj_load_complete'], self.meta)
        h.u.reg_write(UC_ARM_REG_R4, old4); h.u.reg_write(UC_ARM_REG_R5, old5)
