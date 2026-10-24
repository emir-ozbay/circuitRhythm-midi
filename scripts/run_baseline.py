"""Run existing host-only firmware tests in an isolated build directory.
No MIDI/USB, firmware writes, uploads or network access.
"""
from pathlib import Path
import datetime,hashlib,importlib.metadata,json,os,platform,shutil,subprocess,sys,tempfile
ROOT=Path(__file__).resolve().parents[1]
EXPECTED='11d604a6b6bef0d41378da03718658c7fe9c959ac24e7fef6563796b9932afaf'
def main():
    if sys.flags.optimize:
        raise RuntimeError('Do not use Python -O: analysis checks use assert.')
    if sys.version_info<(3,10):raise RuntimeError('Python 3.10+ required; 3.11+ recommended.')
    stock=ROOT/'stock/circuitrhythm-firmware-5706.syx'
    if hashlib.sha256(stock.read_bytes()).hexdigest()!=EXPECTED:raise RuntimeError('Stock hash mismatch; stop.')
    import capstone,unicorn
    capstone_package=importlib.metadata.version('capstone')
    unicorn_package=importlib.metadata.version('unicorn')
    if capstone_package!='5.0.9' or unicorn_package!='2.1.4':
        raise RuntimeError('Install the pinned requirements.txt versions.')
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    logdir=ROOT/'logs'/('baseline-'+stamp);logdir.mkdir(parents=True)
    (ROOT/'build').mkdir(exist_ok=True)
    environment={'utc':stamp,'platform':platform.platform(),'python':sys.version,
        'capstone_package':capstone_package,'capstone_module':capstone.__version__,
        'unicorn_package':unicorn_package,'stock_sha256':EXPECTED,
        'physical_device_tested':False,'network_used_by_runner':False}
    (logdir/'environment.json').write_text(json.dumps(environment,indent=2),encoding='utf-8')
    with tempfile.TemporaryDirectory(prefix='baseline-',dir=ROOT/'build') as tmp:
        work=Path(tmp)
        shutil.copytree(ROOT/'analysis/sources',work/'sources',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        for name in ['verify_stock.py','test_long_pattern.py']:
            shutil.copy2(ROOT/'analysis'/name,work/name)
        env=dict(os.environ);env.pop('PYTHONOPTIMIZE',None);env['PYTHONUTF8']='1'
        for script in ['verify_stock.py','test_long_pattern.py']:
            result=subprocess.run([sys.executable,str(work/script),str(stock)],cwd=work,env=env,
                                  capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=180)
            (logdir/(script+'.log')).write_text(result.stdout+'\nSTDERR:\n'+result.stderr,encoding='utf-8')
            if result.returncode:
                raise RuntimeError(f'{script} failed ({result.returncode}); inspect {logdir}')
        for name in ['verification.json','long-pattern-results.json','selected-disassembly.txt']:
            shutil.copy2(work/name,logdir/name)
    a=json.loads((logdir/'verification.json').read_text());b=json.loads((logdir/'long-pattern-results.json').read_text())
    valid=(a['three_decoders_agree'] and a['two_encoders_byte_identical']
        and len(a['upstream_hook_checks'])==77 and all(x['pass'] for x in a['upstream_hook_checks'])
        and a['stock_step_setter_emulation']['cases_passed']==1536
        and a['midi_mask_dispatch_emulation']['cases_passed']==8
        and b['unsafe_direct_extension']['reproduced_cases']==96
        and b['host_page_adapter_editing']['cases_passed']==384
        and b['host_page_adapter_playback']['steps_verified']==128
        and b['stock_microstep_probability']['cases_passed']==3456)
    if not valid:raise RuntimeError('Results do not match expected baseline; inspect logs.')
    summary={'baseline':'PASS','physical_device_tested':False,'custom_firmware_built':False,
             'firmware_uploaded':False,'log_directory':str(logdir)}
    (logdir/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print('BASELINE PASS — host-only checks; no device accessed.')
    print(logdir)
    return 0
if __name__=='__main__':
    try:sys.exit(main())
    except Exception as exc:
        print('BASELINE FAILED: '+str(exc),file=sys.stderr);sys.exit(1)
