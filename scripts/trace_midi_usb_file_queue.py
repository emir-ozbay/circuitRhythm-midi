"""Pinned native synchronous file submission/wait/worker contract."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from capstone import Cs,CS_ARCH_ARM,CS_MODE_THUMB,CS_MODE_MCLASS
from inspect_ui import load_image
from midi_usb_file_queue_test_support import PINS


def trace(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True);image=load_image();base=0x08010000
    md=Cs(CS_ARCH_ARM,CS_MODE_THUMB|CS_MODE_MCLASS);md.detail=True;windows=[]
    for (p,n),digest in PINS.items():
        raw=image[p-base:p-base+n];assert hashlib.sha256(raw).hexdigest()==digest
        (out/f'stock-{p:08x}.txt').write_text('\n'.join(f'{i.address:08x} {i.bytes.hex():12} {i.mnemonic} {i.op_str}' for i in md.disasm(raw,p)),encoding='utf-8')
        windows.append(dict(address=hex(p),bytes=n,sha256=digest))
    for p,target in ((0x08045EFE,0x0802ACA2),(0x0802ACAA,0x0802ACB8),(0x0802ACB0,0x0802ACF8),
                     (0x0802ACC8,0x08040DC4),(0x0802AD6C,0x08040DEE),(0x0802AE2E,0x0804113A)):
        i=next(md.disasm(image[p-base:p-base+4],p));assert i.mnemonic=='bl' and i.operands[0].imm==target
    assert image[0x0802B00C-base:0x0802B00E-base]==bytes.fromhex('e660') # result -> worker+C
    assert image[0x0802B030-base:0x0802B034-base]==bytes.fromhex('c3e8401f') # completion credit release
    r=dict(scope='Native45EB6 synchronous read ->72B FIFO ->wait ->2AD40 ->4113A ->result/credit',
        submission='4603A builds read args;45EB6 copies a72B packet;callback0 selects2ACA2 synchronous path.',
        request='2ACA2 clears worker+C;2ACB8/40DC4 copy72B packet into ring;2CA6C decrements credit2->1.',
        wait='2ACF8 uses native2508C/25056 current TCB/TLS0. Non-worker caller yields until credit returns2.',
        worker='2AD40/40DEE copy request to worker stack;op6 calls4113A;2B00C stores status at+C before exclusive credit release.',
        result_fifo='Not used by synchronous callback0 reads. Async request/result FIFO/callback dispatch is a distinct path.',
        native=['45EB6/4603A','2ACA2/2ACB8/2ACF8','40D9C/FIFO ring40DC4/40DEE/40E18',
                '2AD40 read branch and result/credit publication','2CA6C/23CEA byte semaphores','2508C/25056 TCB/TLS lookup',
                '53E24/53E8C/WAV/watchdog/MSC/SCSI/queued media worker/HAL/IRQ under prior overlays'],
        model=['Synthetic worker/TCB binding and registered FIFO object;native FIFO constructor allocates its ring.',
               'Only2AD12 yield models a task switch via checked71300 cave,native2AD40 executes before caller resumes.',
               '4113A lower file API copies RAM bytes and returns status/count;missing/short reads do not zero-fill.',
               'Progress/allocator/sample-flash models from previous long-loop fixture remain.',
               'Full RTOS scheduling,file descriptor mount/open/seek/read/close,lower media arbitration and timings remain open.'],
        negative='Injected short file read returns4/count2 through native queue;53E8C still writes requested2048B,including2046B prefilled stale data. Stock control-flow + synthetic file error,not physical reproduction.',
        hardware_release='NO-GO',windows=windows)
    (out/'file-queue-contract.json').write_text(json.dumps(r,indent=2),encoding='utf-8');return r


if __name__=='__main__':print(json.dumps(trace(sys.argv[1]),indent=2))
