"""Apply explicitly approved test-contract migration (user reply, 26 Oct 2026).

User approved replacing obsolete bank/automatic-Load expectations while keeping
complete archives and current grid/ABI/heap/MIDI safety coverage. No test skip.
"""
import ast
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / 'analysis/historical-bank-isolation'
TESTS = ('test_phase1_safety.py', 'test_reaudit_abi.py', 'test_projects_and_mode.py')
proof = {}
for name in TESTS:
    original = (ROOT / 'tests' / name).read_bytes()
    snapshot = (ARCHIVE / name).read_bytes()
    assert original == snapshot, f'Original/archive mismatch: {name}'
    proof[name] = hashlib.sha256(snapshot).hexdigest()
(ARCHIVE / 'test-snapshot-hashes.json').write_text(json.dumps(proof, indent=2), encoding='utf-8')


def migrate(name, keep, replacements=None):
    p = ROOT / 'tests' / name
    s = p.read_text(encoding='utf-8')
    lines = s.splitlines(keepends=True)
    removed = []
    for cls in ast.parse(s).body:
        if not isinstance(cls, ast.ClassDef):
            continue
        methods = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name.startswith('test_')]
        for n in sorted(methods, key=lambda x: x.lineno, reverse=True):
            if n.name in (replacements or {}):
                lines[n.lineno-1:n.end_lineno] = [(replacements[n.name]).rstrip() + '\n']
            elif n.name not in keep:
                removed.append(n.name)
                del lines[n.lineno-1:n.end_lineno]
    result = re.sub(r'\n{4,}', '\n\n\n', ''.join(lines))
    p.write_text(result, encoding='utf-8')
    return sorted(removed)


removed = {}
removed['test_phase1_safety.py'] = migrate('test_phase1_safety.py', {
    'test_sample_rec_without_shift_preserves_button_id',
    'test_shortcut_repeated_press_requires_stock_release',
    'test_projects_heap_failure_never_returns_null',
    'test_reserved_heap_with_overlapping_current_writes_nothing',
    'test_reservation_and_allocator_restore_primask_and_serialize_writes',
    'test_real_note_on_vtable_entry_is_gated_and_note_off_preserved',
    'test_real_track_change_clears_ownership_before_stock_releases',
    'test_all_seven_other_modes_route_identically_to_stock',
    'test_page_store_and_led_hooks_preserve_all_other_modes',
    'test_step_store_canaries_all_32_pads_page_one',
    'test_sample_muting_all_entry_paths_and_active_voice_closure',
    'test_allocator_oom_returns_failure',
    'test_manifest_cannot_overwrite_pinned_input_or_output',
    'test_parser_rejects_skipped_bytes_and_excess_flash_blocks',
    'test_unaligned_cave_start_rejected',
}, {
    'test_shortcut_repeated_press_requires_stock_release': '''    def test_shortcut_repeated_press_requires_stock_release(self):
        from shared_project_test_support import SharedModeFixture
        f = SharedModeFixture(self)
        for _ in range(2):
            f.press()
            self.assertEqual(self.u.mem_read(seq.SEQ_STATE_ADDR+4, 1), b'\\1')
        f.release()
        f.press()
        self.assertEqual(self.u.mem_read(seq.SEQ_STATE_ADDR+4, 1), b'\\0')''',
})
removed['test_reaudit_abi.py'] = migrate('test_reaudit_abi.py', {
    'test_real_constructors_bind_recorders_to_project_storage',
    'test_midi_extreme_notes_preserve_recorder_boundary',
    'test_stock_note_ownership_keeps_other_source_until_release',
    'test_midi_decoder_through_ownership_filters_to_pattern',
    'test_midi_channel_and_note_translation_to_router_boundary',
    'test_record_group_routes_tracks_and_checks_all_three_gates',
    'test_recorder_callbacks_through_pending_to_pattern',
    'test_direct_record_to_nonselected_pattern_marks_dirty',
    'test_direct_delay_to_nonselected_pattern_marks_dirty',
    'test_record_selected_pattern_updates_stores_and_preserves_canaries',
    'test_nonmutation_commit_notification_preserves_dirty_and_abi',
    'test_parameter_commit_without_pad_marks_dirty_and_blocks_switch',
    'test_knob_input_marks_dirty_and_transition_blocks_delivery',
    'test_allocator_rejects_integer_wrap',
}, {
    'test_parameter_commit_without_pad_marks_dirty_and_blocks_switch': '''    def test_parameter_commit_preserved_across_same_project_mode_switch(self):
        from verify_phase1_candidate import EmulatorHarness
        from shared_project_test_support import SharedModeFixture
        for setter, store_name, offset, value in (
            (0x080549B0, 'st1', 3, 99), (0x080549D8, 'st1', 2, 5),
            (0x08054A04, 'st1', 4, 3), (0x08054A30, 'st1', 5, 80),
            (0x08054A5C, 'st2', 0, 72), (0x08054A84, 'st2', 1, 12),
            (0x08054AB0, 'st2', 6, 1),
        ):
            for step in (0, 31):
                with self.subTest(setter=hex(setter), step=step):
                    h = EmulatorHarness(self.image, self.labels)
                    env = h.setup_step_view_environment(active_pattern=7)
                    f = SharedModeFixture(h)
                    h.call(setter, env[store_name], step, value)
                    h.call(base.seq.STOCK_NOTIFY_STORE, env[store_name])
                    self.assertEqual(h.u.mem_read(env['patterns'] + 7*0xA28 + 8*step + offset, 1), bytes([value]))
                    before = bytes(h.u.mem_read(env['patterns'], 8*0xA28))
                    f.press()
                    self.assertEqual(h.u.mem_read(base.seq.SEQ_STATE_ADDR + 4, 1), b'\\x01')
                    self.assertEqual(bytes(h.u.mem_read(env['patterns'], len(before))), before)''',
    'test_knob_input_marks_dirty_and_transition_blocks_delivery': '''    def test_stock_knob_delivery_in_both_runtime_modes(self):
        ctrl, view, vt = 0x20004000, 0x20005000, 0x20006000
        self.word(ctrl + 0x8C, self.store(bytes(4)))
        self.word(ctrl + 0x78, view); self.word(view, vt)
        callback = 0x0800E900
        self.word(vt + 0x10, callback | 1)
        self.u.mem_write(callback, bytes.fromhex('7047'))
        events = []
        self.u.hook_add(base.UC_HOOK_CODE, lambda u,a,z,d: events.append(tuple(u.reg_read(r) for r in base.REGS[:3])), begin=callback, end=callback)
        for mode in (0, 1):
            self.u.mem_write(base.seq.SEQ_STATE_ADDR + 4, bytes([mode]))
            for knob in range(8):
                for delta in (0, 1, 0xFFFFFFFF):
                    self.call(0x0803DDE0, ctrl, knob, delta)
                    self.assertEqual(events[-1], (view, knob, delta))
        self.assertEqual(len(events), 48)''',
})
p = ROOT / 'tests/test_reaudit_abi.py'
s = p.read_text(encoding='utf-8')
s = s.replace('    # Read/Close component tests explicitly bypass containment in emulator RAM.\n    # They cannot establish that production Load is functional.',
              '    # Current stock MIDI/recorder and ABI regressions; no storage hook bypass.')
