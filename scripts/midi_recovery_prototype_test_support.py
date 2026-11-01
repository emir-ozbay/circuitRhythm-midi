"""Install the isolated recovery prototype only in Unicorn RAM/vtables."""
from pathlib import Path
import midi_recovery_prototype as recovery


class MidiRecoveryPrototypeFixture:
    def __init__(self, h, output, sysex=True):
        self.h, self.output = h, output
        self.code, self.labels = recovery.arm_code()
        assert len(output.ports) == recovery.PORTS and len(set(output.ports)) == recovery.PORTS
        assert recovery.STATE_BASE+recovery.STATE_SIZE <= 0x20048000
        self.before_code = bytes(h.u.mem_read(0x08010000, len(h.image)))
        h.u.mem_write(recovery.CODE_BASE, self.code)
        h.u.mem_write(recovery.STATE_BASE-4, b'BEG!')
        h.u.mem_write(recovery.STATE_BASE+recovery.STATE_SIZE, b'END!')
        h.u.mem_write(recovery.STATE_BASE, bytes(recovery.STATE_SIZE))
        h.word(recovery.STATE_BASE, recovery.MAGIC)
        h.word(recovery.STATE_BASE+recovery.ROUTER, output.router)
        self.overlays = []
        if sysex:
            from thumb_asm import b_w
            for address, original, replacement in (
                (recovery.NATIVE_ROUTER, recovery.ROUTER_PROLOGUE,
                 b_w(recovery.NATIVE_ROUTER, self.labels['rp_sysex_route'])),
                (recovery.ROUTER_WAIT, recovery.ROUTER_WAIT_BYTES,
                 b_w(recovery.ROUTER_WAIT, recovery.ROUTER_FAILURE)),
            ):
                assert bytes(h.u.mem_read(address, len(original))) == original
                assert 0x08010200 <= address < address+len(original) <= 0x08080000
                assert all(address+len(original) <= o['address'] or
                           o['address']+len(o['replacement']) <= address for o in self.overlays)
                self.overlays.append(dict(address=address, original=original, replacement=replacement))
                h.u.mem_write(address, replacement)
        self.entries = []
        for n, port in enumerate(output.ports):
            entry = recovery.STATE_BASE+recovery.HEADER_SIZE+n*recovery.ENTRY_SIZE
            self.entries.append(entry)
            h.word(entry, port)
            # Prototype has no flash hooks. Only the emulator's RAM objects
            # point to copied vtables with substituted send/poll methods.
            vtable = 0x20004F00+n*0x20
            original = h.read(port)
            h.u.mem_write(vtable, bytes(h.u.mem_read(original, 24)))
            h.word(vtable+8, self.labels['rp_send'] | 1)
            h.word(vtable+0x14, self.labels['rp_poll'] | 1)
            if sysex:
                h.word(vtable+0x0C, self.labels['rp_sysex_send'] | 1)
                h.word(vtable+0x10, self.labels['rp_sysex_pending'] | 1)
            h.word(port, vtable)
        self.message = 0x20004FC0

    def sysex_send(self, port, descriptor):
        port = self.output.ports[port]
        return self.h.call(self.h.read(self.h.read(port)+0x0C), port, descriptor)

    def sysex_pending(self, port):
        port = self.output.ports[port]
        return self.h.call(self.h.read(self.h.read(port)+0x10), port)

    def send(self, port, status, note=0, velocity=0):
        self.h.u.mem_write(self.message, bytes([status, note, velocity]))
        return self.h.call(self.labels['rp_send'], self.output.ports[port], self.message)

    def pending_off(self, port):
        return int.from_bytes(self.h.u.mem_read(self.entries[port]+recovery.COUNT, 2), 'little')

    def flags(self, port):
        return self.h.u.mem_read(self.entries[port]+recovery.FLAGS, 1)[0]

    def poll(self, port=None):
        if port is None:
            return self.output.poll()  # native router297DE follows RAM vtables
        return self.h.call(self.labels['rp_poll'], self.output.ports[port])

    def pending(self, port):
        return (self.pending_off(port) or self.flags(port) & recovery.STOP_PENDING
                or self.output.pending(port) or self.sysex_pending(port))

    def settle(self, rounds=128):
        for n in range(rounds):
            self.poll()
            if not any(self.pending(p) for p in range(3)):
                return n+1
        raise AssertionError('recovery did not settle within bounded fixture polls')

    def check_canaries(self):
        self.h.assertEqual(self.h.u.mem_read(recovery.STATE_BASE-4, 4), b'BEG!')
        self.h.assertEqual(self.h.u.mem_read(recovery.STATE_BASE+recovery.STATE_SIZE, 4), b'END!')
        expected = bytearray(self.before_code)
        for overlay in self.overlays:
            offset = overlay['address']-0x08010000
            expected[offset:offset+len(overlay['replacement'])] = overlay['replacement']
        self.h.assertEqual(bytes(self.h.u.mem_read(0x08010000, len(self.h.image))), bytes(expected))

    def write_disassembly(self, directory):
        from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB, CS_MODE_MCLASS
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        md = Cs(CS_ARCH_ARM, CS_MODE_THUMB | CS_MODE_MCLASS)
        instructions = list(md.disasm(self.code, recovery.CODE_BASE))
        assert sum(i.size for i in instructions) == len(self.code)
        (directory/'prototype-code.txt').write_text('\n'.join(
            f'{i.address:08X} {i.bytes.hex():12} {i.mnemonic} {i.op_str}' for i in instructions), encoding='utf-8')
        return instructions
