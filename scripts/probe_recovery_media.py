"""Exact-SYX native FatFs/NOR and NULL CTRL_SYNC regression proof."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'src')]
from unicorn import UcError
from unicorn.arm_const import *
from recovery_media_test_support import MediaStartup,SparseNOR,fat12_fixture
from recovery_input_test_support import MAIN_INPUT_READY,MAIN_LOOP
from recovery_spi_test_support import UnmodeledSPIResponse
from inspect_ui import load_image
from patch_firmware import unpack_syx
import midi_recovery_patch as fixed


def execute(image,expect_fault,medium=None):
    h=MediaStartup(image,peer_policy='ready',medium=medium)
    h.main_setup().start_tasks().checkpoint().start_input().checkpoint(MAIN_INPUT_READY,budget=800000).start_spi()
    try:h.checkpoint(MAIN_LOOP,budget=5000000)
    except UcError:
        assert expect_fault and h.u.reg_read(UC_ARM_REG_PC)==0x08041AA2
        assert h.invalid[-1]['address']==0 and h.u.reg_read(UC_ARM_REG_R1)==1
    except UnmodeledSPIResponse:
        assert not expect_fault and h.unmodeled_response['caller']=='0x803151a' and h.memory_selector==0x37300
        assert not h.invalid
    else:raise AssertionError('expected sync failure or consumed DSP memory boundary')
    assert h.bindings and all(h.read(b['owner']+0x3C)==b['root'] for b in h.bindings)
    assert h.validate_stacks() and bytes(h.u.mem_read(0x08010000,len(image)))==image
    names={t['tcb']:t['name'] for t in h.tasks}
    out=dict(pc=hex(h.u.reg_read(UC_ARM_REG_PC)),allocations=h.allocations,allocation_count=len(h.allocations),
        heap=hex(h.read(0x20002B58)),bindings=h.bindings,mounts=h.mounts,fat_type=h.u.mem_read(0x20000AC0,1)[0],
        sync_calls=h.sync_calls,scratch_uses=h.scratch_uses,qspi_transfers=h.qspi_transfers,qspi_dma_irq_count=len(h.qspi_dma_irqs),
        nor_mutations=h.medium.mutations,nor_sha256=hashlib.sha256(h.medium.data).hexdigest(),
        minimum_msp=hex(h.minimum_msp),lowest_task_stack_addresses={names[k]:hex(v) for k,v in h.thread_min.items()},
        invalid_accesses=h.invalid,unmodeled_response=h.unmodeled_response,native_fault=expect_fault,
        instruction_image_identical=True,full_main_complete=False,physical_test=False)
    return h,out


def probe(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    raw=(ROOT/'build/circuitrhythm-5706-phase1-recovery.syx').read_bytes()
    image=unpack_syx(raw,allow_extended=True)['image']
    # Reconstruct the prior40-patch profile from the same pinned stock base.
    from patch_firmware import apply_patches
    prior=apply_patches(load_image(),[p for p in fixed.build_patches() if not p.name.startswith('flash_sync_')])[0]
    initial=fat12_fixture()
    report=dict(hardware_release='NO-GO',firmware_changed=True,device_apis_accessed=False,
        syx_sha256=hashlib.sha256(raw).hexdigest(),image_sha256=hashlib.sha256(image).hexdigest(),
        input_nor_sha256=hashlib.sha256(initial).hexdigest(),
        scope='Native QSPI DMA data-before-TC,physical16MiB NOR model and native FatFs over synthetic FAT12. Old CTRL_SYNC NULL write FAIL vs existing-frame scratch PASS. External802B ready/USB ACK assumptions remain;used DSP memory37300 read rejected;not full boot/physical media/DSP/timing proof.')
    for name,data,bad in (('stock',load_image(),True),('prior',prior,True),('candidate',image,False)):
        h,r=execute(data,bad);report[name]=r
        if not bad:final_medium=bytes(h.medium.data)
    h,r=execute(image,False,SparseNOR(final_medium));report['candidate_reboot']=r
    for name in ('prior','candidate'):
        assert [(a['size'],a['current']) for a in report['stock']['allocations']]==[(a['size'],a['current']) for a in report[name]['allocations']]
    assert report['candidate']['scratch_uses'] and report['candidate']['fat_type']==1
    assert report['candidate']['nor_sha256']!=report['input_nor_sha256']
    assert report['candidate_reboot']['bindings']
    report['next_task']='Trace native314D*/31516 auxiliary memory read selector0x37300/consumer and prior writes. Keep consumed DSP data strict;continue Main25864 without fabricated memory replies. Native media ownership and CTRL_SYNC NULL failures are closed in this fixture.'
    (out/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


if __name__=='__main__':
    r=probe(sys.argv[1]);c=r['candidate']
    print(json.dumps(dict(sync_before='NULL write',sync_after='PASS',native_fat_type=c['fat_type'],
        native_owner_bindings=len(c['bindings']),sync_scratch_calls=len(c['scratch_uses']),qspi=len(c['qspi_transfers']),
        heap=c['heap'],next_memory=c['unmodeled_response']['memory_selector'],hardware_release=r['hardware_release'])))
    raise SystemExit(2)
