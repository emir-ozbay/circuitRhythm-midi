"""Cancellation/register-contract tests; tagged bridge is experimental only."""
import hashlib
import unittest
import test_midi_usb_lifecycle as prior
import midi_usb_session_prototype as session
import midi_usb_lifecycle_prototype as life
import midi_usb_ledger_prototype as ledger
import midi_recovery_prototype as recovery
from midi_usb_session_test_support import UsbSessionFixture, Transfer

base=prior.base


class UsbSessionTests(unittest.TestCase):
    setUpClass=classmethod(prior.UsbLifecycleTests.setUpClass.__func__)
    for name in ('setUp','word','read','store','call','setup_playback','setup_recovery',
                 'setup_sysex_router','sysex_descriptor','install_nested_calls',
                 'setup_notice','setup_request','seed_notes','stall','release',
                 'capture_shorts','attach_native_note_receiver','setup_ledger',
                 'setup_life','send','fill_pending'):
        locals()[name]=getattr(prior.UsbLifecycleTests,name)
    sysex_packets=staticmethod(prior.UsbLifecycleTests.sysex_packets)
    bytes_as_packets=staticmethod(prior.UsbLifecycleTests.bytes_as_packets)

    def setup_session(self):
        self.setup_life(native=True); self.ss=UsbSessionFixture(self)

    def old_reply(self):
        self.send(self.inquiries); self.q.poll(); self.q.poll()
        self.assertEqual(self.q.status()['active'],0)
        self.assertEqual(self.rx.status()['pending'],0)
        self.assertIsNotNone(self.native.in_flight)
        self.assertEqual(len(self.ss.tx_jobs),1)
        return self.ss.tx_jobs[-1]

    def drain_new(self):
        for _ in range(20):
            self.q.poll(); self.rx.poll()
            if self.native.in_flight is not None:
                self.assertEqual(self.ss.tx_done(self.ss.tx_jobs[-1]),1)
            if not self.q.status()['active'] and not self.rx.status()['pending'] and self.native.in_flight is None:
                return
        self.fail('new session did not drain')

    def test_old_inflight_tx_is_cancelled_before_reopen_and_stale_completion_rejected(self):
        self.setup_session(); old=self.old_reply()
        self.lc.configured(0); self.assertEqual(self.rx.poll(),1)
        self.ss.close()
        self.assertEqual(self.ss.status()['cancel_tx'],1)
        self.assertEqual(self.native.usb_completed,[])
        self.assertEqual(self.ss.tx_done(old),0)
        self.assertEqual(self.ss.resume(),1)
        self.lc.configured(3); self.assertEqual(self.ss.resume(),0)
        self.assertEqual(self.ss.status()['epoch'],2)
        self.assertEqual(self.ss.tx_done(old),0)
        self.send(self.inquiries); self.drain_new()
        self.assertEqual(b''.join(self.native.usb_completed),b''.join(self.replies))
        self.ss.check()

    def test_rx_queued_completion_cannot_publish_into_new_session(self):
        self.setup_session(); self.assertEqual(self.ss.arm_rx(),0)
        old=self.ss.rx_jobs[-1]; self.ss.close()
        self.assertEqual(self.ss.status()['cancel_rx'],1)
        self.assertEqual(self.ss.resume(),0); new=self.ss.rx_jobs[-1]
        before=bytes(self.u.mem_read(new.pointer,new.size)); status=self.rx.status()
        self.assertEqual(self.ss.rx_done(old,self.inquiries),0)
        self.assertEqual(self.u.mem_read(new.pointer,new.size),before)
        self.assertEqual(self.rx.status(),status)
        self.assertEqual(self.ss.rx_done(new,self.inquiries),1)
        self.rx.poll(); self.drain_new()
        self.assertEqual(b''.join(self.native.usb_completed),b''.join(self.replies))
        self.ss.check()

    def test_disable_is_requested_for_both_directions_before_fifo_flush(self):
        self.setup_session(); self.old_reply(); self.ss.arm_rx()
        self.assertEqual(self.ss.begin(),0); self.assertEqual(self.ss.step(),1)
        self.assertEqual(self.ss.disable_requested,{session.IN_CTL,session.OUT_CTL})
        for _ in range(3): self.assertEqual(self.ss.step(),1)
        self.assertEqual(self.ss.flushes,[])
        self.ss.ack_disable(session.IN_CTL); self.assertEqual(self.ss.step(),1)
        self.assertEqual(self.ss.flushes,[])
        self.ss.ack_disable(session.OUT_CTL); self.assertEqual(self.ss.step(),1)
        self.assertEqual(self.ss.flushes,[1]); self.assertEqual(self.ss.resume(),1)
        self.assertEqual(self.ss.step(),1)  # no flush-complete signal yet
        self.ss.finish_flush(); self.assertEqual(self.ss.step(),0); self.ss.check()

    def test_disable_ack_is_required_even_after_epena_clears(self):
        self.setup_session(); self.old_reply()
        self.ss.begin(); self.ss.step(); self.ss.ack_disable(session.IN_CTL,ack=False)
        self.assertEqual(self.ss.step(),1); self.assertEqual(self.ss.flushes,[])
        self.ss.poke(session.IN_INT,session.ACK); self.ss.step()
        self.ss.finish_flush(); self.assertEqual(self.ss.step(),0)

    def test_shared_rx_fifo_waits_without_global_flush_or_other_endpoint_writes(self):
        self.setup_session(); self.old_reply(); self.ss.arm_rx()
        self.ss.poke(0x940,0x81234567); self.ss.poke(0xB40,0x87654321)
        self.ss.begin(); self.ss.step()
        for ctl in tuple(self.ss.disable_requested): self.ss.ack_disable(ctl)
        self.ss.poke(session.GINTSTS,16)
        for _ in range(5): self.assertEqual(self.ss.step(),1)
        self.assertEqual(self.ss.flushes,[])
        self.ss.poke(session.GINTSTS,0); self.ss.step(); self.ss.finish_flush(); self.ss.step()
        self.assertEqual(self.ss.regs[0x940],0x81234567)
        self.assertEqual(self.ss.regs[0xB40],0x87654321)
        self.assertFalse(any(off in (0x940,0xB40) for off,val in self.ss.writes))
        self.assertEqual([val for off,val in self.ss.writes if off==session.GRSTCTL],[0x60])
        self.assertEqual(self.ss.regs[session.DAINTMSK],0x80008)
        self.assertEqual(self.ss.regs[session.DEACHMSK],0x80008)
        self.assertEqual(self.ss.regs[session.DIEPEMPMSK],8)
        self.ss.resume(); self.assertEqual(self.ss.regs[session.DAINTMSK],0xA000A)
        self.assertEqual(self.ss.regs[session.DEACHMSK],0xA000A)
        self.ss.check()

    def test_ahb_busy_and_flush_busy_do_not_reopen(self):
        self.setup_session(); self.old_reply(); self.ss.begin(); self.ss.step()
        self.ss.ack_disable(session.IN_CTL); self.ss.poke(session.GRSTCTL,0)
        self.assertEqual(self.ss.step(),1); self.assertEqual(self.ss.flushes,[])
        self.ss.poke(session.GRSTCTL,0x80000010)
        self.assertEqual(self.ss.step(),1); self.assertEqual(self.ss.flushes,[])
        self.ss.poke(session.GRSTCTL,0x80000000); self.ss.step()
        self.assertEqual(self.ss.step(),1); self.assertEqual(self.ss.resume(),1)

    def test_shared_payload_reader_or_rx_debt_prevents_cancellation(self):
        self.setup_session(); self.send(self.inquiries)
        self.assertEqual(self.q.status()['active'],1)
        payload=bytes(self.u.mem_read(0x20047800,428))
        self.assertEqual(self.ss.begin(),1); self.assertEqual(self.ss.status()['phase'],session.OPEN)
        self.assertEqual(self.u.mem_read(0x20047800,428),payload)
        self.q.poll(); self.q.poll(); self.ss.close(); self.ss.check()
        self.setUp(); self.setup_session(); self.fill_pending()
        before=self.rx.status(); self.assertEqual(self.ss.begin(),1)
        self.assertEqual(self.rx.status(),before); self.assertEqual(self.ss.writes,[])

    def test_held_notes_and_partial_parser_prevent_cancellation(self):
        for data in (bytes([0xF0,0x7E]),bytes([0x97,60])):
            self.setUp(); self.setup_session(); self.send(self.bytes_as_packets(data))
            self.assertEqual(self.ss.begin(),1); self.assertEqual(self.ss.writes,[])
        self.setUp(); self.setup_session(); self.attach_native_note_receiver()
        self.send(bytes([9,0x97,60,96])); self.assertEqual(self.ss.begin(),1)
        self.send(bytes([8,0x87,60,0])); self.rx.settle(); self.ss.close(); self.ss.check()

    def test_closed_usb_worker_and_admissions_cannot_create_new_transfer(self):
        self.setup_session(); old=self.old_reply(); self.ss.begin()
        entry=recovery.STATE_BASE+recovery.HEADER_SIZE
        self.assertEqual(self.call(self.recovery.labels['rp_send'],self.output.ports[0],0x00603C97),0)
        desc=self.sysex_descriptor(bytes.fromhex('f001f7'))
        self.assertEqual(self.call(self.recovery.labels['rp_sysex_send'],self.output.ports[0],desc),0)
        for _ in range(4): self.q.poll()
        self.assertEqual(self.ss.tx_jobs,[old])
        self.assertEqual(self.read(entry+recovery.COUNT)&0xFFFF,0)
        self.assertEqual(self.ss.arm_rx(),1)
        self.assertEqual(self.lc.reset(),1); self.assertEqual(self.lc.resume(),1)

    def test_untagged_and_duplicate_completion_cannot_release_current_transfer(self):
        self.setup_session(); job=self.old_reply()
        self.assertEqual(self.call(0x080268D0,self.native.usb_endpoint),0)
        self.assertEqual(self.u.mem_read(self.native.usb_endpoint+28,1),b'\x00')
        self.assertEqual(self.ss.tx_done(job),1)
        self.assertEqual(self.ss.tx_done(job),0)
        self.assertEqual(self.u.mem_read(self.native.usb_endpoint+28,1),b'\x01')
        self.ss.arm_rx(); rjob=self.ss.rx_jobs[-1]
        self.assertEqual(self.call(0x08026988,self.ingress.usb_port),0)
        self.assertEqual(self.ss.status()['rx_ticket'],rjob.ticket)
        self.ss.check()

    def test_same_epoch_old_rx_ticket_cannot_complete_a_rearmed_job(self):
        self.setup_session(); self.ss.arm_rx(); first=self.ss.rx_jobs[-1]
        self.assertEqual(self.ss.rx_done(first,bytes([15,0xF8,0,0])),1)
        second=self.ss.rx_jobs[-1]; self.assertGreater(second.ticket,first.ticket)
        before=self.rx.status()
        self.assertEqual(self.ss.rx_done(first,self.inquiries),0)
        self.assertEqual(self.rx.status(),before)
        self.assertEqual(self.ss.status()['rx_ticket'],second.ticket)
        self.assertEqual(self.ss.rx_done(second,bytes([15,0xFC,0,0])),1)
        self.rx.poll(); self.ss.check()

    def test_wrong_epoch_token_and_ticket_wrap_are_rejected(self):
        self.setup_session(); job=self.old_reply()
        for epoch,ticket in ((0,job.ticket),(job.epoch,job.ticket+1),(job.epoch+1,job.ticket)):
            self.assertEqual(self.ss.tx_done(Transfer(epoch,ticket,job.pointer,job.size,job.snapshot)),0)
        self.assertEqual(self.ss.tx_done(job),1)
        self.word(session.STATE_BASE+session.NEXT,0xFFFFFFFF)
        self.assertEqual(self.ss.arm_rx(),1); self.assertEqual(self.ss.status()['phase'],session.BROKEN)
        self.assertEqual(self.lc.status()['phase'],life.FROZEN)

    def test_epoch_wrap_binding_corruption_and_irq_calls_are_rejected(self):
        self.setup_session(); self.word(session.STATE_BASE+session.EPOCH,0xFFFFFFFF)
        self.word(life.STATE_BASE+life.EPOCH,0xFFFFFFFF)
        self.assertEqual(self.ss.begin(),1); self.assertEqual(self.ss.writes,[])
        self.word(session.STATE_BASE+session.EPOCH,1); self.word(life.STATE_BASE+life.EPOCH,1)
        self.word(self.ss.handle,0x40000000)
        self.assertEqual(self.ss.begin(),1); self.assertEqual(self.ss.writes,[])
        self.word(self.ss.handle,self.ss.base)
        self.u.reg_write(base.UC_ARM_REG_PRIMASK,1)
        self.assertEqual(self.ss.begin(),1)
        self.u.reg_write(base.UC_ARM_REG_PRIMASK,0)
        self.u.reg_write(base.UC_ARM_REG_IPSR,15)
        self.assertEqual(self.ss.begin(),1)
        self.u.reg_write(base.UC_ARM_REG_IPSR,0); self.ss.check()

    def test_lower_submit_failure_pins_session_without_payload_reuse(self):
        self.setup_session(); self.ss.tx_status=1
        self.send(self.inquiries); self.q.poll(); self.q.poll()
        self.assertEqual(self.ss.status()['phase'],session.BROKEN)
        self.assertEqual(self.lc.status()['phase'],life.FROZEN)
        self.assertEqual(self.ss.resume(),1)
        self.assertEqual(self.ss.status()['tx_active'],1)
        self.assertEqual(self.native.usb_completed,[])

    def test_resume_rechecks_endpoint_fifo_and_interrupt_barrier(self):
        self.setup_session(); self.old_reply(); self.ss.close()
        for reg,bits in ((session.IN_CTL,session.EPENA),(session.OUT_CTL,session.EPENA),
                         (session.IN_INT,1),(session.OUT_INT,1),
                         (session.GINTSTS,16),(session.GRSTCTL,0x20)):
            old=self.ss.regs[reg]; self.ss.poke(reg,old|bits)
            self.assertEqual(self.ss.resume(),1)
            self.assertEqual(self.ss.status()['phase'],session.SEALED)
            self.assertEqual(self.lc.status()['phase'],life.CLOSED)
            self.ss.poke(reg,old)
        self.assertEqual(self.ss.resume(),0); self.ss.check()

    def test_driver_buffer_or_endpoint_rebinding_refuses_cleanup(self):
        self.setup_session()
        for pointer in (self.output.drivers[0]+4,self.output.drivers[0]+8,
                        self.output.drivers[0]+12,self.native.usb_raw+4,
                        self.output.ports[0]+4,self.output.ports[0]+16,
                        self.ingress.usb_port+20):
            old=self.read(pointer); self.word(pointer,0x20008000)
            self.assertEqual(self.ss.begin(),1)
            self.assertEqual(self.ss.writes,[])
            self.word(pointer,old)
        self.ss.close(); self.ss.check()

    def test_payload_and_native_staging_remain_owned_until_barrier(self):
        self.setup_session(); job=self.old_reply()
        descriptor=self.read(self.output.drivers[0]+8)
        counters=bytes(self.u.mem_read(self.read(self.output.ports[0]+16),4))
        self.ss.begin(); self.ss.step()
        self.assertEqual(bytes(self.u.mem_read(job.pointer,job.size)),job.snapshot)
        self.assertEqual(self.u.mem_read(self.read(self.output.ports[0]+16),4),counters)
        self.assertEqual(self.ss.status()['tx_active'],1)
        self.assertEqual(self.read(self.output.drivers[0]+24),descriptor)
        self.ss.ack_disable(session.IN_CTL); self.ss.step()
        self.assertEqual(self.ss.status()['tx_active'],1)
        self.ss.finish_flush(); self.ss.step()
        self.assertEqual(self.ss.status()['tx_active'],0)
        self.assertEqual(self.read(self.output.ports[0]+8),0)
        self.assertEqual(self.read(self.output.ports[0]+12),0)
        self.ss.check()

    def test_din_native_driver_continues_while_usb_is_closed(self):
        self.setup_session(); self.old_reply(); self.ss.begin()
        payload=bytes.fromhex('f001020304f7'); desc=self.sysex_descriptor(payload)
        self.assertEqual(self.recovery.sysex_send(1,desc),1)
        for _ in range(3): self.recovery.poll(1)
        self.assertEqual(self.native.drain_uart(0),payload)
        self.assertEqual(self.recovery.sysex_pending(1),0)
        self.assertEqual(len(self.ss.tx_jobs),1)

    def test_nested_tx_completion_cannot_release_twice(self):
        self.setup_session(); job=self.old_reply()
        injected,results=self.install_nested_calls(0x080268E6,[
            (self.ss.labels['ss_tx_done'],(job.epoch,job.ticket))])
        self.ss.record_nested_trampoline()
        self.assertEqual(self.ss.tx_done(job),1)
        self.assertEqual(results(),[0]); self.assertEqual(len(injected),1)
        self.assertEqual(self.u.mem_read(self.native.usb_endpoint+28,1),b'\x01')

    def test_rx_completion_owns_publication_until_its_native_rearm(self):
        self.setup_session(); self.ss.arm_rx(); job=self.ss.rx_jobs[-1]
        injected,results=self.install_nested_calls(0x0802691E,[
            (0x080269AC,(self.ingress.usb_port,))])
        self.ss.record_nested_trampoline()
        self.assertEqual(self.ss.rx_done(job,self.inquiries),1)
        self.assertEqual(results(),[1]); self.assertEqual(len(injected),1)
        self.assertEqual(len(self.ss.rx_jobs),2)
        self.rx.poll(); self.drain_new(); self.ss.check()

    def test_rx_length_above_owned_transfer_capacity_is_rejected(self):
        self.setup_session(); self.ss.arm_rx(); job=self.ss.rx_jobs[-1]
        before=self.rx.status()
        self.assertEqual(self.call(self.ss.labels['ss_rx_done'],job.epoch,job.ticket,job.size+1),0)
        self.assertEqual(self.rx.status(),before)
        self.assertEqual(self.ss.status()['rx_active'],1)
        self.assertEqual(self.ss.rx_done(job,self.inquiries),1)

    def test_tag_does_not_prevent_dma_if_hardware_barrier_contract_is_violated(self):
        self.setup_session(); self.ss.arm_rx(); old=self.ss.rx_jobs[-1]
        self.ss.close(); self.ss.resume(); new=self.ss.rx_jobs[-1]
        self.assertEqual(old.pointer,new.pointer)
        # Deliberate negative: a broken cancellation barrier still permits an
        # old bus master to corrupt reused memory; rejecting its callback alone
        # cannot undo that write. The model cannot prove silicon cancellation.
        self.u.mem_write(old.pointer,b'BAD!')
        self.assertEqual(self.ss.rx_done(old,self.inquiries),0)
        self.assertEqual(bytes(self.u.mem_read(new.pointer,4)),b'BAD!')
        self.assertEqual(self.ss.rx_done(new,self.inquiries),1)
        self.rx.poll(); self.drain_new(); self.ss.check()

    def test_relocated_tx_completion_preserves_timer_and_foreign_native_path(self):
        self.setup_session(); timer=0x20009C00
        self.word(self.native.usb_endpoint+32,timer)
        job=self.old_reply(); self.assertEqual(self.u.mem_read(timer+8,1),b'\x01')
        self.assertEqual(self.ss.tx_done(job),1)
        self.assertEqual(self.u.mem_read(timer+8,1),b'\x00')
        self.assertEqual(self.read(timer+4),self.read(timer))
        foreign=0x20009D00
        self.u.mem_write(foreign+29,b'\x01')  # native counter saturates at capacity
        self.call(0x080268D0,foreign)
        self.assertEqual(self.u.mem_read(foreign+28,1),b'\x01')
        self.ss.check()

    def test_quarantined_off_ownership_is_preserved_by_refusing_close(self):
        self.setup_session(); entry=recovery.STATE_BASE+recovery.HEADER_SIZE
        for off,value in ((recovery.FLAGS,1),(recovery.COUNT,3)):
            self.u.mem_write(entry+off,bytes([value]))
            before=bytes(self.u.mem_read(entry,recovery.ENTRY_SIZE))
            self.assertEqual(self.ss.begin(),1)
            self.assertEqual(self.u.mem_read(entry,recovery.ENTRY_SIZE),before)
            self.assertEqual(self.ss.writes,[])
            self.u.mem_write(entry+off,b'\x00')

    def test_previous_codegen_is_unchanged(self):
        self.assertEqual(hashlib.sha256(life.arm_code()[0]).hexdigest(),
                         '13241d42aebe8d4a9b586932e92239fc67b0cf8df1a2f83d494663acdb121a0b')


if __name__=='__main__': unittest.main()
