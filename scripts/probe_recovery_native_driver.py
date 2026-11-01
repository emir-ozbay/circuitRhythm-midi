"""Integrated SYX through native USB/DIN formatters,modeled final completion."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'scripts'),str(ROOT/'src')]
import test_phase1_safety as base
import midi_recovery_patch as fixed
from patch_firmware import unpack_syx
from integrated_midi_test_support import IntegratedMidiFixture
from native_midi_driver_test_support import NativeMidiDriverFixture


def probe(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    raw=(ROOT/'build/circuitrhythm-5706-phase1-recovery.syx').read_bytes()
    image=unpack_syx(raw,allow_extended=True)['image'];observations=[]
    for mode in (0,1):
        h=base.SafetyTests();h.image=image;h.labels=fixed.seq_code()[1];h.instruction_budget=500000;h.setUp()
        o=IntegratedMidiFixture(h);native=NativeMidiDriverFixture(h,o);din=[bytearray(),bytearray()]
        h.u.mem_write(base.seq.SEQ_STATE_ADDR+4,bytes([mode]))
        def progress():
            o.poll()
            if native.in_flight is not None:native.release_usb_endpoint()
            for n in range(2):din[n].extend(native.drain_uart(n))
        o.note(0,48)
        for _ in range(4):progress()
        for port in range(3):
            for _ in range(64):assert o.send(port,[0xF8,0,0])==1
            assert o.send(port,[0x80,48,0])==1
            assert o.send(port,[0xFC,0,0])==1
        for _ in range(128):progress()
        usb=b''.join(native.usb_completed)
        expected_usb=b'\x09\x90\x30\x60'+b'\x0F\xF8\0\0'*64+b'\x08\x80\x30\0'+b'\x0F\xFC\0\0'
        expected_din=b'\x90\x30\x60'+b'\xF8'*64+b'\x80\x30\0\xFC'
        assert usb==expected_usb,(mode,usb.hex())
        assert [bytes(b) for b in din]==[expected_din]*2
        assert [o.pending(n) for n in range(3)]==[0]*3 and native.in_flight is None
        observations.append(dict(mode=mode,usb_bytes=len(usb),usb_sha256=hashlib.sha256(usb).hexdigest(),
            din_bytes=[len(b) for b in din],din_sha256=[hashlib.sha256(b).hexdigest() for b in din],
            exact_stream=True,on=1,clocks=64,off=1,stop=1,hardware_test=False))
    r=dict(scope='Packaged integrated candidate,native boot-router/ports/USB-DIN formatters and callbacks;explicit bus/UART-drain boundaries,no device APIs',
        hardware_release='NO-GO',firmware_integrated=True,observations=observations)
    (out/'report.json').write_text(json.dumps(r,indent=2),encoding='utf-8');return r


if __name__=='__main__':print(json.dumps(probe(sys.argv[1]),indent=2))
