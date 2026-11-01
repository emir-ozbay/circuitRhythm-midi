"""Read-only pinned5706 SysEx entry/caller/payload evidence. No device APIs."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
sys.path.insert(0, str(ROOT/'src'))
from inspect_ui import load_image
from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB, CS_MODE_MCLASS


def trace(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    image, base = load_image(), 0x08010000
    md = Cs(CS_ARCH_ARM, CS_MODE_THUMB | CS_MODE_MCLASS)
    def disasm(start, end):
        return [f'{i.address:08X} {i.bytes.hex():12} {i.mnemonic} {i.op_str}'
                for i in md.disasm(image[start-base:end-base], start)]
    def continuation(start):
        rows = []
        for ins in md.disasm(image[start-base:start-base+16], start):
            rows.append(f'{ins.address:08X} {ins.bytes.hex():12} {ins.mnemonic} {ins.op_str}')
            if (ins.mnemonic in ('b.w', 'bx') or
                    ins.mnemonic.startswith('pop') and 'pc' in ins.op_str):
                break
        return rows
    targets = {0x08040232: [], 0x0804028C: [], 0x080298B8: []}
    # Scan candidate Thumb wide branches at halfword boundaries; this is not
    # a whole-image control-flow proof (literal/data can resemble instructions).
    for offset in range(0, len(image)-3, 2):
        if image[offset+1] & 0xF8 != 0xF0:
            continue
        for ins in md.disasm(image[offset:offset+4], base+offset, count=1):
            if ins.mnemonic not in ('bl', 'b.w'):
                continue
            target = int(ins.op_str.lstrip('#'), 16)
            if target in targets:
                targets[target].append(ins.address)
    pointers = {}
    for address in (0x08040232, 0x0804028C):
        pointer = (address|1).to_bytes(4, 'little')
        pointers[hex(address)] = [hex(base+n) for n in range(0, len(image)-3, 4)
                                  if image[n:n+4] == pointer]
    assert pointers == {'0x8040232': ['0x8068ab4'], '0x804028c': ['0x8068ab8']}
    assert not targets[0x08040232] and not targets[0x0804028C]
    assert len(targets[0x080298B8]) == 12
    from midi_sysex_retry_test_support import CALLERS
    assert {site for _, site, _, _ in CALLERS} == set(targets[0x080298B8])
    ranges = [(0x0804016C, 0x0804027A), (0x0804028C, 0x0804042C),
              (0x08029714, 0x080297C0), (0x080298B8, 0x080299C0),
              (0x08026F0C, 0x08026F38), (0x0802CBE4, 0x0802CBF8),
              (0x080468EC, 0x08046958)]
    for start, end in ranges:
        (out/f'stock-{start:08x}.txt').write_text('\n'.join(disasm(start, end)), encoding='utf-8')
    result = {
        'scope': 'Pinned bytes/Capstone, not execution or IRQ/wire evidence',
        'port_entry_pointer_references': pointers,
        'candidate_direct_call_sites': {hex(k): [hex(n) for n in v] for k, v in targets.items()},
        'router_call_continuations': {hex(n): continuation(n) for n in targets[0x080298B8]},
        'caller_contracts': [{'entry': hex(entry), 'callsite': hex(site),
                              'source_lifetime': lifetime, 'result': behavior,
                              'local_retry': False}
                             for entry, site, lifetime, behavior in CALLERS],
        'port_return': '1 accepted;0 driver not ready. Existing transfer may spin via vtable+14.',
        'router_return': '0 all selected ports accepted;1 invalid payload/length or any port rejected.',
        'payload_lifetime': '40264 copies descriptor fields only. Worker40378 reads borrowed pointer. Router29978 copies caller bytes into a shared buffer before port fanout.',
        'pending_disconnect': '4028C returns0 when ready=0 even with remaining bytes; unsafe as a raw payload ownership predicate.',
        'caller_retry_limit': '26F36 restores saved r0 (ignores router result);2CBF4 returns result;46954 tail-forwards. No universal retry contract is established.',
        'callback_owner': '46934/46938 store function/context in20006EE0/+4 before298B8 admission;468EC later reads the current global pair. A rejected newer caller can replace the older owner unless guarded before4691A.',
    }
    (out/'sysex-contract.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    return result


if __name__ == '__main__':
    print(json.dumps(trace(sys.argv[1] if len(sys.argv) > 1 else ROOT/'logs/sysex-contract'), indent=2))
