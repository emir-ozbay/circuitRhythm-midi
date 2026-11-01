"""Synthetic USB control events through native EP0/setup/class code; no devices."""
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1
import midi_usb_control_prototype as control
import midi_usb_irq_prototype as irq
import midi_usb_session_prototype as session
from thumb_asm import b_w


class UsbControlFixture:
    def __init__(self,h):
        self.h=h; self.ib=h.ib; self.code,self.labels=control.arm_code()
        h.u.mem_write(control.CODE_BASE,self.code)
        h.u.mem_write(control.STATE_BASE-4,b'XBEG'); h.u.mem_write(control.STATE_BASE+control.STATE_SIZE,b'XEND')
        h.u.mem_write(control.STATE_BASE,bytes(control.STATE_SIZE))
        for off,val in ((0,control.MAGIC),(control.HANDLE,h.ib.handle),
                        (control.CONTROLLER,h.ib.ctrl),(control.CLASS,h.ib.wrapper)):
            h.word(control.STATE_BASE+off,val)
        original,old_labels=irq.arm_code(); variant,new_labels=control.irq_variant()
        assert old_labels==new_labels and len(original)==len(variant)
        assert h.u.mem_read(irq.CODE_BASE,len(original))==original
        h.u.mem_write(irq.CODE_BASE,variant); h.ib.code=variant
        self.overlays=[]
        targets={irq.NATIVE_IRQ:'cc_irq',0x080525B2:'cc_init',0x0805261C:'cc_deinit',0x080268D0:'cc_tx_callback',
                 0x0802C928:'cc_flush',0x080268EC:'cc_rx_poll',0x0802C9D4:'cc_rx_submit'}
        targets[0x080269AC]='cc_rx_rearm'
        for address,original in control.GATES.items():
            previous=next((o for o in h.recovery.overlays if o['address']==address),None)
            expected=previous['replacement'] if previous else original
            assert h.u.mem_read(address,len(expected))==expected and len(expected)==len(original)
            patch=b_w(address,self.labels[targets[address]])+b'\x00\xBF'*(len(original)//2-2)
            assert 0x08010200<=address<address+len(original)<=0x08080000
            for other in h.recovery.overlays:
                if other is not previous:
                    assert address+len(original)<=other['address'] or other['address']+len(other['replacement'])<=address
            if previous: previous['replacement']=patch
            else: h.recovery.overlays.append(dict(address=address,original=original,replacement=patch))
            self.overlays.append(dict(address=address,expected=bytes(expected),replacement=patch))
            h.u.mem_write(address,patch)
        # Parent class notification is a boundary: execute a pinned native no-op
        # instead of fabricating a USB/MIDI driver callback or a device response.
        assert h.u.mem_read(0x080427D2,4)==bytes.fromhex('00207047')
        h.word(h.ib.vtable,0x080427D3)
        for endpoint in (h.native.usb_endpoint,h.ingress.usb_port):
            h.u.mem_write(endpoint+6,b'\x02')  # bulk endpoint type consumed by525B2
        h.ss.poke(0x18,control.CONTROL_GINT)
        h.ss.poke(0x81C,h.ss.regs[0x81C]|0x10001)
        h.word(h.ib.ctrl+0x24,64)
        for off in (0x3C,0x1FC): h.word(h.ib.handle+off+8,64)
        self.constructors=[]; self.bootstrap=[]
        h.ib.native_flush_owner=lambda:self.status()['init_busy']==1
        def ctor(u,pc,size,data):
            if u.reg_read(UC_ARM_REG_R0)!=h.ib.wrapper or u.reg_read(UC_ARM_REG_R1)!=h.ib.ctrl: return
            h.assertEqual(self.status()['init_busy'],1)
            h.assertEqual(h.ss.status()['phase'],session.SEALED)
            h.assertEqual(h.ss.status()['tx_active'],0); h.assertEqual(h.ss.status()['rx_active'],0)
            self.constructors.append(self.status()['requests'])
        h.u.hook_add(UC_HOOK_CODE,ctor,begin=self.labels['cc_native_init'],end=self.labels['cc_native_init'])
        h.u.hook_add(UC_HOOK_CODE,lambda u,a,n,d:self.bootstrap.append(h.ss.status()['phase']),
                     begin=0x080525FE,end=0x080525FE)
        h.u.ctl_remove_cache(0x08010000,0x08080000)
        h.ss.flash=bytes(h.u.mem_read(0x08010000,0x70000))

    def status(self):
        return {name:self.h.read(control.STATE_BASE+off) for name,off in (
            ('flags',control.FLAGS),('busy',control.BUSY),('init_busy',control.INIT_BUSY),
            ('requests',control.REQUESTS),('restarts',control.RESTARTS),('errors',control.ERRORS),
            ('reset',control.RESET_SEEN),('deinit',control.DEINIT_SEEN),('init',control.INIT_SEEN),
            ('init_done',control.INIT_DONE),('irq_depth',control.IRQ_DEPTH),('rx_paused',control.RX_PAUSED))}

    def service(self): return self.h.call(self.labels['cc_service'])

    def pump(self,rounds=16):
        for n in range(rounds):
            result=self.service()
            if not result: return n+1
            phase=self.h.ss.status()['phase']
            if phase==session.WAIT_DISABLE:
                for ctl in tuple(self.h.ss.disable_requested): self.h.ss.ack_disable(ctl)
            if phase==session.WAIT_FLUSH: self.h.ss.finish_flush()
        raise AssertionError('Control service did not reach a settled state')

    def reset(self):
        self.ib.external|=1<<12
        return self.ib.run()

    def enumerate(self):
        self.ib.external|=1<<13
        return self.ib.run()

    def setup(self,packet):
        assert len(packet)==8
        self.ib.events.append((6<<17)|(8<<4))
        self.ib.fifo_words.extend(int.from_bytes(packet[n:n+4],'little') for n in (0,4))
        self.h.assertEqual(self.ib.run(),0)
        self.ib.flags[0xB08]|=8
        return self.ib.run()

    def configure(self,value): return self.setup(bytes([0,9,value,0,0,0,0,0]))
    def address(self,value=7): return self.setup(bytes([0,5,value,0,0,0,0,0]))

    def check(self):
        h=self.h
        h.assertEqual(h.u.mem_read(control.STATE_BASE-4,4),b'XBEG')
        h.assertEqual(h.u.mem_read(control.STATE_BASE+control.STATE_SIZE,4),b'XEND')
        h.assertEqual(self.status()['busy'],0); h.assertEqual(self.status()['init_busy'],0)
        h.assertEqual(self.status()['irq_depth'],0); self.ib.check()
