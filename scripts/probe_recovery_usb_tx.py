"""Packaged pre-admission regression and accepted-cancel replay comparison."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'src'),str(ROOT/'scripts')]
import test_phase1_safety as base
import midi_recovery_patch as fixed
from patch_firmware import unpack_syx
from integrated_midi_test_support import IntegratedMidiFixture
from integrated_usb_tx_test_support import IntegratedUsbTxFixture


def cases(raw,accepted=False):
    image=unpack_syx(raw,allow_extended=True)['image'];rows=[]
    for mode in (0,1):
        h=base.SafetyTests();h.image=image;h.labels=fixed.seq_code()[1];h.instruction_budget=500000;h.setUp()
        out=IntegratedMidiFixture(h);usb=IntegratedUsbTxFixture(h,out)
        h.u.mem_write(base.seq.SEQ_STATE_ADDR+4,bytes([mode]))
        out.note(0,48);out.poll();usb.bus()
        out.note(0,48,0,on=False);out.send(0,[0xFC,0,0])
        if accepted:
            out.poll();assert usb.native.in_flight is not None
            h.u.mem_write(usb.native.usb_controller+0x274,b'\0')
            h.call(0x0805261C,usb.wrapper,usb.native.usb_controller,0)
            assert usb.cancelled==[b'\x08\x80\x30\0\x0F\xFC\0\0']
        else:
            injected,_=usb.disconnect_before_flush(no_credit=True)
            out.poll();assert len(injected)==1 and len(usb.closes)==1
        length,_=usb.main();pending=out.pending(0)
        usb.reconnect()
        for _ in range(128):out.poll();usb.bus()
        stream=b''.join(usb.native.usb_completed)
        rows.append(dict(mode=mode,main_after_close=length,fifo_after_close=pending,native_closes=len(usb.closes),
                         off=stream.count(b'\x08\x80\x30\0'),stop=stream.count(b'\x0F\xFC\0\0'),
                         stream_hex=stream.hex(),passed=stream==b'\x09\x90\x30\x60\x08\x80\x30\0\x0F\xFC\0\0'))
    return rows


def probe(out,before):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    old=Path(before).read_bytes();new=(ROOT/'build/circuitrhythm-5706-phase1-recovery.syx').read_bytes()
    a,b=cases(old),cases(new);cancelled_before,cancelled=cases(old,accepted=True),cases(new,accepted=True)
    r=dict(scope='Packaged native FIFO/formatter plus5261C/2C90C/42F92/52EDC class deinit over MMIO model;configuration/cancel/ACK/flush/completion modeled,not full IRQ or PHY',
           hardware_release='NO-GO',before_sha256=hashlib.sha256(old).hexdigest(),after_sha256=hashlib.sha256(new).hexdigest(),before=a,after=b,
           result='ACCEPTED_CANCEL_FAIL_TO_PASS' if all(x['passed'] for x in cancelled) and all(not x['passed'] for x in cancelled_before) else 'NOT_FIXED',
           pre_admission_regression='PASS' if all(x['passed'] for x in b) else 'FAIL',
           accepted_tx_cancellation=dict(product_result='PASS_IN_RETIREMENT_MODEL' if all(x['passed'] for x in cancelled) else 'FAIL_LOSS_REPRODUCED',
                                         before=cancelled_before,observations=cancelled))
    (out/'report.json').write_text(json.dumps(r,indent=2),encoding='utf-8');return r


if __name__=='__main__':
    r=probe(sys.argv[1],sys.argv[2]);print(json.dumps(r,indent=2));raise SystemExit(2)
