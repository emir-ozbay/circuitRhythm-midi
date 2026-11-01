"""Real native class parents; quiescent composite setup, no device APIs."""
import unittest
import test_midi_usb_control as prior
import midi_usb_composite_prototype as composite
import midi_usb_session_prototype as session
from midi_usb_composite_test_support import UsbCompositeFixture

base=prior.base


class UsbCompositeTests(unittest.TestCase):
    setUpClass=classmethod(prior.UsbControlTests.setUpClass.__func__)
    for name in ('setUp','word','read','store','call','setup_playback','setup_recovery',
                 'setup_sysex_router','sysex_descriptor','install_nested_calls',
                 'setup_notice','setup_request','seed_notes','stall','release',
                 'capture_shorts','attach_native_note_receiver','setup_ledger',
                 'setup_life','setup_session','setup_control','send','fill_pending','finish_reply'):
        locals()[name]=getattr(prior.UsbControlTests,name)
    sysex_packets=staticmethod(prior.UsbControlTests.sysex_packets)
    bytes_as_packets=staticmethod(prior.UsbControlTests.bytes_as_packets)

    def setup_composite(self,guard=True):
        self.setup_control(); self.xc=UsbCompositeFixture(self,guard=guard)

    def test_unprotected_real_parent_erases_pending_din_negative(self):
        self.setup_composite(guard=False); self.output.note(0,60,0,on=False)
        self.assertEqual([self.output.pending(p) for p in (1,2)],[1,1])
        self.call(0x08068A2C,self.ib.ctrl,1)
        self.assertEqual([self.output.pending(p) for p in (1,2)],[0,0])
        self.assertIn(('midi_parent',self.ib.ctrl),self.xc.events); self.xc.check()

    def test_real_parents_run_in_order_after_barrier_and_preserve_din(self):
        self.setup_composite(); self.output.note(0,60,0,on=False)
        self.output.drain(0)  # USB copy in flight; retain both DIN FIFO copies.
        self.lc.configured(2); self.assertEqual(self.cc.configure(1),0)
        self.assertEqual(self.xc.events,[]); self.assertEqual(self.xc.status()['pending'],1)
        self.cc.pump()
        self.assertEqual(self.ss.status()['phase'],session.OPEN)
        self.assertEqual([self.output.pending(p) for p in (1,2)],[1,1])
        self.assertEqual([self.output.pop(p) for p in (1,2)],[bytes([0x80,60,0])]*2)
        names=[x[0] for x in self.xc.events]
        self.assertLess(names.index('midi_parent'),names.index('msc_parent'))
        self.assertIn('rx_rearm_attempt',names); self.assertIn('bot_reset',names)
        self.assertEqual(self.xc.status()['skipped'],1); self.assertEqual(self.xc.status()['starts'],1)
        self.assertEqual(self.ss.flushes[-2:],[1,2]); self.assertNotIn('RX',self.ss.flushes)
        self.assertEqual(self.read(self.ib.handle+0x1FC+2*0x1C+0x14),31)
        self.xc.check()

    def test_native_reset_enumeration_and_ep0_composite_setup(self):
        self.setup_composite(); self.ss.arm_rx(); self.cc.reset(); self.cc.pump()
        self.cc.enumerate(); self.cc.address(); self.cc.configure(1); self.cc.pump()
        self.assertEqual(self.xc.status()['starts'],1)
        self.assertEqual(self.ss.status()['phase'],session.OPEN)
        self.ib.rx_data(self.inquiries); self.ib.rx_complete(); self.ib.run()
        self.rx.poll(); self.finish_reply()
        self.assertEqual(b''.join(self.native.usb_completed),b''.join(self.replies)); self.xc.check()

    def test_msc_is_not_constructed_while_midi_owns_old_tx(self):
        self.setup_composite(); self.send(self.inquiries); self.q.poll(); self.q.poll()
        self.lc.configured(2); self.cc.configure(1)
        self.assertEqual(self.xc.events,[]); self.assertEqual(self.cc.service(),1)
        self.assertFalse(any(n=='msc_parent' for n,_ in self.xc.events))
        self.cc.pump(); self.assertEqual(self.ss.status()['cancel_tx'],1)
        self.assertEqual(self.xc.status()['starts'],1); self.xc.check()

    def test_accepted_rx_debt_retains_closed_and_never_constructs_msc(self):
        self.setup_composite(); self.fill_pending(); before=self.rx.status()
        self.lc.configured(2); self.cc.configure(1)
        for _ in range(4): self.assertEqual(self.cc.service(),1)
        self.assertEqual(self.rx.status(),before); self.assertEqual(self.xc.status()['starts'],0)
        self.assertFalse(any(n=='msc_parent' for n,_ in self.xc.events)); self.xc.check()

    def test_direct_bound_class_call_cannot_bypass_list_barrier(self):
        self.setup_composite()
        self.assertEqual(self.call(0x080525B2,self.xc.msc,self.ib.ctrl,1),1)
        self.assertEqual(self.call(0x080525B2,self.ib.wrapper,self.ib.ctrl,1),1)
        self.assertEqual(self.xc.events,[]); self.xc.check()

    def test_active_msc_or_pending_completion_rejects_list_init(self):
        self.setup_composite()
        for reg,val in ((0xB40,session.EPENA),(0x940,session.EPENA),(0xB48,1),(0x948,2)):
            if reg in self.ib.flags: self.ib.flags[reg]=val
            else: self.ss.poke(reg,val)
            self.assertEqual(self.call(0x08040B5A,self.ib.root,self.ib.ctrl,1),1)
            self.assertEqual(self.xc.status()['starts'],0)
            if reg in self.ib.flags: self.ib.flags[reg]=0
            else: self.ss.poke(reg,0)
        self.assertEqual(self.xc.events,[]); self.xc.check()

    def test_native_composite_descriptor_has_three_interfaces_and_both_pairs(self):
        self.setup_composite(); data=self.xc.descriptor()
        self.assertEqual(len(data),125); self.assertEqual(int.from_bytes(data[2:4],'little'),125)
        self.assertEqual(data[4],3)
        records=[]; pos=0
        while pos<len(data):
            n=data[pos]; self.assertGreaterEqual(n,2); records.append(data[pos:pos+n]); pos+=n
        self.assertEqual(pos,len(data))
        self.assertEqual([r[2] for r in records if r[1]==4],[0,1,2])
        self.assertEqual([r[2] for r in records if r[1]==5],[1,0x81,0x82,2])
        self.xc.check()

    def test_native_list_teardown_calls_real_msc_deinit(self):
        self.setup_composite(); self.lc.configured(2); self.cc.configure(1); self.cc.pump()
        self.xc.events.clear(); self.assertEqual(self.cc.configure(0),0); self.cc.pump()
        self.assertTrue(any(n=='msc_deinit' for n,_ in self.xc.events))
        self.assertEqual(self.ss.status()['phase'],session.SEALED)
        self.assertEqual(self.u.mem_read(0x20006DE4,1),b'\x00'); self.xc.check()

    def test_plain_router_clear_outside_owned_parent_stays_native(self):
        self.setup_composite(); self.output.note(0,60,0,on=False)
        self.call(0x080297C0,self.output.router)
        self.assertEqual([self.output.pending(p) for p in (1,2)],[0,0])
        self.assertEqual(self.xc.status()['skipped'],0); self.xc.check()

    def test_reset_inside_real_midi_parent_stops_following_msc_constructor(self):
        import midi_usb_control_prototype as control
        self.setup_composite(); self.lc.configured(2); self.cc.configure(1)
        injected,results=self.install_nested_calls(0x08068A2C,[
            (self.cc.labels['cc_request'],(control.RESET_EVENT,))])
        self.ss.record_nested_trampoline()
        self.cc.pump()
        self.assertEqual(len(injected),1); self.assertEqual(results(),[0])
        self.assertFalse(any(n=='msc_parent' for n,_ in self.xc.events))
        self.assertEqual(self.ss.status()['phase'],session.SEALED)
        self.assertEqual(self.xc.status()['running'],0); self.xc.check()

    def test_repeated_request_runs_each_real_parent_once(self):
        self.setup_composite(); self.lc.configured(2); self.cc.configure(1)
        self.assertEqual(self.call(0x08040B5A,self.ib.root,self.ib.ctrl,1),0)
        self.cc.pump(); self.assertEqual(self.cc.service(),0)
        self.assertEqual([n for n,_ in self.xc.events].count('midi_parent'),1)
        self.assertEqual([n for n,_ in self.xc.events].count('msc_parent'),1); self.xc.check()

    def test_new_msc_owner_between_queue_and_service_prevents_constructor(self):
        self.setup_composite(); self.lc.configured(2); self.cc.configure(1)
        self.ss.poke(0xB40,session.EPENA)
        for _ in range(4):
            self.cc.service()
            if self.ss.status()['phase']==session.WAIT_FLUSH: self.ss.finish_flush()
        self.assertEqual(self.xc.status()['starts'],0)
        self.assertEqual(self.xc.events,[]); self.assertEqual(self.ss.status()['phase'],session.BROKEN)
        self.xc.check()

    def test_unrelated_class_keeps_native_constructor(self):
        self.setup_composite(); obj,vt,empty=0x2000A600,0x2000A640,0x2000A680
        self.word(obj,vt); self.word(vt,0x080427D3)
        self.word(obj+4,empty); self.word(obj+8,empty)
        self.assertEqual(self.call(0x080525B2,obj,self.ib.ctrl,1),0)
        self.assertEqual(self.xc.status()['starts'],0); self.xc.check()

    def test_wrong_caller_cannot_claim_router_clear_exception(self):
        import midi_usb_control_prototype as control
        self.setup_composite(); self.output.note(0,60,0,on=False)
        for off,value in ((composite.RUNNING,1),(composite.CURRENT,self.ib.wrapper),(composite.GENERATION,0)):
            self.word(composite.STATE_BASE+off,value)
        self.word(control.STATE_BASE+control.INIT_BUSY,1)
        self.word(session.STATE_BASE+session.PHASE,session.SEALED)
        self.assertEqual(self.call(0x080297C0,self.output.router),1)
        self.assertEqual([self.output.pending(p) for p in (1,2)],[1,1])
        self.assertEqual(self.xc.status()['skipped'],0)
        self.word(composite.STATE_BASE+composite.RUNNING,0)
        self.word(control.STATE_BASE+control.INIT_BUSY,0); self.xc.check()

    def test_reset_after_msc_parent_does_not_resume_or_erase_msc_owner(self):
        import midi_usb_control_prototype as control
        self.setup_composite(); self.lc.configured(2); self.cc.configure(1)
        injected,results=self.install_nested_calls(0x080661EA,[
            (self.cc.labels['cc_request'],(control.RESET_EVENT,))])
        self.ss.record_nested_trampoline(); self.cc.pump()
        self.assertEqual(len(injected),1); self.assertEqual(results(),[0])
        self.assertEqual(self.ss.status()['phase'],session.SEALED)
        self.assertTrue(self.ss.regs[0xB40]&session.EPENA)
        self.assertEqual(self.cc.status()['restarts'],0); self.xc.check()


if __name__=='__main__': unittest.main()
