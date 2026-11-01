"""NO-GO containment probe, with an explicit uncontained counterexample option.

Real stock spans/recorder constructors, read/result FIFOs and error cleanup run.
File API and scheduler are stubs; success apply is an observed boundary stub.
This does not claim an actual physical SD failure occurred. Exit 0 proves only
that containment prevented I/O and preserved this buffer, not functional GO.
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'tests'), str(ROOT / 'scripts')]
import test_phase1_safety as base
from project_alias_test_support import ProjectAliasFixture, STORE_LEN, PATTERN_OFFSET
from storage_queue_test_support import StorageQueueFixture


def probe(image=None, labels=None, *, bypass_containment=False):
    h = base.SafetyTests()
    if image is None:
        h.setUpClass()
    else:
        assert labels is not None
        h.image, h.labels = image, labels
    h.setUp()
    alias = ProjectAliasFixture(h)
    q = StorageQueueFixture(h, base=0x20001000)
    q.blob = alias.raw
    commits = []
    h.u.mem_write(base.seq.STOCK_LOAD_SUCCESS, bytes.fromhex('7047'))
    h.u.hook_add(base.UC_HOOK_CODE, lambda u,a,z,d: commits.append(a), begin=base.seq.STOCK_LOAD_SUCCESS, end=base.seq.STOCK_LOAD_SUCCESS)
    note_address = alias.patterns[0]
    h.u.mem_write(note_address, b'\x3c')
    before = h.u.mem_read(note_address, 1)[0]
    raw_before = bytes(h.u.mem_read(alias.raw, STORE_LEN))
    q.begin_project_load(project_kwargs={'p': alias.p, 'ctrl': 0x2000B800, 'view': 0x2000C000}, bypass_containment=bypass_containment)
    q.read_payload = b'\x22' * (PATTERN_OFFSET + 1)
    q.work(read_result=4)
    q.deliver()
    q.work()
    q.deliver()
    after = h.u.mem_read(note_address, 1)[0]
    tainted = h.u.mem_read(base.seq.SEQ_STATE_ADDR + base.seq.OFF_PROJECT_TAINTED, 1)[0]
    # A clean rejected Load must not invoke a real Save with this minimal fixture.
    save_rejected = h.call(0x08037ED0, alias.p, 0, 0) == 1 if tainted else None
    return {
        'decision': 'NO-GO',
        'containment_bypassed_for_counterexample': bypass_containment,
        'file_read_api_calls': q.read_api_calls,
        'entire_raw_buffer_preserved': bytes(h.u.mem_read(alias.raw, STORE_LEN)) == raw_before,
        'load_functionality_available': False,
        'scope': 'synthetic RAM; stock constructors and queues; partial-read API stub',
        'project_raw': hex(alias.read(alias.p + 0x14)),
        'raw_length': STORE_LEN,
        'recorder_pattern_bases': [hex(p) for p in alias.patterns],
        'pattern_note_before': before,
        'pattern_note_after_failed_load': after,
        'apply_calls': len(commits),
        'save_after_failed_load_rejected': save_rejected,
        'project_tainted': tainted,
        'main_sram_model_bytes': 0x50000,
        'two_full_project_buffers_bytes': 2 * STORE_LEN,
        'transition_after_error': h.u.mem_read(base.seq.SEQ_STATE_ADDR + base.seq.OFF_TRANS_STATE, 1)[0],
        'live_pattern_corrupted_without_apply': before != after and not commits,
        'open_requirement': 'Production Load is disabled before read/New; safe transactional Load and boot integration are still required. This is containment, not functional acceptance.',
    }


if __name__ == '__main__':
    result = probe()
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['entire_raw_buffer_preserved'] and result['file_read_api_calls'] == 0 else 1)
