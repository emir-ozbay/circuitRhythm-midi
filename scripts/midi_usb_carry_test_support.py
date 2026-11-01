"""Install asserted generated-code carry detours; no device or host disk I/O."""
from thumb_asm import b_w,bl
import midi_usb_carry_prototype as carry
import midi_usb_task_prototype as task


class UsbCarryFixture:
    def __init__(self,h,staging=False):
        self.h=h;self.code,self.labels=carry.arm_code(staging=staging);self.overlays=[]
        assert not any(h.u.mem_read(carry.CODE_BASE,len(self.code)))
        h.u.mem_write(carry.CODE_BASE,self.code)
        h.u.mem_write(carry.STATE_BASE-4,b'YBEG');h.u.mem_write(carry.STATE_BASE+carry.STATE_SIZE,b'YEND')
        h.u.mem_write(carry.STATE_BASE,bytes(carry.STATE_SIZE));h.word(carry.STATE_BASE,carry.MAGIC)
        changes={p:(original,b_w(p,self.labels[label])+b'\x00\xbf'*(len(original)//2-2)) for p,(original,label) in carry.sites(staging=staging).items()}
        p=task.MAIN_CALL;changes[p]=(bl(p,h.ut.labels['ut_main']),bl(p,self.labels['cy_task']))
        for p,(original,replacement) in changes.items():
            assert len(original)==len(replacement) and h.u.mem_read(p,len(original))==original
            assert 0x08010200<=p<p+len(original)<=0x08080000
            old=next((o for o in h.recovery.overlays if o['address']==p),None)
            for other in h.recovery.overlays:
                if other is not old:assert p+len(original)<=other['address'] or other['address']+len(other['replacement'])<=p
            if old:old['replacement']=replacement
            else:h.recovery.overlays.append(dict(address=p,original=original,replacement=replacement))
            h.u.mem_write(p,replacement);self.overlays.append(dict(address=hex(p),expected=original.hex(),replacement=replacement.hex()))
        h.u.ctl_remove_cache(0x08000000,0x08080000);h.ss.flash=bytes(h.u.mem_read(0x08010000,0x70000))
        # The owned slot can target all three ports. Model external UART TX
        # drain as well as USB events, so a long payload is not pinned forever
        # by two undrained64-byte DIN FIFOs. Native formatting/ring code runs;
        # this is not a physical UART IRQ/timing claim.
        self.din_bytes=[bytearray(),bytearray()];old_bus=h.ut.bus
        def bus():
            old_bus()
            if h.ut.hw_tx:
                for n in range(2):self.din_bytes[n].extend(h.native.drain_uart(n))
        h.ut.bus=bus
    def status(self):
        return {n:self.h.read(carry.STATE_BASE+o) for n,o in (('active',carry.ACTIVE),('seals',carry.SEALS),
            ('resumes',carry.RESUMES),('resume_pending',carry.RESUME_PENDING))}
    def check(self):
        h=self.h;h.assertEqual(h.u.mem_read(carry.STATE_BASE-4,4),b'YBEG')
        h.assertEqual(h.u.mem_read(carry.STATE_BASE+carry.STATE_SIZE,4),b'YEND');h.ut.check()
