"""Read-only Circuit Rhythm 5706 checks; no MIDI, device access or flashing.

Usage: python verify_stock.py /path/to/circuitrhythm-firmware-5706.syx
Dependencies: capstone==5.0.9, unicorn==2.1.4
Source firmware is never changed. Output: verification.json, selected-disassembly.txt.
"""
from pathlib import Path
import ast, hashlib, importlib.util, json, struct, sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'vendor'))
from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB, CS_MODE_MCLASS
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_THUMB, UC_MODE_MCLASS, UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_PC

def module(name, rel):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

syx = module('arr_syx', 'sources/arrhythmia/tools/syx.py')
rh = module('rh_fw', 'sources/CIRCUIT-REMIX/tools/rh_fw.py')
ex = module('extract', 'sources/cr_stereo/extract_firmware.py')
raw = Path(sys.argv[1]).read_bytes()
sha = lambda b: hashlib.sha256(b).hexdigest()
assert sha(raw) == rh.STOCK_5706['syx_sha256'], 'Unexpected input firmware'
p = syx.parse(raw)
b = p['image']
assert p['crc_ok'] and p['device'] == 0x63 and p['header_prefix'][0] == 0
assert sha(b) == rh.STOCK_5706['image_sha256']
assert b == rh.decode(raw)['image'] == ex.extract(raw)[0]
assert raw == syx.build(b, p['init'], p['header_prefix']) == rh.encode(b)
BASE = 0x08010000
md = Cs(CS_ARCH_ARM, CS_MODE_THUMB | CS_MODE_MCLASS)
report = {'input_sha256': sha(raw), 'image_sha256': sha(b), 'input_bytes': len(raw),
          'image_bytes': len(b), 'crc32_mpeg2': f'{p["crc"]:08x}',
          'three_decoders_agree': True, 'two_encoders_byte_identical': True,
          'build_number_at_0x1ca': struct.unpack_from('<H', b, 0x1ca)[0],
          'identity_string': b[0x1ce:0x1ee].split(b'\0')[0].decode(),
          'transport_version_bytes': p['init'][2:].hex(' '),
          'initial_sp': hex(struct.unpack_from('<I', b)[0]),
          'reset_vector': hex(struct.unpack_from('<I', b, 4)[0])}

