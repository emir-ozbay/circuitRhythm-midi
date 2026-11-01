"""Pinned stock endpoint lifetime evidence; does not execute physical MMIO."""
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from inspect_ui import load_image
from capstone import Cs,CS_ARCH_ARM,CS_MODE_THUMB,CS_MODE_MCLASS


def trace(out):
    out=Path(out); out.mkdir(parents=True,exist_ok=True)
    data=load_image(); base=0x08010000; md=Cs(CS_ARCH_ARM,CS_MODE_THUMB|CS_MODE_MCLASS)
    def word(address): return int.from_bytes(data[address-base:address-base+4],'little')
    assert word(0x08053454)==0xEFF37800
    assert data[0x42edc:0x42ee0]==bytes.fromhex('70b44d78')
    windows=[(0x08026880,0x70),(0x0802691E,0xCE),(0x0802B408,0x10A),
             (0x0802C9B8,0x38),(0x080401AC,0x52),(0x0805261C,0x120),
             (0x08042FD8,0x80),(0x0804301A,0x60),(0x08052E04,0x38),
             (0x08052EDC,0x76),(0x08052F52,0x188),(0x08053250,0x64)]
    evidence=[]
    for address,size in windows:
        raw=data[address-base:address-base+size]
        (out/f'stock-{address:08x}.txt').write_text('\n'.join(
            f'{i.address:08x} {i.bytes.hex():12} {i.mnemonic} {i.op_str}' for i in md.disasm(raw,address)),encoding='utf-8')
        evidence.append(dict(address=hex(address),bytes=size,sha256=hashlib.sha256(raw).hexdigest()))
    report=dict(scope='Pinned stock byte/disassembly evidence, not a complete IRQ graph',
        tx_lifetime='Native26880 decrements endpoint availability before2C9B8;268D0 releases it. Retry reader drain is earlier than endpoint completion.',
        rx_callback='26988 receives port in r0 and byte count in r1, then2691E publishes staging records and tail-rearms269AC. It has no epoch/ticket argument.',
        endpoint_close='Pinned52EDC masks endpoint interrupts and ANDs endpoint control with EFF37800. This stock body does not request SNAK/EPDIS, poll disable acknowledgment or flush.',
        flush='52E04 flushes a selected TX FIFO with a bounded busy wait.52E22 flushes shared RX.53250 stops all endpoints and flushes globally; unsuitable for MIDI-only cancellation.',
        irq_bridge='NOT_IMPLEMENTED: production callbacks cannot be replaced by tokens copied from current endpoint state. The token must belong to the immutable submitted job.',
        limits='Silicon identity, exact reset/disconnect ordering, all indirect IRQ callbacks, DMA/cache visibility and absence of a post-barrier bus master remain unproven.',
        primary_references=[
            'https://github.com/STMicroelectronics/stm32f7xx-hal-driver/blob/master/Src/stm32f7xx_ll_usb.c',
            'https://raw.githubusercontent.com/STMicroelectronics/cmsis-device-f7/master/Include/stm32f745xx.h'],
        reference_scope='Comparison and register-name reference only; neither identifies the physical MCU nor proves this stock build follows the latest HAL.',
        windows=evidence)
    (out/'session-contract.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


if __name__=='__main__': print(json.dumps(trace(sys.argv[1] if len(sys.argv)>1 else ROOT/'logs/usb-session-contract'),indent=2))
