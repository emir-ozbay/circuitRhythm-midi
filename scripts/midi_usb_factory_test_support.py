"""Stock USB factory/root/descriptor/stop/start; synthetic HAL/tick boundaries."""
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0
from inspect_ui import load_image
from thumb_asm import b_w
import midi_usb_factory_prototype as factory
import midi_usb_storage_prototype as storage
import midi_usb_msc_prototype as msc
import midi_usb_composite_prototype as composite
import midi_usb_control_prototype as control
import midi_usb_irq_prototype as irq


class UsbFactoryFixture:
    def __init__(self,h):
        self.h=h;self.code,self.labels=factory.arm_code();self.events=[];self.overlays=[]
        # Rebind the synthetic fixture to the actual native factory literals.
        old_root,old_midi,old_msc,old_handle=h.ib.root,h.ib.wrapper,h.xc.msc,h.ib.handle
        h.u.mem_write(0x200000D0,bytes(h.u.mem_read(old_root,32)))
        h.u.mem_write(0x200000F0,bytes(h.u.mem_read(old_midi,12)))
        h.u.mem_write(0x200000FC,bytes(h.u.mem_read(old_msc,12)))
        h.u.mem_write(0x200054B4,bytes(h.u.mem_read(old_handle,0x404)))
        h.ib.root=0x200000D0;h.ib.wrapper=0x200000F0;h.xc.msc=0x200000FC
        h.ib.handle=h.ss.handle=0x200054B4
        h.word(h.ib.root+8,h.ib.wrapper);h.word(h.ib.root+12,h.xc.msc)
        h.word(0x20006F20,h.ib.root);h.word(h.ib.ctrl+0x298,h.ib.handle)
        h.word(h.ib.ctrl+0x29C,1);h.word(h.ib.ctrl+0x2A0,0x0806776C)
        for state,off,value in ((irq.STATE_BASE,irq.HANDLE,h.ib.handle),(irq.STATE_BASE,irq.CLASS,h.ib.wrapper),
                (control.STATE_BASE,control.HANDLE,h.ib.handle),(control.STATE_BASE,control.CLASS,h.ib.wrapper),
                (composite.STATE_BASE,composite.ROOT,h.ib.root),(composite.STATE_BASE,composite.MIDI,h.ib.wrapper),
                (composite.STATE_BASE,composite.MSC,h.xc.msc),(msc.STATE_BASE,msc.ROOT,h.ib.root),(msc.STATE_BASE,msc.HANDLE,h.ib.handle)):
            h.word(state+off,value)
        (mc_code,mc),(sd_code,sd)=factory.variants()
        h.u.mem_write(msc.CODE_BASE,mc_code);h.mc.code=mc_code;h.mc.labels=mc
        h.u.mem_write(storage.CODE_BASE,sd_code);h.sd.code=sd_code;h.sd.labels=sd
        targets={0x08040B5A:'mc_init_list',0x08040B7E:'mc_deinit_list',0x0804293E:'mc_irq',0x08026988:'mc_rx_callback',
            0x0802C9D4:'mc_rx_lower',0x0802EFF8:'mc_bot_reset',0x08027624:'mc_poll',0x0802F014:'mc_bot_0802f014',
            0x0802F04A:'mc_bot_0802f04a',0x080531CC:'mc_fifo_read'}
        for address,label in targets.items():self.repatch(address,mc[label])
        for address,(_,label) in msc.generated_gates().items():self.repatch(address,mc[label])
        targets={0x080458D0:'sd_scsi',0x08065128:'sd_read',0x0802C9B8:'sd_tx_submit',0x080268D0:'sd_tx_callback',
                 0x0804293E:'sd_irq',0x0802C328:'sd_worker_result'}
        for address,label in targets.items():self.repatch(address,sd[label])
        # The storage poll gate moved with the MSC variant; its old cave branch
        # is overwritten by the new variant, then installed at the new entry.
        address=mc['mc_poll'];expected=mc_code[address-msc.CODE_BASE:address-msc.CODE_BASE+6]
        old=next((o for o in h.recovery.overlays if o['address']==address),None)
        if old:old['replacement']=expected
        self.patch(address,expected,sd['sd_poll'],old)
        h.u.mem_write(factory.CODE_BASE,self.code)
        h.u.mem_write(factory.STATE_BASE-4,b'FBEG');h.u.mem_write(factory.STATE_BASE+factory.STATE_SIZE,b'FEND')
        h.u.mem_write(factory.STATE_BASE,bytes(factory.STATE_SIZE))
        for off,value in ((0,factory.MAGIC),(factory.ROOT,h.ib.root),(factory.CONTROLLER,h.ib.ctrl),(factory.APPLIED,0x101)):
            h.word(factory.STATE_BASE+off,value)
        for address,label in ((0x080432A8,'fx_request'),(0x08040B7E,'fx_deinit'),(h.cc.labels['cc_service'],'fx_service')):
            old=next((o for o in h.recovery.overlays if o['address']==address),None)
            expected=old['replacement'] if old else factory.GATES[address]
            self.patch(address,expected,self.labels[label],old)
        # HAL PLL/PHY initialization is the boundary.2C82A's real prefix and
        #43196/43158 FIFO configuration still run, with native handle200054B4.
        stock=load_image()
        for address in (0x080427FC,):
            original=stock[address-0x08010000:address-0x08010000+4]
            assert h.u.mem_read(address,4)==original
            replacement=b_w(address,0x080650D0)
            h.u.mem_write(address,replacement);self.overlays.append(dict(address=address,expected=original,replacement=replacement,boundary=True))
        # Native3ms stop/start and200ms factory delays execute against an
        # advancing synthetic tick. No wall-clock or real timing is asserted.
        from capstone import Cs,CS_ARCH_ARM,CS_MODE_THUMB,CS_MODE_MCLASS
        md=Cs(CS_ARCH_ARM,CS_MODE_THUMB|CS_MODE_MCLASS);md.detail=True
        ins=next(md.disasm(stock[0x08024068-0x08010000:0x08024068-0x08010000+2],0x08024068))
        literal=((ins.address+4)&~3)+ins.operands[1].mem.disp
        tick=int.from_bytes(stock[literal-0x08010000:literal-0x08010000+4],'little')+4
        self.tick_reads=0
        def advance(u,p,n,d):
            self.tick_reads+=1;h.word(tick,h.read(tick)+1)
        h.u.hook_add(UC_HOOK_CODE,advance,begin=0x08024068,end=0x08024068)
        h.u.mem_map(0xE000E000,0x1000)  # NVIC memory effects only; no IRQ scheduling
        for name,address in (('native_factory',0x080432AC),('list_clear',0x08040A40),('stop',0x080428D4),
                ('start',0x0804291A),('hal_init_boundary',0x080427FC),('midi_deinit',0x0805261C),('descriptor',0x08040A78)):
            def see(u,p,n,d,name=name):self.events.append((name,u.reg_read(UC_ARM_REG_R0)))
            h.u.hook_add(UC_HOOK_CODE,see,begin=address,end=address)
        h.u.ctl_remove_cache(0x08000000,0x08080000);h.ss.flash=bytes(h.u.mem_read(0x08010000,0x70000))

    def repatch(self,address,target):
        old=next(o for o in self.h.recovery.overlays if o['address']==address)
        self.patch(address,old['replacement'],target,old)

    def patch(self,address,expected,target,old):
        h=self.h;assert h.u.mem_read(address,len(expected))==expected
        patch=b_w(address,target)+b'\x00\xbf'*(len(expected)//2-2)
        assert 0x08010200<=address<address+len(patch)<=0x08080000
        # Generated poll entry may relocate; remove its obsolete overlay record
        # before checking overlap against the fresh variant.
        for o in tuple(h.recovery.overlays):
            if o is not old and not(address+len(patch)<=o['address'] or o['address']+len(o['replacement'])<=address):
                assert msc.CODE_BASE<=address<msc.CODE_BASE+len(h.mc.code)
                h.recovery.overlays.remove(o)
        if old:old['replacement']=patch
        else:h.recovery.overlays.append(dict(address=address,original=bytes(expected),replacement=patch))
        h.u.mem_write(address,patch);self.overlays.append(dict(address=address,expected=bytes(expected),replacement=patch))

    def status(self):
        return {n:self.h.read(factory.STATE_BASE+o) for n,o in (('pending',factory.PENDING),('running',factory.RUNNING),
            ('busy',factory.BUSY),('generation',factory.GENERATION),('desired',factory.DESIRED),('applied',factory.APPLIED),
            ('switches',factory.SWITCHES),('errors',factory.ERRORS))}

    def request(self,argument):return self.h.call(0x080432A8,argument)
    def pump(self):return self.h.sd.pump()
    def enumerate(self):
        h=self.h;h.cc.reset();self.pump();h.cc.enumerate();h.cc.address();h.cc.configure(1);self.pump()
    def descriptor(self):
        h=self.h;pointer=h.read(h.ib.root+24);length=int.from_bytes(h.u.mem_read(h.ib.root+28,2),'little')
        return bytes(h.u.mem_read(pointer,length))
    def check(self):
        h=self.h;h.assertEqual(h.u.mem_read(factory.STATE_BASE-4,4),b'FBEG');h.assertEqual(h.u.mem_read(factory.STATE_BASE+factory.STATE_SIZE,4),b'FEND')
        h.assertEqual(self.status()['running'],0);h.assertEqual(self.status()['busy'],0);h.sd.check()
