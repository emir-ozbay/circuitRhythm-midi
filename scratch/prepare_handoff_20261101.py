"""Read-only firmware reconciliation and immutable handoff snapshot; no tests/build."""
from pathlib import Path
import ast, difflib, hashlib, json, sys
R=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(R/'scripts'))
from patch_firmware import unpack_syx, STOCK_SYX_SHA256
B=R/'logs/handoff-20261101-load-recovery'
B.mkdir(exist_ok=False)
def sha(data):return hashlib.sha256(data).hexdigest()
def digest(name):return sha((R/name).read_bytes())
old=json.loads((R/'logs/recovery-load-recovery-20261101/before.json').read_text())
evidence=json.loads((R/'logs/recovery-load-recovery-20261101/previous-evidence.json').read_text())
for n,d in evidence.items():assert digest(n)==d,n
for n,d in old.items():
    assert sha((R/'logs/recovery-load-recovery-20261101/before'/n).read_bytes())==d,n
new=['src/project_load_recovery_patch.py','scripts/recovery_load_recovery_test_support.py','tests/test_project_load_recovery.py']
names=sorted(set(old)|set(new))
pins={n:digest(n) for n in names}
for n in names:
    p=B/'snapshot'/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((R/n).read_bytes())
changed=[n for n in old if pins[n]!=old[n]]
diff=[]
for n in changed+new:
    before=(R/'logs/recovery-load-recovery-20261101/before'/n).read_text(encoding='utf-8').splitlines(True) if n in old else []
    diff.extend(difflib.unified_diff(before,(R/n).read_text(encoding='utf-8').splitlines(True),fromfile='before/'+n,tofile='current/'+n))
(B/'work-in-progress.diff').write_text(''.join(diff),encoding='utf-8')
stock=(R/'stock/circuitrhythm-firmware-5706.syx').read_bytes();assert sha(stock)==STOCK_SYX_SHA256
raw=(R/'build/circuitrhythm-5706-phase1-recovery.syx').read_bytes()
parsed=unpack_syx(raw,allow_extended=True);stock_image=unpack_syx(stock)['image']
manifest=json.loads((R/'build/circuitrhythm-5706-phase1-recovery.manifest.json').read_text())
assert sha(raw)==manifest['output']['sha256'] and sha(parsed['image'])==manifest['output']['image_sha256']
assert parsed['crc']==int(manifest['output']['image_crc32_mpeg2'],16)
assert parsed['image'][:512]==stock_image[:512]
assert all(pins[n]==old[n] for n in old if n.startswith('build/'))
source_pins={n:d for n,d in pins.items() if n.startswith(('src/','scripts/','tests/'))}
source_id=sha(json.dumps(source_pins,sort_keys=True,separators=(',',':')).encode())
tree=ast.parse((R/new[-1]).read_text())
tests=[n.name for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name.startswith('test_')]
report=dict(date='2026-11-01',purpose='handoff only',hardware_release='NO-GO',
    firmware_build_executed=False,tests_executed=False,device_access=False,
    stock_sha256=sha(stock),candidate_syx_sha256=sha(raw),candidate_image_sha256=sha(parsed['image']),
    candidate_crc=f'{parsed["crc"]:08X}',candidate_patches=manifest['patches_count'],
    candidate_changed_bytes=manifest['total_bytes_changed'],candidate_matches_before_snapshot=True,
    source_fingerprint_sha256=source_id,source_pins=source_pins,snapshot_pins=pins,
    changed_since_before=changed,new_since_before=new,
    historical_evidence_files_verified=len(evidence),before_snapshot_files_verified=len(old),
    new_synthetic_test_methods=tests,
    synthetic_result_provenance='Four PASS reported in earlier conversation tool output; no persisted run report found. Not rerun for handoff; not exact-SYX/native evidence.',
    current_native_recovery_evidence='None: new helper/test not executed and current source not packaged.',
    previous_canonical_reports=[f'logs/recovery-load-reentry-20261101/probe-{mode}-final/report.json' for mode in ('normal','sequencer')])
(B/'reconciliation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k not in ('source_pins','snapshot_pins')},indent=2))
