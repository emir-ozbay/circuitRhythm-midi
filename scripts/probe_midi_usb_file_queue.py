"""Packaged candidate plus unchanged prototypes; native synchronous file queue."""
import hashlib,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'src'),str(ROOT/'scripts')]
import test_midi_usb_file_queue as tests
from patch_firmware import unpack_syx
from audit_midi_usb_carry_prototype import audit
from trace_midi_usb_file_queue import trace
from probe_sequencer_stop import probe as candidate_negative


def probe(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    syx=(ROOT/'build/circuitrhythm-5706-phase1-sequencer.syx').read_bytes()
    image=unpack_syx(syx,allow_extended=True)['image'];labels=tests.base.seq.arm_code()[1]
    class PackagedFileQueue(tests.UsbFileQueueTests):
        @classmethod
        def setUpClass(cls):cls.image,cls.labels,cls.evidence=image,labels,[]
    with (out/'tests.txt').open('w',encoding='utf-8') as f:
        result=unittest.TextTestRunner(stream=f,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(PackagedFileQueue))
    assert result.wasSuccessful(),'Native synchronous file queue tests failed'
    r=dict(scope='Native synchronous file FIFO/wait/worker;4113A file API and explicit RTOS task-switch/RAM boundaries',
        hardware_release='NO-GO',production_integrated=False,implementation_changed=False,experimental_tests=result.testsRun,
        packaged_syx_sha256=hashlib.sha256(syx).hexdigest(),packaged_image_sha256=hashlib.sha256(image).hexdigest(),
        native_file_queue='PASS_BOUNDED',result_before_credit_release='PASS',normal_and_sequencer='PASS_BOUNDED',
        reset_suspend_and_nested_msc_reader='PASS_BOUNDED',short_sample_read='STALE_TAIL_WRITE_NEGATIVE',
        observations=PackagedFileQueue.evidence,code_audit=audit(out/'audit',staging=True),native_contract=trace(out/'stock-contract'),
        unchanged_candidate_probe=candidate_negative(image,labels),
        remaining=['Native4113A file object/mount/open/seek/read/close/lower media owner graph remains a boundary. No physical short-read reproduction.',
                   '53E8C ignores file read status/count and may write stale bytes on partial read;no stock sample-loading patch was added.',
                   'Long-loop main reachability/retry/power latency,full43E1C UI/allocator/native boot/RTOS/checked2712B RAM/init/integration remain open.',
                   'Production Off/Stop loss,live-pattern storage alias,accepted TX ambiguity/raw ALT/parser/held/fault recovery and PHY/flash/DIN timing remain;no device APIs.'])
    (out/'report.json').write_text(json.dumps(r,indent=2),encoding='utf-8');return r


if __name__=='__main__':
    r=probe(sys.argv[1]);print(json.dumps(dict(tests=r['experimental_tests'],hardware_release=r['hardware_release'],short_sample_read=r['short_sample_read'])));raise SystemExit(2)
