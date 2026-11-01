"""Immutable baseline for the native Load re-entry investigation."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
B=ROOT/'logs/recovery-load-reentry-20261101'
B.mkdir(exist_ok=False)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
prior=json.loads((ROOT/'logs/recovery-load-short-read-20261031/hashes.json').read_text())
for group in ('source_pins_after','files_after_sha256','evidence_sha256','execution_scripts_sha256'):
    for name,digest in prior[group].items():assert sha(ROOT/name)==digest,(group,name)
names=list(dict.fromkeys(list(prior['source_pins_after'])+list(prior['files_after_sha256'])))
for name in names:
    p=B/'before'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((ROOT/name).read_bytes())
(B/'before.json').write_text(json.dumps({name:sha(ROOT/name) for name in names},indent=2))
(B/'previous-evidence.json').write_text(json.dumps(prior['evidence_sha256'],indent=2))
assert sha(ROOT/'stock/circuitrhythm-firmware-5706.syx')=='11d604a6b6bef0d41378da03718658c7fe9c959ac24e7fef6563796b9932afaf'
print(json.dumps(dict(baseline_files=len(names),previous_evidence_verified=len(prior['evidence_sha256']))))
