"""Freeze this turn's review bundle without modifying earlier evidence."""
from pathlib import Path
import json,hashlib,difflib,platform
import capstone,unicorn
from importlib.metadata import version
ROOT=Path(__file__).resolve().parents[1]
B=ROOT/'logs/recovery-load-short-read-20261031'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,data):
    p.parent.mkdir(parents=True,exist_ok=True)
    if p.exists():assert p.read_bytes()==data,p
    else:p.write_bytes(data)
def write(name,value):save(B/name,json.dumps(value,indent=2,ensure_ascii=False).encode())
def relative(p):return p.relative_to(ROOT).as_posix()
prior=json.loads((ROOT/'logs/recovery-running-edits-20261031/hashes.json').read_text())
old={Path(k).as_posix():v for k,v in json.loads((B/'before.json').read_text()).items()}
new=['src/project_load_guard_patch.py','scripts/recovery_load_test_support.py','scripts/probe_recovery_load.py',
     'tests/test_project_load_guard.py','tests/test_recovery_load.py']
pins=dict(prior['source_pins_after'])
assert len(pins)==201
modified=[k for k,v in pins.items() if sha(ROOT/k)!=v]
all_py=list((ROOT/'logs').rglob('*.py'))
for name in modified:
    before=B/'before'/name
    if not before.exists():
        source=next(p for p in all_py if p.name==Path(name).name and sha(p)==pins[name])
        save(before,source.read_bytes())
    assert sha(before)==pins[name]
for name in list(pins)+new:pins[name]=sha(ROOT/name)
assert len(pins)==206 and len(modified)==6
immutable={k:sha(ROOT/k) for k in prior['evidence_sha256']}
assert immutable==prior['evidence_sha256']
for name,source in (('docs/STATUS.md','STATUS-before.md'),('CHANGELOG.md','CHANGELOG-before.md')):
    save(B/'before'/name,(B/source).read_bytes())
docs=['docs/STATUS.md','CHANGELOG.md','docs/MIDI-RECOVERY-LOAD-SHORT-READ-5706.md',
      'docs/ROADMAP.md','docs/RECOVERY.md','docs/UI-TRACE-5706.md','docs/PROJECT-LOAD-ALIAS-RISK.md',
      'docs/MIDI-RECOVERY-CANDIDATE-5706.md','docs/PHASE1-GO-GATES.md','docs/PHASE1-HARDWARE-TEST.md']
build=['build/circuitrhythm-5706-phase1-recovery'+ext for ext in ('.syx','.manifest.json','.scope.json')]
artifacts=modified+new+docs+build
for name in artifacts:save(B/'after'/name,(ROOT/name).read_bytes())
diff=[]
for name in modified+new+docs:
    before=B/'before'/name
    a=before.read_text(encoding='utf-8').splitlines(True) if before.exists() else []
    b=(ROOT/name).read_text(encoding='utf-8').splitlines(True)
    diff.extend(difflib.unified_diff(a,b,fromfile='before/'+name,tofile='after/'+name))
save(B/'changes.diff',''.join(diff).encode())
import sys
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'src')]
from patch_firmware import unpack_syx
old_syx=B/'before-build/circuitrhythm-5706-phase1-recovery.syx'
new_syx=ROOT/build[0]
assert sha(old_syx)=='c9a87a9d4c4849e854114d57ea56320591d653eee274c10b68796c4895beaf96'
assert sha(new_syx)=='272a8128ba159e32c7457f0f123cb148c9e2d93a7803cbd9be327dccc5bb5cc1'
a=unpack_syx(old_syx.read_bytes(),allow_extended=True)['image']
b=unpack_syx(new_syx.read_bytes(),allow_extended=True)['image']
assert a[:512]==b[:512] and len(a)==len(b)==458552
changes=[];i=0
while i<len(a):
    if a[i]==b[i]:i+=1;continue
    start=i
    while i<len(a) and a[i]!=b[i]:i+=1
    changes.append(dict(start_address=hex(0x08010000+start),length=i-start,old=a[start:i].hex(),new=b[start:i].hex()))
