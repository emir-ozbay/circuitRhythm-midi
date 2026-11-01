"""Synthetic RAM/ABI boundary tests; native reset evidence is separate."""
import unittest,struct
from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
import test_phase1_safety as base
import midi_recovery_patch as fixed
import project_load_recovery_patch as guard
from patch_firmware import apply_patches

class ProjectLoadRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.image=apply_patches(base.load_image(),fixed.build_patches())[0]
        cls.labels=fixed.seq_code()[1]
        cls.code,cls.g=guard.arm_code(cls.labels['c_seq_state'],fixed.STATE_BASE)
    setUp=base.SafetyTests.setUp
    word=base.SafetyTests.word;read=base.SafetyTests.read;call=base.SafetyTests.call;store=base.SafetyTests.store
    def byte(self,off,value):self.u.mem_write(base.seq.SEQ_STATE_ADDR+off,bytes([value]))
    def value(self,off):return self.u.mem_read(base.seq.SEQ_STATE_ADDR+off,1)[0]
    def setup_graph(self):
        self.p=0x20001100;self.bridge=0x20001000;self.raw=0x20002000;self.header=0x20001200
        self.ctrl=0x20004000;self.view=0x20004500;self.grid=0x20005000
        self.word(self.p,guard.PROJECT_VTABLE);self.word(self.p+12,guard.PROJECT_LOAD_VTABLE)
        self.word(self.p+20,self.raw);self.word(self.p+0x64,self.bridge)
        self.phase=self.store(struct.pack('<II',0x104,2));self.flags=self.store(struct.pack('<I',3))
        self.meta=self.store(bytes(48));self.word(self.p+0x48,self.phase);self.word(self.p+0x4C,self.flags);self.word(self.p+0x44,self.meta)
        self.word(self.ctrl,guard.CONTROLLER_VTABLE);self.word(self.ctrl+0x50,self.view);self.word(self.ctrl+0x3C,self.grid)
        self.word(self.ctrl+0x8C,self.flags)
        self.shift=self.store(bytes(4));self.transport=self.store(bytes(4));self.active=self.store(struct.pack('<I',6))
        for off,ptr in ((12,self.shift),(0x18,self.transport),(0x14,self.active)):self.word(self.ctrl+off,ptr)
        for off,ptr in ((0x20,self.meta),(0x28,self.phase),(0x24,self.store(struct.pack('<I',14)))):self.word(self.view+off,ptr)
        self.modifiers=[self.store(bytes(4)) for _ in range(3)]
        for off,ptr in zip((0x18,0x1C,0x2C),self.modifiers):self.word(self.view+off,ptr)
        self.notes=[self.store(bytes(4)) for _ in range(8)]
        for t,ptr in enumerate(self.notes):self.word(self.ctrl+0x1C0+4*t,ptr)
        self.word(self.bridge,self.p+12);self.word(self.header,2);self.word(self.header+4,1)
        self.word(0x20040004,self.bridge);self.calls=[]
        for pc in (guard.NATIVE_CLOSE,guard.NATIVE_LOAD):
            self.u.mem_write(pc,bytes.fromhex('00207047'))
            def observe(u,pc,size,_):
                self.calls.append(dict(pc=pc,args=[u.reg_read(r) for r in base.REGS],sp=u.reg_read(UC_ARM_REG_SP),primask=u.reg_read(UC_ARM_REG_PRIMASK)))
            self.u.hook_add(UC_HOOK_CODE,observe,begin=pc,end=pc)
    def fail_read(self,status=4):
        self.word(self.bridge,self.p+12);self.word(0x20040004,self.bridge)
        self.call(guard.SITE,self.header,0,status,self.raw)
        self.assertEqual(self.value(guard.STAGE),guard.CLOSING)
        self.assertEqual(self.value(base.seq.OFF_PROJECT_TAINTED),1)
        self.assertEqual(self.read(self.bridge),0)
        return self.calls[-1]['args'][2]
    def close(self,cookie,status=0,header=None):
        self.word(0x20040004,cookie)
        self.call(self.g['close_done'],header or self.header,0,status,0)
    def set_store(self,obj,index,value):
        for off in (0x40,0xC0):self.word(obj+off+4*index,value)
    def test_close_identity_stale_result_error_and_epoch_wrap_fail_closed(self):
        self.setup_graph();old=self.fail_read();self.close(old+1)
        self.assertEqual(self.value(guard.STAGE),guard.CLOSING)
        self.word(self.header+4,2);self.close(old);self.assertEqual(self.value(guard.STAGE),guard.CLOSING)
        self.word(self.header+4,1);self.close(old,6);self.assertEqual(self.value(guard.STAGE),guard.DEAD)
        current=self.fail_read();self.close(old);self.assertEqual(self.value(guard.STAGE),guard.CLOSING)
        self.close(current);self.assertEqual(self.value(guard.STAGE),guard.READY)
        self.close(current,6);self.assertEqual(self.value(guard.STAGE),guard.READY)
        self.word(base.seq.SEQ_STATE_ADDR+guard.EPOCH,0xFFFFFFFF)
        n=len(self.calls);self.word(self.bridge,self.p+12);self.word(0x20040004,self.bridge)
        self.call(guard.SITE,self.header,0,4,self.raw)
        self.assertEqual(self.value(guard.STAGE),guard.DEAD);self.assertEqual(len(self.calls),n)
    def test_pad_admission_rejects_busy_modifiers_owners_and_masked_context(self):
        self.setup_graph();cookie=self.fail_read()
        for stage in (guard.CLOSING,guard.DEAD,guard.RETRY,guard.READ_OK,guard.NEW_OK):
            self.byte(guard.STAGE,stage);n=len(self.calls);self.call(guard.PAD_SITE,self.ctrl,1,96)
            self.assertEqual(len(self.calls),n)
        self.byte(guard.STAGE,guard.CLOSING);self.close(cookie)
        cases=[(self.transport,0,1),(self.shift,0,1),(self.active,0,0),*( (p,0,1) for p in self.modifiers),
               (self.notes[7],0,1),(self.phase,1,1),(self.flags,0,0)]
        for obj,index,value in cases:
            old=self.read(obj+0x40+4*index);self.set_store(obj,index,value)
            n=len(self.calls);self.call(guard.PAD_SITE,self.ctrl,1,96);self.assertEqual(len(self.calls),n)
            self.set_store(obj,index,old)
        for reg in (UC_ARM_REG_PRIMASK,UC_ARM_REG_BASEPRI):
            self.u.reg_write(reg,1);n=len(self.calls);self.call(guard.PAD_SITE,self.ctrl,1,96)
            self.assertEqual(len(self.calls),n);self.assertEqual(self.u.reg_read(reg),1);self.u.reg_write(reg,0)
        self.word(self.grid+0x228,1);n=len(self.calls);self.call(guard.PAD_SITE,self.ctrl,1,96);self.assertEqual(len(self.calls),n)
    def test_both_pages_native_held_release_and_unmasked_load(self):
        for page in (0,1):
            self.setUp();self.setup_graph();cookie=self.fail_read();self.close(cookie)
            self.u.mem_write(self.view+0x36,bytes([page]));self.call(guard.PAD_SITE,self.ctrl,31,96)
            c=self.calls[-1];self.assertEqual(c['pc'],guard.NATIVE_LOAD)
            self.assertEqual(c['args'][:3],[self.p,31+32*page,1]);self.assertEqual(c['primask'],0)
            self.assertTrue(all(not c['sp']%8 for c in self.calls))
            self.assertEqual(self.read(base.seq.SEQ_STATE_ADDR+guard.HELD),self.ctrl)
            self.assertEqual(self.read(self.ctrl+0x9C),1<<31)
            n=len(self.calls);self.call(guard.PAD_SITE,self.ctrl,31,96);self.assertEqual(len(self.calls),n)
            self.call(guard.RELEASE_SITE,self.ctrl,31)
            self.assertEqual(self.read(base.seq.SEQ_STATE_ADDR+guard.HELD),0)
            self.assertEqual(self.read(self.ctrl+0x9C),0)
    def test_only_authorized_apply_can_clear_taint_after_native_completion(self):
        self.setup_graph();cookie=self.fail_read();self.close(cookie)
        self.word(base.seq.SEQ_STATE_ADDR+guard.SLOT,1)
        # Native apply boundary stub supplies its documented final stores;
        # this is a separate synthetic fixture, not repaired native evidence.
        native=[]
        self.u.mem_write(self.g['apply_native'],bytes.fromhex('7047'))
        def complete(u,pc,size,_):
            native.append(self.value(base.seq.OFF_PROJECT_TAINTED))
            self.set_store(self.phase,1,0);self.set_store(self.flags,0,0);self.set_store(self.meta,11,1)
        self.u.hook_add(UC_HOOK_CODE,complete,begin=self.g['apply_native'],end=self.g['apply_native'])
        self.call(guard.APPLY_SITE,self.p);self.assertFalse(native);self.assertEqual(self.value(base.seq.OFF_PROJECT_TAINTED),1)
        self.byte(guard.STAGE,guard.READ_OK);self.call(guard.APPLY_SITE,self.p)
        self.assertEqual(native,[1]);self.assertEqual(self.value(base.seq.OFF_PROJECT_TAINTED),0)
        self.assertEqual(self.value(guard.STAGE),guard.CLEAN)

    def test_close_queue_failure_and_invalid_descriptor_fail_closed(self):
        for invalid in (False,True):
            with self.subTest(invalid=invalid):
                self.setUp();self.setup_graph()
                self.u.mem_write(guard.NATIVE_CLOSE,bytes.fromhex('01207047'))
                header=guard.CODE_BASE if invalid else self.header
                self.call(guard.SITE,header,0,4,self.raw)
                self.assertEqual(self.value(guard.STAGE),guard.DEAD)
                self.assertEqual(self.value(base.seq.OFF_PROJECT_TAINTED),1)
                self.assertEqual(self.read(self.bridge),0)
                self.assertEqual(len(self.calls),0 if invalid else 1)
                self.close(1);self.assertEqual(self.value(guard.STAGE),guard.DEAD)

    def test_close_context_and_pointer_boundaries_cannot_authorize(self):
        self.setup_graph();cookie=self.fail_read()
        for pointer in (1,0x1FFFFFFC,fixed.STATE_BASE-8,fixed.STATE_BASE,guard.CODE_BASE):
            self.close(cookie,header=pointer);self.assertEqual(self.value(guard.STAGE),guard.CLOSING)
        for reg,value in ((UC_ARM_REG_PRIMASK,1),(UC_ARM_REG_BASEPRI,32),(UC_ARM_REG_IPSR,16)):
            old=self.u.reg_read(reg);self.u.reg_write(reg,value)
            self.close(cookie);self.assertEqual(self.value(guard.STAGE),guard.CLOSING)
            self.assertEqual(self.u.reg_read(reg),value);self.u.reg_write(reg,old)
        self.close(cookie);self.assertEqual(self.value(guard.STAGE),guard.READY)

    def test_admission_rejects_bad_pointers_banks_and_wrong_identity(self):
        self.setup_graph();cookie=self.fail_read();self.close(cookie)
        slots=[self.ctrl+0x50,self.ctrl+0x3C,self.ctrl+0x14,self.p+0x48,self.view+0x24,self.ctrl+0x1DC]
        for address in slots:
            old=self.read(address)
            for ptr in (0,1,0x1FFFFFFC,fixed.STATE_BASE-4,fixed.STATE_BASE,guard.CODE_BASE):
                self.word(address,ptr);n=len(self.calls)
                self.call(guard.PAD_SITE,self.ctrl,1,96);self.assertEqual(len(self.calls),n)
                self.assertEqual(self.value(guard.STAGE),guard.READY)
            self.word(address,old)
        # The bounded native word accessor returns a pointer; it is checked
        # before dereference, including invalid active bank data.
        for ptr in (0,1,0x1FFFFFFC,fixed.STATE_BASE,guard.CODE_BASE):
            old=self.read(self.active+12);self.word(self.active+12,ptr)
            n=len(self.calls);self.call(guard.PAD_SITE,self.ctrl,1,96);self.assertEqual(len(self.calls),n)
            self.word(self.active+12,old)
        for obj in (self.ctrl,self.p):
            old=self.read(obj);self.word(obj,0);n=len(self.calls)
            self.call(guard.PAD_SITE,self.ctrl,1,96);self.assertEqual(len(self.calls),n);self.word(obj,old)

    def test_busy_stock_release_without_taint_and_normal_fallback(self):
        self.setup_graph();self.word(self.ctrl+0x9C,2)
        self.call(guard.RELEASE_SITE,self.ctrl,1)
        self.assertEqual(self.read(self.ctrl+0x9C),0)
        self.assertEqual(self.value(base.seq.OFF_PROJECT_TAINTED),0)
        self.set_store(self.flags,0,0)
        self.call(guard.RELEASE_SITE,self.ctrl,1,end=self.g['release_native'])
        self.call(guard.PAD_SITE,self.ctrl,1,96,end=self.g['pad_native'])

    def test_bounded_admission_masks_and_writes_only_owned_state(self):
        self.setup_graph();cookie=self.fail_read();self.close(cookie)
        for n in range(4):self.word(base.seq.SEQ_STATE_ADDR+base.seq.OFF_MIDI_RECEIVERS+4*n,0x20014000+n*0x200)
        for n in range(8):self.word(self.grid+0x74+4*n,0x20016000+n*0x200)
        writes=[];masked=[]
        def instruction(u,pc,size,_):
            if u.reg_read(UC_ARM_REG_PRIMASK):masked.append(pc)
        self.u.hook_add(UC_HOOK_CODE,instruction)
        self.u.hook_add(UC_HOOK_MEM_WRITE,lambda u,k,a,n,v,d:writes.append((a,n)))
        self.call(guard.PAD_SITE,self.ctrl,31,96)
        self.assertEqual(self.calls[-1]['pc'],guard.NATIVE_LOAD)
        self.assertTrue(0<len(masked)<20000)
        self.assertNotIn(guard.NATIVE_LOAD,masked)
        allowed={base.seq.SEQ_STATE_ADDR+guard.HELD:4,base.seq.SEQ_STATE_ADDR+guard.SLOT:4,
                 base.seq.SEQ_STATE_ADDR+guard.STAGE:1,self.ctrl+0x9F:1}
        self.assertEqual([(a,n) for a,n in writes if not (0x2003F000<=a<a+n<=0x20040000 or allowed.get(a)==n)],[])
        print('Bounded populated-owner admission masked instructions:',len(masked))
        self.assertEqual(self.u.reg_read(UC_ARM_REG_PRIMASK),0)

    def test_apply_incomplete_native_final_state_retains_taint(self):
        for field in ('phase','flags','slot'):
            with self.subTest(field=field):
                self.setUp();self.setup_graph();cookie=self.fail_read();self.close(cookie)
                self.word(base.seq.SEQ_STATE_ADDR+guard.SLOT,1);self.byte(guard.STAGE,guard.READ_OK)
                self.u.mem_write(self.g['apply_native'],bytes.fromhex('7047'))
                def incomplete(u,pc,size,_):
                    self.set_store(self.phase,1,2 if field=='phase' else 0)
                    self.set_store(self.flags,0,3 if field=='flags' else 0)
                    self.set_store(self.meta,11,2 if field=='slot' else 1)
                self.u.hook_add(UC_HOOK_CODE,incomplete,begin=self.g['apply_native'],end=self.g['apply_native'])
                self.call(guard.APPLY_SITE,self.p)
                self.assertEqual(self.value(base.seq.OFF_PROJECT_TAINTED),1)

    def test_busy_page_branch_only_admits_ready_recovery_and_preserves_original_eq(self):
        for button in (18,19,20,24):
            for stage in (guard.CLOSING,guard.READY,guard.RETRY,guard.DEAD):
                self.setUp();self.setup_graph();cookie=self.fail_read();self.close(cookie);self.byte(guard.STAGE,stage)
                self.u.reg_write(UC_ARM_REG_R4,self.ctrl);self.u.reg_write(UC_ARM_REG_R5,button)
                self.u.reg_write(UC_ARM_REG_APSR,0)
                before=bytes(self.u.mem_read(base.seq.SEQ_STATE_ADDR,256));n=len(self.calls)
                target=guard.BUTTON_CONTINUE if button in (19,20) and stage==guard.READY else guard.BUTTON_REJECT
                self.call(guard.BUTTON_SITE,end=target)
                self.assertEqual(self.u.reg_read(UC_ARM_REG_SP),0x20040000)
                self.assertEqual(self.u.reg_read(UC_ARM_REG_PRIMASK),0)
                self.assertEqual(bytes(self.u.mem_read(base.seq.SEQ_STATE_ADDR,256)),before)
                self.assertEqual(len(self.calls),n)
        for taint,mask,z in ((0,0,0),(1,1,0),(0,0,1),(1,1,1)):
            self.setUp();self.setup_graph();cookie=self.fail_read();self.close(cookie)
            self.byte(base.seq.OFF_PROJECT_TAINTED,taint)
            self.u.reg_write(UC_ARM_REG_R4,self.ctrl);self.u.reg_write(UC_ARM_REG_R5,19)
            self.u.reg_write(UC_ARM_REG_PRIMASK,mask);self.u.reg_write(UC_ARM_REG_APSR,z<<30)
            self.call(guard.BUTTON_SITE,end=guard.BUTTON_CONTINUE if z else guard.BUTTON_REJECT)
            self.assertEqual(self.u.reg_read(UC_ARM_REG_PRIMASK),mask)

if __name__=='__main__':unittest.main()
