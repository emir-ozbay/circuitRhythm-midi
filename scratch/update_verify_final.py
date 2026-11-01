from pathlib import Path

path = Path('scripts/verify_phase1_candidate.py')
text = path.read_text(encoding='utf-8')

start_marker = "def release_blockers(image: bytes, labels: dict[str, int]) -> list[dict]:"
end_marker = "def main() -> int:"

start_idx = text.find(start_marker)
end_idx = text.find(end_marker)

assert start_idx != -1 and end_idx != -1

new_func = """def release_blockers(image: bytes, labels: dict[str, int]) -> list[dict]:
    \"\"\"Verify bank isolation, state machine transition, and active project safety.\"\"\"
    from unicorn.arm_const import UC_ARM_REG_R4, UC_ARM_REG_R5
    h = EmulatorHarness(image, labels)
    ctrl, project_view = 0x20004000, 0x20004500
    P = 0x20007000
    shift = h.store(bytes([1, 0, 0, 0]))
    active_view = h.store(bytes([6, 0, 0, 0])) # Projects view visible
    meta = h.store(bytes(48))
    h.u.mem_write(meta + 0x40 + 44, bytes([7])) # current project 7 in normal bank
    h.word(ctrl + 0x0C, shift)
    h.word(ctrl + 0x14, active_view)
    h.word(ctrl + 0x50, project_view)
    h.word(project_view + 0x20, meta)
    h.word(project_view + 0x0C, P + 0x38)
    h.word(project_view + 0x24, h.store(bytes([8, 0, 0, 0])))
    h.word(project_view + 0x28, h.store(bytes([0, 0, 0, 0])))
    h.u.mem_write(project_view + 0x36, b'\\x00')

    # Mock hardware LED boundary and action dispatch
    h.u.mem_write(0x0804F27E, bytes.fromhex('7047'))
    dispatched = []
    h.u.mem_write(0x08047038, bytes.fromhex('00207047')) # return 0 (success)
    h.u.hook_add(UC_HOOK_CODE, lambda u, a, s, d: dispatched.append((u.reg_read(UC_ARM_REG_R0), u.reg_read(UC_ARM_REG_R1))), begin=0x08047038, end=0x08047038)

    # 1. Trigger mode toggle via button pre-handler
    h.call(0x0803D8B8, ctrl, 18)
    target_slot = h.u.mem_read(SEQ_STATE_ADDR + 0x07, 1)[0]
    trans_state = h.u.mem_read(SEQ_STATE_ADDR + 0x05, 1)[0]

    blockers = []

    # Check 1: In-flight state machine armed
    if trans_state != 1:
        blockers.append({
            'id': 'transition_state_not_armed',
            'evidence': {'trans_state': trans_state},
            'risk': 'Mode toggle failed to initiate verified state machine (trans_state != 1).',
        })

    # Check 2: Action dispatched to correct Sequencer slot (32..63)
    if not (len(dispatched) == 1 and 32 <= dispatched[0][1] <= 63):
        blockers.append({
            'id': 'active_project_not_isolated',
            'evidence': {'dispatched': dispatched, 'target_slot': target_slot},
            'risk': 'Mode toggle does not dispatch Load/New to a separate project slot in bank 1.',
        })

    # 2. Complete load via stock completion callback
    store_44 = h.store(bytes(64))
    h.word(P + 0x44, store_44)
    h.u.reg_write(UC_ARM_REG_R4, P)
    h.u.reg_write(UC_ARM_REG_R5, target_slot)
    h.call(labels['c_proj_load_complete'], P, target_slot)

    enabled = h.u.mem_read(SEQ_STATE_ADDR + 4, 1)[0]
    final_page = h.u.mem_read(project_view + 0x36, 1)[0]
    final_trans = h.u.mem_read(SEQ_STATE_ADDR + 5, 1)[0]

    if enabled != 1 or final_trans != 0:
        blockers.append({
            'id': 'mode_transition_commit_failed',
            'evidence': {'enabled': enabled, 'trans_state': final_trans},
            'risk': 'Mode switch completion failed to commit seq_enabled = 1 or clear trans_state.',
        })

    if final_page != 1:
        blockers.append({
            'id': 'projects_visible_page_stale',
            'evidence': {'seq_enabled': enabled, 'page': final_page},
            'risk': 'Mode switch inside Projects leaves normal-bank pads actionable in Sequencer Mode.',
        })

    return blockers


"""

new_text = text[:start_idx] + new_func + text[end_idx:]
path.write_text(new_text, encoding='utf-8')
print("Updated verify_phase1_candidate.py with full release blockers check")
