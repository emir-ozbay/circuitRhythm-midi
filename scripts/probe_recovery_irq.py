"""Same frozen/current SYX through native IRQ/reset/EP0,explicit registers."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'src'),str(ROOT/'scripts')]
import test_phase1_safety as base
import midi_recovery_patch as fixed
import midi_accepted_tx_patch as guard
from integrated_midi_test_support import IntegratedMidiFixture
from integrated_usb_irq_test_support import IntegratedUsbIrqFixture
from patch_firmware import unpack_syx


def cases(raw):
    image=unpack_syx(raw,allow_extended=True)['image'];rows=[]
    for mode in (0,1):
        h=base.SafetyTests();h.image=image;h.labels=fixed.seq_code()[1];h.instruction_budget=500000;h.setUp()
        out=IntegratedMidiFixture(h);usb=IntegratedUsbIrqFixture(h,out)
        h.u.mem_write(base.seq.SEQ_STATE_ADDR+4,bytes([mode]))
        out.note(0,48);out.poll();usb.bus()
        out.note(0,48,0,on=False);out.send(0,[0xFC,0,0]);out.poll();assert usb.native.in_flight is not None
        usb.reset_irq();after_reset=dict(job=h.read(guard.STATE_BASE+guard.JOB),phase=h.read(guard.STATE_BASE+guard.PHASE))
        usb.enumerate_irq();usb.address();usb.configure();before_service=usb.irq_visits.count(0x080525B6)
        for _ in range(128):out.poll();usb.bus()
        usb.reset.check_rx();stream=b''.join(usb.native.usb_completed)
        rows.append(dict(mode=mode,after_reset=after_reset,constructors_before_service=before_service,
            constructors_total=usb.irq_visits.count(0x080525B6),off=stream.count(b'\x08\x80\x30\0'),
            stop=stream.count(b'\x0F\xFC\0\0'),job_after=h.read(guard.STATE_BASE+guard.JOB),phase_after=h.read(guard.STATE_BASE+guard.PHASE),
            stream_hex=stream.hex(),native_path=[hex(p) for p in sorted(set(usb.irq_visits))],
            passed=stream==b'\x09\x90\x30\x60\x08\x80\x30\0\x0F\xFC\0\0'))
    return rows


def probe(out,before_path):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    before_raw=Path(before_path).read_bytes();after_raw=(ROOT/'build/circuitrhythm-5706-phase1-recovery.syx').read_bytes()
    a,b=cases(before_raw),cases(after_raw)
    r=dict(scope='Packaged native646D0/4293E/HAL/FIFO/completion/reset/enumeration/EP0/class init over modeled registers;no prototype recovery overlays or physical devices',
        hardware_release='NO-GO',before_sha256=hashlib.sha256(before_raw).hexdigest(),after_sha256=hashlib.sha256(after_raw).hexdigest(),
        before=a,after=b,result='FAIL_TO_PASS' if all(c['passed'] for c in b) and all(not c['passed'] for c in a) else 'NOT_FIXED',
        limits='CPU FIFO/ACK/flush/FIFO-event/configuration and UART-drain model;no real NVIC/PHY/DMA or malicious late hardware event after the retirement contract')
    (out/'report.json').write_text(json.dumps(r,indent=2),encoding='utf-8');return r


if __name__=='__main__':
    r=probe(sys.argv[1],sys.argv[2]);print(json.dumps(dict(result=r['result'],before=[[c['off'],c['stop']] for c in r['before']],
        after=[[c['off'],c['stop']] for c in r['after']],hardware_release=r['hardware_release'])));raise SystemExit(2)
