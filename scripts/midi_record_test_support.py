"""Synthetic stock object graph: short MIDI messages to real recorder code.

No UART/USB, scheduler, SD or sample engine is emulated. Only the final sample
recipient is a stub; all intermediate ownership filters and recorder calls run.
"""
import struct


class MidiRecordFixture:
    def __init__(self, h, track, router=0x20020000):
        self.h, self.track = h, track
        self.decoder, self.receiver = 0x20004000, 0x20004100
        adapter, offset_adapter = 0x20004300, 0x20004320
        voice, outer = 0x20004400, 0x20004440
        self.group, self.recorder = 0x20004500, 0x20007000
        self.patterns, self.router = 0x20010000, router
        self.message = 0x20004700
        self.filters = (0x20004800, 0x20004840)
        h.word(self.decoder, self.receiver)
        h.u.mem_write(self.decoder + 4, bytes(reversed(range(8))))
        h.u.mem_write(self.decoder + 0x1C, b'\x01')
        h.word(self.receiver, 0x080665E4)
        h.word(self.receiver + 0x24, adapter)
        h.word(adapter, 0x080694D0)
        h.word(adapter + 4, offset_adapter)
        h.word(offset_adapter, 0x08069510)
        h.word(offset_adapter + 4, self.router)
        h.u.mem_write(offset_adapter + 8, b'\x10')
        h.word(self.router, 0x080694B0)
        h.word(self.router + 0xA4, self.group)
        h.word(self.router + 0x44 + track * 12, outer)
        h.word(self.router + 0x19E4 + track * 12, self.router + 0x2000)
        h.word(voice, 0x08069500)

        def callback(obj, owner, identifier):
            # Stock 0x0803C570 layout and actual vtable.
            h.word(obj, 0x080694C0)
            h.word(obj + 8, owner)
            h.u.mem_write(obj + 0x0C, bytes([identifier]))

        callback(outer, voice, 2)
        # At 3B31E..324 r1=third allocation (32+t), r2=second (24+t),
        # r3=first (40+t). Thus voice+24, NOT +1C, is the recorder path.
        for n, (field, ident, recipient) in enumerate(((8, 4, 24 + track), (12, 5, 40 + track))):
            filt, cb, final = self.filters[n], 0x20004900 + n * 0x20, 0x20004980 + n * 0x20
            h.word(voice + field, filt)
            h.call(0x08054F10, filt, cb)  # actual constructor clears both ownership masks
            callback(cb, voice, ident)
            h.word(voice + (0x20 if n == 0 else 0x24), final)
            callback(final, self.router, recipient)

        self.sample, sample_vt = 0x20004600, 0x20004620
        self.sample_on, self.sample_off = 0x0800E900, 0x0800E904
        h.word(self.router + 0x9C, self.sample)
        h.word(self.sample, sample_vt)
        h.word(sample_vt, self.sample_on | 1)
        h.word(sample_vt + 4, self.sample_off | 1)
        h.u.mem_write(self.sample_on, bytes.fromhex('704700007047'))
        held_array, active_array = 0x20004A00, 0x20004A40
        self.held, self.active = h.store(bytes(20)), h.store(bytes(4))
        h.word(held_array + track * 4, self.held)
        h.word(active_array + track * 4, self.active)
        h.word(self.router + 0x24, 4)
        h.word(self.router + 0x2C, held_array)
        h.word(self.router + 0x1A3C, 4)
        h.word(self.router + 0x1A44, active_array)
        h.word(self.group, 0x08068CE4)
        self.flags = h.store(struct.pack('<3I', 1, 1, 0))
        h.word(self.group + 8, self.flags)
        h.word(self.group + 0x0C + track * 4, self.recorder)
        h.word(self.recorder, 0x08067864)
        h.word(self.recorder + 0x50, self.patterns)
        h.word(self.recorder + 0x14, h.store(bytes([1, 0, 0, 0])))
        h.word(self.recorder + 0x20, h.store(bytes(4)))
        h.word(self.recorder + 0x5C, h.store(bytes(8)))
        h.word(self.recorder + 0x0C, h.store(struct.pack('<3I', 7, 31, 0)))
        h.word(self.recorder + 0x10, h.store(struct.pack('<2I', 7, 31)))
        self.clock = h.store(bytes(4))
        h.word(self.recorder + 0x1C, self.clock)

    def send(self, status, note=48, velocity=96):
        self.h.u.mem_write(self.message, bytes([status | (7 - self.track), note, velocity]))
        self.h.call(0x0805AF94, self.decoder, self.message)

    def finish(self):
        self.h.word(0x20040000, 0)
        self.h.call(0x08048D2A, self.recorder, 7, 31, 24)
