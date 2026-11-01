"""Pin this investigation; never overwrite earlier evidence bundles."""
from pathlib import Path
import json,hashlib,difflib,sys,platform
from importlib.metadata import version
ROOT=Path(__file__).resolve().parents[1]
B=ROOT/'logs/recovery-load-reentry-20261101'
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'src')]
from patch_firmware import unpack_syx
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,data):
    p.parent.mkdir(parents=True,exist_ok=True)
    if p.exists():assert p.read_bytes()==data,p
    else:p.write_bytes(data)
def write(name,value):save(B/name,json.dumps(value,indent=2,ensure_ascii=False).encode())
def relative(p):return p.relative_to(ROOT).as_posix()
prior=json.loads((ROOT/'logs/recovery-load-short-read-20261031/hashes.json').read_text())
before=json.loads((B/'before.json').read_text())
for name,digest in before.items():assert sha(B/'before'/name)==digest,name
for name,digest in prior['evidence_sha256'].items():assert sha(ROOT/name)==digest,name
raw=(ROOT/'build/circuitrhythm-5706-phase1-recovery.syx').read_bytes()
image=unpack_syx(raw,allow_extended=True)['image']
assert hashlib.sha256(raw).hexdigest()==prior['current_syx_sha256']=='272a8128ba159e32c7457f0f123cb148c9e2d93a7803cbd9be327dccc5bb5cc1'
assert hashlib.sha256(image).hexdigest()==prior['current_image_sha256']=='dcc89001f753947acf8873c10b594b9386c5389b2d7e76c1097a6a6082e1791e'
assert sha(ROOT/'stock/circuitrhythm-firmware-5706.syx')=='11d604a6b6bef0d41378da03718658c7fe9c959ac24e7fef6563796b9932afaf'
for name,digest in before.items():
    if name.startswith(('src/','build/')):assert sha(ROOT/name)==digest,name
runs=[json.loads((B/f'{name}/report.json').read_text()) for name in ('probe-normal-final','probe-sequencer-final')]
boundaries=[]
for mode,r in enumerate(runs):
    assert r['mode']==mode and r['packaged_tests']==1
    assert r['syx_sha256']==prior['current_syx_sha256'] and r['image_sha256']==prior['current_image_sha256']
    assert r['setup']['cycles']==216 and r['total_cycles']==r['timer_events']
    assert len(r['ui_rejected'])==len(r['diagnostic_view_rejected'])==2
    assert not r['application_ram_repaired'] and not r['taint_cleared'] and not r['ui_quarantine_recovery']
    assert len(r['setup']['uart']['interrupts'])==r['setup']['uart']['used_credits']
    assert len(r['uart']['interrupts'])==r['uart']['used_credits']
    stages={stage:[e for e in r['events'] if e['stage']==stage] for stage in
        ('diagnostic_backend_full_reload','ui_full_reload','ui_new_empty_slot')}
    rows=[]
    for stage,events in stages.items():
        selected=[]
        for pc in (0x08037E3C,0x080379B2,0x08037E7E,0x08038798):
            hits=[e for e in events if e['pc']==pc]
            assert len(hits)==1,(stage,hex(pc),len(hits))
            e=hits[0];s=e['state'];assert s['taint']==1 and s['transport']==0
            assert s['phase']==(0 if pc==0x08038798 else 2)
            assert s['project_flags']==(0 if pc==0x08038798 else 3)
            if stage!='ui_new_empty_slot':assert s['raw_sha256']==r['setup']['saved']['raw_sha256']
            selected.append(dict(pc=hex(pc),cycle=e['cycle'],phase=s['phase'],flags=s['project_flags'],taint=s['taint'],raw_sha256=s['raw_sha256']))
        rows.append(dict(stage=stage,boundaries=selected))
    boundaries.append(dict(mode=mode,observations=rows))
write('apply-boundaries.json',boundaries)
assert __debug__ and version('capstone')=='5.0.9' and version('unicorn')=='2.1.4'
write('environment.json',dict(python=platform.python_version(),capstone_distribution=version('capstone'),
    unicorn_distribution=version('unicorn'),assertions_enabled=__debug__,device_apis_accessed=False))
new=['scripts/recovery_load_reentry_test_support.py','scripts/probe_recovery_load_reentry.py','tests/test_recovery_load_reentry.py']
pins=dict(prior['source_pins_after'])
modified=[name for name,digest in pins.items() if sha(ROOT/name)!=digest]
assert set(modified)=={'scripts/recovery_load_test_support.py','scripts/verify_recovery_candidate.py'},modified
for name in list(pins)+new:pins[name]=sha(ROOT/name)
docs=['docs/STATUS.md','CHANGELOG.md','docs/MIDI-RECOVERY-LOAD-REENTRY-5706.md','docs/ROADMAP.md',
      'docs/RECOVERY.md','docs/UI-TRACE-5706.md']
