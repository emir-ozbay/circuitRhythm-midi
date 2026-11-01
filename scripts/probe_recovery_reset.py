"""Same native MIDI parent reset,previous candidate versus current build."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'scripts'),str(ROOT/'src')]
import test_phase1_safety as base
import midi_recovery_patch as fixed
from patch_firmware import unpack_syx
from integrated_midi_test_support import IntegratedMidiFixture
from integrated_reset_test_support import IntegratedResetFixture


def cases(raw):
    image=unpack_syx(raw,allow_extended=True)['image'];rows=[]
    # The Phase1 code cave/labels do not change for this reset-only fix.
    for mode in (0,1):
        for mixed in (False,True):
            h=base.SafetyTests();h.image=image;h.labels=fixed.seq_code()[1];h.instruction_budget=500000;h.setUp()
            out=IntegratedMidiFixture(h);reset=IntegratedResetFixture(h,out)
            h.u.mem_write(base.seq.SEQ_STATE_ADDR+4,bytes([mode]))
            for note in range(64):
                for port in range(3):assert out.send(port,[0x90,note,96])==1
            out.poll()
            for port in range(3):
                for note in range(64):
                    if mixed and note==32:
                        for _ in range(32):assert out.send(port,[0xF8,0,0])==1
                    assert out.send(port,[0x80,note,0])==1
                assert out.send(port,[0xFC,0,0])==1
            before=reset.snapshot();assert before['pending']==[64]*3
            assert reset.parent()==0;after=reset.snapshot();reset.check_rx()
            for _ in range(128):out.poll()
            off=[sum(m[0]==8 for m in messages) for messages in out.delivered]
            stop=[messages.count(b'\x0F\xFC\0\0') for messages in out.delivered]
            rows.append(dict(mode=mode,mixed_fifo_and_bitmap=mixed,queued_before=before['pending'],queued_after=after['pending'],
                off=off,stop=stop,off_delivery='PASS' if off==[64]*3 else 'FAIL',stop_delivery='PASS' if stop==[1]*3 else 'FAIL',
                native_parent_calls=reset.events.count('parent'),native_router_clears=reset.events.count('router_clear'),
                native_port_clears=reset.events.count('port_clear'),native_rx_rearms=reset.events.count('rx_rearm')))
    return rows


def probe(out,before_path):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    old=Path(before_path).read_bytes();new=(ROOT/'build/circuitrhythm-5706-phase1-recovery.syx').read_bytes()
    before,after=cases(old),cases(new)
    r=dict(scope='Real native68A2C MIDI class-init parent,output queues and native RX no-capacity path;synthetic driver/RX ring bindings,no USB hardware reset/barrier proof',
        hardware_release='NO-GO',before_sha256=hashlib.sha256(old).hexdigest(),after_sha256=hashlib.sha256(new).hexdigest(),
        before=before,after=after,result='FAIL_TO_PASS' if all(c['off_delivery']==c['stop_delivery']=='PASS' for c in after) and any(c['off_delivery']=='FAIL' for c in before) else 'NOT_FIXED')
    (out/'report.json').write_text(json.dumps(r,indent=2),encoding='utf-8');return r


if __name__=='__main__':
    r=probe(sys.argv[1],sys.argv[2]);print(json.dumps(dict(result=r['result'],before=[c['off'] for c in r['before']],after=[c['off'] for c in r['after']])));raise SystemExit(2)
