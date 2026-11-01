"""Replay the unchanged alias counterexample against its archived firmware source.

Builds only in host memory; never changes the current candidate or opens devices.
Exit1 intentionally confirms the historical critical corruption counterexample.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tests'), str(ROOT / 'scripts')]


def main():
    archived = ROOT / 'analysis/historical-bank-isolation/probe_project_alias.py'
    original = ROOT / 'scripts/probe_project_alias.py'
    assert archived.read_bytes() == original.read_bytes(), 'Historical probe changed'
    import test_phase1_safety as base
    from inspect_ui import load_image
    from patch_firmware import apply_patches
    spec = importlib.util.spec_from_file_location(
        'historical_bank_seq', ROOT / 'analysis/historical-bank-isolation/seq_Patch.py')
    seq = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = seq
    spec.loader.exec_module(seq)
    image = apply_patches(load_image(), seq.build_phase1_patches())[0]
    labels = seq.arm_code()[1]
    # SafetyTests uses these constants for stack/state setup. Only this short-lived
    # Python process changes its module binding; no file or packaged image changes.
    base.seq = seq
    spec = importlib.util.spec_from_file_location('historical_alias', archived)
    probe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(probe)
    result = probe.probe(image, labels, bypass_containment=True)
    result['historical_image_sha256'] = hashlib.sha256(image).hexdigest()
    result['historical_probe_sha256'] = hashlib.sha256(archived.read_bytes()).hexdigest()
    result['current_candidate_not_modified'] = True
    print(json.dumps(result, indent=2))
    assert result['live_pattern_corrupted_without_apply'], 'Counterexample did not reproduce'
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
