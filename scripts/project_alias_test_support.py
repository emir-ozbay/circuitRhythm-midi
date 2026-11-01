"""Execute stock constructors to connect the raw project to eight recorders.

Only Project Controller's pointer-binding prefix is executed. The pattern span
and all eight recorder constructors run in full with synthetic store arguments.
"""
import seq_Patch as seq

STORE_LEN = 0x29484
PATTERN_OFFSET = 0x2E4
TRACK_STRIDE = 0x5140
PATTERN_SIZE = 0xA28


class ProjectAliasFixture:
    def __init__(self, h):
        self.h, self.raw, self.p = h, 0x20010000, 0x2000B000
        self.span, self.out = 0x2003B000, 0x2003B080
        # Keep stores, raw bytes, stack arguments and actual allocations disjoint.
        h.next_store = 0x2000D000
        h.u.mem_write(self.raw, b'\x11' * STORE_LEN)
        h.word(self.raw + STORE_LEN, self.raw)
        common = h.store(bytes(64))
        h.word(common + 0x14, 0x2003B500)  # room for real listener registrations
        h.call(0x08036FA8, self.p, self.raw, common, common, end=0x08036FDE)
        h.call(0x08033120, self.span, self.raw)
        h.word(seq.HEAP_CUR_PTR, 0x20041000)
        bundle, vec, ctx, rates = 0x2003B100, 0x2003B200, 0x2003B240, 0x2003B300
        for off in range(0, 0x88, 4):
            h.word(bundle + off, common)
        for off in range(0, 0x2C, 4):
            h.word(ctx + off, common)
        for track in range(8):
            h.word(vec + track * 4, ctx)
            h.word(rates + track * 4, common)
        args = (common, common, bundle, common, 4, common, vec, 4, common, rates)
        for n, value in enumerate(args):
            h.word(0x20040000 + n * 4, value)
        h.call(0x08036950, self.out, self.read(self.span), self.read(self.span + 4), self.read(self.span + 8))
        self.recorders = tuple(self.read(self.out + track * 4) for track in range(8))
        self.patterns = tuple(self.read(recorder + 0x50) for recorder in self.recorders)

    def read(self, address):
        return int.from_bytes(self.h.u.mem_read(address, 4), 'little')
