"""Replace obsolete verification contracts with shared-project checks."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
p = ROOT / 'scripts/verify_phase1_candidate.py'
s = p.read_text(encoding='utf-8')
a = s.index('def run_criterion_1_mode_toggle(')
b = s.index('\ndef run_criterion_2_', a)
s = s[:a] + '''def run_criterion_1_mode_toggle(image: bytes, labels: dict[str, int]) -> dict:
    """Real button dispatch, no deferred Load completion or storage API stubs."""
    from shared_project_test_support import SharedModeFixture
    h = EmulatorHarness(image, labels)
    f = SharedModeFixture(h)
    calls = []
    for address in (0x08047038, 0x08037BD6, 0x08037ED0, 0x08047288, 0x080472E2):
        h.u.hook_add(UC_HOOK_CODE, lambda u,a,z,d: calls.append(a), begin=address, end=address)
    before = bytes(h.u.mem_read(f.meta, 0x100))
    for mode in (1, 0):
        f.press()
        assert h.u.mem_read(SEQ_STATE_ADDR + 4, 1) == bytes([mode])
        assert bytes(h.u.mem_read(f.meta, 0x100)) == before
        f.release()
    f.set_byte(f.transport, 0, 1)
    f.press()
    assert h.u.mem_read(SEQ_STATE_ADDR + 4, 1) == bytes(1)
    assert calls == []
    return {"status": "PASS", "details": "Same-project toggle through real stock button ownership; metadata preserved; zero project actions. Running transport refuses toggle."}

''' + s[b+1:]
a = s.index('def run_criterion_5_independent_projects_and_packs_lock(')
b = s.index('\ndef run_criterion_6_', a)
s = s[:a] + '''def run_criterion_5_shared_projects(image: bytes, labels: dict[str, int]) -> dict:
    from shared_project_test_support import SharedModeFixture
    h = EmulatorHarness(image, labels)
    f = SharedModeFixture(h)
    h.u.mem_write(0x0804F27E, bytes.fromhex("7047"))  # LED output boundary
    h.word(f.view + 0x1C, h.store(bytes(4)))
    for mode in (0, 1):
        h.u.mem_write(SEQ_STATE_ADDR + 4, bytes([mode]))
        for slot in range(64):
            f.set_byte(f.meta, 44, slot)
            h.call(0x0804F080, f.view)
            assert h.u.mem_read(f.view + 0x36, 1)[0] == slot >> 5
            for button, page in ((19, 1), (20, 0)):
                h.call(0x0804F12C, f.view, button)
                assert h.u.mem_read(f.view + 0x36, 1)[0] == page
    stock = load_image()
    assert image[0x2DB54:0x2DB60] == stock[0x2DB54:0x2DB60]
    assert image[0x3ED60:0x3F3F0] == stock[0x3ED60:0x3F3F0]
    return {"status": "PASS", "details": "Both modes share64 stock project slots; page selection follows active slot, both page buttons work; Projects/Save/Packs code is byte-identical to stock."}

''' + s[b+1:]
a = s.index('def release_blockers(')
b = s.index('\ndef main()', a)
s = s[:a] + '''def release_blockers(image: bytes, labels: dict[str, int]) -> list[dict]:
    """Honest remaining obligations; shared mode no longer triggers project I/O."""
    return [
        {'id': 'runtime_midi_transport_unproven',
         'risk': 'Stopped/idle/controller-note/grid ownership guards pass synthetic RAM tests. UART/USB ingress, external clock races, all MIDI ownership filters, output queue and Stop lifecycle still need integrated proof.'},
        {'id': 'stock_storage_failure_behavior_unresolved',
         'risk': 'Project/storage code is restored byte-for-byte to stock and mode toggle performs zero I/O. The previously demonstrated stock partial-read/live-pattern alias is not repaired; stock error/recovery behavior remains an inherited data-loss risk.'},
        {'id': 'allocator_boot_timing_unproven',
         'risk': 'Heap reservation and overflow guards pass isolated tests; full boot/OOM caller handling and the PRIMASK timing budget on the actual task/ISR graph remain unproven.'},
    ]

''' + s[b+1:]
s = s.replace('run_criterion_5_independent_projects_and_packs_lock', 'run_criterion_5_shared_projects')
s = s.replace('Testing Criterion 5: Independent 32 Projects & Packs View Lock', 'Testing Criterion 5: Shared64 Stock Projects & Page Buttons')
s = s.replace('"test_scope_warning": "Mode completion is injected in component tests. Read/Close regressions explicitly bypass the containment hook in emulator RAM. Neither demonstrates functional production Load or boot.",',
              '"test_scope_warning": "Synthetic controller/store RAM, real button ownership; no Load-completion injection. Projects/storage byte identity is not proof against inherited stock media failures or full boot.",')
p.write_text(s, encoding='utf-8')
print('Shared-project verifier criteria prepared.')
