"""Recovery hooks, direct CFG, ABI and write-surface audit; no physical claim."""
from capstone import Cs,CS_ARCH_ARM,CS_MODE_THUMB,CS_MODE_MCLASS
from capstone.arm import ARM_OP_MEM
from audit_midi_recovery_prototype import conditional_branch
import hashlib
import project_load_recovery_patch as g
import seq_Patch as seq
import midi_accepted_tx_patch as accepted
BASE=0x08010000

def audit_load_recovery(image,stock,fixed,out):
    code,L=g.arm_code(fixed.seq_code()[1]['c_seq_state'],fixed.STATE_BASE)
    assert g.CODE_BASE%4==0 and g.CODE_BASE+len(code)<=g.CODE_LIMIT<=fixed.CORE_BASE
    assert image[g.CODE_BASE-BASE:g.CODE_BASE-BASE+len(code)]==code
    md=Cs(CS_ARCH_ARM,CS_MODE_THUMB|CS_MODE_MCLASS);md.detail=True
    ins=list(md.disasm(code,g.CODE_BASE));I={i.address:i for i in ins}
    assert sum(i.size for i in ins)==len(code)
    hooks=[]
    for site,original,name in g.HOOKS:
        assert stock[site-BASE:site+4-BASE]==original
        hook=list(md.disasm(image[site-BASE:site+4-BASE],site))
        assert len(hook)==1 and hook[0].mnemonic=='b.w' and hook[0].operands[0].imm==L[name]
        # Displaced prologue and continuation remain byte-identical.
        if name=='button_busy':
            old=list(md.disasm(original,site))
            assert len(old)==1 and old[0].mnemonic=='bne.w' and old[0].operands[0].imm==g.BUTTON_REJECT
            assert I[L[name]].mnemonic=='beq.w' and I[L[name]].operands[0].imm==L['button_stock']
        else:
            label=L[{'read_result':'read_native','pad':'pad_native','release':'release_native','new':'new_native','apply':'apply_native',
                     'button_gate':'gate_native','button_up':'button_up_native','start':'start_native','cont':'cont_native',
                     'save':'save_native','sync_all':'sync_native'}[name]]
            if name!='apply':label+=I[label].size
            assert image[label-BASE:label+4-BASE]==original
        if site+4!=g.BUTTON_GATE_SITE:
            assert image[site+4-BASE:site+8-BASE]==stock[site+4-BASE:site+8-BASE]
        hooks.append(dict(site=hex(site),original=original.hex(),entry=hex(L[name])))
    external={fixed.seq_code()[1]['c_seq_state'],g.NATIVE_CLOSE,g.NATIVE_LOAD,g.READ_WORD,g.PAD_DOWN,g.PAD_UP}
    internal={L[n] for n in ('word','operation_matches','admit','apply_native')}
    tails={g.SITE+4:-8,g.PAD_SITE+4:-16,g.RELEASE_SITE+4:-16,g.NEW_SITE+4:-8,g.APPLY_SITE+4:-24,
           g.BUTTON_CONTINUE:0,g.BUTTON_REJECT:0,g.BUTTON_GATE_SITE+4:0,g.BUTTON_UP_SITE+4:-16,
           g.START_SITE+4:-16,g.CONTINUE_SITE+4:-16,g.SAVE_SITE+4:-36,g.SYNC_SITE+4:-24}
    stores=[]
    # Every nonstack store is a fixed field in the existing seq reservation,
    # or the validated 4-byte callback bridge. No raw/project pointer store.
    allowed_state={g.OWNER:4,g.DESCRIPTOR:4,g.DESCRIPTOR+4:4,g.DESCRIPTOR+8:4,
                   g.EPOCH:4,g.SLOT:4,g.BRIDGE:4,g.HELD:4,seq.OFF_PROJECT_TAINTED:1,g.STAGE:1}
    seq.check_layout()
    spans=sorted((off,off+size) for off,size in allowed_state.items())
    assert all(a[1]<=b[0] for a,b in zip(spans,spans[1:]))
    assert spans[0][0]==seq.OFF_RECORDERS+32 and spans[-1][1]<=seq.OFF_MIDI_RECEIVERS
    assert fixed.STATE_BASE+fixed.STATE_SIZE==seq.SEQ_STATE_ADDR
    assert accepted.STATE_BASE==seq.SEQ_STATE_ADDR+0x80
    assert accepted.STATE_BASE+accepted.STATE_SIZE==seq.SEQ_STATE_ADDR+256
    for i in ins:
        m=i.mnemonic
        assert m not in ('bkpt','udf','svc','blx','msr','stm','stm.w')
        if m=='bl':assert i.operands[0].imm in external|internal
        elif m in ('b','b.w') or conditional_branch(m):
            assert i.operands[-1].imm in I or m in ('b','b.w') and i.operands[-1].imm in tails
        if m.startswith('str'):
            mem=i.operands[1];assert mem.type==ARM_OP_MEM and not mem.mem.index
            base=i.reg_name(mem.mem.base);off=mem.mem.disp;width=1 if m.startswith('strb') else 4
            if base=='r6':assert allowed_state.get(off)==width
            else:
                assert base=='r4' and off==0 and width==4
                assert L['read_failed']<=i.address<L['read_native']
                assert i.reg_name(i.operands[0].reg)=='r1'
                prev=ins[ins.index(i)-1];assert prev.mnemonic=='movs' and prev.op_str=='r1, #0'
            stores.append(dict(pc=hex(i.address),base=base,offset=off,bytes=width))
        if i.address<L['word']:
            # Every writer's r6 is the nonzero c_seq_state return. Helpers
            # temporarily repurpose r6 only inside their balanced saved frame.
            _,written=i.regs_access()
            if 'r6' in [i.reg_name(r) for r in written] and not m.startswith('pop'):
                assert m=='mov' and i.op_str=='r6, r0'
    # The only external calls inside admission are fixed stock read-only bank
    # selection and a one-byte bitmap write, both byte-identical to stock.
    for lo,hi in ((g.READ_WORD,0x0803FC6C),(g.PAD_DOWN,0x08051BD8)):
        assert image[lo-BASE:hi-BASE]==stock[lo-BASE:hi-BASE]
    # No writes or interrupt-mask changes in bounded admission/read helpers.
    assert all(not i.mnemonic.startswith(('str','stm')) and i.mnemonic not in ('cpsid','cpsie','msr') for i in ins if i.address>=L['word'])
    assert [(i.mnemonic,i.op_str) for i in ins if i.mnemonic in ('cpsid','cpsie')]==[
        ('cpsid','i'),('cpsie','i'),('cpsie','i'),
        ('cpsid','i'),('cpsie','i'),('cpsie','i'),
        ('cpsid','i'),('cpsie','i'),('cpsie','i')]
    masks=[i for i in ins if i.mnemonic=='cpsid']
    for mask,(start,fail) in zip(masks,(('pad','pad_exit'),('button_busy','button_blocked'),('button_gate','gate_reject'))):
        prefix=[i for i in ins if L[start]<=i.address<mask.address]
        assert [(i.mnemonic,i.op_str) for i in prefix if i.mnemonic=='mrs']==[('mrs','r1, ipsr'),('mrs','r1, primask'),('mrs','r1, basepri')]
        for j,i in enumerate(prefix):
            if i.mnemonic=='mrs':
                assert prefix[j+1].mnemonic=='cmp' and prefix[j+1].op_str=='r1, #0'
                assert prefix[j+2].mnemonic.startswith('bne') and prefix[j+2].operands[-1].imm==L[fail]
    functions={}
    for name in ('read_result','close_done','pad','release','new','apply','apply_native','button_busy',
                 'button_gate','button_up','start','cont','save','sync_all','word','operation_matches','admit'):
        work=[(L[name],0,False)];seen=set();exits=set();calls=[];max_stack=0
        while work:
            pc,depth,locked=work.pop()
            if (pc,depth,locked) in seen:continue
            seen.add((pc,depth,locked));assert len(seen)<10000
            i=I[pc];m=i.mnemonic
            if m.startswith('push'):depth-=4*len(i.operands)
            if m.startswith('pop'):depth+=4*len(i.operands)
            if m in ('sub','add') and i.op_str.startswith('sp,'):depth+=(-1 if m=='sub' else 1)*i.operands[-1].imm
            max_stack=max(max_stack,-depth)
            if m=='cpsid':assert not locked;locked=True
            if m=='cpsie':assert locked;locked=False
            if m=='bl':
                assert depth%8==0
                target=i.operands[0].imm
                if locked:assert target in (L['admit'],g.PAD_DOWN)
                if target in (g.NATIVE_LOAD,g.NATIVE_CLOSE,L['apply_native']):assert not locked
                calls.append(dict(pc=hex(pc),target=hex(target),masked=locked,local_stack_bytes=-depth))
            if m.startswith('pop') and 'pc' in i.op_str or m=='bx' and i.op_str=='lr':
                assert depth==0 and not locked;exits.add(depth);continue
            if m in ('b','b.w'):
                target=i.operands[0].imm
                if target in tails:assert depth==tails[target] and not locked;exits.add(depth);continue
                work.append((target,depth,locked));continue
            if conditional_branch(m):work.append((i.operands[-1].imm,depth,locked))
            work.append((pc+i.size,depth,locked))
        assert exits
        functions[name]=dict(max_local_stack_bytes=max_stack,exit_sp_deltas=sorted(exits),calls=calls)
    by_address={L[name]:name for name in functions}
    def own_depth(name,path=()):
        assert name not in path
        return max([functions[name]['max_local_stack_bytes']]+[
            call['local_stack_bytes']+own_depth(by_address[int(call['target'],16)],path+(name,))
            for call in functions[name]['calls'] if int(call['target'],16) in by_address])
    depths={name:own_depth(name) for name in functions}
    (out/'project-load-recovery-code.txt').write_text('\n'.join(f'{i.address:08x} {i.bytes.hex():12} {i.mnemonic} {i.op_str}' for i in ins),encoding='utf-8')
    return dict(hooks=hooks,base=hex(g.CODE_BASE),limit=hex(g.CODE_LIMIT),bytes=len(code),sha256=hashlib.sha256(code).hexdigest(),
        functions=functions,stores=stores,reserved_state_offsets=allowed_state,additional_reserved_ram_bytes=0,
        recovery_only_stack_bytes=depths,peak_recovery_only_stack_bytes=max(depths.values()),
        admission_bounds=dict(receivers=4,words_per_receiver=40,tracks=8,held_bits_per_track=32),
        irq_restore='Only initially unmasked thread pad/page admission masks IRQ;every exit restores it before native Load or stock page continuation. Other entries do not change PRIMASK.',
        native_write_boundaries=['PAD_DOWN/PAD_UP controller bitmap','native Close queue','native Load/defaults/apply'],
        direct_raw_writes=False,rollback=False,physical_proof=False,
        limits='Direct CFG/local ABI and fixed write surface;pointer identity and state transitions also require runtime tests. Native callee stack and elapsed-time upper bounds remain M7 work.')
