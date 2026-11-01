"""Synthetic endpoint2 cancellation/ACK contract; never opens a device."""
import midi_usb_msc_prototype as msc
import midi_usb_control_prototype as control
import midi_usb_session_prototype as session
from thumb_asm import b_w
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0


class UsbMscFixture:
    def __init__(self,h):
        self.h=h; self.code,self.labels=msc.arm_code(); self.events=[]; self.overlays=[]
        h.u.mem_write(msc.CODE_BASE,self.code)
        h.u.mem_write(msc.STATE_BASE-4,b'MBEG'); h.u.mem_write(msc.STATE_BASE+msc.STATE_SIZE,b'MEND')
        h.u.mem_write(msc.STATE_BASE,bytes(msc.STATE_SIZE))
        for off,val in ((0,msc.MAGIC),(msc.HANDLE,h.ib.handle),(msc.CONTROLLER,h.ib.ctrl),(msc.ROOT,h.ib.root),
                        (msc.RX_PORT,0x20006124),(msc.TX_PORT,0x20006100),(msc.PHASE,msc.OPEN),(msc.EPOCH,1)):
            h.word(msc.STATE_BASE+off,val)
        # Native27624 reads these actual global endpoint slots and media-lock
        # presence. No storage command or disk callback is fabricated here.
        h.word(0x20006E68,0x20006100); h.word(0x20006E6C,0x20006124)
        h.u.mem_write(0x20003F8C,b'\x01\x01\x00')
        targets={0x08040B5A:'mc_init_list',0x08040B7E:'mc_deinit_list',
                 0x0804293E:'mc_irq',0x08026988:'mc_rx_callback',0x0802C9D4:'mc_rx_lower',
                 0x0802EFF8:'mc_bot_reset',0x08027624:'mc_poll',0x0802F014:'mc_bot_0802f014',0x0802F04A:'mc_bot_0802f04a',
                 0x080531CC:'mc_fifo_read'}
        for address,original in msc.GATES.items():
            previous=next((o for o in h.recovery.overlays if o['address']==address),None)
            expected=previous['replacement'] if previous else original
            self.patch(address,expected,self.labels[targets[address]],original,previous)
        for address,(expected,label) in msc.generated_gates().items():
            self.patch(address,expected,self.labels[label],expected,None)
        h.ib.barrier_disable_controls={msc.IN_CTL,msc.OUT_CTL}
        h.ib.barrier_flush_owner=lambda:self.status()['busy']==1 and self.status()['phase']==msc.WAIT_DISABLE
        for name,address in (('native_bot_reset',0x0802EFFC),('msc_poll',0x0802762A),
                             ('scsi_dispatch',0x080458D0),('msc_class_deinit',0x080661EE)):
            def see(u,p,n,d,name=name): self.events.append((name,u.reg_read(UC_ARM_REG_R0)))
            h.u.hook_add(UC_HOOK_CODE,see,begin=address,end=address)
        h.u.ctl_remove_cache(0x08010000,0x08080000)
        h.ss.flash=bytes(h.u.mem_read(0x08010000,0x70000))

    def patch(self,address,expected,target,original,previous):
        h=self.h
        assert h.u.mem_read(address,len(expected))==expected and len(expected)==len(original)
        patch=b_w(address,target)+b'\x00\xBF'*(len(original)//2-2)
        assert 0x08010200<=address<address+len(patch)<=0x08080000
        for other in h.recovery.overlays:
            if other is not previous:
                assert address+len(patch)<=other['address'] or other['address']+len(other['replacement'])<=address
        if previous: previous['replacement']=patch
        else: h.recovery.overlays.append(dict(address=address,original=original,replacement=patch))
        h.u.mem_write(address,patch)
        self.overlays.append(dict(address=address,expected=bytes(expected),replacement=patch))

    def status(self):
        return {name:self.h.read(msc.STATE_BASE+off) for name,off in (
            ('phase',msc.PHASE),('op',msc.OP),('busy',msc.BUSY),('task_busy',msc.TASK_BUSY),('arm_busy',msc.ARM_BUSY),
            ('rx_active',msc.RX_ACTIVE),('epoch',msc.EPOCH),('ticket',msc.RX_TICKET),('cancel_rx',msc.CANCEL_RX),
            ('errors',msc.ERRORS),('irq_active',msc.IRQ_ACTIVE),('irq_done',msc.IRQ_DONE),('rx_seen',msc.RX_SEEN),
            ('submits',msc.SUBMITS),('teardowns',msc.TEARDOWNS),('blocked',msc.BLOCKED),('reset_done',msc.RESET_DONE))}

    def service(self): return self.h.cc.service()

    def ack(self,ctl=msc.OUT_CTL,ack=True):
        h=self.h; h.ss.poke(ctl,h.ss.regs[ctl]&~(session.EPENA|session.EPDIS))
        reg=msc.OUT_INT if ctl==msc.OUT_CTL else msc.IN_INT
        h.ib.flags[reg]|=2 if ack else 0; h.ss.poke(reg,h.ib.flags[reg])

    def finish_flush(self):
        self.h.ss.poke(session.GRSTCTL,self.h.ss.regs[session.GRSTCTL]&~0x30|0x80000000)

    def pump(self,rounds=32):
        h=self.h
        for i in range(rounds):
            result=self.service()
            if result==0: return i+1
            if self.status()['phase']==msc.WAIT_DISABLE:
                for ctl in (msc.IN_CTL,msc.OUT_CTL):
                    if ctl in h.ss.disable_requested: self.ack(ctl)
            if self.status()['phase']==msc.WAIT_FLUSH: self.finish_flush()
            if h.ss.status()['phase']==session.WAIT_DISABLE:
                for ctl in (session.IN_CTL,session.OUT_CTL):
                    if ctl in h.ss.disable_requested: h.ss.ack_disable(ctl)
            if h.ss.status()['phase']==session.WAIT_FLUSH: h.ss.finish_flush()
        raise AssertionError(f'MSC control did not settle: {self.status()} / {h.cc.status()} / {h.ss.status()}')

    def configure(self):
        h=self.h; h.lc.configured(2); h.assertEqual(h.cc.configure(1),0); self.pump()
        h.assertEqual(self.status()['rx_active'],1); h.assertEqual(self.status()['phase'],msc.OPEN)

    def reset_request(self): return self.h.cc.setup(bytes([0x21,0xFF,0,0,2,0,0,0]))
    def poll(self): return self.h.call(0x08027624)

    def check(self):
        h=self.h
        h.assertEqual(h.u.mem_read(msc.STATE_BASE-4,4),b'MBEG')
        h.assertEqual(h.u.mem_read(msc.STATE_BASE+msc.STATE_SIZE,4),b'MEND')
        for key in ('busy','task_busy','arm_busy','irq_active'): h.assertEqual(self.status()[key],0)
        h.xc.check()
