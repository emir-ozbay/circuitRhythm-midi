"""Synthetic stopped controller; real button ownership/store reads, no I/O stubs."""


class SharedModeFixture:
    def __init__(self, h, ctrl=0x20004000, view=0x20004500, grid=0x20005000):
        self.h, self.ctrl, self.view, self.grid = h, ctrl, view, grid
        self.shift = h.store(bytes([1, 0, 0, 0]))
        self.transport = h.store(bytes(4))
        self.ready = h.store(bytes([8, 0, 0, 0]))
        self.phase = h.store(bytes(8))
        metadata = bytearray(64)
        metadata[44] = 7
        self.meta = h.store(bytes(metadata))
        for off, obj in ((0x0C, self.shift), (0x18, self.transport), (0x3C, grid), (0x50, view)):
            h.word(ctrl + off, obj)
        for off, obj in ((0x20, self.meta), (0x24, self.ready), (0x28, self.phase)):
            h.word(view + off, obj)
        self.note_owners = tuple(h.store(bytes(4)) for _ in range(8))
        for track, obj in enumerate(self.note_owners):
            h.word(ctrl + 0x1C0 + 4 * track, obj)

    def press(self):
        return self.h.call(0x0803D8B8, self.ctrl, 18)

    def release(self):
        return self.h.call(0x08051BB8, self.ctrl + 0xA0, 18)

    def set_byte(self, store, offset, value):
        for bank in (0x40, 0xC0):
            self.h.u.mem_write(store + bank + offset, bytes([value]))
