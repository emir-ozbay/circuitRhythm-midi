"""Native5706 pattern playback -> voice ownership -> sample/MIDI output.

Objects/stores are synthetic, following3C29E/4ADA4/3B2A0/4A8CC constructors.
The player constructor itself and timer/IRQ scheduling are not executed.
Linked-list helpers, step preparation/playback, gate expiry, flush, callbacks,
ownership filters, routing, output queues and workers execute real machine code.
Only final sample engine calls are stubbed; MidiOutputFixture owns driver limits.
"""
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2


class SequencerPlaybackFixture:
    def __init__(self, h, output, transport=None):
        self.h, self.output = h, output
        self.router, self.offset = 0x2000C000, 0x20004C00
        self.players = [0x20041000 + t*0x200 for t in range(8)]
        self.voices = [0x20043000 + t*0x400 for t in range(8)]
        self.sample_calls = []
        # Keep stores outside the complete stock169092-byte project RAM span.
        # The existing full transport graph uses3A000..3D200. Its remaining
        # gap below the stack cannot hold another25 two-buffer stores.
        h.next_store = 0x20048000
        self.transport = transport if transport is not None else h.store(bytes(16))
        h.word(self.router, 0x080694B0)
        # 3B6B2 ADR literal at3BB3C: class0/1 note offsets1, class2 offset12.
        h.u.mem_write(self.router+0xA8, bytes([1, 1, 12]))
        h.word(self.offset, 0x08069510)
        h.word(self.offset+4, self.router)
        h.u.mem_write(self.offset+8, b'\x00')  # stock router+30 class0 subobject
        midi_adapter = self.offset+0x10
        h.call(0x0803B258, midi_adapter, output.adapter)
        h.word(self.router+0xA0, midi_adapter)
        # Stock recorder group is disabled in this playback-only fixture.
        group = self.offset+0x20
        h.word(group, 0x08068CE4)
        h.word(group+8, h.store(bytes(12)))
        h.word(self.router+0xA4, group)
        sample = self.offset+0x40
        h.word(sample, 0x080685E0)  # real31A18 On /31A22 Off adapters
        h.word(self.router+0x9C, sample)
        for pc, kind in ((0x08046780, 'on'), (0x080467AA, 'off')):
            h.u.mem_write(pc, bytes.fromhex('7047'))
            def capture(u, address, size, data, kind=kind):
                self.sample_calls.append((kind, u.reg_read(UC_ARM_REG_R0),
                                          u.reg_read(UC_ARM_REG_R1),
                                          u.reg_read(UC_ARM_REG_R2)))
            h.u.hook_add(UC_HOOK_CODE, capture, begin=pc, end=pc)

        def callback(obj, owner, identifier):
            # 3C570 native callback; fifth argument is the stock139-note domain.
            h.word(0x20040000, 0x8B)
            h.call(0x0803C570, obj, owner, identifier, 1)

        held_array, active_array = 0x20004D00, 0x20004D40
        h.word(self.router+0x24, 4)
        h.word(self.router+0x2C, held_array)
        h.word(self.router+0x1A3C, 4)
        h.word(self.router+0x1A44, active_array)
        self.pattern_span = 0x20004C80
        # Native33124 creates the exact raw+2E4, stride5140,count8 span
        # passed through boot28BE4/3C29E to player+50. No ST1 cache offset128.
        h.call(0x08033124, self.pattern_span, 0x20010000)
        for t, (player, voice) in enumerate(zip(self.players, self.voices)):
            h.u.mem_write(player-4, b'PLY!')
            h.u.mem_write(player+0x150, b'END!')
            h.word(player, 0x08068D24)
            h.word(player+0x50, h.read(self.pattern_span+8)+t*h.read(self.pattern_span))
            h.word(player+0x10, h.store(bytes(12)))  # rate0
            h.word(player+0x1C, self.transport)
            h.word(player+0x54, voice+0x80)
            # 3C32C passes12 modulation lanes to the55008 base constructor.
            # Stop552F6 also resets these two12-halfword arrays.
            h.u.mem_write(player+0x3C, b'\x0C')
            h.word(player+0x48, voice+0x240)
            h.word(player+0x4C, voice+0x280)
            h.u.mem_write(voice+0x240, b'\xFF'*24)
            h.u.mem_write(voice+0x280, b'\xFF'*24)
            # Constructor4AE36..AECC:139-note map,8 records,2 list sentinels.
            h.u.mem_write(player+0xAC, b'\xFF'*0x8B)
            for n in range(10):
                h.call(0x08051ACC, n, player+0x78)
            for n in range(8):
                h.call(0x08051AFC, n, player+0x78, 8)
            callback(voice+0x80, self.offset, 16+t)
            h.word(voice, 0x08069500)
            for cls in range(3):
                outer = voice+0x90+cls*0x10
                callback(outer, voice, cls)
                h.word(self.router+0x3C+t*12+cls*4, outer)
            # All three real two-source ownership filters, with native ctor.
            for n, field in enumerate((4, 8, 12)):
                filt, cb = voice+0xC0+n*0x40, voice+0x180+n*0x10
                callback(cb, voice, 3+n)
                h.call(0x08054F10, filt, cb)
                h.word(voice+field, filt)
            for field, ident in ((0x1C, 32+t), (0x20, 24+t), (0x24, 40+t)):
                final = voice+0x200+(field-0x1C)*4
                callback(final, self.router, ident)
                h.word(voice+field, final)
            mapping = 0x20045000+t*0x114  # stock class0 track stride276 bytes
            h.word(self.router+0x19DC+t*12, mapping)
            # Class0 Off also checks matching class2 ownership (3BB08..BB32).
            # No external-input notes are held in this playback fixture.
            h.word(self.router+0x19E4+t*12, 0x20046000+t*0x100)
            h.word(held_array+t*4, h.store(bytes(20)))
            h.word(active_array+t*4, h.store(bytes(4)))
        assert h.next_store+0x140 < h.read(0x20002B58)

    def step(self, track, step, note=60, velocity=96, gate=6, pattern=0, tie=0):
        assert 0 <= track < 8 and 0 <= step < 32 and 0 <= pattern < 8
        # The tested pitches are within the stock note-map domain. Zero means48.
        assert note == 0 or 1 <= note <= 138
        p = self.players[track]
        self.h.u.mem_write(self.h.read(p+0x50)+pattern*0xA28+step*8,
                          bytes([note, gate, 1, velocity, 7, 255, tie, 0]))
        self.h.word(0x20040000, 0)
        self.h.call(0x0804AEEE, p, pattern, step, 0)
        self.h.call(0x0804AFBC, p, pattern, step, 0)

    def expire_tick(self, track):
        self.h.word(0x20040000, 1)
        # microstep6 skips preparation, executes the native gate countdown.
        self.h.call(0x0804AEEE, self.players[track], 0, 0, 6)

    def flush(self, track):
        self.h.call(0x0804AED8, self.players[track])

    def active(self, track):
        p = self.players[track]
        node = self.h.u.mem_read(p+0x8A, 1)[0]  # sentinel9 next
        result = []
        while node != 255:
            assert node < 8 and node not in [n for n, note in result]
            result.append((node, self.h.u.mem_read(p+0x8E+node*4, 1)[0]))
            node = self.h.u.mem_read(p+0x78+2*node, 1)[0]
        return result

    def attach_stop_listeners(self):
        # Native FBEC notification reaches player55120 ->552F6 ->4AED8.
        listeners = 0x20004E00
        for n, p in enumerate(self.players):
            self.h.word(listeners+8*n, p)
            self.h.word(listeners+8*n+4, 1)
        self.h.word(self.transport+0x14, listeners)
        self.h.u.mem_write(self.transport+1, b'\x08')
