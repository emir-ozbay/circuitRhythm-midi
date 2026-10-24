"""Boundary experiments on unmodified 5706; never opens MIDI or writes firmware.

Run: python test_long_pattern.py PATH_TO_STOCK_SYX
The page adapter is a HOST TEST MODEL, not an installed firmware feature.
"""
from pathlib import Path
import hashlib, importlib.util, json, struct, sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT/'vendor'))
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_THUMB, UC_MODE_MCLASS, UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_PC

spec=importlib.util.spec_from_file_location('syx',ROOT/'sources/arrhythmia/tools/syx.py')
syx=importlib.util.module_from_spec(spec);spec.loader.exec_module(syx)
raw=Path(sys.argv[1]).read_bytes()
assert hashlib.sha256(raw).hexdigest()=='11d604a6b6bef0d41378da03718658c7fe9c959ac24e7fef6563796b9932afaf'
p=syx.parse(raw);assert p['crc_ok'];image=p['image']
BASE=0x08010000;STOP=0x0800f000
R=[UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]
def machine():
    u=Uc(UC_ARCH_ARM,UC_MODE_THUMB|UC_MODE_MCLASS)
    u.mem_map(0x08000000,0x80000);u.mem_write(BASE,image)
    u.mem_map(0x20000000,0x50000)
    return u
def call(u,address,*args):
    for reg,arg in zip(R,args):u.reg_write(reg,arg)
    u.reg_write(UC_ARM_REG_SP,0x2004f000);u.reg_write(UC_ARM_REG_LR,STOP|1)
    u.mem_write(0x2004f000,bytes(4))  # fifth stack argument = 0 for player pre-pass
    u.emu_start(address|1,STOP,count=2000)
    assert u.reg_read(UC_ARM_REG_PC)==STOP
def w(u,a,n):u.mem_write(a,struct.pack('<I',n))

out={'firmware_sha256':hashlib.sha256(raw).hexdigest(),
     'scope':'Stock function boundary experiments and host-side page adapter model. No device or patched firmware.'}

# The real stock note setter has no 32-step bounds check. Note indices 32..63 alias gate bytes.
u=machine();obj,a,b=0x20001000,0x20002000,0x20003000
aliases=[]
for name,address,expected_group in [('note',0x08054a5c,32),('gate',0x08054a84,64),('flags',0x08054ab0,96)]:
    for step in range(32,64):
        baseline=bytes([0x55])*128
        u.mem_write(a,baseline);u.mem_write(b,baseline)
        u.mem_write(obj,struct.pack('<5I',0,0,0,a,b))
        call(u,address,obj,step,0x66)
        delta=[i for i,(old,new) in enumerate(zip(baseline,u.mem_read(b,128))) if old!=new]
        expected=expected_group+step-32
        assert delta==[expected],(name,step,delta)
        aliases.append({'setter':name,'human_step':step+1,'modified_buffer_byte':delta[0],
                        'alias':'gate lane' if name=='note' else 'flags lane' if name=='gate' else 'past 24-word ST2 layout'})
out['unsafe_direct_extension']={'reproduced_cases':len(aliases),'details':aliases,
    'interpretation':'Expected failures of naive extension, successfully reproduced. They are NOT successful long-pattern edits.'}

# Real player and real rate accessor, but note scheduling and old-note cleanup are intercepted.
u=machine();player=0x20004000;patterns=0x20010000;rateobj=0x20008000;ratebuf=0x20008100
w(u,player+0x50,patterns);w(u,player+0x10,rateobj)
u.mem_write(rateobj,struct.pack('<5I',0,0,0,ratebuf,ratebuf+0x40))
w(u,ratebuf+4,0)
# Synthetic free-list head != FF avoids the allocator-exhaustion cleanup branch.
u.mem_write(player+0x88,b'\x00')
u.mem_write(player+0xab,b'\xff'*128)
u.mem_write(player+0x14c,b'\x3f')
calls=[];reads=[]
def intercept(uc,addr,size,data):
    if addr==0x0804afd6:
        from unicorn.arm_const import UC_ARM_REG_R7
        reads.append(uc.reg_read(UC_ARM_REG_R7))
    elif addr==0x0804b0d4:
        args=[uc.reg_read(x) for x in R]
        tie=struct.unpack('<I',uc.mem_read(uc.reg_read(UC_ARM_REG_SP),4))[0]
        calls.append({'note':args[1],'velocity':args[2],'gate_ticks':args[3],'tie':tie})
        uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
    elif addr==0x0804b19e:
        raise AssertionError('Unexpected old-note cleanup in this synthetic fixture')
