"""Conditional native boot with explicit DSP inputs and M4F frame ownership."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'src')]
from unicorn.arm_const import *
from recovery_fpu_test_support import FPUStartup,UnsupportedFPContext,FPCCR
from recovery_worker_test_support import BasicFrameOnly
from recovery_dsp_test_support import ScriptedDSPPeer,mailbox_script
from recovery_spi_test_support import UnmodeledSPIResponse
from recovery_input_test_support import MAIN_INPUT_READY,MAIN_LOOP
from probe_recovery_dsp import snapshot
from patch_firmware import unpack_syx


def probe(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    raw=(ROOT/'build/circuitrhythm-5706-phase1-recovery.syx').read_bytes()
    image=unpack_syx(raw,allow_extended=True)['image']
    peer=ScriptedDSPPeer(mailbox_script())
    h=FPUStartup(image,peer_policy='ready',dsp_peer=peer)
    report=dict(hardware_release='NO-GO',firmware_changed=False,physical_test=False,device_apis_accessed=False,
        auxiliary_dsp_executed=False,syx_sha256=hashlib.sha256(raw).hexdigest(),image_sha256=hashlib.sha256(image).hexdigest(),
        scope='Native MCU/VFP/PendSV execution with non-nested basic/extended/lazy-frame hardware shim. Finite explicit six-value DSP mailbox input;native FatFs/synthetic NOR,ADC and ready/USB ACK assumptions remain. Not NVIC/cycle/fault/full peripheral/physical proof.')
    h.main_setup().start_tasks().checkpoint().start_input().checkpoint(MAIN_INPUT_READY,budget=800000).start_spi()
    report['progress']=[]
    for _ in range(8):
        before=h.instructions
        try:pc=h.run(h.u.reg_read(UC_ARM_REG_PC),MAIN_LOOP,budget=2000000)
        except (UnmodeledSPIResponse,UnsupportedFPContext,BasicFrameOnly) as error:
            report['boundary']=dict(kind=type(error).__name__,detail=str(error))
            pc=h.u.reg_read(UC_ARM_REG_PC)
        row=snapshot(h);row['instruction_delta']=h.instructions-before
        report['progress'].append(row)
        print(json.dumps(dict(pc=hex(pc),stop=row['stop_reason'],instructions=row['instruction_delta'],heap=row['heap'],FP=len(h.fp_events))),flush=True)
        if pc==MAIN_LOOP or 'boundary' in report:break
        assert row['instruction_delta']>=2000000,row
    assert h.validate_stacks() and not h.invalid
    assert bytes(h.u.mem_read(0x08010000,len(image)))==image
    report.update(conditional_main_reached=h.u.reg_read(UC_ARM_REG_PC)==MAIN_LOOP,
        fp_instructions={hex(k):v for k,v in h.fp_instructions.items()},fp_events=h.fp_events,
        exceptions=h.exception_events,switches=h.switches,allocations=h.allocations,
        dsp_reads=peer.reads,FPCCR=hex(h.read(FPCCR)),last_trace=[hex(pc) for pc in h.trace],native_media_bindings=h.bindings)
    (out/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


if __name__=='__main__':
    r=probe(sys.argv[1]);print(json.dumps(dict(conditional_main_reached=r['conditional_main_reached'],FP=len(r['fp_events']),boundary=r.get('boundary'),hardware_release=r['hardware_release'])))
    raise SystemExit(2)
