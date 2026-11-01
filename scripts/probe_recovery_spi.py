"""Exact-SYX native SPI transport and explicitly conditional peer boot trace."""
import hashlib
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'scripts'),str(ROOT/'src')]
from recovery_spi_test_support import SPIStartup, UnmodeledSPIResponse, NativeMediaUnavailable, MEDIA_GATE, SPI_WAIT
from recovery_input_test_support import MAIN_INPUT_READY, MAIN_LOOP
from inspect_ui import load_image
from patch_firmware import unpack_syx
from unicorn.arm_const import *
import midi_recovery_patch as fixed
import midi_accepted_tx_patch as accepted
import seq_Patch as seq


def probe(out):
    out = Path(out); out.mkdir(parents=True,exist_ok=True)
    raw = (ROOT/'build/circuitrhythm-5706-phase1-recovery.syx').read_bytes()
    image = unpack_syx(raw,allow_extended=True)['image']
    result = dict(hardware_release='NO-GO',firmware_changed=False,device_apis_accessed=False,
        syx_sha256=hashlib.sha256(raw).hexdigest(),image_sha256=hashlib.sha256(image).hexdigest(),
        scope='Native DMA1 stream3/4 IRQs and ignored-MISO return proof. Strict policy stops consumed bank0/register802B response. Conditional external-peer reply000000/000000/000001 and idle USB reset ACK permit later native boot;not DSP execution/physical ready/full boot/media proof.')
    for name,data,fill in (('stock',load_image(),0),('candidate',image,0),('candidate_fill_a5',image,0xA5)):
        h = SPIStartup(data,discarded_byte=fill).main_setup().start_tasks().checkpoint().start_input().checkpoint(MAIN_INPUT_READY,budget=800000).start_spi()
        state = bytes(h.u.mem_read(fixed.STATE_BASE,1088))
        try:
            h.checkpoint(MEDIA_GATE,budget=5000000)
        except UnmodeledSPIResponse:
            pass
        else:
            raise AssertionError('strict policy unexpectedly supplied used peer response')
        assert h.u.reg_read(UC_ARM_REG_PC) == SPI_WAIT and len(h.spi_transfers)==3605
        assert len(h.spi_irqs)==7210 and not h.status_reads and not h.invalid
        # Rejection is transactional: no DMA/RAM/flags/CPU update.
        ram = bytes(h.u.mem_read(0x20000000,0x50000)); mmio = bytes(h.u.mem_read(0x40026000,0x90))
        try:
            h.complete_spi_dma()
        except UnmodeledSPIResponse:
            pass
        else:
            raise AssertionError('strict response was not rejected')
        assert bytes(h.u.mem_read(0x20000000,0x50000))==ram and bytes(h.u.mem_read(0x40026000,0x90))==mmio
        strict = dict(transport_transfers=len(h.spi_transfers),irq_count=len(h.spi_irqs),
                      unmodeled_response=h.unmodeled_response,heap=hex(h.read(seq.HEAP_CUR_PTR)),
                      allocations=len(h.allocations),completion_tokens=list(h.u.mem_read(0x20000170,4)))
        # Explicit model assumption;only wire bytes change,never native R0 or
        # completion RAM. The first two used reads remain busy.
        h.peer_policy = 'ready'
        h.checkpoint(MEDIA_GATE,budget=5000000)
        assert len(h.spi_transfers)==3819 and len(h.allocations)==1296
        assert [s['reply'] for s in h.status_reads]==['000000','000000','000001']
        first_media = dict(pc=hex(h.u.reg_read(UC_ARM_REG_PC)),argument=hex(h.u.reg_read(UC_ARM_REG_R0)),
                           caller=hex(h.u.reg_read(UC_ARM_REG_LR)),heap=hex(h.read(seq.HEAP_CUR_PTR)))
        try:
            h.checkpoint(MAIN_LOOP,budget=600000)
        except NativeMediaUnavailable:
            pass
        else:
            raise AssertionError('no-response-media boundary not reached')
        assert h.u.reg_read(UC_ARM_REG_PC) == 0x0802E4CC
        assert h.u.reg_read(UC_ARM_REG_R0)==0 and h.validate_stacks() and not h.invalid
        assert bytes(h.u.mem_read(0x08010000,len(data)))==data
        after = bytes(h.u.mem_read(fixed.STATE_BASE,1088))
        differences = [i for i,(a,b) in enumerate(zip(state,after)) if a!=b]
        if name != 'stock':
            assert all(i>=accepted.STATE_BASE-fixed.STATE_BASE for i in differences)
        names = {t['tcb']:t['name'] for t in h.tasks}
        result[name] = dict(strict=strict,conditional_peer_policy='ready_after_two_busy_reads',
            discarded_byte=fill,status_reads=h.status_reads,ignored_return_proofs=h.ignored_return_proofs,
            transfers=h.spi_transfers,irq_count=len(h.spi_irqs),allocations=h.allocations,
            allocation_count=len(h.allocations),heap=hex(h.read(seq.HEAP_CUR_PTR)),
            first_media=first_media,media_calls=h.media_calls,
            next_gate=dict(pc=hex(h.u.reg_read(UC_ARM_REG_PC)),argument=0,
                           caller=hex(h.u.reg_read(UC_ARM_REG_LR)),task=names[h.running_tcb],
                           note='Stop before native2E4CC would dereference NULL;no responding SD card/QSPI media.'),
            minimum_msp=hex(h.minimum_msp),lowest_task_stack_addresses={names[k]:hex(v) for k,v in h.thread_min.items()},
            reserved_byte_differences=differences,reserved_writes=h.reserved_writes,
            usb_reset_writes=h.usb_resets,invalid_accesses=h.invalid,instruction_image_identical=True,
            full_main_complete=False,auxiliary_dsp_executed=False,physical_test=False)
    old,new,variant = (result[k] for k in ('stock','candidate','candidate_fill_a5'))
    for other in (new,variant):
        assert [(x['size'],x['current']) for x in old['allocations']]==[(x['size'],x['current']) for x in other['allocations']]
        assert old['next_gate']==other['next_gate']
        assert [e['tx_hex'] for e in old['transfers']]==[e['tx_hex'] for e in other['transfers']]
    result['next_task']='Trace Content2E8B4 owner+3C NULL argument to native2E4C0/2E4CC under no-response SDIO and zero-data QSPI;model validated media input before Main25864. Keep external DSP-ready assumption explicit.'
    (out/'report.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


if __name__=='__main__':
    r=probe(sys.argv[1]); c=r['candidate']
    print(json.dumps(dict(strict_transfers=c['strict']['transport_transfers'],conditional_transfers=len(c['transfers']),
        conditional_allocations=c['allocation_count'],conditional_heap=c['heap'],next_gate=c['next_gate'],hardware_release=r['hardware_release'])))
    raise SystemExit(2)
