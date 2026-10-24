"""Stock code in synthetic RAM, not a device or complete UI emulation.

Run from the project root: .venv/Scripts/python.exe tests/test_ui_contracts.py
"""
import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from inspect_ui import load_image, BASE
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_THUMB, UC_MODE_MCLASS, UC_HOOK_CODE
from unicorn.arm_const import (
    UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3,
    UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_PC,
)

REGS = [UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3]
STOP = 0x0800F000


class Contracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.image = load_image()

    def setUp(self):
        self.u = Uc(UC_ARCH_ARM, UC_MODE_THUMB | UC_MODE_MCLASS)
        self.u.mem_map(0x08000000, 0x80000)
        self.u.mem_write(BASE, self.image)
        self.u.mem_map(0x20000000, 0x50000)
        self.next_store = 0x20008000

    def word(self, addr, value):
        self.u.mem_write(addr, struct.pack("<I", value))

    def readword(self, addr):
        return struct.unpack("<I", self.u.mem_read(addr, 4))[0]

    def store(self, data, active=0):
        obj = self.next_store
        self.next_store += 0x200
        self.u.mem_write(obj, struct.pack("<5I", len(data) // 4, active, 0, obj + 0x40, obj + 0xC0))
        self.u.mem_write(obj + 0x40, data)
        self.u.mem_write(obj + 0xC0, data)
        return obj

    def call(self, addr, *args):
        for reg, value in zip(REGS, args):
            self.u.reg_write(reg, value)
        self.u.reg_write(UC_ARM_REG_SP, 0x2004F000)
        self.u.reg_write(UC_ARM_REG_LR, STOP | 1)
        self.u.emu_start(addr | 1, STOP, count=20000)
        self.assertEqual(self.u.reg_read(UC_ARM_REG_PC), STOP)
        return self.u.reg_read(UC_ARM_REG_R0)

    def test_pad_press_release_dispatch(self):
        cell, obj, vt = 0x20001000, 0x20001100, 0x20001200
        self.word(cell, obj)
        self.word(obj, vt)
        callbacks = [0x0800E000, 0x0800E004]
        for slot, addr in enumerate(callbacks):
            self.word(vt + slot * 4, addr | 1)
            self.u.mem_write(addr, bytes.fromhex("7047"))
        seen = []

        def record(u, addr, size, data):
            if addr in callbacks:
                seen.append((addr, *(u.reg_read(r) for r in REGS[:3])))

        self.u.hook_add(UC_HOOK_CODE, record)
        for pad in (0, 15, 16, 31):
            for velocity in (0, 1, 2, 127, 255):
                seen.clear()
                self.call(0x08040108, cell, pad, velocity, 1)
                self.assertEqual(seen, [(callbacks[0], obj, pad, max(1, velocity >> 1))])
            seen.clear()
            self.call(0x08040108, cell, pad, 0, 0)
            self.assertEqual([x[:3] for x in seen], [(callbacks[1], obj, pad)])

    def test_container_selection_and_local_pad(self):
        grid = 0x20001000
        selected = self.store(bytes(4))
        self.word(grid + 0x25C, selected)
        for track in (0, 7):
            self.u.mem_write(selected + 0x40, bytes([track, 0, 0, 0]))
            self.assertEqual(self.call(0x0805800E, grid), track)
            for mode in (0, 2, 3):
                top, bottom, page_obj = 0x20002000, 0x20003000, 0x20004000
                self.u.mem_write(grid + 0x264, bytes([mode]))
                self.word(grid + 0x74 + track * 4, top)
                bottom_offset = {0: 0x14, 2: 0x9C, 3: 0xBC}[mode]
                self.word(grid + bottom_offset + track * 4, bottom)
                self.word(grid + 0x19C + track * 4, page_obj)
                page = self.store(bytes(4))
                self.word(page_obj + 0x10, page)
                for half in (0, 1):
                    self.u.mem_write(page + 0x40, bytes([half, 0, 0, 0]))
                    for pad in (0, 15, 16, 31):
                        self.assertEqual(self.call(0x0804DC86, grid, pad), top if pad < 16 else bottom,
                                         (track, mode, half, pad))
                        local = pad if pad < 16 else pad - 16 + (half * 16 if mode == 0 else 0)
                        self.assertEqual(self.call(0x0804DF3E, grid, pad, track, mode), local)

    def test_setter_notify_and_pattern_commit(self):
        # All eight pattern blocks retained; one selected pattern changes.
        patterns, listener, listeners = 0x20010000, 0x20001000, 0x20001100
        self.word(listener, 0x080696A0)  # real stock vtable -> 0x08048208
        self.word(listener + 4, patterns)
        original = bytes([60, 6, 1, 96, 7, 255, 0, 0]) * 32 + bytes([0xA5]) * (0xA28 - 256)
        for pattern in (0, 7):
            for active in (0, 0xFFFFFFFF):
                for step in (0, 15, 16, 31):
                    with self.subTest(pattern=pattern, active=active, step=step):
                        self.next_store = 0x20008000
                        st1 = self.store(bytes([96]) * 32 + bytes([7]) * 32 + bytes([1]) * 32 + bytes([255]) * 32, active)
                        st2 = self.store(bytes([60]) * 32 + bytes([6]) * 32 + bytes(32), active)
                        selection = self.store(bytes([pattern, 0, 0, 0]))
                        self.word(listener + 0x1C, st1)
                        self.word(listener + 0x20, st2)
                        self.word(listener + 0x28, selection)
                        for store in (st1, st2):
                            self.u.mem_write(store + 1, bytes([1]))
                            self.word(store + 0x14, listeners)
                        self.word(listeners, listener)
                        self.word(listeners + 4, 0xFFFFFFFF)
                        self.u.mem_write(patterns, original * 8)
                        # Real accessors, setters, notification, vtable callback and commit; no mocks.
                        self.call(0x08054A5C, st2, step, 72)
                        self.call(0x08054A84, st2, step, 12)
                        self.call(0x08054AB0, st2, step, 1)
                        self.call(0x080549D8, st1, step, 5)
                        self.call(0x08054A04, st1, step, 3)
                        self.assertEqual(bytes(self.u.mem_read(patterns, 8 * 0xA28)), original * 8)
                        dirty1, dirty2 = self.readword(st1 + 8), self.readword(st2 + 8)
                        self.call(0x0803FBEC, st2)
                        self.call(0x0803FBEC, st1)
                        expected = bytearray(original * 8)
                        offset = pattern * 0xA28 + step * 8
                        expected[offset:offset + 8] = bytes([72, 12, 5, 96, 3, 255, 1, 0])
                        self.assertEqual(self.u.mem_read(patterns, len(expected)), expected)
                        for store, dirty in ((st1, dirty1), (st2, dirty2)):
                            self.assertEqual(self.readword(store + 8), 0)
                            self.assertEqual(self.readword(store + 4), active ^ dirty)
                        # A subsequent edit must keep the earlier committed note/gate/flags.
                        self.call(0x08054A04, st1, step, 7)
                        self.call(0x0803FBEC, st1)
                        expected[offset + 4] = 7
                        self.assertEqual(self.u.mem_read(patterns, len(expected)), expected)

    def test_toggle_commit_and_led_observer(self):
        view, led_cell, leds = 0x20002000, 0x20003000, 0x20003100
        listener, listeners, patterns = 0x20001000, 0x20001100, 0x20010000
        empty = bytes([0, 6, 0, 0, 7, 255, 0, 0]) * 32 + bytes([0xA5]) * (0xA28 - 256)
        st1 = self.store(bytes(32) + bytes([7]) * 32 + bytes(32) + bytes([255]) * 32)
        st2 = self.store(bytes(32) + bytes([6]) * 32 + bytes(32))
        selection = self.store(bytes([7, 0, 0, 0]))
        note = self.store(bytes([60, 0, 0, 0]))
        held = self.store(bytes([255, 0, 0, 0]) * 2)
        page = self.store(bytes(4))
        self.word(listener, 0x080696A0)
        for offset, value in ((4, patterns), (0x1C, st1), (0x20, st2), (0x28, selection)):
            self.word(listener + offset, value)
        self.word(listeners, listener)
        self.word(listeners + 4, 0xFFFFFFFF)
        self.word(listeners + 8, view + 8)
        self.word(listeners + 12, 0xFFFFFFFF)
        for store, count in ((st1, 2), (st2, 1)):
            self.u.mem_write(store + 1, bytes([count]))
            self.word(store + 0x14, listeners)
        for offset, value in ((0, 0x080682CC), (4, led_cell), (8, 0x080682F8),
                              (0xC, st1), (0x10, st2), (0x18, held), (0x5C, note),
                              (0x60, page), (0x64, held)):
            self.word(view + offset, value)
        self.word(led_cell, leds)
        self.u.mem_write(patterns, empty * 8)
        for step in (0, 15, 16, 31):
            with self.subTest(step=step):
                self.call(0x0805CF24, view, step)
                off_colour = bytes(self.u.mem_read(leds + 2 * step, 2))
                self.call(0x0805D610, view, step)
                expected = bytearray(empty * 8)
                offset = 7 * 0xA28 + step * 8
                expected[offset:offset + 8] = bytes([60, 6, 1, 96, 7, 255, 0, 0])
                self.assertEqual(self.u.mem_read(patterns, len(expected)), expected)
                self.assertEqual(struct.unpack('<H', self.u.mem_read(view + 0x74 + 2 * step, 2))[0], 2)
                self.assertNotEqual(bytes(self.u.mem_read(leds + 2 * step, 2)), off_colour)
                self.call(0x0805D610, view, step)
                self.assertEqual(bytes(self.u.mem_read(patterns, 8 * 0xA28)), empty * 8)
                self.assertEqual(bytes(self.u.mem_read(leds + 2 * step, 2)), off_colour)
        # The LED getter returns a 16-step window of the existing 32-entry buffer.
        for half in (0, 1):
            self.u.mem_write(page + 0x40, bytes([half, 0, 0, 0]))
            self.assertEqual(self.call(0x0805D3BC, view), leds + half * 32)

    def test_pressed_step_colour_branch_and_vtables(self):
        pointers = {0x080672E4: 0x0803D7FF, 0x080678DC: 0x0804D7A1,
                    0x080678F8: 0x0804DD1D, 0x080682CC: 0x0805CB05,
                    0x080682D0: 0x0805CCF1, 0x080682E8: 0x0805D3BD,
                    0x080682F8: 0x0805D093, 0x080696A0: 0x08048209}
        for addr, expected in pointers.items():
            self.assertEqual(struct.unpack_from('<I', self.image, addr - BASE)[0], expected)
        self.assertEqual(self.image[0x0805CF68 - BASE:0x0805CF6A - BASE], bytes.fromhex('1f22'))
        view, cell, leds = 0x20002000, 0x20003000, 0x20003100
        self.word(view + 4, cell)
        self.word(cell, leds)
        palette = 0x08062AB0
        for step in (0, 15, 16, 31):
            self.u.mem_write(leds, bytes([0xA5]) * 64)
            self.u.mem_write(view + 0x74 + step * 2, struct.pack('<H', 8))
            self.call(0x0805CF24, view, step)
            expected = bytearray([0xA5] * 64)
            expected[step * 2:step * 2 + 2] = self.image[palette - BASE + 31 * 2:palette - BASE + 32 * 2]
            self.assertEqual(self.u.mem_read(leds, 64), expected)


if __name__ == "__main__":
    if sys.flags.optimize:
        raise RuntimeError("Do not use Python -O")
    unittest.main(verbosity=2)