# Parse literal address maps without executing the upstream build script.
tree = ast.parse((ROOT / 'sources/arrhythmia/tools/build_lightshow.py').read_text())
maps = {}
for node in tree.body:
    if isinstance(node, ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id in ('STOCK_BL', 'STOCK_BW', 'VT_SITES'):
                maps[target.id] = ast.literal_eval(node.value)
checks = []
for key, mnemonic in [('STOCK_BL', 'bl'), ('STOCK_BW', 'b.w')]:
    for addr, target in maps[key].items():
        ins = next(md.disasm(b[addr-BASE:addr-BASE+4], addr))
        ok = ins.mnemonic == mnemonic and int(ins.op_str.lstrip('#'), 16) == target
        checks.append({'kind': key, 'address': hex(addr), 'expected': hex(target),
                       'actual': ins.mnemonic + ' ' + ins.op_str, 'pass': ok})
for name, (addr, target) in maps['VT_SITES'].items():
    got = struct.unpack_from('<I', b, addr-BASE)[0]
    checks.append({'kind': 'vtable', 'name': name, 'address': hex(addr),
                   'expected': hex(target), 'actual': hex(got), 'pass': got == target})
assert all(c['pass'] for c in checks)
report['upstream_hook_checks'] = checks

def machine():
    u = Uc(UC_ARCH_ARM, UC_MODE_THUMB | UC_MODE_MCLASS)
    u.mem_map(0x08000000, 0x80000)
    u.mem_write(BASE, b)
    u.mem_map(0x20000000, 0x50000)
    return u

STOP = 0x0800f000
def invoke(u, addr, *args):
    for reg, arg in zip([UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3], args):
        u.reg_write(reg, arg)
    u.reg_write(UC_ARM_REG_SP, 0x2004f000)
    u.reg_write(UC_ARM_REG_LR, STOP | 1)
    u.emu_start(addr | 1, STOP, count=1000)
    assert u.reg_read(UC_ARM_REG_PC) == STOP, 'Function failed to return within instruction budget'

# Real stock step setter AND real stock double-buffer accessor. No mocked function calls.
# Synthetic object fixtures cover both active buffers and clean/already-dirty words.
u = machine()
obj, a, z = 0x20001000, 0x20002000, 0x20003000
setters = {'note': (0x08054a5c, 0), 'gate': (0x08054a84, 8), 'flags': (0x08054ab0, 16)}
cases = 0
for name, (address, group) in setters.items():
    for step in range(32):
        word = group + step // 4
        for active in (0, 0xffffffff):
            for dirty in (0, 1 << word):
                for value in (0, 1, 127, 255):
                    buf_a = bytes((i * 7 + 3) & 255 for i in range(128))
                    buf_z = bytes((i * 11 + 5) & 255 for i in range(128))
                    u.mem_write(a, buf_a); u.mem_write(z, buf_z)
                    u.mem_write(obj, struct.pack('<5I', 0, active, dirty, a, z))
                    expected = [bytearray(buf_a), bytearray(buf_z)]
                    source = 1 if active else 0
                    dest = source ^ 1
                    if not dirty:
                        expected[dest][word*4:word*4+4] = expected[source][word*4:word*4+4]
                    expected[dest][word*4 + step%4] = value
                    invoke(u, address, obj, step, value)
                    assert u.mem_read(a,128) == expected[0], (name,step,active,dirty,value,'a')
                    assert u.mem_read(z,128) == expected[1], (name,step,active,dirty,value,'b')
                    assert struct.unpack('<I',u.mem_read(obj+8,4))[0] == dirty | (1 << word)
                    cases += 1
report['stock_step_setter_emulation'] = {
    'cases_passed': cases, 'steps': '0..31', 'fields': list(setters),
    'actual_firmware_functions': [hex(x[0]) for x in setters.values()] + ['0x0803fd26'],
    'mocked_calls': [], 'synthetic_ram': True,
    'limit': 'Does not test UI dispatch, notification/commit, save/load, transport, hardware or timing.'}

# Real MIDI output mask dispatcher, with fake port callbacks (no hardware queues).
u = machine()
obj, arr, msg = 0x20001000, 0x20001100, 0x20001200
u.mem_write(obj+0x14,struct.pack('<I',arr)+bytes([3]))
ports = [0x20002000 + i*0x100 for i in range(3)]
u.mem_write(arr,struct.pack('<3I',*ports))
callbacks = [0x0800e000+i*4 for i in range(3)]
for port, callback in zip(ports,callbacks):
    vt = port+0x40
    u.mem_write(port,struct.pack('<I',vt))
    u.mem_write(vt+8,struct.pack('<I',callback|1))
    u.mem_write(callback,bytes.fromhex('7047'))
u.mem_write(msg,bytes([0x90,60,100,0]))
seen=[]
def callback_hook(uc, address, size, data):
    if address in callbacks:
        idx=callbacks.index(address)
        assert uc.reg_read(UC_ARM_REG_R0)==ports[idx]
        assert uc.reg_read(UC_ARM_REG_R1)==msg
        seen.append(idx)
        uc.reg_write(UC_ARM_REG_R0,1)  # synthetic success from port backend
u.hook_add(UC_HOOK_CODE,callback_hook)
for mask in range(8):
    seen.clear()
    invoke(u,0x0802986a,obj,mask,msg)
    assert seen == [i for i in range(3) if mask >> i & 1], (mask,seen)
report['midi_mask_dispatch_emulation'] = {'cases_passed':8,'function':'0x0802986a',
    'mocked_calls':'Three output-port callbacks return success; no actual MIDI transmission or queue pressure tested.'}

ranges = [('step_setters',0x08054a5c,0x84),('param_write_accessor',0x0803fd26,0x48),
          ('midi_mask_dispatch',0x0802986a,0x48),('step_player',0x0804afbc,0x98),
          ('note_router_on',0x0803b7ec,0x104),('sample_pad_press',0x0805c1ac,0x60)]
lines=[]
for name,addr,length in ranges:
    lines.append(f'\n{name} @ {addr:#010x}')
    for ins in md.disasm(b[addr-BASE:addr-BASE+length],addr):
        lines.append(f'{ins.address:08x} {ins.bytes.hex():10} {ins.mnemonic:10} {ins.op_str}')
(ROOT/'selected-disassembly.txt').write_text('\n'.join(lines)+'\n')
(ROOT/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'round_trip':'PASS','hook_sites_passed':len(checks),'step_setter_cases_passed':cases,
                  'midi_dispatch_cases_passed':8,'build':report['build_number_at_0x1ca']},indent=2))
