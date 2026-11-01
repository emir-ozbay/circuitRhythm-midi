"""Pinned stock scatter-load and synchronous SysEx notification evidence.

Unicorn-only startup data initializer, not full boot, RTOS or device access.
"""
import json
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'scripts'), str(ROOT/'src')]
from inspect_ui import load_image
from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB, CS_MODE_MCLASS
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_THUMB, UC_MODE_MCLASS
from unicorn.arm_const import UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_PC
import midi_sysex_retry_prototype as retry


def trace(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    image = load_image()
    u = Uc(UC_ARCH_ARM, UC_MODE_THUMB | UC_MODE_MCLASS)
    u.mem_map(0x08000000, 0x80000)
    u.mem_write(0x08010000, image)
    u.mem_map(0x20000000, 0x50000)
    u.reg_write(UC_ARM_REG_SP, 0x2004F000)
    u.reg_write(UC_ARM_REG_LR, 0x0800E001)
    # Native scatter-loader only. Peripheral memory is deliberately unmapped.
    u.emu_start(0x08068A55, 0x0800E000, count=1000000)
    assert u.reg_read(UC_ARM_REG_PC) == 0x0800E000
    event = struct.unpack('<8I', u.mem_read(retry.NATIVE_EVENT, 32))
    assert event == (retry.NATIVE_EVENT_VTABLE, 0, 0, 0, 0, 0, 0, 0)
    vtable = struct.unpack('<2I', u.mem_read(event[0], 8))
    assert vtable == (0x0802D44D, retry.NATIVE_NOTIFY | 1)
    pins = {0x080263CC: retry.NATIVE_EVENT, 0x08046964: retry.NATIVE_EVENT,
            0x08046968: retry.NATIVE_OWNER_ADAPTER, 0x08046958: retry.NATIVE_OWNER}
    for address, expected in pins.items():
        assert struct.unpack_from('<I', image, address-0x08010000)[0] == expected
    md = Cs(CS_ARCH_ARM, CS_MODE_THUMB | CS_MODE_MCLASS)
    for start, end in [(0x080299A8, 0x080299C2), (0x08024B68, 0x08024B90),
                       (0x080468EC, 0x08046958), (0x0802D44C, 0x0802D46E),
                       (0x080297DE, 0x080297FE), (0x08068A54, 0x08068A7C)]:
        (out/f'stock-{start:08x}.txt').write_text('\n'.join(
            f'{i.address:08X} {i.bytes.hex():12} {i.mnemonic} {i.op_str}'
            for i in md.disasm(image[start-0x08010000:end-0x08010000], start)), encoding='utf-8')
    result = {
        'scope': 'Pinned bytes/Capstone and isolated native scatter-load in Unicorn; no full boot or hardware',
        'event_object': hex(retry.NATIVE_EVENT), 'initial_words': [hex(n) for n in event],
        'vtable': [hex(n) for n in vtable], 'listener_capacity_from_layout': 3,
        'notification_abi': '24B68(object,r1=event,r2=router) -> callback(event,router,listener_context). 468EC replaces r1 with global owner context and tail-calls global owner function.',
        'trigger': '299B0 invokes vtable+4 synchronously after all selected ports ACCEPT, before payload drains. r1=0. It is not a discovered deferred job/wire-completion event.',
        'poll': '297DE only invokes each port poll; no completion notification in this function.',
        'negative_scope': 'No claim that all indirect producers/events are found; pointer/count lifecycle requires production review.'
    }
    (out/'notification-contract.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    return result


if __name__ == '__main__':
    print(json.dumps(trace(sys.argv[1] if len(sys.argv)>1 else ROOT/'logs/sysex-notification-trace'), indent=2))
