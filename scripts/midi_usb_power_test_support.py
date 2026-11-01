"""Synthetic USB suspend/wakeup with native state callbacks and ungate."""
from unicorn import UC_HOOK_MEM_WRITE,UC_HOOK_MEM_READ
from unicorn.arm_const import UC_ARM_REG_PRIMASK
from inspect_ui import load_image
from thumb_asm import b_w
import midi_usb_power_prototype as power
import midi_usb_factory_prototype as factory
import midi_usb_control_prototype as control
import midi_usb_irq_prototype as irq
import midi_usb_session_prototype as session
import midi_usb_msc_prototype as msc


class UsbPowerFixture:
    def __init__(self,h):
        self.h=h;self.code,self.labels=power.arm_code();self.overlays=[];self.clock_stops=[];self.clock_starts=[]
        self.strict_clock=True
        original,old_labels=control.irq_variant();variant,new_labels=power.irq_variant()
        assert old_labels==new_labels and len(original)==len(variant)
        assert h.u.mem_read(irq.CODE_BASE,len(original))==original
        h.u.mem_write(irq.CODE_BASE,variant);h.ib.code=variant
        assert factory.CODE_BASE+len(h.fx.code)<=power.CODE_BASE
        # This is an emulator overlay, never a packaged firmware image.
        assert not any(h.u.mem_read(power.CODE_BASE,len(self.code)))
        h.u.mem_write(power.CODE_BASE,self.code)
        h.u.mem_write(power.STATE_BASE-4,b'PBEG');h.u.mem_write(power.STATE_BASE+power.STATE_SIZE,b'PEND')
        h.u.mem_write(power.STATE_BASE,bytes(power.STATE_SIZE))
        for off,val in ((0,power.MAGIC),(power.HANDLE,h.ib.handle),(power.CONTROLLER,h.ib.ctrl)):
            h.word(power.STATE_BASE+off,val)
        stock=load_image()
        for address,label in ((irq.NATIVE_IRQ,'pw_irq'),(0x0802C7E6,'pw_suspend'),(0x0802C802,'pw_wakeup'),
                              (h.cc.labels['cc_service'],'pw_service')):
            previous=next((o for o in h.recovery.overlays if o['address']==address),None)
            expected=previous['replacement'] if previous else power.GATES[address]
            if not previous:assert stock[address-0x08010000:address-0x08010000+len(expected)]==expected
            assert h.u.mem_read(address,len(expected))==expected
            replacement=b_w(address,self.labels[label])+b'\x00\xbf'*(len(expected)//2-2)
            assert 0x08010200<=address<address+len(replacement)<=0x08080000
            for other in h.recovery.overlays:
                if other is not previous:assert address+len(replacement)<=other['address'] or other['address']+len(other['replacement'])<=address
            if previous:previous['replacement']=replacement
            else:h.recovery.overlays.append(dict(address=address,original=expected,replacement=replacement))
            h.u.mem_write(address,replacement);self.overlays.append(dict(address=address,expected=expected.hex(),replacement=replacement.hex()))
        h.ss.poke(0x18,power.POWER_GINT)
        h.word(h.ib.handle+32,0)  # Native low-power-system flag; deep stop is unsupported.
        def clock(u,access,address,size,value,data):
            if value&1:
                if self.strict_clock:
                    h.assertEqual(h.ss.status()['phase'],session.SEALED)
                    h.assertEqual(h.mc.status()['phase'],msc.SEALED)
                    h.assertEqual(h.sd.status()['tx_active'],0);h.assertEqual(h.sd.status()['io_busy'],0)
                    h.assertEqual(h.u.reg_read(UC_ARM_REG_PRIMASK),1)
                self.clock_stops.append(value)
            else:self.clock_starts.append(value)
        h.u.hook_add(UC_HOOK_MEM_WRITE,clock,begin=h.ib.base+0xE00,end=h.ib.base+0xE03)
        self.sleeping_reads=[]
        def sleeping_read(u,access,address,size,value,data):
            if self.strict_clock and h.ss.regs.get(0xE00,0)&1:
                off=address-h.ib.base;self.sleeping_reads.append(off)
                h.assertIn(off,(0x14,0x18,0xE00),'Normal USB MMIO read while clock-stopped')
        h.u.hook_add(UC_HOOK_MEM_READ,sleeping_read,begin=h.ib.base,end=h.ib.base+0x2FFF)
        h.u.ctl_remove_cache(0x08010000,0x08080000);h.ss.flash=bytes(h.u.mem_read(0x08010000,0x70000))

    def status(self):
        return {n:self.h.read(power.STATE_BASE+o) for n,o in (('desired',power.DESIRED),('pending',power.PENDING),
            ('generation',power.GENERATION),('asleep',power.ASLEEP),('busy',power.BUSY),('irq_depth',power.IRQ_DEPTH),
            ('errors',power.ERRORS),('suspends',power.SUSPENDS),('wakes',power.WAKES),('stage',power.RESUME_STAGE))}
    def suspend(self):
        self.h.ss.poke(0x808,1);self.h.ib.external|=power.SUSPEND;return self.h.ib.run()
    def wake(self):
        self.h.ss.poke(0x808,0);self.h.ib.external|=power.WAKE;return self.h.ib.run()
    def service(self):return self.h.mc.service()
    def pump(self):return self.h.sd.pump()
    def check(self):
        h=self.h;h.assertEqual(h.u.mem_read(power.STATE_BASE-4,4),b'PBEG')
        h.assertEqual(h.u.mem_read(power.STATE_BASE+power.STATE_SIZE,4),b'PEND')
        for n in ('busy','irq_depth','errors'):h.assertEqual(self.status()[n],0)
        h.fx.check()