write('image-diff.json',dict(before_sha256=hashlib.sha256(a).hexdigest(),after_sha256=hashlib.sha256(b).hexdigest(),
    changed_bytes=sum(r['length'] for r in changes),ranges=changes,vector_preserved=True))
runs=[json.loads((B/f'probe-{n}/report.json').read_text()) for n in ('normal','sequencer')]
reg=json.loads((B/'regression/report.json').read_text());audit=json.loads((B/'audit-final/report.json').read_text())
assert reg['tests']==31 and len(reg['criteria'])==6 and audit['patches']==46
assert all(r['syx_sha256']==sha(new_syx) and r['cycles']==216 for r in runs)
write('environment.json',dict(python=platform.python_version(),capstone=capstone.__version__,unicorn=unicorn.__version__,
    assertions_enabled=__debug__,device_apis_accessed=False))
write('environment-distributions.json',dict(capstone=version('capstone'),unicorn=version('unicorn'),
    note='Capstone5.0.9 distribution reports module __version__5.0.7;requirements pins are distribution versions. Initial finalizer assumption rejected;no firmware/test result changed.'))
assert __debug__ and version('capstone')=='5.0.9' and version('unicorn')=='2.1.4'
summary=dict(date='2026-11-01',bundle_started='2026-10-31',hardware_release='NO-GO',firmware_changed=True,
    device_apis_accessed=False,old_candidate_syx_sha256=sha(old_syx),current_syx_sha256=sha(new_syx),
    current_image_sha256=hashlib.sha256(b).hexdigest(),crc='985753F7',patches=46,changed_bytes_from_stock=8009,
    separate_packaged_tests_on_current_image=33,scoped_phase1_criteria=6,targeted_tests=31,
    native_load_modes=[dict(mode=r['mode'],cycles=r['cycles'],timer_events=r['timer_events'],reads=r['read_results'],
        after=dict(phase=r['final']['phase'],flags=r['final']['project_flags'],taint=r['final']['taint']),
        changed_offsets=r['changed_offsets'],step0=r['step0']) for r in runs],
    old_image_tests_not_carried_forward=159,full_suite_executed=False,
    suite_collection=json.loads((B/'suite-layout.json').read_text()),excluded=reg['excluded'],
    cave_bytes=152,wrapper_stack_bytes=32,additional_reserved_ram_bytes=0,application_ram_repaired=False,
    rollback=False,native_eof_or_physical_fault=False,
    next_task='Tainted native session:stock Projects/Load/New reachability and safe taint-clearing boundary after a complete successful reload;no RAM repair.',
    limits=['741B lower-read request limit is an explicit synthetic input;native FatFs supplies bytes/count and4113A produces4.',
            'Partial live alias mutation remains;Play/Save/other readers and complete recovery are not proved.',
            'Native Save/Load backend adapters;not full Projects/GPIO input queue or physical delivery.',
            'Tie UI/Load,RX–MSC–power,worst resources and full new-image M7 regression remain open.'])
write('summary.json',summary)
hashes=dict(date='2026-11-01',hardware_release='NO-GO',firmware_changed=True,device_apis_accessed=False,
    current_syx_sha256=sha(new_syx),current_image_sha256=hashlib.sha256(b).hexdigest(),crc='985753F7',
    source_pins_after=pins,modified_source_pins={k:pins[k] for k in modified},
    unchanged_source_pins=len(prior['source_pins_after'])-len(modified),new_source_pins={k:pins[k] for k in new},
    files_after_sha256={name:sha(ROOT/name) for name in artifacts},
    previous_immutable_evidence_verified=len(immutable),
    evidence_sha256={relative(p):sha(p) for p in B.rglob('*') if p.is_file() and p.name!='hashes.json'},
    execution_scripts_sha256={relative(p):sha(p) for p in (ROOT/'scratch').glob('*load*.py')})
write('hashes.json',hashes)
print(json.dumps(dict(source_pins=len(pins),changed_sources=len(modified),evidence=len(hashes['evidence_sha256']),
    prior_immutable=len(immutable),distinct_packaged_tests=33,hardware_release='NO-GO')))
