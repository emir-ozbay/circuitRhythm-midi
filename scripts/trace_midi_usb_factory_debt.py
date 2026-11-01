"""Factory/class/caller contract with retained MAIN, not a full Packs UI trace."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from capstone import Cs,CS_ARCH_ARM,CS_MODE_THUMB,CS_MODE_MCLASS
from inspect_ui import load_image
from trace_midi_usb_factory import trace as factory_trace
from trace_midi_usb_staging import trace as staging_trace


def trace(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    f=factory_trace(out/'factory');s=staging_trace(out/'staging');b=load_image()
    md=Cs(CS_ARCH_ARM,CS_MODE_THUMB|CS_MODE_MCLASS);windows=[]
    for start,end in ((0x08035814,0x0803583C),(0x0803FC58,0x0803FC6C),(0x0802CB18,0x0802CB32)):
        data=b[start-0x08010000:end-0x08010000]
        (out/f'stock-{start:08x}.txt').write_text('\n'.join(
            f'{i.address:08x} {i.bytes.hex():12} {i.mnemonic} {i.op_str}' for i in md.disasm(data,start)),encoding='utf-8')
        windows.append(dict(address=hex(start),bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
    assert b[0x08035820-0x08010000:0x08035824-0x08010000]==bytes.fromhex('c1f34040')
    r=dict(scope='Native callers/formatter/factory/class/IRQ in synthetic RAM/MMIO, not physical hardware or full Packs UI',
        guards='Unsubmitted MAIN/owned partial SysEx cursor use the existing staging=True carry. MSC old read/CBW readers retire before native root class clear.',
        settings='Native35814 ->3FC58(slot2) reads bit17;0 ->1 (MIDI-only),1 ->101 (MIDI+MSC). Test view/store are synthetic; native callback/branch runs unchanged.',
        boot_wrapper='Native2CB18 calls43286 and packs low bytes1/current storage mode before432A8; unspecified upper16 bits remain native.',
        progress='Only native25870..25880 main advances retry/power/factory/MSC. Host stimulus supplies reset/address/configuration and modeled ACK/flush/completion/UART drain.',
        lifetime='MAIN bytes/cursor,owned payload,query ledger and committed realtime provenance survive factory before host reconfiguration;byte streams compare exactly.',
        races='A separate checked test-only71100 cave allows a second request or real native reset IRQ during native rebuild without overwriting the first executed71000 injection.',
        limits='Accepted MIDI TX ambiguity,partial parser/held input/fault/raw mode,full UI/project operations,other callers,RTOS/boot/RAM/init and real PHY/flash/UART timing remain open.',
        windows=windows,inherited_factory=f,inherited_staging=s)
    (out/'factory-debt-contract.json').write_text(json.dumps(r,indent=2),encoding='utf-8');return r


if __name__=='__main__':print(json.dumps(trace(sys.argv[1]),indent=2))
