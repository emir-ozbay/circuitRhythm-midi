"""One-time local refactor; snapshots retain superseded isolation work."""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
p = ROOT / 'src/seq_Patch.py'
s = p.read_text(encoding='utf-8')
archive = ROOT / 'analysis/historical-bank-isolation'
archive.mkdir(exist_ok=True)
for name in ('src/seq_Patch.py', 'tests/test_phase1_safety.py', 'tests/test_reaudit_abi.py',
             'tests/test_projects_and_mode.py', 'scripts/verify_phase1_candidate.py'):
    target = archive / Path(name).name
    if target.exists():
        raise RuntimeError(f'Archive already exists: {target}')
    target.write_bytes((ROOT / name).read_bytes())

remove = {'emit_grid_press_gate', 'emit_proj_enter_page', 'emit_check_packs_allowed',
          'emit_proj_led_bank', 'emit_proj_pad_gate', 'emit_proj_dispatch_guard',
          'emit_save_btn_gate', 'emit_proj_load_complete', 'emit_proj_save_complete',
          'emit_proj_load_cb', 'emit_proj_save_cb', 'emit_save_storage_result',
          'emit_load_storage_result', 'emit_proj_timer_or_direct',
          'emit_project_load_containment', 'emit_record_start_guard',
          'emit_direct_record_dirty', 'emit_pattern_commit_dirty',
          'emit_knob_dirty_gate', 'emit_save_snapshot'}
lines = s.splitlines(keepends=True)
for node in sorted((n for n in ast.parse(s).body if isinstance(n, ast.FunctionDef) and n.name in remove),
                   key=lambda n: n.lineno, reverse=True):
    del lines[node.lineno-1:node.end_lineno]
s = ''.join(lines)
for name in remove:
    s = s.replace(f'    {name}(a)\n', '')
s = s.replace('    # Mark project dirty on user edit\n    E(movs_imm, 2, 1)\n    E(strb_w, 2, 0, OFF_SAVE_EDITED)\n    E(strb_imm, 2, 0, OFF_PROJECT_DIRTY)\n\n', '')
# Sample muting is controlled solely by runtime mode, never a project transaction.
for prefix in ('sample_trigger', 'metro_trigger', 'dsp_trigger', 'preview_trigger'):
    old = f'''    E(ldrb_imm, 1, 0, OFF_TRANS_STATE)
    E(cbz, "{prefix}_orig", 1)
    E(ldrb_imm, 2, 0, OFF_TRANS_TARGET_MODE)
    E(cmp_imm, 2, 1)
    E(b_cond, "{prefix}_mute", "eq")
'''
    assert old in s, prefix
    s = s.replace(old, '')