# In the new scope stock recording no longer writes private dirty-tracker bytes.
# All pattern/store/canary assertions remain; only this removed private side effect changes.
s = s.replace("base.seq.OFF_PROJECT_DIRTY, 1), b'\\x01'", "base.seq.OFF_PROJECT_DIRTY, 1), b'\\x00'")
s = s.replace("base.seq.OFF_SAVE_EDITED, 1), b'\\x01'", "base.seq.OFF_SAVE_EDITED, 1), b'\\x00'")
s = s.replace('base.seq.OFF_PROJECT_DIRTY, 1), bytes([enabled])', 'base.seq.OFF_PROJECT_DIRTY, 1), bytes(1)')
s = s.replace('test_direct_record_to_nonselected_pattern_marks_dirty', 'test_stock_direct_record_nonselected_pattern_preserves_canaries')
s = s.replace('test_direct_delay_to_nonselected_pattern_marks_dirty', 'test_stock_direct_delay_nonselected_pattern_preserves_canaries')
s = s.replace('test_nonmutation_commit_notification_preserves_dirty_and_abi', 'test_nonmutation_commit_notification_preserves_private_state_and_abi')
p.write_text(s, encoding='utf-8')
removed['test_projects_and_mode.py'] = migrate('test_projects_and_mode.py', {
    'test_all_phase1_hooks_and_code_cave_integrity',
    'test_page_1_16_button_locked_only_in_grid_mode_0',
    'test_sample_engine_muting_midi_only',
}, {
    'test_all_phase1_hooks_and_code_cave_integrity': '''    def test_current_hook_integrity_and_removed_project_hooks_are_stock(self):
        md = Cs(CS_ARCH_ARM, CS_MODE_THUMB | CS_MODE_MCLASS)
        for site, label in ((HOOK_PAGE_BTN_MODE0, 'c_page_btn_mode0'),
                            (HOOK_BUTTON_MODE, 'c_button_mode_hook')):
            insns = list(md.disasm(self.patched_image[site-BASE:site-BASE+4], site))
            self.assertEqual(len(insns), 1)
            self.assertEqual(insns[0].mnemonic, 'bl')
            self.assertEqual(insns[0].op_str, f"#{self.labels[label]:#x}")
        for site in (HOOK_PROJ_ENTER_PAGE, HOOK_PROJ_PAGE_LOCK, HOOK_CHECK_PACKS):
            self.assertEqual(self.patched_image[site-BASE:site-BASE+4], self.stock_image[site-BASE:site-BASE+4])
        gate = list(md.disasm(self.patched_image[HOOK_SAMPLE_TRIGGER_GATE-BASE:HOOK_SAMPLE_TRIGGER_GATE-BASE+4], HOOK_SAMPLE_TRIGGER_GATE))
        self.assertEqual(gate[0].mnemonic, 'b.w')
        self.assertEqual(gate[0].op_str, f"#{self.labels['c_sample_trigger_gate']:#x}")''',
})
p = ROOT / 'tests/test_projects_and_mode.py'
s = p.read_text(encoding='utf-8')
a = s.index('"""'); b = s.index('"""', a+3)
s = s[:a] + '"""Current UI/sample hooks; shared64-project coverage is in test_shared_project.py.\n\nHistorical bank-isolation tests are fully archived under analysis/historical-bank-isolation.\n"""' + s[b+3:]
p.write_text(s, encoding='utf-8')
(ARCHIVE / 'approved-test-migration.json').write_text(json.dumps({
    'authorization': 'Explicit user approval via request_user_input_async reply: Evet, eski kapsam testlerini yeni testlerle degistir',
    'snapshot_sha256': proof,
    'superseded_methods': removed,
    'replacement_contract': 'tests/test_shared_project.py plus migrated current UI/MIDI assertions',
    'no_skips': True,
}, indent=2), encoding='utf-8')
print(json.dumps({name: len(items) for name, items in removed.items()}, indent=2))
