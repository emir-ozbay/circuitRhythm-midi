"""Native MIDI/MSC parents, list walker and descriptors over synthetic MMIO."""
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0
import midi_usb_composite_prototype as composite
import midi_usb_control_prototype as control
from thumb_asm import b_w


class UsbCompositeFixture:
    def __init__(self,h,guard=True):
        self.h=h; self.code,self.labels=composite.arm_code(); self.events=[]
        self.msc=0x2000A180; self.storage=0x2000A300
        # Actual stock callback tables and the actual MSC ROM endpoint arrays.
        h.word(h.ib.wrapper,0x080676F4)
        h.word(self.msc,0x08067730); h.word(self.msc+4,0x08069784); h.word(self.msc+8,0x0806978C)
        for off,val in ((0,2),(4,h.ib.ctrl),(12,self.msc),(16,0)):
            h.word(h.ib.root+off,val)
        # Execute26828 with count0/mps64 as native6668C does for MSC. Heap
        # allocation is the existing model, and is not production RAM evidence.
        for address,endpoint in ((0x20006100,0x82),(0x20006124,2)):
            h.word(0x20040000,0); h.word(0x20040004,64)
            h.call(0x08026828,address,h.ib.ctrl,endpoint,2)
        # Only the storage Init(LUN0) vtable boundary returns a pinned native0.
        # BOT state reset and31-byte CBW arm execute the real parent bodies.
        h.word(0x200038AC,self.storage); h.word(self.storage,0x080427D3)
        h.ib.native_flush_indices={1,2}
        h.u.mem_write(composite.STATE_BASE-4,b'CBEG')
        h.u.mem_write(composite.STATE_BASE+composite.STATE_SIZE,b'CEND')
        h.u.mem_write(composite.STATE_BASE,bytes(composite.STATE_SIZE))
        for off,val in ((0,composite.MAGIC),(composite.ROOT,h.ib.root),(composite.MIDI,h.ib.wrapper),
                        (composite.MSC,self.msc),(composite.CONTROLLER,h.ib.ctrl),(composite.ROUTER,h.output.router)):
            h.word(composite.STATE_BASE+off,val)
        self.overlays=[]
        if guard:
            h.u.mem_write(composite.CODE_BASE,self.code)
            targets={0x08040B5A:'xc_init_list',0x080525B2:'xc_init_class',
                     0x080297C0:'xc_clear_router',0x0802C928:'xc_flush'}
            for address,original in composite.GATES.items():
                previous=next((o for o in h.recovery.overlays if o['address']==address),None)
                expected=previous['replacement'] if previous else original
                assert h.u.mem_read(address,len(expected))==expected and len(expected)==len(original)
                patch=b_w(address,self.labels[targets[address]])+b'\x00\xBF'*(len(original)//2-2)
                assert 0x08010200<=address<address+len(patch)<=0x08080000
                for other in h.recovery.overlays:
                    if other is not previous:
                        assert address+len(patch)<=other['address'] or other['address']+len(other['replacement'])<=address
                if previous: previous['replacement']=patch
                else: h.recovery.overlays.append(dict(address=address,original=original,replacement=patch))
                h.u.mem_write(address,patch)
                self.overlays.append(dict(address=address,expected=bytes(expected),replacement=patch))
            address=h.cc.labels['cc_native_init']; expected=control.GATES[0x080525B2]
            assert h.u.mem_read(address,4)==expected
            patch=b_w(address,self.labels['xc_deferred_list']); h.u.mem_write(address,patch)
            self.overlays.append(dict(address=address,expected=expected,replacement=patch))
        for name,address in (('midi_parent',0x08068A2C),('router_clear',0x080297C0),
                             ('rx_rearm_attempt',0x08029AB0),('msc_parent',0x080661DC),
                             ('msc_deinit',0x080661EE),('bot_reset',0x0802F00C),
                             ('storage_init_boundary',0x080427D2)):
            def observe(u,pc,size,data,name=name): self.events.append((name,u.reg_read(UC_ARM_REG_R0)))
            h.u.hook_add(UC_HOOK_CODE,observe,begin=address,end=address)
        h.u.ctl_remove_cache(0x08010000,0x08080000)
        h.ss.flash=bytes(h.u.mem_read(0x08010000,0x70000))

    def status(self):
        return {name:self.h.read(composite.STATE_BASE+off) for name,off in (
            ('pending',composite.PENDING),('running',composite.RUNNING),('errors',composite.ERRORS),
            ('skipped',composite.SKIPPED),('starts',composite.STARTS),('generation',composite.GENERATION))}

    def descriptor(self):
        #40B24's PC-relative literal is200067E0:40A78 updates this same header.
        h=self.h; address=0x200067E0
        h.call(0x08040A78,h.ib.root,address)
        n=int.from_bytes(h.u.mem_read(h.ib.root+0x1C,2),'little')
        return bytes(h.u.mem_read(address,n))

    def check(self):
        h=self.h
        h.assertEqual(h.u.mem_read(composite.STATE_BASE-4,4),b'CBEG')
        h.assertEqual(h.u.mem_read(composite.STATE_BASE+composite.STATE_SIZE,4),b'CEND')
        h.assertEqual(self.status()['running'],0); h.cc.check()
