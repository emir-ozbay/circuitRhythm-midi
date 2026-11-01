"""Freeze the current candidate and all prior evidence before recovery changes."""
from pathlib import Path
import json,hashlib
R=Path(__file__).resolve().parents[1];B=R/'logs/recovery-load-recovery-20261101'
B.mkdir(exist_ok=False)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
p=json.loads((R/'logs/recovery-load-reentry-20261101/hashes.json').read_text())
groups=('source_pins_after','files_after_sha256','unchanged_build_sha256','evidence_sha256','execution_scripts_sha256')
for g in groups:
    for n,d in p[g].items():assert sha(R/n)==d,(g,n)
names=list(dict.fromkeys(list(p['source_pins_after'])+list(p['files_after_sha256'])+list(p['unchanged_build_sha256'])))
for n in names:
    q=B/'before'/n;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes((R/n).read_bytes())
(B/'before.json').write_text(json.dumps({n:sha(R/n) for n in names},indent=2))
(B/'previous-evidence.json').write_text(json.dumps(p['evidence_sha256'],indent=2))
print(dict(files=len(names),prior_evidence=len(p['evidence_sha256'])))
