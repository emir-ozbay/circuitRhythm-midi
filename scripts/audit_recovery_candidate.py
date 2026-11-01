"""Independent transport/range/CFG/ABI audit for the integrated recovery SYX."""
import hashlib,json,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts'),str(ROOT/'tests')]
from capstone import Cs,CS_ARCH_ARM,CS_MODE_THUMB,CS_MODE_MCLASS
from audit_phase1_safety import decode,code_audit,PIN,BASE
from audit_midi_recovery_prototype import conditional_branch
import seq_Patch as seq
import midi_recovery_patch as fixed
import midi_recovery_prototype as recovery
import midi_accepted_tx_patch as accepted
import flash_query_patch as sync
import midi_dense_stop_patch as dense
import project_load_recovery_patch as load_guard
from audit_project_load_recovery import audit_load_recovery


def audit(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    stock_raw=(ROOT/'stock/circuitrhythm-firmware-5706.syx').read_bytes();assert hashlib.sha256(stock_raw).hexdigest()==PIN
    stock,stock_transport=decode(stock_raw)
    raw=(ROOT/'build/circuitrhythm-5706-phase1-recovery.syx').read_bytes();image,transport=decode(raw)
    manifest=json.loads((ROOT/'build/circuitrhythm-5706-phase1-recovery.manifest.json').read_text())
    assert image[:512]==stock[:512] and transport['init_hex']==stock_transport['init_hex'] and transport['finish_hex']==stock_transport['finish_hex']
    assert transport['sha256']==manifest['output']['sha256'] and transport['crc']==manifest['output']['image_crc32_mpeg2']
    assert len(image)==manifest['output']['image_size'] and hashlib.sha256(image).hexdigest()==manifest['output']['image_sha256']
    old=stock+b'\xFF'*(len(image)-len(stock));covered=set();changed=set()
    for p in manifest['patches']:
        a,n=int(p['address'],16),p['length'];assert BASE+512<=a<a+n<=0x08080000
        addresses=set(range(a,a+n));assert not covered&addresses;covered|=addresses
        assert old[a-BASE:a-BASE+n].hex()==p['expected_hex'] and image[a-BASE:a-BASE+n].hex()==p['replacement_hex']
    for r in manifest['changed_ranges']:
        a,b=int(r['start_address'],16),int(r['end_address'],16);addresses=set(range(a,b))
        assert b-a==r['byte_count'] and not changed&addresses;changed|=addresses
        assert old[a-BASE:b-BASE].hex()==r['old_bytes'] and image[a-BASE:b-BASE].hex()==r['new_bytes']
    actual={BASE+i for i,(a,b) in enumerate(zip(old,image)) if a!=b}
    assert actual==changed and actual<=covered and len(actual)==manifest['total_bytes_changed']
    expected=fixed.build_patches();assert len(expected)==len(manifest['patches'])
    for site,original,name in load_guard.HOOKS:
        assert sum(p.address==site and p.expected==original and p.name=='project_recovery_'+name for p in expected)==1
    for e,p in zip(expected,manifest['patches']):
        assert (e.address,e.expected.hex(),e.replacement.hex(),e.name)==(int(p['address'],16),p['expected_hex'],p['replacement_hex'],p['name'])
    phase_names={p.name for p in seq.build_phase1_patches(**fixed.OPTIONS)}
    phase_audit=code_audit(image,stock,dict(patches=[p for p in manifest['patches'] if p['name'] in phase_names]),out,seq_options=fixed.OPTIONS)
    load_audit=audit_load_recovery(image,stock,fixed,out)
    core,rp,glue,ip=fixed.arm_code();md=Cs(CS_ARCH_ARM,CS_MODE_THUMB|CS_MODE_MCLASS);md.detail=True
    tx,tg=accepted.arm_code(fixed.STATE_BASE,fixed.FLUSH_BUSY)
    sync_code=sync.arm_code()
    assert image[sync.CODE_BASE-BASE:sync.CODE_BASE-BASE+len(sync_code)]==sync_code
    assert image[sync.SITE+4-BASE:0x080231D6-BASE]==stock[sync.SITE+4-BASE:0x080231D6-BASE]
    assert image[0x08041A80-BASE:0x08041AC2-BASE]==stock[0x08041A80-BASE:0x08041AC2-BASE]
    sync_ins=list(md.disasm(sync_code,sync.CODE_BASE))
    assert [i.mnemonic for i in sync_ins]==['push','mov','cbnz','cbnz','mov','movs','str','b.w','nop']
    assert sync_ins[0].op_str=='{r3, r4, r5, r6, r7, lr}'
    assert sync_ins[2].operands[-1].imm==sync_ins[3].operands[-1].imm==sync.CODE_BASE+14
    assert sync_ins[4].op_str=='r2, sp' and sync_ins[6].op_str=='r3, [sp]'
    assert sync_ins[7].operands[0].imm==sync.SITE+4
    site=list(md.disasm(image[sync.SITE-BASE:sync.SITE-BASE+4],sync.SITE))
    assert len(site)==1 and site[0].mnemonic=='b.w' and site[0].operands[0].imm==sync.CODE_BASE
    assert accepted.CODE_BASE+len(tx)<=sync.CODE_BASE and sync.CODE_BASE+len(sync_code)<=0x08080000
    (out/'flash-sync-code.txt').write_text('\n'.join(f'{i.address:08x} {i.bytes.hex():12} {i.mnemonic} {i.op_str}' for i in sync_ins),encoding='utf-8')
    dense_code,dense_labels=dense.arm_code(fixed.STATE_BASE)
    assert image[dense.CODE_BASE-BASE:dense.CODE_BASE-BASE+len(dense_code)]==dense_code
    assert sync.CODE_BASE+len(sync_code)<=dense.CODE_BASE and dense.CODE_BASE+len(dense_code)<=0x08080000
    assert stock[dense.SITE-BASE:dense.SITE-BASE+4]==dense.EXPECTED==bytes.fromhex('90470020')
    for lo,hi in ((0x08055008,dense.SITE),(dense.SITE+4,0x0805552C),(0x0804ADA4,0x0804B1D0)):
        assert image[lo-BASE:hi-BASE]==stock[lo-BASE:hi-BASE]
    dense_site=list(md.disasm(image[dense.SITE-BASE:dense.SITE-BASE+4],dense.SITE))
    assert len(dense_site)==1 and dense_site[0].mnemonic=='bl' and dense_site[0].operands[0].imm==dense.CODE_BASE
    dense_ins=list(md.disasm(dense_code,dense.CODE_BASE));assert sum(i.size for i in dense_ins)==len(dense_code)
    assert dense_ins[0].mnemonic=='push' and dense_ins[0].op_str=='{r4, r5, r6, lr}'
    assert [(i.mnemonic,i.op_str) for i in dense_ins if i.mnemonic in ('bl','blx')]==[('blx','r2'),('bl','#0x80297de')]
    assert [(i.mnemonic,i.op_str) for i in dense_ins if i.mnemonic=='mrs']==[('mrs','r1, ipsr'),('mrs','r1, primask'),('mrs','r1, basepri')]
    assert all(not i.mnemonic.startswith(('str','stm')) and i.mnemonic not in ('cpsid','cpsie','msr') for i in dense_ins)
    for i in dense_ins:
        if conditional_branch(i.mnemonic):assert i.operands[-1].imm==dense_labels['return']>i.address
        assert i.mnemonic not in ('b','b.w','bx','bkpt','udf')
    assert [(i.mnemonic,i.op_str) for i in dense_ins[-3:]]==[('movs','r0, #0'),('pop','{r4, r5, r6, pc}'),('nop','')]
    (out/'dense-stop-code.txt').write_text('\n'.join(f'{i.address:08x} {i.bytes.hex():12} {i.mnemonic} {i.op_str}' for i in dense_ins),encoding='utf-8')
    insns={}
    for name,base,code in (('core',fixed.CORE_BASE,core),('glue',fixed.GLUE_BASE,glue),('accepted-tx',accepted.CODE_BASE,tx)):
        assert image[base-BASE:base-BASE+len(code)]==code
        decoded=list(md.disasm(code,base));assert sum(i.size for i in decoded)==len(code)
        insns.update({i.address:i for i in decoded})
        (out/f'{name}-code.txt').write_text('\n'.join(f'{i.address:08x} {i.bytes.hex():12} {i.mnemonic} {i.op_str}' for i in decoded),encoding='utf-8')
    sq=fixed.seq_code()[1]
    # Deliberate terminal allocation fault, separately audited from bounded
    # normal critical sections. Never treat OOM as a balanced returning path.
    fatal=sq['alloc_fatal']
    assert image[fatal-2-BASE:fatal+2-BASE]==bytes.fromhex('72b6fee7')
    assert sq['alloc_oom']==fatal-2
    seq_md=list(md.disasm(image[sq['c_allocator_guard']-BASE:sq['c_resolve_subview']-BASE],sq['c_allocator_guard']))
    assert all(i.mnemonic not in ('bkpt','udf') for i in seq_md)
    fatal_incoming=[i for i in seq_md if (i.mnemonic in ('b','b.w') or conditional_branch(i.mnemonic))
                    and i.operands[-1].imm==sq['alloc_oom']]
    assert len(fatal_incoming)==4  # invalid state,alignment carry,address carry,limit overflow
    external_calls={recovery.NATIVE_SEND,recovery.NATIVE_POLL,recovery.NATIVE_COUNT,sq['c_seq_state'],0x08026880,0x0802B4D8}
    tails={recovery.NATIVE_ROUTER+4:-32,fixed.CTOR+4:-16,0x080297C0:0,fixed.USB_FLUSH+4:-16,ip['ip_native_usb_flush']:0}
    tails.update({accepted.FULL+4:-8,accepted.CLOSE_SITE+4:-24,accepted.DONE_SITE+6:0,0x080268DE:0,
                  tg['tg_native_full']:0,tg['tg_native_close']:0,tg['tg_native_done']:0,
                  accepted.IRQ_SITE+4:-36,accepted.INIT_SITE+4:-24,accepted.RESET_SITE+4:0,tg['tg_native_irq']:0,tg['tg_native_init']:0})
    for i in insns.values():
        if i.mnemonic in ('b','b.w','bl') or conditional_branch(i.mnemonic):
            t=i.operands[-1].imm
            assert t in insns or i.mnemonic=='bl' and t in external_calls or i.mnemonic in ('b','b.w') and t in tails
        if i.mnemonic=='blx':assert rp['rp_ready']<=i.address<rp['rp_sysex_remaining'] and i.op_str=='r2'
        if i.mnemonic=='movw':
            nxt=insns.get(i.address+i.size)
            if nxt and nxt.mnemonic=='movt' and nxt.operands[0].reg==i.operands[0].reg:
                v=i.operands[1].imm | nxt.operands[1].imm<<16
                assert (not 0x40000000<=v<0x60000000 or accepted.CODE_BASE<=i.address<accepted.CODE_BASE+len(tx)
                        and v in (accepted.USB_BASE,accepted.EPDIS)) and not 0x1FFF0000<=v<0x20000000
    # Fixed flash vtable fields,not copied RAM test vtables.
    for off,name in ((8,'ip_send'),(12,'ip_sysex_send'),(16,'ip_sysex_pending'),(20,'ip_poll')):
        assert struct.unpack_from('<I',image,fixed.VTABLE+off-BASE)[0]==ip[name]|1
    parent_call=list(md.disasm(image[fixed.PARENT_CLEAR_CALL-BASE:fixed.PARENT_CLEAR_CALL-BASE+4],fixed.PARENT_CLEAR_CALL))
    assert len(parent_call)==1 and parent_call[0].mnemonic=='bl' and parent_call[0].operands[0].imm==ip['ip_parent_clear']
    parent_code=[i for pc,i in insns.items() if ip['ip_parent_clear']<=pc<ip['parent_end']]
    assert all(not i.mnemonic.startswith(('str','stm')) and i.mnemonic not in ('bl','blx','cpsid','cpsie','msr') for i in parent_code)
    assert all(i.operands[-1].imm>i.address or i.operands[-1].imm==0x080297C0 for i in parent_code
               if i.mnemonic in ('b','b.w') or conditional_branch(i.mnemonic))
    for address,label in ((fixed.USB_FLUSH,'ip_usb_flush'),(fixed.USB_NO_CREDIT,'ip_usb_nocredit')):
        call=list(md.disasm(image[address-BASE:address-BASE+4],address))
        assert len(call)==1 and call[0].mnemonic=='b.w' and call[0].operands[0].imm==ip[label]
    assert stock[0x0804305C-BASE:0x08043060-BASE]==bytes.fromhex('002032bd')
    assert image[0x0804301A-BASE:0x08043060-BASE]==stock[0x0804301A-BASE:0x08043060-BASE]
    snapshot_loop=list(md.disasm(tx[tg['copy_snapshot']-accepted.CODE_BASE:tg['copy_snapshot']-accepted.CODE_BASE+14],tg['copy_snapshot']))
    assert len(snapshot_loop)==6 and snapshot_loop[-2].mnemonic=='subs' and snapshot_loop[-2].op_str.replace(' ','')=='r7,#4'
    assert conditional_branch(snapshot_loop[-1].mnemonic) and snapshot_loop[-1].operands[0].imm==tg['copy_snapshot']
    functions={}
    for name,start in {**rp,**ip,**tg}.items():
        if not name.startswith(('rp_','ip_','tg_')):continue
        work=[(start,0)];visited=set();exits=set();depthmax=0;calls=[]
        while work:
            pc,depth=work.pop()
            if (pc,depth) in visited:continue
            visited.add((pc,depth));assert len(visited)<4000
            i=insns[pc];m=i.mnemonic;op=i.op_str
            if m.startswith('push'):depth-=4*len(i.operands)
            if m.startswith('pop'):depth+=4*len(i.operands)
            if m in ('sub','add') and op.startswith('sp,'):depth+=(-1 if m=='sub' else 1)*i.operands[-1].imm
            depthmax=max(depthmax,-depth)
            if m in ('bl','blx'):assert depth%8==0;calls.append(hex(pc))
            if m=='bx' and op=='lr' or m.startswith('pop') and 'pc' in op:
                assert depth==(16 if name=='ip_usb_nocredit' else 0),(name,hex(pc),depth);exits.add(depth);continue
            if m in ('b','b.w'):
                target=i.operands[0].imm
                if target in tails:assert depth==tails[target];exits.add(depth);continue
                work.append((target,depth));continue
            if conditional_branch(m):work.append((i.operands[-1].imm,depth))
            work.append((pc+i.size,depth))
        wanted={-16} if name in ('ip_native_ctor','ip_native_usb_flush') else {16} if name=='ip_usb_nocredit' else {-8} if name=='tg_native_full' else {-24} if name in ('tg_native_close','tg_native_init') else {-36} if name=='tg_native_irq' else {0}
        assert exits==wanted,(name,exits)
        functions[name]=dict(max_local_stack_bytes=depthmax,exit_sp_deltas=sorted(exits),aligned_calls=len(calls))
    mask_paths=[]
    for start in insns.values():
        if start.mnemonic!='cpsid':continue
        work=[(start.address+start.size,0,frozenset())];lengths=[]
        while work:
            pc,count,path=work.pop();assert pc not in path;path=path|{pc};i=insns[pc];count+=1
            assert i.mnemonic not in ('bl','blx','bx','pop','pop.w')
            if i.mnemonic=='msr' and i.op_str.startswith('primask,'):lengths.append(count);continue
            if i.mnemonic in ('b','b.w'):work.append((i.operands[0].imm,count,path));continue
            if conditional_branch(i.mnemonic):work.append((i.operands[-1].imm,count,path))
            work.append((pc+i.size,count,path))
        mask_paths.append(dict(start=hex(start.address),max_instructions=max(lengths)))
    # Measure the initial allocator reservation,including its explicitly bounded
    #1088B clear. This is instruction evidence,not an elapsed-time/RTOS proof.
    import test_phase1_safety as base
    h=base.SafetyTests();h.image=image;h.labels=sq;h.setUp()
    h.word(seq.HEAP_LIMIT_PTR,seq.HEAP_LIMIT);h.word(seq.HEAP_CUR_PTR,0x2004EA98)
    h.u.mem_write(fixed.STATE_BASE,b'\xA5'*1088);masked=[0];total=[0]
    def seen(u,p,n,d):
        total[0]+=1
        if u.reg_read(base.UC_ARM_REG_PRIMASK):masked[0]+=1
    hook=h.u.hook_add(base.UC_HOOK_CODE,seen)
    h.u.ctl_remove_cache(0x08010000,0x08080000)
    assert h.call(seq.STOCK_ALLOCATOR_ADDR,4)==0x2004EA98
    h.u.hook_del(hook)
    assert h.read(seq.HEAP_LIMIT_PTR)==fixed.STATE_BASE and h.read(fixed.STATE_BASE)==recovery.MAGIC
    assert h.read(seq.SEQ_STATE_ADDR)==seq.SEQ_STATE_MAGIC and h.u.reg_read(base.UC_ARM_REG_PRIMASK)==0
    r=dict(transport='PASS',hardware_release='NO-GO',firmware_integrated=True,syx_sha256=transport['sha256'],image_sha256=hashlib.sha256(image).hexdigest(),
        crc32_mpeg2=transport['crc'],image_bytes=len(image),patches=len(expected),changed_bytes=len(actual),vector_identical_bytes=512,
        state=dict(base=hex(fixed.STATE_BASE),recovery_bytes=832,total_reserved_bytes=1088,allocator_init_instructions=total[0],allocator_init_masked_instructions=masked[0],timing_proof=False,
            allocation_failure=dict(pc=hex(fatal),terminal_bytes='72b6fee7',returns=False,interrupts_masked=True,
                ram_or_mmio_writes=False,reset=False,policy='Terminal OOM/invalid reservation;normal execution requires restart. Watchdog not modeled. Not graceful recovery or a bounded critical section.')),
        phase1_code_audit=phase_audit,functions=functions,core_and_glue_masked_paths=mask_paths,
        core_sha256=hashlib.sha256(core).hexdigest(),glue_sha256=hashlib.sha256(glue).hexdigest(),accepted_tx_sha256=hashlib.sha256(tx).hexdigest(),
        dense_stop_service=dict(site=hex(dense.SITE),base=hex(dense.CODE_BASE),bytes=len(dense_code),sha256=hashlib.sha256(dense_code).hexdigest(),
            wrapper_stack_bytes=16,additional_reserved_ram_bytes=0,forward_only=True,aligned_calls=2,native_output_polls_per_flush=1,
            nonstack_writes_or_fault_clears=False,contexts='IPSR/PRIMASK/BASEPRI all zero',physical_proof=False),
        flash_sync_guard=dict(site=hex(sync.SITE),base=hex(sync.CODE_BASE),bytes=len(sync_code),sha256=hashlib.sha256(sync_code).hexdigest(),
            existing_native_frame_bytes=24,additional_stack_bytes=0,additional_reserved_ram_bytes=0,
            applies_to='CTRL_SYNC0 with NULL buffer only',paths_instructions=[4,5,8],masked_sections=0,
            unchanged_native_query=True,physical_proof=False),
        accepted_tx_guard=dict(base=hex(accepted.CODE_BASE),bytes=len(tx),state_base=hex(accepted.STATE_BASE),state_bytes=128,
            additional_reserved_ram_bytes=0,reused_seq_tail=[128,256],retirement='CPU IN1 mask/disable/ACK/AHB/FIFO1 flush/W1C/DSB',
            native_irq_site=hex(accepted.IRQ_SITE),native_late_reset_site=hex(accepted.RESET_SITE),native_init_site=hex(accepted.INIT_SITE),
            irq_gen_snapshot=True,deferred_init_gen_compare=True,wait_for_host_configuration=True,
            snapshot_copy_max_words=16,replay_unrolled_slots=16,
            replay='Unconfirmed closing USB events only;not On/Clock/SysEx;duplicates possible after ambiguous partial delivery',
            old_untagged_event_after_barrier='Cannot distinguish a forged hardware event after the assumed retirement barrier',physical_proof=False),
        parent_guard=dict(callsite=hex(fixed.PARENT_CLEAR_CALL),stock_bl_hex=fixed.PARENT_CLEAR_EXPECTED.hex(),
            entry=hex(ip['ip_parent_clear']),required_lr=hex(fixed.PARENT_CLEAR_CALL+5),native_fallback='0x080297c0',
            read_only_except_stack=True,additional_ram_bytes=0,additional_masked_sections=0,hardware_reset_barrier_proved=False),
        usb_main_guard=dict(flush=hex(fixed.USB_FLUSH),zero_credit_branch=hex(fixed.USB_NO_CREDIT),
            zero_credit_required_lr=hex(ip['usb_submit_return']|1),native_failure_frame_retired_bytes=16,
            flush_owner_byte=hex(fixed.STATE_BASE+recovery.HEADER_SIZE+fixed.FLUSH_BUSY),additional_reserved_ram_bytes=0,
            native_success_status=0,success_status_stock_return_hex='002032bd',
            alt_and_foreign_fallback=True,physical_accepted_tx_cancellation_proved=False),
        limits='Local direct CFG/ABI and synthetic allocator initialization only;full boot/OOM/native indirect driver callbacks/USB sessions/elapsed timing are not proved.')
    r['project_load_recovery']=load_audit
    (out/'report.json').write_text(json.dumps(r,indent=2),encoding='utf-8');return r


if __name__=='__main__':
    r=audit(sys.argv[1]);print(json.dumps(dict(transport=r['transport'],patches=r['patches'],init_masked=r['state']['allocator_init_masked_instructions'],hardware_release=r['hardware_release'])))
