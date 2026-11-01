"""Pin native format/flush/admission windows for optional staging carry."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from capstone import Cs,CS_ARCH_ARM,CS_MODE_THUMB,CS_MODE_MCLASS
from inspect_ui import load_image
import midi_usb_carry_prototype as carry


def trace(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True);image=load_image();windows=[]
    md=Cs(CS_ARCH_ARM,CS_MODE_THUMB|CS_MODE_MCLASS)
    for start,end in ((0x080402FC,0x080403A2),(0x0802B460,0x0802B4B2),
                      (0x0802B3BC,0x0802B3C8),(0x08026880,0x080268D0)):
        data=image[start-0x08010000:end-0x08010000]
        text='\n'.join(f'{i.address:08x} {i.bytes.hex():12} {i.mnemonic} {i.op_str}' for i in md.disasm(data,start))
        (out/f'stock-{start:08x}.txt').write_text(text,encoding='utf-8')
        windows.append(dict(address=hex(start),bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
    assert image[0x1B498:0x1B49C]==carry.sites(staging=True)[0x0802B498][0]
    r=dict(scope='Pinned native byte/disassembly contract; no physical receiver or timing proof',
        producer='402FC consumes immutable SysEx bytes and advances software cursor. Native2B460 adds4B USB events to selected MAIN until64B.',
        bug='2B498 calls raw2B3BC, whose return1 hides ss_tx_arm rejection;2B4AE clears MAIN unconditionally. An IRQ close before admission therefore discards prepared bytes.',
        fix='Registered CPU MAIN flush uses the pinned endpoint26880 gate directly; MAIN is consumed only if TX_TICKET changes. Closure-before-admission retains bytes; accepted transfer ambiguity remains strict.',
        full_main='402FC returns before flushing if MAIN is full at entry. Registered OPEN rp_poll flushes retained MAIN before continuing its normal native worker.',
        admission='No TX_ACTIVE/producer/flush owner;MAIN length0..64 multiple4,selected MAIN,64B capacities,ALT length/pointer idle,raw count/mode0. Partial cursor only for USB-accepted immutable retry slot and matching descriptor length.',
        retention='Same full disable/ACK/shared RX/AHB/TX flush and generation checks. RX ledger/software bytes and staged MAIN remain in place. No rewind or reconstruction.',
        limits='In-flight,raw ALT mode,partial parser,held input,existing port fault and physical/RTOS/boot/RAM/integration remain outside scope. Previous default variant machine code unchanged.',
        windows=windows)
    (out/'staging-contract.json').write_text(json.dumps(r,indent=2),encoding='utf-8');return r


if __name__=='__main__':print(json.dumps(trace(sys.argv[1]),indent=2))
