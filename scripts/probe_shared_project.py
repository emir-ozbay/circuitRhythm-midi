"""Same-project mode-toggle preservation, with real constructors/button dispatch.

Synthetic controller/store RAM; no Load completion injection or storage stubs.
The historical alias corruption experiment in probe_project_alias.py is retained.
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'tests'), str(ROOT / 'scripts')]
import test_phase1_safety as base
from project_alias_test_support import ProjectAliasFixture, STORE_LEN
from shared_project_test_support import SharedModeFixture


def probe(image=None, labels=None):
    h = base.SafetyTests()
    if image is None:
        h.setUpClass()
    else:
        assert labels is not None
        h.image, h.labels = image, labels
    h.setUp()
    alias = ProjectAliasFixture(h)
    f = SharedModeFixture(h, ctrl=0x2000B800, view=0x2000C000, grid=0x2000C800)
    h.u.mem_write(alias.patterns[0], bytes([60]))
    before = bytes(h.u.mem_read(alias.raw, STORE_LEN))
    metadata = bytes(h.u.mem_read(f.meta, 0x100))
    project = bytes(h.u.mem_read(alias.p, 0x100))
    calls, modes = [], []
    for address in (0x08047038, 0x08037B8C, 0x08037BD6, 0x08037ED0,
                    0x08047288, 0x080472E2, 0x0804113A, 0x080411D8, 0x08041906):
        h.u.hook_add(base.UC_HOOK_CODE, lambda u,a,z,d: calls.append(hex(a)), begin=address, end=address)
    for _ in range(2):
        f.press()
        modes.append(h.u.mem_read(base.seq.SEQ_STATE_ADDR + 4, 1)[0])
        f.release()
    raw_preserved = bytes(h.u.mem_read(alias.raw, STORE_LEN)) == before
    context_preserved = (bytes(h.u.mem_read(f.meta, 0x100)) == metadata
                         and bytes(h.u.mem_read(alias.p, 0x100)) == project)
    passed = raw_preserved and context_preserved and modes == [1, 0] and not calls
    return {
        'mode_toggle_preservation': 'PASS' if passed else 'FAIL',
        'hardware_release': 'NO-GO',
        'scope': 'synthetic RAM; real constructors/button ownership; no storage stubs',
        'mode_sequence': modes,
        'project_raw': hex(alias.read(alias.p + 0x14)),
        'raw_length': STORE_LEN,
        'entire_raw_buffer_preserved': raw_preserved,
        'metadata_and_controller_preserved': context_preserved,
        'recorder_pattern_bases': [hex(p) for p in alias.patterns],
        'pattern_note_after_toggle': h.u.mem_read(alias.patterns[0], 1)[0],
        'project_io_calls': calls,
        'stock_storage_failure_risk_resolved': False,
        'open_requirement': 'External MIDI/transport races, stock storage errors, boot/OOM and timing remain unproven.',
    }


if __name__ == '__main__':
    result = probe()
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['mode_toggle_preservation'] == 'PASS' else 1)
