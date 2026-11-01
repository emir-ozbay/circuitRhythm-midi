"""Current packaged firmware native boot/button/pad mode regression evidence."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'src')]
from recovery_live_mode_test_support import boot_session,exercise_live_mode,UnsupportedDWTClock
from recovery_spi_test_support import UnmodeledSPIResponse,DMA1
from recovery_input_test_support import MAIN_LOOP
from unicorn.arm_const import UC_ARM_REG_PC
from patch_firmware import unpack_syx


def probe(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    raw=(ROOT/'build/circuitrhythm-5706-phase1-recovery.syx').read_bytes()
    image=unpack_syx(raw,allow_extended=True)['image']
    s=boot_session(image);h=s.h
    result=exercise_live_mode(s)
    # Main's first live802F read remains strict without an explicit input.
    try:s.cycle()
    except UnmodeledSPIResponse:pass
    else:raise AssertionError('used sample status must not get a default zero')
    assert h.read_register==dict(bank=0,register=0x802F)
    ram=bytes(h.u.mem_read(0x20000000,0x50000));mmio=bytes(h.u.mem_read(DMA1,0x90))
    try:h.complete_spi_dma()
    except UnmodeledSPIResponse:pass
    else:raise AssertionError('strict retry must stop')
    assert bytes(h.u.mem_read(0x20000000,0x50000))==ram and bytes(h.u.mem_read(DMA1,0x90))==mmio
    boundary=dict(h.unmodeled_response)
    h.sample_status=tuple([0]*2);h.unmodeled_response=None
    h.checkpoint(MAIN_LOOP,budget=2000000)
    s.cycle()
    assert len(h.sample_status_reads)==2 and h.dwt_reads==4
    try:s.cycle()
    except UnmodeledSPIResponse:pass
    else:raise AssertionError('finite status input must exhaust')
    assert not h.invalid and h.validate_stacks()
    result.update(hardware_release='NO-GO',physical_test=False,firmware_changed=True,device_apis_accessed=False,
        syx_sha256=hashlib.sha256(raw).hexdigest(),image_sha256=hashlib.sha256(image).hexdigest(),
        strict_sample_status=boundary,strict_retry_atomic=True,sample_status_inputs=h.sample_status_reads,
        exhausted_sample_status=h.unmodeled_response,dwt_reads=h.dwt_reads,after_cycles=s.snapshot(),
        scope='Native reset objects/vtable input callbacks;no startup seeds/stubs. All32 native pad edits each followed by mode roundtrips without track changes. C0/bit3 held rejection,retained B8 history,native timer6 arm/cancel and countdown/expiry with explicit255+44+1 synthetic tick debt. Transient transport/project-phase/note-owner injections are labeled apart. Finite DSP mailbox/802F inputs and disabled DWT;other NOR/ADC/USB/FPU model limits remain. Not GPIO scan,event-queue,NVIC,timing or physical proof.')
    (out/'report.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


if __name__=='__main__':
    r=probe(sys.argv[1]);print(json.dumps(dict(inputs=len(r['inputs']),io=len(r['project_io']),heap=hex(r['final']['heap']),mode=r['final']['mode'],hardware_release=r['hardware_release'])))
    raise SystemExit(2)
