"""Offline counterexample at the completion boundary; not a storage replay.

Two Save snapshots use the same P/slot. Injecting an old acknowledgement after
the second snapshot demonstrates that this boundary carries no generation ID.
Whether the real storage queue can deliver that sequence remains unproven.
Exit 1 deliberately retains NO-GO; this is not part of the passing unit suite.
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'tests'), str(ROOT / 'scripts')]
import test_phase1_safety as base


def probe():
    h = base.SafetyTests()
    h.setUpClass()
    h.setUp()
    state, p, slot = base.seq.SEQ_STATE_ADDR, 0x20006000, 7
    meta = h.store(bytes(64))
    h.u.mem_write(state + base.seq.OFF_PROJECT_DIRTY, b'\x01')
    h.call(0x08037ED0, p, slot, 0, end=0x08037ED4)
    first = (h.read(state + base.seq.OFF_SAVE_OWNER), h.u.mem_read(state + base.seq.OFF_SAVE_SLOT, 1)[0])
    # A real dirty hook runs at the entry of a pattern commit; stop before the
    # store continuation because this probe concerns transaction identity only.
    listener, store = 0x20005000, 0x20005500
    h.word(listener + 0x1C, store)
    h.call(0x08048208, listener, store, 1, end=0x0804820C)
    h.call(0x08037ED0, p, slot, 0, end=0x08037ED4)
    second = (h.read(state + base.seq.OFF_SAVE_OWNER), h.u.mem_read(state + base.seq.OFF_SAVE_SLOT, 1)[0])
    h.u.reg_write(base.UC_ARM_REG_R5, p)
    h.u.reg_write(base.UC_ARM_REG_R6, slot)
    h.call(h.labels['c_proj_save_complete'], meta)
    dirty = h.u.mem_read(state + base.seq.OFF_PROJECT_DIRTY, 1)[0]
    return {
        'decision': 'NO-GO',
        'scope': 'synthetic completion-boundary injection; no actual storage queue',
        'first_identity': [hex(first[0]), first[1]],
        'second_identity': [hex(second[0]), second[1]],
        'identities_equal': first == second,
        'dirty_after_injected_old_ack': dirty,
        'hazard_at_boundary': first == second and dirty == 0,
        'open_proof': 'Establish exactly-once terminal delivery and serialization in the real request queue, or carry immutable per-request identity through that queue. A local counter alone cannot identify this callback.',
    }


if __name__ == '__main__':
    result = probe()
    print(json.dumps(result, indent=2))
    raise SystemExit(1)
