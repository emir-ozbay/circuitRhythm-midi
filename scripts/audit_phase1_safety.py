"""Offline independent transport/diff/disassembly audit; no device libraries.

Deliberately does not import the production SysEx codec or CRC implementation.
PASS here is byte-level evidence, not authorization to flash.
"""
from pathlib import Path
import hashlib
import json
import struct
import sys

from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB, CS_MODE_MCLASS
from capstone.arm import ARM_OP_IMM

ROOT = Path(__file__).resolve().parents[1]
BASE = 0x08010000
PIN = "11d604a6b6bef0d41378da03718658c7fe9c959ac24e7fef6563796b9932afaf"


def code_audit(candidate, stock, manifest, out, *, seq_options=None):
    """All cave instruction boundaries/branches and path-sensitive stack depths.

    Labels identify data and function entries only. Actual instructions and targets
    are independently decoded from the packaged image with Capstone.
    """
    sys.path.insert(0,str(ROOT/'src'))
    import seq_Patch as seq
    source, labels = seq.arm_code(**(seq_options or {}))
    cave = 0x0806A570
    assert candidate[cave-BASE:cave-BASE+len(source)] == source
    md = Cs(CS_ARCH_ARM,CS_MODE_THUMB|CS_MODE_MCLASS); md.detail=True
    data = set()
    for name in ('c_zero_word', 'c_proj_zero_word', 'c_proj_seq_word', 'pad_gate_zero_word', 'dispatch_guard_byte_two', 'save_btn_zero_word'):
        if name in labels:
            a = labels[name]
            assert a % 4 == 0
            data.update(range(a, a + 4))
    insns = {i.address:i for i in md.disasm(source,cave) if i.address not in data}
    # Raw zero alignment padding is data too (never a legitimate branch target).
    targets=set()
    constants=[]
    stock_targets = {
        0x08023690: 'unchanged diagnostic no-op; APSR/register-preserving overflow observer tail',
        0x08029AF2: 'USB RX next-port continuation (original CMP flags; no local frame)',
        0x08029B66: 'USB RX packet continuation (stolen LDR replayed; no local frame)',
        0x08037ED4: 'save serialization continuation (original push replayed)',
        0x0803DDE4: 'controller knob continuation (original prologue replayed)',
        0x0804820C: 'pattern commit continuation (original 40-byte push replayed)',
        0x08022CF0: 'memcpy',
        0x08025A9C: 'allocator continuation',
        0x08037C84: 'new proj callback',
        0x08037DD0: 'load error cleanup',
        0x08037E3C: 'load success callback',
        0x08038074: 'clear callback',
        0x08038078: 'save success callback',
        0x080460C8: 'enqueue stock Close request',
        0x0803FBEC: 'store notify',
        0x0803FC58: 'store read',
        0x0803FD26: 'store write',
        0x0803F5AC: 'MIDI receiver Note On continuation (24-byte stock push and MOVS replayed)',
        0x080407F0: 'sample preview stock start',
        0x08040874: 'sample DSP voice trigger',
        0x08046780: 'sample Note On wrapper',
        0x080467D2: 'sample voice force off',
        0x08046DDE: 'timer schedule',
        0x08047038: 'action dispatch',
        0x0804D6B6: 'grid mode update',
        0x0804D7A4: 'grid press continuation',
        0x0804DAAC: 'grid release/cancel transition',
        0x0804DC86: 'resolve subview',
        0x0804DF3E: 'transform pad',
        0x0804F27E: 'draw project LEDs',
        0x08051B7A: 'button press ownership',
        0x08051C82: 'Packs admission',
        0x08052108: 'vtable slot 7 dispatcher',
        0x0805800E: 'active track getter',
        0x0805CF24: 'step LED calculator',
    }
    for i in insns.values():
        if i.mnemonic in ('bl','b.w','b','cbz','cbnz') or i.mnemonic.startswith(('beq','bne','bhi','bls','bhs','blo','bge','blt','bgt','ble','bpl','bmi','bvs','bvc','bcs','bcc')):
            t=[o.imm for o in i.operands if o.type==ARM_OP_IMM][-1]
            if t>=cave:
                assert t in insns, f'branch into data or half instruction: {i.address:#x}->{t:#x}'
            else:
                assert BASE+512<=t<BASE+len(stock)
                assert t in stock_targets, f'Unreviewed direct stock target {t:#x}'
            targets.add(t)
        if i.mnemonic=='adr':
            t=((i.address+4)&~3)+i.operands[1].imm
            if t == labels.get('record_start_noop'):
                assert t%4 == 0 and candidate[t-BASE:t-BASE+2] == bytes.fromhex('7047')
                nxt = insns[i.address + i.size]
                assert i.op_str.startswith('r5,') and nxt.mnemonic == 'adds' and nxt.op_str == 'r5, #1'
            elif t in (labels.get('c_save_close_result'), labels.get('c_load_close_result')):
                assert t%4 == 0 and t in insns and insns[t].mnemonic.startswith('push')
                nxt = insns[i.address + i.size]
                assert i.op_str.startswith('r1,') and nxt.mnemonic == 'adds' and nxt.op_str == 'r1, #1'
            else:
                assert t in data and t%4==0
        if i.mnemonic=='movw':
            nxt=insns.get(i.address+4)
            if nxt and nxt.mnemonic=='movt' and nxt.operands[0].reg==i.operands[0].reg:
                v=i.operands[1].imm | (nxt.operands[1].imm<<16)
                constants.append(hex(v))
                assert not (0x40000000<=v<0x60000000 or 0x1FFF0000<=v<0x20000000)
    for p in manifest['patches']:
        a=int(p['address'],16)
        if a>=cave: continue
        if a == seq.HOOK_MIDI_TX_OVERFLOW:
            # Keep the new BL in the final slot of the existing IT block.
            prefix = bytes.fromhex('11bf012400241748')
            assert stock[0x08040220-BASE:0x08040228-BASE] == prefix
            assert candidate[0x08040220-BASE:0x08040228-BASE] == prefix
        old=list(md.disasm(stock[a-BASE:a-BASE+p['length']],a))
        new=list(md.disasm(candidate[a-BASE:a-BASE+p['length']],a))
        assert sum(i.size for i in old)==p['length']==sum(i.size for i in new)
        for i in new:
            if i.mnemonic in ('bl','b.w'):
                assert i.operands[0].imm in insns
    functions = {n: a for n, a in labels.items() if n.startswith('c_') and not any(k in n for k in ('zero_word', 'byte_two', 'seq_word'))}
    results={}
    for name,start in functions.items():
        work=[(start,0)]; visited=set(); exits=set(); max_depth=0; calls=[]
        while work:
            pc,depth=work.pop()
            if (pc,depth) in visited: continue
            visited.add((pc,depth)); assert len(visited)<5000
            i=insns[pc]; m=i.mnemonic; op=i.op_str
            if m.startswith('push'): depth-=4*len(i.operands)
            if m.startswith('pop'): depth+=4*len(i.operands)
            if m in ('sub','add') and op.startswith('sp,'):
                depth+=(-1 if m=='sub' else 1)*i.operands[-1].imm
            max_depth=max(max_depth,-depth)
            if m=='bl':
                assert depth%8==0,(name,hex(pc),depth)
                calls.append(hex(i.operands[0].imm))
            if (m.startswith('pop') and 'pc' in op) or (m=='bx' and op=='lr'):
                allowed=(0,16) if name=='c_page_btn_mode0' else (0,)
                assert depth in allowed,(name,hex(pc),depth)
                exits.add(depth); continue
            if m in ('b','b.w'):
                t=i.operands[0].imm
                if t<cave:
                    allowed = (-24,) if name == 'c_grid_press_gate' and t == 0x0804D7A4 else (0,)
                    if name == 'c_pattern_commit_dirty' and t == 0x0804820C:
                        assert stock[0x38208:0x3820C] == bytes.fromhex('2de9f84f')
                        allowed = (-40,)
                    if name == 'c_knob_dirty_gate' and t == 0x0803DDE4:
                        assert stock[0x2DDE0:0x2DDE4] == bytes.fromhex('70b50446')
                        allowed = (-16,)
                    if name == 'c_save_snapshot' and t == 0x08037ED4:
                        assert stock[0x27ED0:0x27ED4] == bytes.fromhex('2de9f847')
                        allowed = (-36,)
                    if name == 'c_midi_receive_on_stock' and t == 0x0803F5AC:
                        assert stock[0x2F5A8:0x2F5AC] == bytes.fromhex('f8b51d00')
                        allowed = (-24,)
                    assert depth in allowed,(name,hex(pc),depth)
                    exits.add(depth); continue
                work.append((t,depth)); continue
            if m.startswith(('beq','bne','bhi','bls','bhs','blo','bge','blt','bgt','ble','bpl','bmi','bvs','bvc','bcs','bcc')) or m in ('cbz','cbnz'):
                work.append((i.operands[-1].imm,depth))
            work.append((pc+i.size,depth))
        results[name]={'entry':hex(start),'local_stack_max_bytes':max_depth,
                       'exit_sp_deltas':sorted(exits),'calls':sorted(set(calls)),
                       'reachable_states':len(visited)}
    # The sole +16 return intentionally consumes the unchanged caller frame.
    assert stock[0x0804DCB2-BASE:0x0804DCB2-BASE+2]==bytes.fromhex('38b5')
    assert stock[0x0804D7A0-BASE:0x0804D7A0-BASE+2]==bytes.fromhex('f8b5')
    report={'functions':results,'direct_external_targets':sorted(hex(t) for t in targets if t<cave),
            'reviewed_stock_targets':{hex(t):stock_targets[t] for t in targets if t<cave},
            'movw_movt_constants':constants,
            'limits':'Direct cave control flow only; indirect stock callbacks/storage are not proven safe by this scan.'}
    (out/'code-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


def decode(raw):
    frames, pos = [], 0
    while pos < len(raw):
        assert raw[pos:pos+5] == bytes.fromhex("f000202900"), hex(pos)
        end = raw.index(0xF7, pos)
        frame = raw[pos:end+1]
        assert all(b < 128 for b in frame[1:-1])
        frames.append(frame)
        pos = end + 1
    assert frames[0][5] == 0x71 and len(frames[0]) == 15
    assert frames[0][6:8] == bytes([1, 0x63])
    assert frames[1][5] == 0x7C and len(frames[1]) == 30
    assert frames[1][6] == 0, "bootloader target forbidden"
    assert frames[-1][5] == 0x73
    assert all(f[5] == 0x72 for f in frames[2:-1])
    header = frames[1][6:-1]
    assert all(n < 16 for n in header[7:])
    size = int(''.join(format(x, 'x') for x in header[7:15]), 16)
    crc = int(''.join(format(x, 'x') for x in header[15:23]), 16)
    assert 0x5A570 <= size <= 0x70000 and size % 4 == 0
    assert len(frames) == (size + 31) // 32 + 2
    chunks = []
    for f in [frames[-1]] + frames[2:-1]:
        assert len(f) == 44
        acc = 0
        for v in f[6:-1]:
            acc = (acc << 7) | v
        assert acc & 7 == 0
        chunks.append((acc >> 3).to_bytes(32, 'big'))
    padded = b''.join(chunks)
    assert padded[size:] == b'\xff' * (len(padded)-size)
    image = padded[:size]
    check = 0xFFFFFFFF
    for byte in image:
        check ^= byte << 24
        for _ in range(8):
            check = ((check << 1) ^ (0x04C11DB7 if check & 0x80000000 else 0)) & 0xFFFFFFFF
    assert check == crc
    return image, {'frames': len(frames), 'size': size, 'crc': f'{crc:#010x}',
                   'init_hex': frames[0].hex(), 'header_hex': frames[1].hex(),
                   'finish_hex': frames[-1].hex(), 'sha256': hashlib.sha256(raw).hexdigest()}


def audit(out=None):
    if out is None:
        out = ROOT / 'logs' / 'phase1-safety-audit'
    out.mkdir(parents=True, exist_ok=True)
    stock_raw = (ROOT/'stock/circuitrhythm-firmware-5706.syx').read_bytes()
    assert hashlib.sha256(stock_raw).hexdigest() == PIN
    stock, sm = decode(stock_raw)
    raw = (ROOT/'build/circuitrhythm-5706-phase1-sequencer.syx').read_bytes()
    candidate, cm = decode(raw)
    assert stock[:512] == candidate[:512]
    assert b'DR1.1.5143.5706' in stock[:512]
    assert sm['init_hex'] == cm['init_hex'] and sm['finish_hex'] == cm['finish_hex']
    manifest = json.loads((ROOT/'build/circuitrhythm-5706-phase1-sequencer.manifest.json').read_text())
    assert cm['sha256'] == manifest['output']['sha256']
    assert len(candidate) == manifest['output']['image_size']
    assert cm['crc'] == manifest['output']['image_crc32_mpeg2']
    assert hashlib.sha256(candidate).hexdigest() == manifest['output']['image_sha256']
    old = stock + b'\xff' * (len(candidate)-len(stock))
    actual = {BASE+i for i, (a,b) in enumerate(zip(old, candidate)) if a != b}
    declared, covered = set(), set()
    for p in manifest['patches']:
        a, n = int(p['address'], 16), p['length']
        assert BASE+512 <= a < a+n <= 0x08080000
        r = set(range(a,a+n))
        assert not covered & r
        covered |= r
        assert old[a-BASE:a-BASE+n].hex() == p['expected_hex']
        assert candidate[a-BASE:a-BASE+n].hex() == p['replacement_hex']
    for r in manifest['changed_ranges']:
        a, b = int(r['start_address'],16), int(r['end_address'],16)
        assert b-a == r['byte_count'] and not declared & set(range(a,b))
        assert old[a-BASE:b-BASE].hex() == r['old_bytes']
        assert candidate[a-BASE:b-BASE].hex() == r['new_bytes']
        declared.update(range(a,b))
    assert actual == declared and actual <= covered
    assert len(actual) == manifest['total_bytes_changed']
    md = Cs(CS_ARCH_ARM, CS_MODE_THUMB | CS_MODE_MCLASS)
    lines = []
    def dis(image, a, b):
        for i in md.disasm(image[a-BASE:b-BASE], a):
            lines.append(f'{i.address:08x}  {i.bytes.hex():10} {i.mnemonic:9} {i.op_str}')
    for p in manifest['patches']:
        a, n = int(p['address'],16), p['length']
        lines.append('\n'+p['name'])
        if a < BASE+len(stock):
            lines.append('STOCK'); dis(stock,a,a+n)
        lines.append('CANDIDATE'); dis(candidate,a,a+n)
    (out/'changed-code.txt').write_text('\n'.join(lines),encoding='utf-8')
    contexts = [(0x0804D6B6,0x0804D77C),(0x0804DAAC,0x0804DC86),
                (0x0804D7A0,0x0804D81E),(0x0804DC86,0x0804DE18),
                (0x0804DF3E,0x0804E00A),(0x0804F080,0x0804F27E),
                (0x0803D8B8,0x0803D90A),(0x0803DB2E,0x0803DB84),
                (0x08031A18,0x08031A3C),(0x0803FC58,0x0803FC78),
                (0x0805CB04,0x0805CB40),(0x0805CCF0,0x0805CD24),
                (0x08025A98,0x08025AD0),(0x08051B7A,0x08051BAA),
                (0x0805CE48,0x0805CF24)]
    lines.clear()
    for a,b in contexts:
        lines.append(f'\nSTOCK {a:#010x}'); dis(stock,a,b)
    (out/'stock-contexts.txt').write_text('\n'.join(lines),encoding='utf-8')
    report = {'transport':'PASS','stock':sm,'candidate':cm,
              'vector_identical_bytes':512,'initial_sp':hex(struct.unpack_from('<I',stock)[0]),
              'reset':hex(struct.unpack_from('<I',stock,4)[0]),
              'changed_bytes':len(actual),'app_end':hex(BASE+len(candidate)),
              'decision':'TRANSPORT ONLY; runtime audit required'}
    report['code']=code_audit(candidate,stock,manifest,out)
    (out/'binary-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))
    return stock, candidate


if __name__ == '__main__':
    assert not sys.flags.optimize
    audit(Path(sys.argv[1]) if len(sys.argv)>1 else None)
