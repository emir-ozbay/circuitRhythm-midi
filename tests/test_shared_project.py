"""Current shared-project contract. Real button dispatch; no Load completion injection."""
import struct
import unittest
import test_phase1_safety as base
from inspect_ui import load_image, BASE
from shared_project_test_support import SharedModeFixture


class SharedProjectTests(unittest.TestCase):
    setUpClass = classmethod(base.SafetyTests.setUpClass.__func__)
    setUp = base.SafetyTests.setUp
    word = base.SafetyTests.word
    read = base.SafetyTests.read
    store = base.SafetyTests.store
    call = base.SafetyTests.call

    def test_full_button_toggle_preserves_project_and_never_dispatches_io(self):
        from project_alias_test_support import ProjectAliasFixture, STORE_LEN
        alias = ProjectAliasFixture(self)
        f = SharedModeFixture(self, ctrl=0x2000B800, view=0x2000C000, grid=0x2000C800)
        before = bytes(self.u.mem_read(alias.raw, STORE_LEN))
        metadata = bytes(self.u.mem_read(f.meta, 0x100))
        project = bytes(self.u.mem_read(alias.p, 0x100))
        calls = []
        for address in (0x08047038, 0x08037B8C, 0x08037BD6, 0x08037ED0,
                        0x08047288, 0x080472E2, 0x0804113A, 0x080411D8, 0x08041906):
            self.u.hook_add(base.UC_HOOK_CODE, lambda u,a,z,d: calls.append(a), begin=address, end=address)
        # Unsaved-edit markers from the superseded layout cannot veto the mode.
        self.u.mem_write(base.seq.SEQ_STATE_ADDR + 0x1A, b'\x01')
        for expected in (1, 0, 1, 0):
            f.press()
            self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR + 4, 1), bytes([expected]))
            self.assertEqual(bytes(self.u.mem_read(alias.raw, STORE_LEN)), before)
            self.assertEqual(bytes(self.u.mem_read(f.meta, 0x100)), metadata)
            self.assertEqual(bytes(self.u.mem_read(alias.p, 0x100)), project)
            self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR + 0x1A, 1), b'\x01')
            self.assertEqual(self.read(base.seq.SEQ_STATE_ADDR + base.seq.OFF_GRID_PTR), f.grid)
            f.release()
        self.assertEqual(calls, [])

    def test_stock_button_ownership_requires_release(self):
        f = SharedModeFixture(self)
        f.press()
        f.press()
        self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR + 4, 1), b'\x01')
        f.release()
        f.press()
        self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR + 4, 1), b'\x00')

    def test_running_transport_and_project_io_busy_reject_both_directions(self):
        for mode in (0, 1):
            for which, offset, value in (('transport', 0, 1), ('transport', 0, 2),
                                         ('ready', 0, 0), ('ready', 0, 1), ('ready', 0, 3),
                                         ('ready', 0, 7), ('phase', 4, 1), ('phase', 4, 2)):
                with self.subTest(mode=mode, which=which, value=value):
                    self.setUp()
                    f = SharedModeFixture(self)
                    f.set_byte(getattr(f, which), offset, value)
                    self.u.mem_write(base.seq.SEQ_STATE_ADDR + 4, bytes([mode]))
                    before = bytes(self.u.mem_read(base.seq.SEQ_STATE_ADDR, 256))
                    f.press()
                    self.assertEqual(bytes(self.u.mem_read(base.seq.SEQ_STATE_ADDR, 256)), before)

    def test_ready_bit_matches_stock_ui_and_busy_phase_is_independent(self):
        for flags in (8,9,10,11,12,14,15):
            for phase in (0,1,2):
                for mode in (0,1):
                    with self.subTest(flags=flags,phase=phase,mode=mode):
                        self.setUp();f=SharedModeFixture(self)
                        f.set_byte(f.ready,0,flags);f.set_byte(f.phase,4,phase)
                        self.u.mem_write(base.seq.SEQ_STATE_ADDR+4,bytes([mode]))
                        f.press()
                        self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR+4,1),bytes([mode if phase else mode^1]))

    def test_missing_context_and_invalid_heap_fail_closed(self):
        for where, offset in (('ctrl', 0x18), ('ctrl', 0x50), ('ctrl', 0x3C),
                              ('ctrl', 0x1C0), ('view', 0x24), ('view', 0x28)):
            with self.subTest(where=where, offset=offset):
                self.setUp()
                f = SharedModeFixture(self)
                self.word(getattr(f, where) + offset, 0)
                before = bytes(self.u.mem_read(base.seq.SEQ_STATE_ADDR, 256))
                f.press()
                self.assertEqual(bytes(self.u.mem_read(base.seq.SEQ_STATE_ADDR, 256)), before)
        self.setUp()
        f = SharedModeFixture(self)
        self.word(base.seq.HEAP_CUR_PTR, base.seq.SEQ_STATE_ADDR + 4)
        before = bytes(self.u.mem_read(base.seq.SEQ_STATE_ADDR, 256))
        f.press()
        self.assertEqual(bytes(self.u.mem_read(base.seq.SEQ_STATE_ADDR, 256)), before)

    def test_held_notes_and_pads_reject_without_clearing_ownership(self):
        for track in range(8):
            for kind in ('note', 'physical', 'held', 'bit3'):
                with self.subTest(track=track, kind=kind):
                    self.setUp()
                    f = SharedModeFixture(self)
                    view = 0x20006000
                    self.word(f.grid + 0x74 + 4*track, view)
                    address, payload = {
                        'note': (f.note_owners[track] + 0x40, bytes([1, 0, 0, 0])),
                        'physical': (f.grid + 0x228, (1 << 31).to_bytes(4, 'little')),
                        'held': (view + 0xC0, (1 << 31).to_bytes(4, 'little')),
                        'bit3': (view + 0x74 + 31*2, bytes([8, 0])),
                    }[kind]
                    self.u.mem_write(address, payload)
                    f.press()
                    self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR + 4, 1), b'\x00')
                    self.assertEqual(bytes(self.u.mem_read(address, len(payload))), payload)

    def test_released_click_history_all_tracks_allows_both_modes_without_mutation(self):
        for track in range(8):
            for mode in (0,1):
                with self.subTest(track=track,mode=mode):
                    self.setUp();f=SharedModeFixture(self);view=0x20006000
                    self.word(f.grid+0x74+4*track,view)
                    self.word(view+0xB8,0x80000001)
                    self.u.mem_write(view+0x74,bytes([1,0,4,0]))
                    self.u.mem_write(base.seq.SEQ_STATE_ADDR+4,bytes([mode]))
                    before=bytes(self.u.mem_read(view,0x118))
                    f.press()
                    self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR+4,1),bytes([mode^1]))
                    self.assertEqual(bytes(self.u.mem_read(view,0x118)),before)

    def test_rejected_mode_preserves_click_history_and_live_ownership(self):
        for mode in (0,1):
            for held in (0,0x80000000):
                with self.subTest(mode=mode,held=held):
                    self.setUp();f=SharedModeFixture(self);view=0x20006000
                    self.word(f.grid+0x74,view);self.word(view+0xB8,0x80000001)
                    self.word(view+0xC0,held);f.set_byte(f.transport,0,1)
                    self.u.mem_write(base.seq.SEQ_STATE_ADDR+4,bytes([mode]))
                    before=bytes(self.u.mem_read(view,0x118))
                    f.press()
                    self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR+4,1),bytes([mode]))
                    self.assertEqual(bytes(self.u.mem_read(view,0x118)),before)

    def test_primask_restored_and_commit_serialized_voice_calls_outside_lock(self):
        for primask in (0, 1):
            with self.subTest(primask=primask):
                self.setUp()
                f = SharedModeFixture(self)
                commits, voices = [], []
                self.word(0x20000310, 1)
                self.u.mem_write(base.seq.STOCK_SAMPLE_FORCE_OFF, bytes.fromhex('7047'))
                self.u.hook_add(base.UC_HOOK_CODE,
                    lambda u,a,z,d: voices.append((u.reg_read(base.UC_ARM_REG_R0), u.reg_read(base.UC_ARM_REG_PRIMASK))),
                    begin=base.seq.STOCK_SAMPLE_FORCE_OFF, end=base.seq.STOCK_SAMPLE_FORCE_OFF)
                mask = [None]
                def instruction(u, address, size, data):
                    mask[0] = u.reg_read(base.UC_ARM_REG_PRIMASK)
                def written(u, access, address, size, value, data):
                    if address == base.seq.SEQ_STATE_ADDR + 4:
                        commits.append((value, mask[0]))
                self.u.hook_add(base.UC_HOOK_CODE, instruction)
                self.u.hook_add(base.UC_HOOK_MEM_WRITE, written)
                self.u.reg_write(base.UC_ARM_REG_PRIMASK, primask)
                f.press()
                self.assertEqual(commits, [(1, 1)] if primask == 0 else [])
                self.assertEqual(voices, [(ch, 0) for ch in range(16, 24)] if primask == 0 else [])
                self.assertEqual(self.u.reg_read(base.UC_ARM_REG_PRIMASK), primask)

    def test_all_64_slots_route_load_duplicate_save_clear_in_both_modes(self):
        f = SharedModeFixture(self)
        clear, save, duplicate = (self.store(bytes(4)) for _ in range(3))
        for off, obj in ((0x18, clear), (0x2C, save), (0x1C, duplicate),
                         (0x30, 0x20007000), (0x0C, 0x20006000),
                         (0x10, 0x20006100), (0x14, 0x20006200)):
            self.word(f.view + off, obj)
        calls = []
        # Observe stock UI dispatch arguments; no storage outcome is fabricated.
        self.u.mem_write(0x08047038, bytes.fromhex('7047'))
        self.u.hook_add(base.UC_HOOK_CODE,
            lambda u,a,z,d: calls.append(tuple(u.reg_read(r) for r in base.REGS)),
            begin=0x08047038, end=0x08047038)
        for mode in (0, 1):
            self.u.mem_write(base.seq.SEQ_STATE_ADDR + 4, bytes([mode]))
            for slot in range(64):
                self.u.mem_write(f.view + 0x36, bytes([slot >> 5]))
                f.set_byte(f.meta, 44, slot)
                for op, flags in (('load', (0, 0, 0)), ('duplicate', (0, 0, 1)),
                                  ('save', (0, 1, 0)), ('clear', (1, 0, 0))):
                    for obj, value in zip((clear, save, duplicate), flags):
                        f.set_byte(obj, 0, value)
                    calls.clear()
                    self.call(0x0804F09E, f.view, slot & 31)
                    expected = {'load': (0x20006000, slot+64, 0, 0),
                                'duplicate': (0x20006000, slot, 0, 0),
                                'save': (0x20006100, slot, 0, 0),
                                'clear': (0x20006200, 0, 0, 0)}[op]
                    self.assertEqual(calls, [expected], (mode, slot, op))

    def test_projects_storage_recording_and_packs_bytes_are_stock(self):
        stock = load_image()
        from project_load_recovery_patch import HOOKS,arm_code
        import midi_recovery_patch as fixed
        from thumb_asm import b_w
        recovery_labels=arm_code(fixed.seq_code()[1]['c_seq_state'],fixed.STATE_BASE)[1]
        expected=bytearray(stock)
        for site,original,name in HOOKS:
            actual=self.image[site-BASE:site-BASE+4]
            self.assertIn(actual,(original,b_w(site,recovery_labels[name])))
            expected[site-BASE:site-BASE+4]=actual
        for start, end in ((0x08036A02, 0x08036B04), (0x08037B8C, 0x08038798),
                           (0x0803DB54, 0x0803DB60), (0x0803DDE0, 0x0803DDE8),
                           (0x0804113A, 0x080411D8), (0x08047288, 0x080472A8),
                           (0x080472AC, 0x08047364),
                           (0x08048208, 0x08048210), (0x08048AE0, 0x08049400),
                           (0x0804ED60, 0x0804F3F0)):
            self.assertEqual(self.image[start-BASE:end-BASE], expected[start-BASE:end-BASE], hex(start))
        # Only the recovery profile contains failed project reads at this bridge.
        from project_load_recovery_patch import SITE,EXPECTED,CODE_BASE
        from thumb_asm import b_w
        self.assertIn(self.image[SITE-BASE:SITE-BASE+4],(EXPECTED,b_w(SITE,CODE_BASE)))
        self.assertNotIn('c_project_load_containment', self.labels)
        self.assertNotIn('c_proj_dispatch_guard', self.labels)

    def test_both_project_pages_follow_active_slot_in_both_modes(self):
        f = SharedModeFixture(self)
        self.u.mem_write(0x0804F27E, bytes.fromhex('7047'))  # LED hardware boundary
        duplicate = self.store(bytes(4))
        self.word(f.view + 0x1C, duplicate)
        for mode in (0, 1):
            self.u.mem_write(base.seq.SEQ_STATE_ADDR + 4, bytes([mode]))
            for slot in range(64):
                f.set_byte(f.meta, 44, slot)
                self.call(0x0804F080, f.view)
                self.assertEqual(self.u.mem_read(f.view + 0x36, 1), bytes([slot >> 5]))
                for button, page in ((19, 1), (20, 0)):
                    self.call(0x0804F12C, f.view, button)
                    self.assertEqual(self.u.mem_read(f.view + 0x36, 1), bytes([page]))


if __name__ == '__main__':
    unittest.main()
