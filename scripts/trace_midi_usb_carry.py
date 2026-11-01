"""Native queue/staging/parent bytes and explicit generated carry boundaries."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from capstone import Cs,CS_ARCH_ARM,CS_MODE_THUMB,CS_MODE_MCLASS
from inspect_ui import load_image
import midi_usb_carry_prototype as carry
import midi_usb_session_prototype as session
import midi_usb_lifecycle_prototype as life
import midi_recovery_prototype as recovery


def trace(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True);b=load_image();base=0x08010000
    md=Cs(CS_ARCH_ARM,CS_MODE_THUMB|CS_MODE_MCLASS)
    windows=[]
    for p,n in ((0x080401AC,0x1E),(0x0802B3CE,0x1E),(0x0802B408,0x4E),(0x0802B498,0x1A),(0x080268D0,0x12),(0x08068A2C,0x12)):
        raw=b[p-base:p-base+n]
        (out/f'stock-{p:08x}.txt').write_text('\n'.join(f'{i.address:08x} {i.bytes.hex():12} {i.mnemonic} {i.op_str}' for i in md.disasm(raw,p)),encoding='utf-8')
        windows.append(dict(address=hex(p),bytes=n,sha256=hashlib.sha256(raw).hexdigest()))
    r=dict(scope='Pinned native bytes and generated entry expectations; not whole-device proof',
        original_cycle='cl_poll freezes accepted ledger/parser debt;ss_quiet requires that debt/queued TX empty before physical close. Native main alone cannot resolve it.',
        original_destructive_reset='ss_step invokes native401AC and resets USB driver/ledger/parser at seal; safe only under its old logical-idle predicate.',
        eligibility='No SS TX_ACTIVE, driver+12hex=0/+14hex=0, main/alt lengths0 and selected MAIN; software TX cursor0 or cursor==total; no partial parser/held input/USB port fault or active software producer.',
        carry='Full disable/ACK/shared FIFO/AHB/TX flush first;retire only HAL transfer objects and RX job. Advance physical epoch while keeping RX FIFO/parser/SCANNED/EXPECTED_READ and all TX software bytes/cursors.',
        reset_race='Separate CY BUSY rejects nested ss_step while old SS BUSY stays0;native reset IRQ can advance generation. Seal/resume atomic commits reject changed generations.',
        planned_close='Registered USB rp_poll is parked only during owned carry and CLOSING..SEALED; planned sleep does not poison queued Note Off with an unexpected-disconnect FAULT. Real preexisting fault is retained.',
        model_limit='IRQ completion byte-stream checks under synthetic cancellation/tick/PHY/RTOS/flash/UART drain. In-flight or staged debt/partial cursor/parser/held musical input/genuine fault do not receive carry. Legacy empty-debt cancellation policy unchanged.',
        generated_gates=[dict(address=hex(p),expected=raw.hex(),entry=name) for p,(raw,name) in carry.sites().items()],windows=windows)
    (out/'carry-contract.json').write_text(json.dumps(r,indent=2),encoding='utf-8');return r


if __name__=='__main__':print(json.dumps(trace(sys.argv[1]),indent=2))
