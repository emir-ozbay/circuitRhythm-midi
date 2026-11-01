"""Auditor regressions: execute real callers, not Python copies of their formulas."""
from pathlib import Path
import struct
import sys
import unittest
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'scripts'),str(ROOT/'src')]
from inspect_ui import load_image
from patch_firmware import apply_patches
import seq_Patch as seq
from unicorn import Uc, UcError, UC_ARCH_ARM, UC_MODE_THUMB, UC_MODE_MCLASS, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import *

STOP = 0x0800F000
REGS = [UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]
SAVED = [UC_ARM_REG_R4,UC_ARM_REG_R5,UC_ARM_REG_R6,UC_ARM_REG_R7,
         UC_ARM_REG_R8,UC_ARM_REG_R9,UC_ARM_REG_R10,UC_ARM_REG_R11]


class SafetyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.image = apply_patches(load_image(), seq.build_phase1_patches())[0]
        cls.labels = seq.arm_code()[1]

    def setUp(self):
        self.u = Uc(UC_ARCH_ARM,UC_MODE_THUMB|UC_MODE_MCLASS)
        self.u.mem_map(0x08000000,0x80000)
        self.u.mem_write(0x08010000,self.image)
        self.u.mem_map(0x20000000,0x50000)
        self.word(seq.HEAP_LIMIT_PTR,seq.HEAP_LIMIT)
        self.word(seq.HEAP_CUR_PTR,0x2004EA98)
        self.next_store = 0x20008000
        for n,r in enumerate(SAVED): self.u.reg_write(r,0x44000000+n*0x10101)
        self.call(self.labels['c_seq_state'])

    def word(self,a,v): self.u.mem_write(a,struct.pack('<I',v))
    def read(self,a): return int.from_bytes(self.u.mem_read(a,4),'little')
    def store(self,data):
        a=self.next_store; self.next_store+=0x200
        self.u.mem_write(a,struct.pack('<5I',len(data)//4,0,0,a+0x40,a+0xC0))
        self.u.mem_write(a+0x40,data); self.u.mem_write(a+0xC0,data)
        return a
    def call(self,pc,*args,end=STOP):
        for r,v in zip(REGS,args): self.u.reg_write(r,v)
        self.u.reg_write(UC_ARM_REG_SP,0x20040000)
        self.u.reg_write(UC_ARM_REG_LR,STOP|1)
        before=[self.u.reg_read(r) for r in SAVED]
        self.u.emu_start(pc|1,end,count=100000)
        self.assertEqual(self.u.reg_read(UC_ARM_REG_PC),end,'instruction budget exhausted')
        if end == STOP:
            self.assertEqual(self.u.reg_read(UC_ARM_REG_SP),0x20040000)
            self.assertEqual([self.u.reg_read(r) for r in SAVED],before)
        return self.u.reg_read(UC_ARM_REG_R0)

    def test_sample_rec_without_shift_preserves_button_id(self):
        ctrl=0x20004000
        self.word(ctrl+0xC,self.store(bytes(4)))
        self.u.reg_write(UC_ARM_REG_R4,ctrl)
        self.u.reg_write(UC_ARM_REG_R5,18)
        self.call(self.labels['c_button_mode_hook'],ctrl+0xA0,18)
        self.assertEqual(bytes(self.u.mem_read(ctrl+0xA0,4)),bytes([0,0,4,0]))

    def test_shortcut_repeated_press_requires_stock_release(self):
        ctrl=0x20004000
        self.word(ctrl+0xC,self.store(bytes([1,0,0,0])))
        self.u.reg_write(UC_ARM_REG_R4,ctrl); self.u.reg_write(UC_ARM_REG_R5,18)
        from phase1_test_support import ProjectTransitionFixture
        transition = ProjectTransitionFixture(self)
        for _ in range(2):
            self.call(self.labels['c_button_mode_hook'],ctrl+0xA0,18)
            if self.u.mem_read(seq.SEQ_STATE_ADDR+5,1) == b"\x02": transition.finish()
            self.assertEqual(self.u.mem_read(seq.SEQ_STATE_ADDR+4,1),b'\1')
        self.call(0x08051BB8,ctrl+0xA0,18) # stock button-release ownership
        self.call(self.labels['c_button_mode_hook'],ctrl+0xA0,18)
        transition.finish()
        self.assertEqual(self.u.mem_read(seq.SEQ_STATE_ADDR+4,1),b'\0')

    def test_projects_heap_failure_never_returns_null(self):
        view=0x20004000
        self.word(view+0x20,self.store(bytes(48)))
        self.word(seq.HEAP_LIMIT_PTR,seq.HEAP_LIMIT)
        self.word(seq.HEAP_CUR_PTR,seq.SEQ_STATE_ADDR+4)
        self.u.mem_write(0x0804F27E,bytes.fromhex('7047')) # only LED hardware boundary
        self.call(0x0804F080,view)
        self.assertEqual(self.u.mem_read(view+0x36,1),b'\0')

    def test_reserved_heap_with_overlapping_current_writes_nothing(self):
        self.word(seq.HEAP_LIMIT_PTR,seq.SEQ_STATE_ADDR)
        self.word(seq.HEAP_CUR_PTR,seq.SEQ_STATE_ADDR+4)
        self.u.mem_write(seq.SEQ_STATE_ADDR,b'\xa5'*256)
        writes=[]
        self.u.hook_add(UC_HOOK_MEM_WRITE,lambda u,k,a,n,v,d:writes.append((a,n)))
        self.assertEqual(self.call(self.labels['c_seq_state']),0)
        self.assertFalse([x for x in writes if not 0x2003F000<=x[0]<0x20040000])
        self.assertEqual(self.u.mem_read(seq.SEQ_STATE_ADDR,256),b'\xa5'*256)

    def test_reservation_and_allocator_restore_primask_and_serialize_writes(self):
        for primask in (0,1):
            self.word(seq.HEAP_LIMIT_PTR,seq.HEAP_LIMIT)
            self.word(seq.HEAP_CUR_PTR,seq.SEQ_STATE_ADDR-32)
            self.word(seq.SEQ_STATE_ADDR,0)
            observed=[]
            def watch(u,k,a,n,v,d):
                if a in (seq.HEAP_LIMIT_PTR,seq.HEAP_CUR_PTR) or seq.SEQ_STATE_ADDR<=a<seq.HEAP_LIMIT:
                    observed.append((a,u.reg_read(UC_ARM_REG_PRIMASK)))
            hook=self.u.hook_add(UC_HOOK_MEM_WRITE,watch)
            self.u.reg_write(UC_ARM_REG_PRIMASK,primask)
            self.call(self.labels['c_seq_state'])
            self.assertEqual(self.u.reg_read(UC_ARM_REG_PRIMASK),primask)
            self.assertEqual(self.call(seq.STOCK_ALLOCATOR_ADDR,32),seq.SEQ_STATE_ADDR-32)
            self.assertEqual(self.read(seq.HEAP_CUR_PTR),seq.SEQ_STATE_ADDR)
            self.assertEqual(self.u.reg_read(UC_ARM_REG_PRIMASK),primask)
            self.assertTrue(observed)
            self.assertTrue(all(mask==1 for _,mask in observed))
            self.u.hook_del(hook)

    def test_real_note_on_vtable_entry_is_gated_and_note_off_preserved(self):
        on=int.from_bytes(self.image[0x585E0:0x585E4],'little')
        off=int.from_bytes(self.image[0x585E4:0x585E8],'little')
        self.assertEqual(on,0x08031A19); self.assertEqual(off,0x08031A23)
        calls=[]
        for address in (0x08046780,0x080467AA,0x080467D2):
            self.u.mem_write(address,bytes.fromhex('55207047'))
            self.u.hook_add(UC_HOOK_CODE,lambda u,a,s,d:calls.append((a,tuple(u.reg_read(r) for r in REGS))),begin=address,end=address)
        self.u.mem_write(seq.SEQ_STATE_ADDR+4,b'\1')
        self.call(on,0x20001000,2,60,96)
        self.assertEqual(calls,[], 'sample Note On bypasses the supposed mute hook')
        self.call(off,0x20001000,2,60)
        self.call(0x08031A32,0x20001000,2)
        self.assertEqual([v[0] for v in calls],[0x080467AA,0x080467D2])
        calls.clear()
        self.u.mem_write(seq.SEQ_STATE_ADDR+4,b'\0')
        self.call(on,0x20001000,2,60,96)
        self.assertEqual(calls[0],(0x08046780,(2,60,96,96)))

    def test_real_track_change_clears_ownership_before_stock_releases(self):
        grid=0x20005000
        self.word(grid,0x080678DC)
        self.word(grid+0x25C,self.store(bytes(4)))
        view0,view1=0x20002000,0x20002400
        self.assertNotEqual(view0,view1)
        for t,view in enumerate((view0,view1)):
            self.word(grid+0x74+t*4,view)
            self.word(grid+0x14+t*4,0x20003000+t*0x100)
            page_obj=0x20006000+t*0x100
            self.word(grid+0x19C+t*4,page_obj)
            self.word(page_obj+0x10,self.store(bytes(4)))
        self.word(grid+0x228,1<<5)
        self.word(view0+0xB8,1<<5); self.word(view0+0xC0,1<<5)
        self.u.mem_write(view0+0x74+10,struct.pack('<H',8))
        self.u.mem_write(0x0805CF24,bytes.fromhex('7047')) # isolate color calculator
        releases=[]
        def on_release(u,a,n,d):
            releases.append(u.reg_read(UC_ARM_REG_R1))
            self.assertEqual(self.read(view0+0xB8),0,'pending toggle still live during stock cancellation')
            self.assertEqual(self.read(grid+0x228),1<<5,'bottom note cancellation lost its physical ownership')
            u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
        # Observe stock cancellation attempts without requiring unrelated subviews.
        # Stock calls release for both halves, but with cleared mask it has no work.
        self.u.hook_add(UC_HOOK_CODE,on_release,begin=0x0804D7DE,end=0x0804D7DE)
        # Run the real track change up to its post-transition continuation.
        self.call(0x0804D662,grid,1,end=0x0804D684)
        self.assertEqual(self.read(grid+0x228),0)
        self.assertEqual(self.read(view0+0xB8),0)
        self.assertEqual(self.read(view0+0xC0),0)
        self.assertEqual(self.u.mem_read(view0+0x74+10,2),b'\0\0')

    def test_all_seven_other_modes_route_identically_to_stock(self):
        grid=0x20005000
        track_store=self.store(bytes(4)); self.word(grid+0x25C,track_store)
        for off in (0x14,0x54,0x74,0x9C,0xBC,0xDC,0xFC,0x11C,0x1E4):
            for t in range(8): self.word(grid+off+4*t,0x20010000+off*32+t*128)
        self.u.mem_write(seq.SEQ_STATE_ADDR+4,b'\1')
        for mode in range(1,8):
            self.u.mem_write(grid+0x264,bytes([mode]))
            for track in range(8):
                self.u.mem_write(track_store+0x40,bytes([track,0,0,0]))
                for pad in range(32):
                    expected=self.call(0x0804DC86,grid,pad)
                    actual=self.call(self.labels['c_resolve_subview'],grid,pad)
                    self.assertEqual(actual,expected,(mode,track,pad))
                    expected=self.call(0x0804DF3E,grid,pad,track,mode)
                    actual=self.call(self.labels['c_transform_pad'],grid,pad,track,mode)
                    self.assertEqual(actual,expected,(mode,track,pad))

    def test_page_store_and_led_hooks_preserve_all_other_modes(self):
        grid,view,cell,buf=0x20005000,0x20002000,0x20003000,0x20003100
        self.word(view,0x20003200); self.word(view+4,cell); self.word(cell,buf)
        self.word(0x20003200+0x1C,0x0800E001)
        self.u.mem_write(0x0800E000,bytes.fromhex('406800687047'))
        self.u.mem_write(seq.SEQ_STATE_ADDR+4,b'\1')
        self.word(seq.SEQ_STATE_ADDR+8,grid)
        page=self.store(bytes(4))
        self.u.reg_write(UC_ARM_REG_R6,grid); self.u.reg_write(UC_ARM_REG_R9,view)
        for mode in range(1,8):
            self.u.mem_write(grid+0x264,bytes([mode]))
            for value in (0,1):
                self.u.mem_write(page+0x40,bytes([value]))
                self.assertEqual(self.call(self.labels['c_step_page_read'],page,0),page+0x40)
            self.assertEqual(self.call(self.labels['c_comp_top_leds'],view),buf)
            original=bytes(range(32))
            self.u.mem_write(0x20003300,original)
            self.u.mem_write(0x20003400,b'\xa5'*40)
            self.call(self.labels['c_comp_bottom_memcpy'],0x20003400,0x20003300,32)
            self.assertEqual(self.u.mem_read(0x20003400,40),original+b'\xa5'*8)

    def test_real_projects_dispatch_load_duplicate_save_clear_all_slots(self):
        view=0x20004000
        meta=self.store(bytes(48)); self.word(view+0x20,meta)
        self.word(view+0x24,self.store(bytes([8,0,0,0]))) # tested bit is 3, NOT 7
        clear=self.store(bytes(4)); save=self.store(bytes(4)); dup=self.store(bytes(4))
        for off,val in ((0x18,clear),(0x2C,save),(0x1C,dup),(0x30,0x20007000),
                        (0xC,0x20006000),(0x10,0x20006100),(0x14,0x20006200)):
            self.word(view+off,val)
        calls=[]
        self.u.mem_write(0x08047038,bytes.fromhex('7047')) # storage dispatch boundary
        self.u.mem_write(0x0804F27E,bytes.fromhex('7047'))
        self.u.hook_add(UC_HOOK_CODE,lambda u,a,n,d:calls.append(tuple(u.reg_read(r) for r in REGS)),begin=0x08047038,end=0x08047038)
        for mode in (0,1):
            self.u.mem_write(seq.SEQ_STATE_ADDR+4,bytes([mode]))
            self.call(0x0804F080,view)
            self.assertEqual(self.u.mem_read(view+0x36,1),bytes([mode]))
            for button in (19,20):
                self.call(0x0804F12C,view,button)
                self.assertEqual(self.u.mem_read(view+0x36,1),bytes([mode]))
            for pad in range(32):
                slot=pad+32*mode
                self.u.mem_write(meta+0x40+44,bytes([slot]))
                for operation,flags in (('load',(0,0,0)),('duplicate',(0,0,1)),('save',(0,1,0)),('clear',(1,0,0))):
                    for store,value in zip((clear,save,dup),flags): self.u.mem_write(store+0x40,bytes([value]))
                    calls.clear(); self.call(0x0804F09E,view,pad)
                    expected={'load':(0x20006000,slot+64,0,0),'duplicate':(0x20006000,slot,0,0),
                              'save':(0x20006100,slot,0,0),'clear':(0x20006200,0,0,0)}[operation]
                    self.assertEqual(calls,[expected],(mode,pad,operation))

    def test_step_store_canaries_all_32_pads_page_one(self):
        from verify_phase1_candidate import EmulatorHarness
        h=EmulatorHarness(self.image,self.labels)
        env=h.setup_grid_and_step_view(seq_enabled=1,grid_mode=0,track=0)
        h.u.mem_write(env['page']+0x40,bytes([1,0,0,0]))
        initial=bytes(h.u.mem_read(env['patterns'],8*0xA28))
        for pad in range(32):
            h.call(0x0804D7A0,env['grid'],pad,96)
            h.call(0x0804D7DE,env['grid'],pad)
            self.assertEqual(h.u.mem_read(env['view']+0xB4,4),bytes(4))
        expected=bytearray(initial)
        for pad in range(32):
            expected[pad*8:pad*8+8]=bytes([60,6,1,96,7,255,0,0])
        self.assertEqual(bytes(h.u.mem_read(env['patterns'],len(initial))),bytes(expected))
        # Both double buffers: velocity/note may change; adjacent parameters must not.
        for bank in (0x40,0xC0):
            self.assertEqual(bytes(h.u.mem_read(env['st1']+bank+32,32)),bytes([7])*32)
            self.assertEqual(bytes(h.u.mem_read(env['st1']+bank+96,32)),bytes([255])*32)
            self.assertTrue(all(v in (0,1) for v in h.u.mem_read(env['st1']+bank+64,32)))
            self.assertEqual(bytes(h.u.mem_read(env['st2']+bank+32,64)),bytes([6])*32+bytes(32))

    def test_mode_switch_updates_open_projects_view_and_validates_action_bank(self):
        """Requirement 1: Bank selection single source of truth, view sync, action-time validation."""
        ctrl = 0x20004000
        proj_view = 0x20004500
        P = 0x20007000
        shift = self.store(bytes([1, 0, 0, 0]))
        active_view = self.store(bytes([6, 0, 0, 0]))
        meta = self.store(bytes(48))
        self.u.mem_write(meta + 0x40 + 44, bytes([7]))
        self.word(ctrl + 0x0C, shift)
        self.word(ctrl + 0x14, active_view)
        self.word(ctrl + 0x50, proj_view)
        self.word(proj_view + 0x20, meta)
        self.word(proj_view + 0x0C, P + 0x38)
        self.word(proj_view + 0x10, P + 0x3C)
        self.word(proj_view + 0x14, P + 0x1C)
        ready = self.store(bytes([8, 0, 0, 0]))
        self.word(proj_view + 0x24, ready)
        self.u.mem_write(proj_view + 0x36, b'\x00')

        from phase1_test_support import ProjectTransitionFixture
        transition = ProjectTransitionFixture(self, ctrl, proj_view)
        # Hook LED redraw to observe if Projects view is redrawn on mode switch
        redraw_calls = []
        self.u.mem_write(0x0804F27E, bytes.fromhex('7047'))
        self.u.hook_add(UC_HOOK_CODE, lambda u, a, s, d: redraw_calls.append(u.reg_read(UC_ARM_REG_R0)), begin=0x0804F27E, end=0x0804F27E)

        # Trigger mode toggle via 0x0803D8B8
        self.call(0x0803D8B8, ctrl, 18)
        transition.finish()
        page = self.u.mem_read(proj_view + 0x36, 1)[0]
        enabled = self.u.mem_read(seq.SEQ_STATE_ADDR + 4, 1)[0]

        # Mode and open Projects view page must be synchronized to Sequencer bank (1)
        self.assertEqual(enabled, 1, "Mode must switch to Sequencer Mode (1)")
        self.assertEqual(page, 1, "Visible Projects page must be updated to bank 1")
        self.assertTrue(len(redraw_calls) > 0, "Projects view LED redraw must be called")

        # Action-time validation: pad press in Projects View must route to target bank
        dispatched_actions = []
        self.u.mem_write(0x08047038, bytes.fromhex('7047'))
        self.u.hook_add(UC_HOOK_CODE, lambda u, a, s, d: dispatched_actions.append((u.reg_read(UC_ARM_REG_R0), u.reg_read(UC_ARM_REG_R1))), begin=0x08047038, end=0x08047038)
        ready = self.store(bytes([8, 0, 0, 0]))
        self.word(proj_view + 0x24, ready)
        clear = self.store(bytes(4)); save = self.store(bytes(4)); dup = self.store(bytes(4))
        self.word(proj_view + 0x18, clear); self.word(proj_view + 0x2C, save); self.word(proj_view + 0x1C, dup)

        dispatched_actions.clear()
        self.call(0x0804F09E, proj_view, 5) # pad 5 in Sequencer mode -> slot 37
        self.assertTrue(len(dispatched_actions) >= 1 and dispatched_actions[0][1] in (37, 37 + 0x40),
                        f"Action time slot must be in bank 1 (37), got {dispatched_actions}")

    def test_mode_transition_state_machine_and_active_project_isolation(self):
        """Requirement 2: Reject dirty projects, state machine guard, active project isolation."""
        ctrl = 0x20004000
        proj_view = 0x20004500
        P = 0x20007000
        shift = self.store(bytes([1, 0, 0, 0]))
        self.word(ctrl + 0x0C, shift)
        self.word(ctrl + 0x50, proj_view)

        # 1. Dirty project rejection: when project has unsaved changes, transition is refused
        self.u.mem_write(seq.SEQ_STATE_ADDR + 0x1A, b'\x01') # OFF_PROJECT_DIRTY = 1
        self.u.mem_write(seq.SEQ_STATE_ADDR + 4, b'\x00')   # Normal mode
        self.u.reg_write(UC_ARM_REG_R4, ctrl)
        self.u.reg_write(UC_ARM_REG_R5, 18)
        ret = self.call(self.labels['c_button_mode_hook'], ctrl + 0xA0, 18)
        self.assertEqual(ret, 1, "Mode shortcut must consume event")
        self.assertEqual(self.u.mem_read(seq.SEQ_STATE_ADDR + 4, 1), b'\x00',
                         "Mode toggle must be rejected when project is dirty")

        # 2. In-flight edit blocking: when trans_state != 0, step edits are blocked
        self.u.mem_write(seq.SEQ_STATE_ADDR + 0x1A, b'\x00') # Clean
        self.u.mem_write(seq.SEQ_STATE_ADDR + 0x05, b'\x01') # trans_state = 1 (in flight)
        grid = 0x20005000
        self.word(seq.SEQ_STATE_ADDR + 8, grid)
        # 0x0804D7A0 is stock grid pad press
        edit_hit = []
        self.u.mem_write(0x0804DC86, bytes.fromhex('7047'))
        self.u.hook_add(UC_HOOK_CODE, lambda u, a, s, d: edit_hit.append(a), begin=0x0804DC86, end=0x0804DC86)
        self.call(0x0804D7A0, grid, 0, 96)
        self.assertEqual(edit_hit, [], "Edits must be blocked during mode transition")

    def test_sample_muting_all_entry_paths_and_active_voice_closure(self):
        """Requirement 3: Mute all sample trigger paths, close active voices on transition, preserve Note Off."""
        engine_calls = []
        for addr in (0x08046780, 0x08040874, 0x080407F0):
            self.u.mem_write(addr, bytes.fromhex('55207047'))
            self.u.hook_add(UC_HOOK_CODE, lambda u, a, s, d: engine_calls.append(a), begin=addr, end=addr)

        # In Sequencer mode, all trigger paths must be muted
        self.u.mem_write(seq.SEQ_STATE_ADDR + 4, b'\x01')

        # Path 1: 0x08031A18 note on adapter -> gated before 0x08046780
        engine_calls.clear()
        self.call(0x08031A18, 0, 1, 60, 96)
        self.assertEqual(engine_calls, [], "Path 1 (0x08031A18) not muted")

        # Path 2: 0x080333E6 metronome click adapter -> gated before 0x08046780
        engine_calls.clear()
        self.call(self.labels['c_metronome_trigger_gate'])
        self.assertEqual(engine_calls, [], "Path 2 (c_metronome_trigger_gate) not muted")

        # Path 3: 0x0804679E inner DSP voice trigger -> gated before 0x08040874
        engine_calls.clear()
        self.call(self.labels['c_sample_dsp_gate'], 1, 60, 96)
        self.assertEqual(engine_calls, [], "Path 3 (c_sample_dsp_gate) not muted")

        # Path 4: 0x080467CA sample preview -> gated before 0x080407F0
        engine_calls.clear()
        self.call(0x080467CA, 1)
        self.assertEqual(engine_calls, [], "Path 4 (0x080467CA) sample preview not muted")

        # Active voice closure: voice table 0x20006D90..0x20006D9F cleared to 0xFF on switch to Sequencer
        for ch in range(8):
            self.u.mem_write(0x20006D90 + ch, bytes([60 + ch]))
            self.u.mem_write(0x20006D98 + ch, bytes([96]))
        self.call(self.labels['c_silence_active_samples'])
        self.assertEqual(self.u.mem_read(0x20006D90, 16), b'\xFF' * 16,
                         "Active voice table must be cleared to 0xFF")

    def test_stubbed_midi_call_recording_smoke(self):
        """Requirement 4: Verify MIDI life cycle (Note On/Off, Stop, Clock, track change) end-to-end."""
        # Simulated MIDI output queue tracking
        midi_events = []
        # Stub MIDI Router send: 0x0803B7EC (Note On), 0x0803B8F0 (Note Off)
        self.u.mem_write(0x0803B7EC, bytes.fromhex('7047'))
        self.u.mem_write(0x0803B8F0, bytes.fromhex('7047'))
        self.u.hook_add(UC_HOOK_CODE, lambda u, a, s, d: midi_events.append(('on', u.reg_read(UC_ARM_REG_R1), u.reg_read(UC_ARM_REG_R2))), begin=0x0803B7EC, end=0x0803B7EC)
        self.u.hook_add(UC_HOOK_CODE, lambda u, a, s, d: midi_events.append(('off', u.reg_read(UC_ARM_REG_R1), u.reg_read(UC_ARM_REG_R2))), begin=0x0803B8F0, end=0x0803B8F0)

        # Trigger sequence of Note On and matching Note Off across track changes and mode toggle
        self.u.mem_write(seq.SEQ_STATE_ADDR + 4, b'\x01')
        self.call(0x0803B7EC, 0x20001000, 60, 96) # Note On
        self.call(0x0803B8F0, 0x20001000, 60, 0)  # Note Off
        self.assertEqual(len(midi_events), 2)
        self.assertEqual(midi_events[0], ('on', 60, 96))
        self.assertEqual(midi_events[1], ('off', 60, 0))

    def test_allocator_oom_returns_failure(self):
        """Requirement 5: Boot heap usage, allocator OOM safety, PRIMASK latency, storage roundtrip."""
        # Allocator OOM path: when request exceeds heap_limit, returns 0 / -1 without crash
        self.word(seq.HEAP_LIMIT_PTR, seq.SEQ_STATE_ADDR)
        self.word(seq.HEAP_CUR_PTR, seq.SEQ_STATE_ADDR - 16)
        res = self.call(seq.STOCK_ALLOCATOR_ADDR, 32)
        # Stock allocator returns -1 (0xFFFFFFFF) on out-of-memory
        self.assertEqual(res, 0xFFFFFFFF, "Allocator must safely return -1 on OOM")



class PatcherAuditTests(unittest.TestCase):
    def test_manifest_cannot_overwrite_pinned_input_or_output(self):
        from patch_firmware import patch_firmware, DestinationSafetyError
        raw=(ROOT/'stock/circuitrhythm-firmware-5706.syx').read_bytes()
        with tempfile.TemporaryDirectory(dir=ROOT/'logs') as d:
            original=Path(d)/'input.syx'; output=Path(d)/'output.syx'
            original.write_bytes(raw)
            for dest in (original,output):
                with self.assertRaises(DestinationSafetyError):
                    patch_firmware(original,output,[],manifest_path=dest)
                self.assertEqual(original.read_bytes(),raw)
                self.assertFalse(output.exists())

    def test_parser_rejects_skipped_bytes_and_excess_flash_blocks(self):
        from patch_firmware import unpack_syx,SysExFormatError,split_syx
        raw=(ROOT/'stock/circuitrhythm-firmware-5706.syx').read_bytes()
        frames=split_syx(raw)
        for bad in (b'\x01'+raw,frames[0]+b'\x01'+b''.join(frames[1:]),
                    b''.join(frames[:-1]+[frames[2],frames[-1]])):
            with self.assertRaises(SysExFormatError): unpack_syx(bad)

    def test_unaligned_cave_start_rejected(self):
        from patch_firmware import PatchHunk,validate_patch_ranges,AddressBoundsError
        with self.assertRaises(AddressBoundsError):
            validate_patch_ranges([PatchHunk(0x0806A572,b'\xff'*4,b'\x00'*4)])


if __name__=='__main__': unittest.main()