u.hook_add(UC_HOOK_CODE,intercept)
def rec(note,gate=6,velocity=100,tie=0):return bytes([note,gate,1,velocity,7,255,tie,0])
u.mem_write(patterns,rec(60)*32)
u.mem_write(patterns+0x100,rec(13,9,80,1))
direct=[]
for step in [0,15,16,31,32]:
    calls.clear();reads.clear()
    call(u,0x0804afbc,player,0,step,0)
    assert reads==[patterns+step*8] and len(calls)==1
    direct.append({'human_step':step+1,'relative_record_address':hex(reads[0]-patterns),'event':dict(calls[0])})
assert direct[-1]['event']['note']==13
out['player_boundary']={'cases':direct,
    'finding':'Direct step index 32 reads pattern+0x100 (settings), not a 33rd note record.',
    'mocked':'Note scheduling intercepted; no actual note lifetime, Note Off, MIDI or DSP executed.'}

# Host-side page adapter: one logical pattern backed by 32-step blocks.
# The backing slots here are TEST memory, not user-visible stock patterns.
PAT=0xa28;gate_rate=struct.unpack_from('<I',image,0x08068d9c-BASE)[0]
for page in range(4):
    for local in range(32):
        absolute=page*32+local
        u.mem_write(patterns+page*PAT+local*8,rec(24+absolute%80,1+absolute%24,20+absolute%100,absolute%2))
