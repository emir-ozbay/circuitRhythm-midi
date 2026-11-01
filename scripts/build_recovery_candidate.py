"""Offline integrated Off/Stop candidate;never transmits to a device."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from patch_firmware import patch_firmware
import midi_recovery_patch as integrated
import flash_query_patch as sync
import midi_dense_stop_patch as dense
import project_load_recovery_patch as load_guard


def build():
    stock=ROOT/'stock/circuitrhythm-firmware-5706.syx'
    output=ROOT/'build/circuitrhythm-5706-phase1-recovery.syx'
    manifest=patch_firmware(stock,output,integrated.build_patches(),stock_path=stock)
    core,_,glue,_=integrated.arm_code()
    report=dict(hardware_release='NO-GO',scope='Integrated bounded Off/Stop candidate;not physical validation',
        output=str(output),syx_sha256=manifest['output']['sha256'],image_sha256=manifest['output']['image_sha256'],
        state_base=hex(integrated.STATE_BASE),recovery_bytes=integrated.STATE_SIZE,total_reserved_bytes=integrated.STATE_SIZE+256,
        core_sha256=hashlib.sha256(core).hexdigest(),glue_sha256=hashlib.sha256(glue).hexdigest(),patches=len(integrated.build_patches()),
        flash_sync_guard=dict(site=hex(sync.SITE),base=hex(sync.CODE_BASE),bytes=len(sync.arm_code()),
            sha256=hashlib.sha256(sync.arm_code()).hexdigest(),additional_ram_bytes=0,additional_stack_bytes=0,
            scope='Native CTRL_SYNC NULL buffer uses existing24B frame scratch;not filesystem replacement'),
        dense_stop_service=dict(site=hex(dense.SITE),base=hex(dense.CODE_BASE),bytes=len(dense.arm_code(integrated.STATE_BASE)[0]),
            sha256=hashlib.sha256(dense.arm_code(integrated.STATE_BASE)[0]).hexdigest(),additional_ram_bytes=0,wrapper_stack_bytes=16,
            scope='One native router output poll per stock player flush,only unmasked thread context and registered ports;no wait or fault clearing'))
    load_code,_=load_guard.arm_code(integrated.seq_code()[1]['c_seq_state'],integrated.STATE_BASE)
    report['project_load_recovery']=dict(hooks=[dict(site=hex(a),original=b.hex(),entry=n) for a,b,n in load_guard.HOOKS],base=hex(load_guard.CODE_BASE),limit=hex(load_guard.CODE_LIMIT),bytes=len(load_code),
        sha256=hashlib.sha256(load_code).hexdigest(),additional_ram_bytes=0,max_local_wrapper_stack_bytes=32,
        recovery_helper_peak_stack_bytes_excluding_native=64,
        scope='Close descriptor/generation-confirmed,stopped and unheld Projects Load/New recovery. Only authorized full read/defaults and complete native apply return clear taint. Real pad release remains required. Retry error preserves phase2/flags3/taint1. No raw rollback,automatic retry or physical storage claim.')
    (output.with_suffix('.scope.json')).write_text(json.dumps(report,indent=2),encoding='utf-8');return report


if __name__=='__main__':print(json.dumps(build(),indent=2))
