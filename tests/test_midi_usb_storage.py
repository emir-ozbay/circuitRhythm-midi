"""Stock READ10/readonly WRITE10, real queue worker, synthetic lower flash/USB."""
import unittest
import test_midi_usb_msc as prior
import midi_usb_storage_prototype as storage
import midi_usb_msc_prototype as msc
from midi_usb_storage_test_support import UsbStorageFixture

base=prior.base


class UsbStorageTests(unittest.TestCase):
    setUpClass=classmethod(prior.UsbMscTests.setUpClass.__func__)
    for name in ('setUp','word','read','store','call','setup_playback','setup_recovery','setup_sysex_router',
                 'sysex_descriptor','install_nested_calls','setup_notice','setup_request','seed_notes','stall','release',
                 'capture_shorts','attach_native_note_receiver','setup_ledger','setup_life','setup_session',
                 'setup_control','setup_composite','setup_msc','send','fill_pending','finish_reply'):
        locals()[name]=getattr(prior.UsbMscTests,name)
    sysex_packets=staticmethod(prior.UsbMscTests.sysex_packets)
    bytes_as_packets=staticmethod(prior.UsbMscTests.bytes_as_packets)

    def setup_storage(self): self.setup_msc(); self.sd=UsbStorageFixture(self); self.mc.configure()

    def test_native_read10_runs_queued_worker_then_real_usb_fifo_and_csw(self):
        self.setup_storage(); self.sd.command()
        self.assertEqual(self.sd.status()['reads'],1); self.assertEqual(len(self.sd.flash_reads),1)
        self.assertGreaterEqual(self.sd.worker_visits,2)
        self.assertEqual(self.u.mem_read(storage.BUFFER,4096),self.sd.media)
        self.sd.complete_tx(); self.mc.poll(); self.sd.complete_tx()
        self.assertEqual(self.sd.sent[0],self.sd.media)
        self.assertEqual(self.sd.sent[1][:4],b'USBS'); self.assertEqual(self.sd.sent[1][12],0)
        self.assertEqual(self.mc.status()['rx_active'],1); self.sd.check()

    def test_read_buffer_is_retained_until_tx_disable_ack_and_flush(self):
        self.setup_storage(); self.sd.command(); before=self.u.mem_read(storage.BUFFER,4096)
        self.cc.configure(0); self.assertEqual(self.mc.service(),1)
        self.assertEqual(self.mc.status()['phase'],msc.WAIT_DISABLE)
        self.assertEqual(self.sd.status()['tx_active'],1)
        self.mc.ack(msc.IN_CTL); self.mc.ack(msc.OUT_CTL); self.mc.service()
        self.assertEqual(self.sd.status()['tx_active'],1)
        self.assertEqual(self.u.mem_read(storage.BUFFER,4096),before)
        self.mc.finish_flush(); self.sd.pump()
        self.assertEqual(self.sd.status()['cancel_tx'],1); self.assertEqual(self.sd.sent,[])
        self.assertEqual(self.mc.status()['phase'],msc.SEALED); self.sd.check()

    def test_native_write10_is_write_protected_and_never_calls_storage_write(self):
        from unicorn import UC_HOOK_CODE
        self.setup_storage(); calls=[]
        self.u.hook_add(UC_HOOK_CODE,lambda u,a,n,d:calls.append(a),begin=0x08065194,end=0x08065194)
        self.sd.command(0x2A)
        self.assertEqual(calls,[]); self.assertEqual(self.sd.flash_reads,[])
        self.sd.complete_tx(); self.assertEqual(self.sd.sent[0][:4],b'USBS')
        self.assertEqual(self.sd.sent[0][12],1); self.sd.check()

    def test_reset_after_read_cancels_old_data_then_allows_a_new_read(self):
        self.setup_storage(); self.sd.command(); self.mc.reset_request(); self.sd.pump()
        self.assertEqual(self.sd.status()['cancel_tx'],1)
        self.assertEqual(self.sd.sent,[]); self.sd.command(); self.sd.complete_tx()
        self.assertEqual(self.sd.sent,[self.sd.media]); self.sd.check()

    def test_reset_inside_native_flash_worker_waits_for_reader_and_drain(self):
        import midi_usb_control_prototype as control
        self.setup_storage()
        injected,results=self.install_nested_calls(0x0800ED00,[
            (self.cc.labels['cc_request'],(control.RESET_EVENT,)),(self.mc.labels['mc_service'],())])
        self.ss.record_nested_trampoline(); self.sd.command()
        self.assertEqual(len(injected),1); self.assertEqual(results(),[0,1])
        self.assertEqual(self.sd.status()['tx_active'],0)
        self.assertEqual(self.read(self.sd.backend+16),0)
        self.assertEqual(self.u.mem_read(self.sd.backend+12,1),b'\x00')
        self.sd.pump(); self.assertEqual(self.mc.status()['phase'],msc.SEALED)
        self.assertEqual(self.sd.sent,[]); self.sd.check()

    def test_second_cbw_during_csw_does_not_overwrite_borrowed_csw(self):
        self.setup_storage(); self.sd.command(); self.sd.complete_tx(); self.mc.poll()
        snapshot=self.sd.job[2]; self.sd.command()
        self.assertEqual(self.u.mem_read(msc.BOT,13),snapshot)
        self.assertEqual(self.sd.status()['reads'],1)
        self.sd.complete_tx(); self.mc.poll(); self.assertEqual(self.sd.status()['reads'],2)
        self.sd.complete_tx(); self.sd.check()

    def test_direct_read_cannot_reuse_buffer_owned_by_usb(self):
        self.setup_storage(); self.sd.command(); snapshot=self.sd.job[2]
        self.assertEqual(self.call(0x08065128,0,storage.BUFFER,0,1),0xFFFFFFFF)
        self.assertEqual(self.u.mem_read(storage.BUFFER,4096),snapshot)
        self.assertEqual(self.sd.status()['reads'],1); self.sd.check()

    def test_backend_binding_or_drain_debt_prevents_cancel_finalization(self):
        self.setup_storage(); self.sd.command(); self.cc.configure(0)
        self.word(self.sd.backend+16,1)
        for _ in range(3): self.assertEqual(self.mc.service(),1)
        self.assertEqual(self.mc.status()['phase'],msc.CLOSING)
        self.assertEqual(self.sd.status()['tx_active'],1)
        self.word(self.sd.backend+16,0); self.sd.pump()
        self.assertEqual(self.sd.status()['cancel_tx'],1); self.sd.check()

    def test_readonly_binding_is_preserved_by_each_native_factory_mode(self):
        self.setup_storage()
        for mode in (1,2,3):
            self.call(0x08043264,mode)
            self.assertEqual(self.read(0x200038AC),storage.OPS)
            self.assertEqual(self.call(self.read(storage.OPS+12)&~1,0),1)
        self.sd.command(0x2A); self.sd.complete_tx()
        self.assertEqual(self.sd.sent[0][12],1); self.assertEqual(self.sd.flash_reads,[]); self.sd.check()

    def test_tampered_write_protection_table_is_rejected_before_write_dispatch(self):
        self.setup_storage(); self.word(storage.OPS+12,0x080650E5)
        self.sd.command(0x2A)
        self.assertEqual(self.sd.flash_reads,[])
        self.assertEqual(self.sd.job[1],13)
        self.sd.complete_tx(); self.assertEqual(self.sd.sent[0][12],1); self.sd.check()

    def test_din_off_and_midi_query_survive_cancelled_read(self):
        self.setup_storage(); self.sd.command(); self.output.note(0,60,0,on=False); self.output.drain(0)
        self.mc.reset_request(); self.sd.pump()
        self.assertEqual([self.output.pop(p) for p in (1,2)],[bytes([0x80,60,0])]*2)
        self.ib.rx_data(self.inquiries); self.ib.rx_complete(); self.ib.run(); self.rx.poll(); self.finish_reply()
        self.assertEqual(b''.join(self.native.usb_completed),b''.join(self.replies)); self.sd.check()

    def test_missing_in_disable_ack_keeps_borrowed_read_buffer(self):
        self.setup_storage(); self.sd.command(); self.mc.reset_request(); self.mc.service()
        self.mc.ack(msc.IN_CTL,ack=False)
        for _ in range(3): self.assertEqual(self.mc.service(),1)
        self.assertEqual(self.sd.status()['tx_active'],1)
        self.assertEqual(self.u.mem_read(storage.BUFFER,4096),self.sd.job[2])
        self.mc.ack(msc.IN_CTL); self.sd.pump(); self.sd.check()

    def test_flash_read_error_produces_failed_csw_instead_of_success_data(self):
        self.setup_storage(); self.word(self.sd.lower+4,1); self.sd.command()
        self.assertEqual(self.read(storage.STATE_BASE+storage.READ_RESULT),1)
        self.assertEqual(self.sd.job[1],13); self.sd.complete_tx()
        self.assertEqual(self.sd.sent[0][:4],b'USBS'); self.assertEqual(self.sd.sent[0][12],1)
        self.word(self.sd.lower+4,0); self.sd.command(); self.sd.complete_tx()
        self.assertEqual(self.sd.sent[-1],self.sd.media); self.sd.check()

    def test_two_block_read_keeps_each_chunk_until_completion(self):
        self.setup_storage(); self.sd.command(blocks=2); self.sd.complete_tx()
        self.mc.poll(); self.sd.complete_tx(); self.mc.poll(); self.sd.complete_tx()
        self.assertEqual(self.sd.sent[:2],[self.sd.media]*2)
        self.assertEqual(self.sd.sent[2][12],0); self.assertEqual(self.sd.status()['reads'],2); self.sd.check()

    def test_csw_and_next_cbw_can_be_cancelled_together(self):
        self.setup_storage(); self.sd.command(); self.sd.complete_tx(); self.mc.poll()
        self.assertEqual(self.sd.job[1],13); self.assertEqual(self.mc.status()['rx_active'],1)
        self.mc.reset_request(); self.sd.pump()
        self.assertEqual(self.sd.status()['cancel_tx'],1)
        self.assertGreaterEqual(self.mc.status()['cancel_rx'],1)
        self.assertEqual(self.sd.sent,[self.sd.media]); self.sd.check()

    def test_original_native_read_swallows_backend_error_negative(self):
        self.setup_storage(); self.word(self.sd.lower+4,1)
        self.assertEqual(self.call(self.sd.labels['sd_native_read'],0,storage.BUFFER,0,1),0)
        self.assertEqual(self.u.mem_read(self.sd.backend+24,1),b'\x01'); self.sd.check()

    def test_matching_read_error_survives_a_later_successful_worker_job(self):
        import struct
        from thumb_asm import Asm,movs_imm,str_imm,bx_lr
        self.setup_storage(); self.word(self.sd.lower+4,1)
        descriptor=0x2000AD00
        self.u.mem_write(descriptor,struct.pack('<HH5I',1,0,0x94000,0x21001000,8,0,0))
        a=Asm(0x0800ED80); a.imm32(1,self.sd.lower+4); a.emit(movs_imm,0,0); a.emit(str_imm,0,1); a.emit(bx_lr)
        self.u.mem_write(a.base,a.assemble()[0]); self.ss.flash=bytes(self.u.mem_read(0x08010000,0x70000))
        injected,results=self.install_nested_calls(0x0802C328,[(0x0802C1CC,(self.sd.backend,descriptor)),(a.base,())])
        self.ss.record_nested_trampoline(); self.sd.command()
        self.assertEqual(len(injected),1); self.assertEqual(results(),[0,0])
        self.assertEqual(len(self.sd.flash_reads),2)
        self.assertEqual(self.u.mem_read(self.sd.backend+24,1),b'\x00')
        self.assertEqual(self.read(storage.STATE_BASE+storage.READ_RESULT),1)
        self.sd.complete_tx(); self.assertEqual(self.sd.sent[0][12],1); self.sd.check()

    def test_old_tx_xfrc_after_broken_barrier_remains_indistinguishable_negative(self):
        self.setup_storage(); self.sd.command(); self.mc.reset_request(); self.sd.pump(); self.sd.command()
        for _ in range(64): self.ib.flags[msc.IN_INT]|=0x80; self.ib.run()
        self.assertEqual(self.sd.status()['tx_active'],1)
        # Deliberately violate the hardware cancellation contract. All CPU FIFO
        # bytes are staged, but an untagged old XFRC still claims the new job.
        self.ib.flags[msc.IN_INT]|=1; self.ib.run()
        self.assertEqual(self.sd.status()['tx_active'],0)
        self.assertEqual(self.sd.status()['done'],1); self.sd.check()


if __name__=='__main__': unittest.main()