artifacts=modified+new+docs
diff=[]
for name in artifacts:
    save(B/'after'/name,(ROOT/name).read_bytes())
    p=B/'before'/name
    a=p.read_text(encoding='utf-8').splitlines(True) if p.exists() else []
    b=(ROOT/name).read_text(encoding='utf-8').splitlines(True)
    diff.extend(difflib.unified_diff(a,b,fromfile='before/'+name,tofile='after/'+name))
save(B/'changes.diff',''.join(diff).encode())
summary=dict(date='2026-11-01',hardware_release='NO-GO',firmware_changed=False,device_apis_accessed=False,
    current_syx_sha256=prior['current_syx_sha256'],current_image_sha256=prior['current_image_sha256'],crc='985753F7',
    canonical_tests=2,new_distinct_tests=2,cumulative_distinct_tests_same_image=35,
    passing_test_executions_including_superseded_reports=4,
    previous_tests_same_image_not_all_rerun=33,scoped_phase1_criteria_this_run=0,previous_scoped_criteria_same_image=6,
    full_suite_executed=False,suite_collection=json.loads((B/'suite-layout.json').read_text()),
    audit=json.loads((B/'audit/report.json').read_text())['transport'],
    native_modes=[dict(mode=r['mode'],cycles=r['cycles'],setup_cycles=r['setup']['cycles'],total_cycles=r['total_cycles'],
        timer_events=r['timer_events'],ui_rejections=len(r['ui_rejected']),diagnostic_view_rejections=len(r['diagnostic_view_rejected']),
        mode_rejections=len(r['rejected_shortcuts']),read_results=r['read_results'],
        restored=r['diagnostic_backend_restored'],created=r['ui_created'],final=r['final']) for r in runs],
    failed_hypotheses=['Initial pilot assumed controller pads reached Projects at flags3;stock3D814 rejects bit1 first.',
        'Next Normal/Sequencer pilots expected explicit Close after successful Load;stock successful bridge/apply does not call41906 in the observed window. Not a proven leak.'],
    failed_pilot_runs=3,failed_pilots_preserved=True,
    superseded_passing_reports='probe-normal-v3/probe-sequencer-v2 passed assertions but setup UART IRQ list retained later events (96 credit snapshot/328 events). Native outcomes unchanged. Deep-copy snapshot added and both modes rerun as canonical final probes.',
    application_ram_repaired=False,taint_cleared=False,ui_quarantine_recovery=False,
    next_task='Implement and natively verify a narrowly admitted stock Load/New recovery path after confirmed Close,remaining quarantined on retry failure;no host RAM repair.',
    limits=['Finite peripheral/native ARM emulation;one synthetic741B lower-read input per boot,not natural EOF/card fault.',
            'Controller vtable input bypasses GPIO/event scanning. Direct Projects handler/backend probes bypass UI gates and are explicitly diagnostic.',
            'Complete read/default construction and native apply establish data replacement boundaries,not a proven taint-clearing protocol.',
            'Partial raw aliases,other readers,Play/Save,combined RX–MSC–power,worst resources and full M7 remain open.'])
write('summary.json',summary)
hashes=dict(date='2026-11-01',firmware_changed=False,hardware_release='NO-GO',
    current_syx_sha256=prior['current_syx_sha256'],current_image_sha256=prior['current_image_sha256'],crc='985753F7',
    source_pins_after=pins,modified_source_pins={k:pins[k] for k in modified},new_source_pins={k:pins[k] for k in new},
    unchanged_source_pins=len(prior['source_pins_after'])-len(modified),
    files_after_sha256={name:sha(ROOT/name) for name in artifacts},
    unchanged_build_sha256={name:sha(ROOT/name) for name in before if name.startswith('build/')},
    previous_immutable_evidence_verified=len(prior['evidence_sha256']),
    evidence_sha256={relative(p):sha(p) for p in B.rglob('*') if p.is_file() and p.name!='hashes.json'},
    execution_scripts_sha256={relative(ROOT/'scratch'/name):sha(ROOT/'scratch'/name) for name in
        ('prepare_load_reentry.py','count_load_reentry_suite.py','finalize_load_reentry.py','update_load_reentry_docs.py')})
write('hashes.json',hashes)
print(json.dumps(dict(tests=2,cumulative_tests=35,firmware_changed=False,source_pins=len(pins),previous_evidence=len(prior['evidence_sha256']),hardware_release='NO-GO')))