start = s.index('def emit_button_mode_hook(')
end = s.index('\ndef emit_sample_trigger_gate(', start)
s = s[:start] + '''def emit_button_mode_hook(a: Asm) -> None:
    """Shift + Sample Rec changes only the runtime mode of the current project."""
    E = a.emit
    a.label("c_button_mode_hook")
    E(push, [4, 5, 6, 7], lr=True)
    E(sub_sp_imm, 4)  # 24B; r4=controller, r5=stock button id
    E(mov_reg, 0, 4)
    E(adds_imm8, 0, 0xA0)
    E(mov_reg, 1, 5)
    E(bl, STOCK_CTRL_BUTTON_PRE)
    E(cmp_imm, 0, 0)
    E(b_cond_w, "btn_mode_handled", "ne")
    E(cmp_imm, 5, 18)
    E(b_cond_w, "btn_mode_orig", "ne")
    E(ldr_imm, 0, 4, 0x0C)
    E(cbz, "btn_mode_handled", 0)
    E(movs_imm, 1, 0)
    E(bl, STOCK_READ_STORE_WORD)
    E(ldrb_imm, 0, 0, 0)
    E(cbz, "btn_mode_orig", 0)
    E(bl, "c_seq_state")
    E(cbz, "btn_mode_handled", 0)
    E(mov_reg, 6, 0)
    # Serialize the final stopped/ownership check and single-byte mode commit.
    # Never call voice locks or grid notifications while interrupts are masked.
    E(raw, bytes.fromhex("eff31087 72b6"))  # mrs r7,primask; cpsid i
    E(mov_reg, 0, 4)
    E(bl, "c_mode_can_switch")
    E(cbz, "btn_mode_unlock", 0)
    E(ldr_imm, 0, 4, 0x3C)
    E(str_imm, 0, 6, OFF_GRID_PTR)
    E(str_imm, 4, 6, OFF_CTRL_PTR)
    E(ldrb_imm, 1, 6, OFF_SEQ_ENABLED)
    E(movs_imm, 2, 1)
    E(eors_reg, 1, 2)
    E(strb_imm, 1, 6, OFF_SEQ_ENABLED)
    E(raw, bytes.fromhex("87f31088"))  # restore caller PRIMASK
    E(cmp_imm, 1, 1)
    E(b_cond, "btn_mode_handled", "ne")
    E(bl, "c_silence_active_samples")
    E(b, "btn_mode_handled")
    a.label("btn_mode_unlock")
    E(raw, bytes.fromhex("87f31088"))
    a.label("btn_mode_handled")
    E(movs_imm, 0, 1)
    E(b, "btn_mode_exit")
    a.label("btn_mode_orig")
    E(movs_imm, 0, 0)
    a.label("btn_mode_exit")
    E(add_sp_imm, 4)
    E(pop, [4, 5, 6, 7], pc=True)


def emit_mode_can_switch(a: Asm) -> None:
    """r0=controller; return1 only for stopped, idle, unheld synthetic/stock graph.

    ctrl+18 is the store also passed to play-view+14 (3D3C0/501E8).
    Play-view50270..502A0 reads word0 to select start versus stop.
    ctrl+1C0..1DC ownership stores are cleared by stock3E448..3E478.
    Full external MIDI/scheduler integration remains a separate release gate.
    """
    E = a.emit
    a.label("c_mode_can_switch")
    E(push, [4, 5, 6], lr=True)
    E(mov_reg, 4, 0)
    E(ldr_imm, 0, 4, 0x18)
    E(cbz, "mode_check_reject", 0)
    E(movs_imm, 1, 0)
    E(bl, STOCK_READ_STORE_WORD)
    E(ldrb_imm, 1, 0, 0)
    E(cbnz, "mode_check_reject", 1)
    # Stock ready word: ready bit3, no Load/Save busy bits0..1.
    E(ldr_imm, 5, 4, 0x50)
    E(cbz, "mode_check_reject", 5)
    E(ldr_imm, 0, 5, 0x24)
    E(cbz, "mode_check_reject", 0)
    E(movs_imm, 1, 0)
    E(bl, STOCK_READ_STORE_WORD)
    E(ldrb_imm, 1, 0, 0)
    E(movs_imm, 2, 11)
    E(ands_reg, 1, 2)
    E(cmp_imm, 1, 8)
    E(b_cond_w, "mode_check_reject", "ne")
    E(ldr_imm, 0, 5, 0x28)
    E(cbz, "mode_check_reject", 0)
    E(movs_imm, 1, 1)
    E(bl, STOCK_READ_STORE_WORD)
    E(ldrb_imm, 1, 0, 0)
    E(cbnz, "mode_check_reject", 1)
    # Refuse held controller notes on any track; never synthesize Note Off.
    E(mov_reg, 5, 4)
    E(adds_imm8, 5, 0xE0)
    E(adds_imm8, 5, 0xE0)  # ctrl+1C0
    E(movs_imm, 6, 8)
    a.label("mode_check_notes")
    E(ldr_imm, 0, 5, 0)
    E(cbz, "mode_check_reject", 0)
    E(movs_imm, 1, 0)
    E(bl, STOCK_READ_STORE_WORD)
    E(ldr_imm, 1, 0, 0)
    E(cbnz, "mode_check_reject", 1)
    E(adds_imm8, 5, 4)
    E(subs_imm8, 6, 1)
    E(b_cond, "mode_check_notes", "ne")
    E(ldr_imm, 5, 4, 0x3C)
    E(cbz, "mode_check_reject", 5)
    E(ldr_w, 1, 5, 0x228)
    E(cbnz, "mode_check_reject", 1)
    E(movs_imm, 6, 0)
    a.label("mode_check_steps")
    E(mov_reg, 0, 6)
    E(adds_imm8, 0, 0x74)
    E(ldr_reg, 0, 5, 0)
    E(cbz, "mode_check_next_step", 0)
    E(ldr_w, 1, 0, 0xB8)
    E(ldr_w, 2, 0, 0xC0)
    E(orrs_reg, 1, 2)
    E(cbnz, "mode_check_reject", 1)
    # Reject stale per-step held bit3 too, before changing presentation.
    E(adds_imm8, 0, 0x74)
    E(movs_imm, 3, 32)
    a.label("mode_check_held_bit")
    E(ldrh_imm, 1, 0, 0)
    E(movs_imm, 2, 8)
    E(tst_reg, 1, 2)
    E(b_cond, "mode_check_reject", "ne")
    E(adds_imm8, 0, 2)
    E(subs_imm8, 3, 1)
    E(b_cond, "mode_check_held_bit", "ne")
    a.label("mode_check_next_step")
    E(adds_imm8, 6, 4)
    E(cmp_imm, 6, 32)
    E(b_cond, "mode_check_steps", "ne")
    E(movs_imm, 0, 1)
    E(pop, [4, 5, 6], pc=True)
    a.label("mode_check_reject")
    E(movs_imm, 0, 0)
    E(pop, [4, 5, 6], pc=True)


''' + s[end+1:]
s = s.replace('    emit_button_mode_hook(a)\n', '    emit_button_mode_hook(a)\n    emit_mode_can_switch(a)\n')
# Keep only UI/sample/heap hooks. Storage/recorder and project bank code is absent.
start = s.index('    resolve_addr = ', s.index('def build_step_routing_patches'))
end = s.index('\n    return [', start)
s = s[:start] + s[end:]
start = s.index('    return [', s.index('def build_step_routing_patches'))
end = s.index('\n\n\nbuild_phase1_patches', start)
hooks = [
    ('STOCK_ALLOCATOR_ADDR', 'EXPECTED_ALLOCATOR_ENTRY', 'c_allocator_guard', 'b_w'),
    ('HOOK_GRID_TRACK_CLEANUP', 'EXPECTED_GRID_TRACK_CLEANUP', 'c_grid_mode_cleanup', 'bl'),
    ('HOOK_GRID_MODE_CLEANUP', 'EXPECTED_GRID_MODE_CLEANUP', 'c_grid_mode_cleanup', 'bl'),
    ('HOOK_GRID_PRESS_RESOLVE', 'EXPECTED_GRID_PRESS_RESOLVE', 'c_resolve_subview', 'bl'),
    ('HOOK_GRID_PRESS_TRANSFORM', 'EXPECTED_GRID_PRESS_TRANSFORM', 'c_transform_pad', 'bl'),
    ('HOOK_GRID_RELEASE_RESOLVE', 'EXPECTED_GRID_RELEASE_RESOLVE', 'c_resolve_subview', 'bl'),
    ('HOOK_GRID_RELEASE_TRANSFORM', 'EXPECTED_GRID_RELEASE_TRANSFORM', 'c_transform_pad', 'bl'),
    ('HOOK_STEP_PRESS_PAGE', 'EXPECTED_STEP_PRESS_PAGE', 'c_step_page_read', 'bl'),
    ('HOOK_STEP_RELEASE_PAGE', 'EXPECTED_STEP_RELEASE_PAGE', 'c_step_page_read', 'bl'),
    ('HOOK_COMP_TOP_LEDS', 'EXPECTED_COMP_TOP_LEDS', 'c_comp_top_leds', 'bl'),
    ('HOOK_COMP_BOTTOM_MEMCPY', 'EXPECTED_COMP_BOTTOM_MEMCPY', 'c_comp_bottom_memcpy', 'bl'),
    ('HOOK_PAGE_BTN_MODE0', 'EXPECTED_PAGE_BTN_MODE0', 'c_page_btn_mode0', 'bl'),
    ('HOOK_BUTTON_MODE', 'EXPECTED_BUTTON_MODE', 'c_button_mode_hook', 'bl'),
    ('HOOK_SAMPLE_TRIGGER_GATE', 'EXPECTED_SAMPLE_TRIGGER_GATE', 'c_sample_trigger_gate', 'b_w'),
    ('HOOK_METRONOME_TRIGGER_GATE', 'EXPECTED_METRONOME_TRIGGER_GATE', 'c_metronome_trigger_gate', 'b_w'),
    ('HOOK_SAMPLE_DSP_GATE', 'EXPECTED_SAMPLE_DSP_GATE', 'c_sample_dsp_gate', 'bl'),
    ('HOOK_SAMPLE_PREVIEW_GATE', 'EXPECTED_SAMPLE_PREVIEW_GATE', 'c_sample_preview_gate', 'b_w'),
]
replacement = '    return [\n'
for site, expect, label, branch in hooks:
    replacement += f'        PatchHunk({site}, {expect},\n                  {branch}({site}, labels["{label}"]), "{label}_hook"),\n'
replacement += '''        PatchHunk(base, b"\\xFF" * len(cave_bytes), cave_bytes,
                  "seq_shared_project_code_cave"),
    ]'''
s = s[:start] + replacement + s[end:]
p.write_text(s, encoding='utf-8')
print('Shared-project source generated; historical snapshot saved.')
