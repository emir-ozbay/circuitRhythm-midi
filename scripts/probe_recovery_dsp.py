"""Exact-SYX strict boundary, then explicitly conditional DSP mailbox input."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'src')]
from unicorn.arm_const import UC_ARM_REG_PC,UC_ARM_REG_SP,UC_ARM_REG_CONTROL,UC_ARM_REG_MSP,UC_ARM_REG_PSP
from recovery_dsp_test_support import DSPStartup,ScriptedDSPPeer,mailbox_script
from recovery_spi_test_support import UnmodeledSPIResponse,DMA1
from recovery_input_test_support import MAIN_INPUT_READY,MAIN_LOOP
from patch_firmware import unpack_syx
from recovery_worker_test_support import BasicFrameOnly


def snapshot(h):
    names={t['tcb']:t['name'] for t in h.tasks}
    return dict(pc=hex(h.u.reg_read(UC_ARM_REG_PC)),instructions=h.instructions,
        stop_reason=h.stop_reason,heap=hex(h.read(0x20002B58)),allocation_count=len(h.allocations),
        spi_transfers=len(h.spi_transfers),spi_irqs=len(h.spi_irqs),
        dsp_writes=len(h.dsp_writes),last_dsp_writes=h.dsp_writes[-8:],
        minimum_msp=hex(h.minimum_msp),task_min={names[k]:hex(v) for k,v in h.thread_min.items()},
        invalid=h.invalid,unmodeled=h.unmodeled_response)


def probe(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    raw=(ROOT/'build/circuitrhythm-5706-phase1-recovery.syx').read_bytes()
    image=unpack_syx(raw,allow_extended=True)['image']
    h=DSPStartup(image,peer_policy='ready')
    h.main_setup().start_tasks().checkpoint().start_input().checkpoint(MAIN_INPUT_READY,budget=800000).start_spi()
    try:h.checkpoint(MAIN_LOOP,budget=5000000)
    except UnmodeledSPIResponse:pass
    else:raise AssertionError('strict consumed DSP boundary missing')
    assert h.dsp_read==dict(bank=0,address=0x37300)
    assert len(h.dsp_writes)==516 and not any(w['address']==0x37300 for w in h.dsp_writes)
    ram,mmio=bytes(h.u.mem_read(0x20000000,0x50000)),bytes(h.u.mem_read(DMA1,0x90))
    try:h.complete_spi_dma()
    except UnmodeledSPIResponse:pass
    else:raise AssertionError('strict repeated read unexpectedly completed')
    assert bytes(h.u.mem_read(0x20000000,0x50000))==ram and bytes(h.u.mem_read(DMA1,0x90))==mmio
    report=dict(hardware_release='NO-GO',physical_test=False,firmware_changed=False,
        auxiliary_dsp_executed=False,device_apis_accessed=False,
        syx_sha256=hashlib.sha256(raw).hexdigest(),image_sha256=hashlib.sha256(image).hexdigest(),
        strict=snapshot(h),strict_failure_atomic=True,
        scope='Finite explicitly supplied external mailbox replies; not inferred DSP RAM or actual program initialization. Native MCU loops,wire writes and IRQs execute. No zero fallback or automatic command clear. Existing ADC/NOR/802B/USB/basic-frame/timing assumptions remain.')
    peer=ScriptedDSPPeer(mailbox_script());peer.active=True;h.dsp_peer=peer
    h.unmodeled_response=None
    h.checkpoint(0x0806455C,budget=100000)
    caller=h.read(h.u.reg_read(UC_ARM_REG_SP)+12)&~1
    h.checkpoint(caller,budget=100)
    assert peer.position==len(peer.script) and peer.writes[0,0x372FB]==1
    report['mailbox_return']=snapshot(h)
    report['mailbox_return']['caller']=hex(caller)
    report['reads']=peer.reads
    report['progress']=[]
    for _ in range(4):
        before=h.instructions
        fp_boundary=False
        try:pc=h.run(h.u.reg_read(UC_ARM_REG_PC),MAIN_LOOP,budget=2000000)
        except UnmodeledSPIResponse:pc=h.u.reg_read(UC_ARM_REG_PC)
        except BasicFrameOnly as error:
            pc=h.u.reg_read(UC_ARM_REG_PC);fp_boundary=True
            h.stop_reason='unsupported_FP_context_before_instruction'
            report['FP_boundary']=dict(error=str(error),pc=hex(pc),
                instruction=bytes(h.u.mem_read(pc,4)).hex(),executed=False,
                control=h.u.reg_read(UC_ARM_REG_CONTROL),msp=hex(h.u.reg_read(UC_ARM_REG_MSP)),
                psp=hex(h.u.reg_read(UC_ARM_REG_PSP)),cpacr=hex(h.read(0xE000ED88)),
                fpccr=hex(h.read(0xE000EF34)))
        row=snapshot(h);row['instruction_delta']=h.instructions-before
        report['progress'].append(row)
        print(json.dumps(dict(pc=hex(pc),stop=row['stop_reason'],instructions=row['instruction_delta'],writes=row['dsp_writes'])),flush=True)
        if pc==MAIN_LOOP or h.unmodeled_response is not None or fp_boundary:break
        assert row['instruction_delta']>=2000000, row
    assert h.validate_stacks() and not h.invalid
    assert bytes(h.u.mem_read(0x08010000,len(image)))==image
    report['conditional_main_reached']=h.u.reg_read(UC_ARM_REG_PC)==MAIN_LOOP
    report['all_dsp_writes']=h.dsp_writes
    report['allocations']=h.allocations
    report['last_trace']=[hex(pc) for pc in h.trace]
    report['native_media_bindings']=h.bindings
    report['script_exhausted']=peer.position==len(peer.script)
    (out/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


if __name__=='__main__':
    r=probe(sys.argv[1]);print(json.dumps(dict(mailbox_return=r['mailbox_return']['caller'],conditional_main_reached=r['conditional_main_reached'],hardware_release=r['hardware_release'])))
    raise SystemExit(2)
