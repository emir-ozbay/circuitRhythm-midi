"""Native MSC/SCSI/queued flash worker with RAM-only lower flash and RTOS edges."""
import struct
from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3
from inspect_ui import load_image
from thumb_asm import Asm,b_w,bl,bx_lr,ldr_imm,mov_reg,movs_imm,push,pop,raw
import midi_usb_storage_prototype as storage
import midi_usb_msc_prototype as msc
import midi_usb_control_prototype as control


class UsbStorageFixture:
    def __init__(self,h):
        self.h=h; self.code,self.labels=storage.arm_code(); self.job=None; self.sent=[]; self.cancelled=[]
        self.tx_fifo=[]; self.flash_reads=[]; self.worker_visits=0; self.overlays=[]
        self.backend,self.lower,self.vt=0x2000A800,0x2000AA00,0x2000AA40
        stock=load_image(); variant,labels=storage.msc_variant()
        h.u.mem_write(msc.CODE_BASE,variant); h.mc.code=variant; h.mc.labels=labels
        targets={0x08040B5A:'mc_init_list',0x08040B7E:'mc_deinit_list',0x0804293E:'mc_irq',0x08026988:'mc_rx_callback',
                 0x0802C9D4:'mc_rx_lower',0x0802EFF8:'mc_bot_reset',0x08027624:'mc_poll',0x0802F014:'mc_bot_0802f014',
                 0x0802F04A:'mc_bot_0802f04a',0x080531CC:'mc_fifo_read'}
        for address,label in targets.items():
            old=next(x for x in h.recovery.overlays if x['address']==address)
            self.patch(address,old['replacement'],labels[label],old)
        for address,(original,label) in msc.generated_gates().items():
            old=next(x for x in h.recovery.overlays if x['address']==address)
            self.patch(address,old['replacement'],labels[label],old)
        h.u.mem_write(storage.CODE_BASE,self.code)
        h.u.mem_write(storage.STATE_BASE-4,b'STBG'); h.u.mem_write(storage.STATE_BASE+storage.STATE_SIZE,b'STEN')
        h.u.mem_write(storage.STATE_BASE,bytes(storage.STATE_SIZE))
        # Actual static-initializer-produced MSC function table (trace pins it).
        ops=(0x080650D1,0x080650D5,0x080650E5,0x080650E9,0x08065129,0x08065195,0x08065251,0x08065255,0x08068BC0)
        h.u.mem_write(storage.OPS,struct.pack('<9I',*ops)); h.word(0x200038AC,storage.OPS)
        h.call(0x08043264,1)
        # Real queued backend constructor, FIFO, read wrapper, drain and worker.
        h.word(self.lower,self.vt); h.word(self.vt+0xC,0x0800ED01); h.word(self.vt+0x1C,0x080650D1)
        h.call(0x0802C190,self.backend,3,self.lower,7); self.queue=h.read(self.backend+8)
        h.word(0x20006E60,self.backend)
        for off,v in ((0,storage.MAGIC),(storage.CONTROLLER,h.ib.ctrl),(storage.BACKEND,self.backend),(storage.QUEUE,self.queue)):
            h.word(storage.STATE_BASE+off,v)
        h.u.mem_map(0x40023000,0x3000); h.u.mem_write(storage.BUFFER-4,b'DBEG'); h.u.mem_write(storage.BUFFER+4096,b'DEND')
        h.u.mem_map(0x21000000,0x2000); self.media=b'Native queued flash read'+bytes(4096-24)
        h.u.mem_write(0x21000000,self.media)
        # Lower flash copies RAM; native worker, queue and drain remain real.
        a=Asm(0x0800ED00); E=a.emit; E(push,[4],lr=True); E(mov_reg,4,0); E(mov_reg,0,2); a.imm32(1,0x21000000)
        E(mov_reg,2,3); E(bl,0x08022CF0); E(ldr_imm,0,4,4); E(pop,[4],pc=True)
        h.u.mem_write(a.base,a.assemble()[0])
        def read(u,p,n,d):
            self.flash_reads.append(tuple(u.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)))
        h.u.hook_add(UC_HOOK_CODE,read,begin=a.base,end=a.base)
        # Native drain yields until2C278 clears the request bit. Model the RTOS
        # yield by running that real worker, never by clearing its fields in Python.
        a=Asm(0x0800ED40); E=a.emit; E(push,[0,1,2,3,4,5,6],lr=True); a.imm32(0,self.backend)
        E(bl,0x0802C278); E(pop,[0,1,2,3,4,5,6],pc=True); h.u.mem_write(a.base,a.assemble()[0])
        for address,replacement in ((0x08024138,b_w(0x08024138,a.base)),(0x080240C0,bytes.fromhex('704700bf'))):
            expected=stock[address-0x08010000:address-0x08010000+4]
            assert h.u.mem_read(address,4)==expected
            h.u.mem_write(address,replacement); self.overlays.append(dict(address=address,expected=expected,replacement=replacement,boundary='RTOS'))
        def worker(u,p,n,d): self.worker_visits+=1
        h.u.hook_add(UC_HOOK_CODE,worker,begin=0x0802C278,end=0x0802C278)
        targets={0x080458D0:'sd_scsi',0x08065128:'sd_read',0x0802C9B8:'sd_tx_submit',0x080268D0:'sd_tx_callback',
                 0x0804293E:'sd_irq',0x0802C328:'sd_worker_result'}
        for address,original in storage.GATES.items():
            old=next((x for x in h.recovery.overlays if x['address']==address),None)
            self.patch(address,old['replacement'] if old else original,self.labels[targets[address]],old)
        address=labels['mc_poll']; expected=variant[address-msc.CODE_BASE:address-msc.CODE_BASE+6]
        self.patch(address,expected,self.labels['sd_poll'],None)
        h.native.foreign_usb_submit=self.submit
        h.u.mem_map(h.ib.base+0x3000,0x1000)
        h.ss.poke(0x958,16)  # FIFO2 space in words; one64B packet at a time
        def fifo(u,access,address,size,value,data): self.tx_fifo.append(value.to_bytes(4,'little'))
        h.u.hook_add(UC_HOOK_MEM_WRITE,fifo,begin=h.ib.base+0x3000,end=h.ib.base+0x3003)
        def flush(u,access,address,size,value,data):
            if value&0x20 and (value>>6)&31 in (2,16): self.tx_fifo.clear()
        h.u.hook_add(UC_HOOK_MEM_WRITE,flush,begin=h.ib.base+0x10,end=h.ib.base+0x13)
        h.u.ctl_remove_cache(0x08000000,0x08080000); h.ss.flash=bytes(h.u.mem_read(0x08010000,0x70000))

    def patch(self,address,expected,target,old):
        h=self.h; assert h.u.mem_read(address,len(expected))==expected
        patch=b_w(address,target)+b'\x00\xbf'*(len(expected)//2-2)
        assert 0x08010200<=address<address+len(patch)<=0x08080000
        for other in h.recovery.overlays:
            if other is not old: assert address+len(patch)<=other['address'] or other['address']+len(other['replacement'])<=address
        if old: old['replacement']=patch
        else: h.recovery.overlays.append(dict(address=address,original=bytes(expected),replacement=patch))
        h.u.mem_write(address,patch); self.overlays.append(dict(address=address,expected=bytes(expected),replacement=patch))

    def status(self):
        return {n:self.h.read(storage.STATE_BASE+o) for n,o in (('io_busy',storage.IO_BUSY),('scsi_busy',storage.SCSI_BUSY),
            ('tx_active',storage.TX_ACTIVE),('irq_active',storage.IRQ_ACTIVE),('cancel_tx',storage.CANCEL_TX),('reads',storage.READS),('done',storage.DONE))}

    def submit(self,endpoint,pointer,length):
        assert endpoint==0x82 and self.job is None
        self.job=(pointer,length,bytes(self.h.u.mem_read(pointer,length))); self.tx_fifo.clear()

    def command(self,opcode=0x28,blocks=1):
        h=self.h
        # Execute the real capacity callback; don't mirror its size constants.
        h.call(0x080650D4,0,storage.SCSI+8,storage.SCSI+4)
        cdb=bytes([opcode,0,0,0,0,0,0,blocks>>8,blocks&255,0])+bytes(6)
        packet=struct.pack('<4sIIBBB',b'USBC',0x12345678,blocks*4096,0x80 if opcode==0x28 else 0,0,10)+cdb
        assert len(packet)==31
        h.ib.rx_data(packet,endpoint=2); h.ib.rx_complete(endpoint=2); h.ib.run(); return h.mc.poll()

    def complete_tx(self):
        h=self.h; assert self.job is not None
        # Real TXFE service copies each64B packet, then real XFRC walks classes.
        for _ in range(80):
            if h.read(h.ib.handle+0x3C+2*0x1C+24)>=self.job[1]: break
            h.ib.flags[msc.IN_INT]|=0x80; h.ib.run()
        assert b''.join(self.tx_fifo)[:self.job[1]]==self.job[2]
        h.ib.flags[msc.IN_INT]|=1; h.ss.poke(msc.IN_CTL,h.ss.regs[msc.IN_CTL]&~0x80000000)
        h.ib.run(); assert self.status()['tx_active']==0
        self.sent.append(self.job[2]); self.job=None; self.tx_fifo.clear()

    def pump(self):
        self.h.mc.pump()
        if self.job and not self.status()['tx_active']:
            self.cancelled.append(self.job[2]); self.job=None; self.tx_fifo.clear()

    def check(self):
        h=self.h
        h.assertEqual(h.u.mem_read(storage.STATE_BASE-4,4),b'STBG'); h.assertEqual(h.u.mem_read(storage.STATE_BASE+storage.STATE_SIZE,4),b'STEN')
        h.assertEqual(h.u.mem_read(storage.BUFFER-4,4),b'DBEG'); h.assertEqual(h.u.mem_read(storage.BUFFER+4096,4),b'DEND')
        for n in ('io_busy','scsi_busy','irq_active'): h.assertEqual(self.status()[n],0)
        h.mc.check()