adapted=0
for absolute in range(128):
    page,local=divmod(absolute,32)
    calls.clear();reads.clear()
    call(u,0x0804afbc,player,page,local,0)
    expected={'note':24+absolute%80,'velocity':20+absolute%100,
              'gate_ticks':max(1,(1+absolute%24)*gate_rate//6),'tie':absolute%2}
    assert calls==[expected],(absolute,calls,expected)
    assert reads==[patterns+page*PAT+local*8]
    adapted+=1
out['host_page_adapter_playback']={'steps_verified':adapted,'gate_rate_entry_0':gate_rate,
    'verified':'All page/local record addresses, note, velocity, scaled gate and tie arguments match.',
    'not_verified':'Gate/tie lifetime across pages, mutation, scheduler page switching, storage, UI, project operations.',
    'warning':'128 steps is a test fixture capacity, not a selected product limit or on-device memory allocation.'}

# Independent edit buffers per test page; guard against global index leakage into stock setters.
u=machine();edit_count=0
for field,address,group in [('note',0x08054a5c,0),('gate',0x08054a84,8),('flags',0x08054ab0,16)]:
    objects=[];buffers=[]
    for page in range(4):
        ob=0x20001000+page*0x100;ba=0x20002000+page*0x200;bb=ba+0x100
        u.mem_write(ob,struct.pack('<5I',0,0,0,ba,bb))
        u.mem_write(ba,b'\x55'*128);u.mem_write(bb,b'\x55'*128)
        objects.append(ob);buffers.append(bb)
    expected=[bytearray(b'\x55'*128) for _ in range(4)]
    for absolute in range(128):
        page,local=divmod(absolute,32);value=(absolute*3+7)&255
        call(u,address,objects[page],local,value)
        expected[page][group*4+local]=value
        assert all(u.mem_read(bb,128)==e for bb,e in zip(buffers,expected))
        edit_count+=1
out['host_page_adapter_editing']={'cases_passed':edit_count,
    'verified':'Local indices only; target fields and all other page buffers checked after every edit.',
    'not_verified':'Commit/notify, actual firmware allocation, current UI and persistence.'}

# Real stock pre-pass: microstep/probability gating, with no held ties and no elapsed pulse.
# Control the already-generated random threshold; do not replace or claim to test RNG.
u=machine();w(u,player+0x50,patterns);micro_cases=0
for page in range(4):
    local=31 if page%2==0 else 0
    for mask in [0,1,2,32,63,21]:
        for probability in [0,3,7]:
            for threshold in range(8):
                for micro in range(6):
                    u.mem_write(patterns+page*PAT+local*8,bytes([60,6,mask,100,probability,255,0,0]))
                    u.mem_write(player+4,bytes([threshold]))
                    initial=0x2a
                    u.mem_write(player+0x14c,bytes([initial]))
                    call(u,0x0804aeee,player,page,local,micro)
                    enabled=bool(mask & (1<<micro)) and probability>=threshold
                    expected=(initial | (1<<micro)) if enabled else (initial & ~(1<<micro))
                    assert u.mem_read(player+0x14c,1)==bytes([expected])
                    micro_cases+=1
out['stock_microstep_probability']={'cases_passed':micro_cases,'function':'0x0804aeee',
    'mocked_calls':[], 'conditions':'Synthetic player and pattern memory, no held ties, fifth argument zero, controlled pre-existing random threshold.',
    'verified':'Six microstep positions; empty/single/multiple hit masks; probability acceptance and untouched other hit bits across four backing pages.',
    'not_verified':'RNG distribution, real clock, note lifetime and gate/tie transitions.'}

# UI arithmetic proposal, not a real pad handler: page then 1-based pad selects end step.
def end_from_pad(page,pad,capacity):
    if not 0<=page<(capacity+31)//32 or not 1<=pad<=32:raise ValueError('invalid page/pad')
    end=page*32+pad
    if end>capacity:raise ValueError('beyond capacity')
    return end
assert end_from_pad(1,10,128)==42
length_cases=0
for length in range(1,129):
    assert end_from_pad((length-1)//32,(length-1)%32+1,128)==length
    # Sequential playback model covers exactly the active range then wraps.
    visited=[i%length for i in range(length+1)]
    assert visited[:-1]==list(range(length)) and visited[-1]==0
    length_cases+=1
for args in [(-1,1,128),(4,1,128),(0,0,128),(0,33,128),(1,11,42)]:
    try:end_from_pad(*args)
    except ValueError:pass
    else:raise AssertionError(args)
out['length_gesture_host_model']={'lengths_passed':length_cases,'invalid_cases_rejected':5,
    'example':'page 2 + pad 10 => length 42','limit':'Arithmetic only; no button event or timing integration.'}

out['memory_estimates']={
    'assumptions':'8 tracks, 8 patterns/track retained. Costs exclude allocator overhead and added edit buffers.',
    'source_reported_heap_margin_bytes_unverified_on_user_device':3272,
    'rows':[{'steps':n,'extra_note_records_bytes':64*(n-32)*8,
             'extra_full_32step_blocks_bytes':64*(n//32-1)*PAT,
             'total_full_pattern_blocks_bytes':64*(n//32)*PAT} for n in [32,64,128]],
    'note':'Full block duplication preserves a stock-sized automation area per page but is just one expensive design; not proof all other designs are impossible.'}
out['status']={
 'stock_32_boundary':'CONFIRMED: naive extension aliases data',
 'paged_adapter':'HOST POC PASSED, not firmware implementation',
 'gate_tie_lifetime':'NOT TESTED', 'mutation':'NOT TESTED',
 'projects_isolation':'NOT IMPLEMENTED/TESTED','packs_disabled':'NOT IMPLEMENTED/TESTED',
 'mode_shortcut':'NOT IMPLEMENTED/TESTED','physical_device':'NOT TESTED'}
(ROOT/'long-pattern-results.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({k:v for k,v in out.items() if k not in ['unsafe_direct_extension','player_boundary']},indent=2))
