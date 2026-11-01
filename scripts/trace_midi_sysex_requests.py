"""Read-only pinned5706 request/formatter/caller evidence; no device access."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'scripts'), str(ROOT/'src')]
from inspect_ui import load_image
from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB, CS_MODE_MCLASS
import midi_sysex_retry_prototype as retry


def trace(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    image, base = load_image(), 0x08010000
    md = Cs(CS_ARCH_ARM, CS_MODE_THUMB | CS_MODE_MCLASS)
    expected = {0x08026F0C: [0x08026E4C], 0x0802CD60: [0x0802CD58],
                0x0802D0B0: [0x08043544, 0x080435D6],
                0x08032120: [0x0803ECBA], 0x08032154: [0x0803FAE2],
                0x08032188: [0x0803FB40], 0x080321BC: [0x0803F996],
                0x080321F4: [0x0803EDEC]}
    actual = {key: [] for key in expected}
    for offset in range(0, len(image)-3, 2):
        if image[offset+1] & 0xF8 != 0xF0:
            continue
        for i in md.disasm(image[offset:offset+4], base+offset, count=1):
            if i.mnemonic not in ('bl', 'b.w'):
                continue
            target = int(i.op_str.lstrip('#'), 16)
            if target in actual:
                actual[target].append(i.address)
    assert actual == expected
    assert image[0x170D0:0x170D6] == bytes.fromhex('f07e7f0601f7')
    for start, end in [(0x08026DE8, 0x08026E68), (0x08026F0C, 0x08026F38),
                       (0x0802CD1A, 0x0802CDA8), (0x0804350E, 0x0804360E),
                       (0x08032120, 0x08032228), (0x08029B96, 0x08029BB8),
                       (0x08029C1A, 0x08029C6C), (0x08024B68, 0x08024B90)]:
        (out/f'stock-{start:08x}.txt').write_text('\n'.join(
            f'{i.address:08X} {i.bytes.hex():12} {i.mnemonic} {i.op_str}'
            for i in md.disasm(image[start-base:end-base], start)), encoding='utf-8')
    result = {
        'scope': 'Pinned bytes/Capstone candidate crossrefs; not whole CFG or physical evidence',
        'call_sites': {hex(k): [hex(n) for n in v] for k, v in actual.items()},
        'upper_formatters': [{'entry': hex(entry), 'lower_return_pc': hex(ret), 'stack_argument_words': n}
                             for entry, (_, ret, n) in retry.REQUEST_GATES.items()],
        'void_ingress_dispatch': '29BAA USB and29C64 DIN call24B68 after404BC completed the message.24B68 ignores each listener r0;26DE8 also discards26F0C result. Producer failure alone does not retain RX request.',
        'ignored_response_origins': '26F0C universal inquiry;CD60 reached viaCD1A nibble response;D0B0 called after update-operation side effects at43544/435D6. Update handlers are disassembled only, not executed by this experiment.',
        'upstream_source_mutation': '32120/154/188/1BC/1F4 call46A54/46B18/46B50/46B74/46BAC BEFORE4691A. Stack args5..7 include source/output/callback/context.',
        'remaining': 'Native RX cursor/pop/ack or owned pending-request policy must retain a rejected inquiry before consumption, while preserving realtime/Off/Stop service. No such input hook is installed.'
    }
    (out/'request-contract.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    return result


if __name__ == '__main__':
    print(json.dumps(trace(sys.argv[1] if len(sys.argv)>1 else ROOT/'logs/sysex-request-contract'), indent=2))
