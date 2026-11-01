"""Pinned native USB lifetime entry/caller evidence; never peripheral execution."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'scripts'), str(ROOT/'src')]
from inspect_ui import load_image
from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB, CS_MODE_MCLASS
import midi_usb_lifecycle_prototype as life


def trace(out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    data = load_image(); base = 0x08010000
    md = Cs(CS_ARCH_ARM, CS_MODE_THUMB | CS_MODE_MCLASS)
    expected = {
        0x08026828: [0x080666A2,0x080666B6,0x080666E6,0x080666FA],
        0x080269F0: [0x08029B2A], 0x08029AC8: [0x08029ABE],
        0x0802A374: [0x080401BA,0x080401E2],
        0x080405D4: [0x08040598,0x0804060A],
        0x08026988: [0x080526E8], 0x080268EC: [0x0805271A],
        0x08025ACC: [0x080252B8,0x0802C72C,0x0804044C],
    }
    actual = {key: [] for key in expected}
    for offset in range(0, len(data)-3, 2):
        if data[offset+1] & 0xF8 != 0xF0:
            continue
        for i in md.disasm(data[offset:offset+4], base+offset, count=1):
            if i.mnemonic in ('bl','b.w'):
                target = int(i.op_str.lstrip('#'), 16)
                if target in actual:
                    actual[target].append(i.address)
    assert actual == expected
    for address, (_,_,original) in life.GATES.items():
        assert data[address-base:address-base+len(original)] == original
    assert data[0x566A6:0x566A8] == bytes.fromhex('1027')  # RX16 records
    assert int.from_bytes(data[0x56704:0x56708], 'little') == 0x20005F70
    assert int.from_bytes(data[0x56708:0x5670C], 'little') == 0x20005CC8
    aliases = {0x080268E0: 0x080268D0, 0x080268E2: 0x080269FC, 0x08040620: 0x080405D4}
    for address, target in aliases.items():
        i = list(md.disasm(data[address-base:address-base+2], address))
        assert len(i) == 1 and i[0].mnemonic == 'b' and int(i[0].op_str.lstrip('#'),16) == target
    windows = [(0x0806668C,0x90),(0x08026828,0x52),(0x080268D0,0x138),
               (0x0802A374,0x11E),(0x08025ACC,0x96),(0x080525B2,0x1BC),
               (0x080405D4,0x4E),(0x080401AC,0x52)]
    evidence = []
    for address, size in windows:
        raw = data[address-base:address-base+size]
        (out/f'stock-{address:08x}.txt').write_text('\n'.join(
            f'{i.address:08x} {i.bytes.hex():12} {i.mnemonic} {i.op_str}'
            for i in md.disasm(raw, address)), encoding='utf-8')
        evidence.append(dict(address=hex(address), bytes=size, sha256=hashlib.sha256(raw).hexdigest()))
    report = {
        'scope': 'Pinned direct-call/alias candidates and disassembly; not a complete indirect graph',
        'direct_refs': {hex(k):[hex(v) for v in vs] for k,vs in actual.items()},
        'aliases': {hex(k):hex(v) for k,v in aliases.items()},
        'constructor_prefix': '6668C..666BA constructs TX81 with no RX ring and RX01 with16x64B records:1057B ring. Partial constructor execution only, not full boot.',
        'native_pop_owner': '29AC8 is the only direct269F0 caller found. Generic25B1A/2A470/2A426 are separately gated by registered pointer and native return PC.',
        'generic_clear': '2A374 zeroes ring indexes; direct stock callers401BA/E2 belong to MIDI TX port clear/poll, not a USB RX disconnect clear.',
        'disconnect_callback': '5261C disables endpoint lists through2C90C then forwards a callback; it contains no RX ring clear. Tests stub only the hardware close boundary.',
        'remaining': 'Arbitrary inline writers, IRQ/DMA ordering, complete vtable dispatch and TX session cancellation remain unproven.',
        'windows': evidence
    }
    (out/'lifecycle-contract.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    print(json.dumps(trace(sys.argv[1] if len(sys.argv)>1 else ROOT/'logs/usb-lifecycle-contract'), indent=2))
