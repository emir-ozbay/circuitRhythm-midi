"""Native FatFs over synthetic NOR bytes;no custom device filesystem code.

Explicit16MiB/4KiB NOR and synthetic FAT12 input. Reads move actual DMA data
before TC;program/erase obey WEL,page bounds and1-to0 programming. Native
FatFs creates its own files and media ownership objects. Peripheral timing,
auxiliary DSP ready and other inherited model assumptions remain conditional.
"""
import struct
from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
from recovery_spi_test_support import SPIStartup
from recovery_boot_test_support import STOP
import flash_query_patch as sync

QSPI = 0xA0001000
DMA = 0x40026400
STREAM = DMA+0xB8
NOR_SIZE = 16*1024*1024
VOLUME_BASE = 0xD4000
SECTOR = 4096


class SparseNOR:
    def __init__(self,data=None):
        self.data = bytearray(b'\xff'*NOR_SIZE if data is None else data)
        assert len(self.data)==NOR_SIZE
        self.wel = False
        self.mutations = []

    def bounds(self,address,length):
        assert 0 <= address < address+length <= len(self.data)

    def read(self,address,length):
        self.bounds(address,length)
        return bytes(self.data[address:address+length])

    def erase(self,address):
        self.bounds(address,SECTOR)
        assert self.wel and address%SECTOR==0
        self.data[address:address+SECTOR] = b'\xff'*SECTOR
        self.wel = False
        self.mutations.append(dict(op='erase',address=address,length=SECTOR))

    def program(self,address,payload):
        length=len(payload); self.bounds(address,length)
        assert self.wel and 0 < length <= 256 and address//256==(address+length-1)//256
        assert all(a&b==b for a,b in zip(self.data[address:address+length],payload))
        self.data[address:address+length] = payload
        self.wel = False
        self.mutations.append(dict(op='program',address=address,length=length))


def fat12_fixture():
    """4096B sectors,2 FATs,Rhythm/00_INIT directories;application files absent."""
    image=bytearray(b'\xff'*NOR_SIZE)
    boot=bytearray(SECTOR)
    boot[:3]=b'\xeb\x3c\x90'; boot[3:11]=b'MSWIN4.1'
    count=(NOR_SIZE-VOLUME_BASE)//SECTOR
    struct.pack_into('<HBHBHHBHHHII',boot,11,SECTOR,1,1,2,512,count,0xF8,2,32,64,0,0)
    boot[36]=0x80; boot[38]=0x29
    struct.pack_into('<I',boot,39,0x12345678)
    boot[43:54]=b'TESTVOLUME '; boot[54:62]=b'FAT12   '; boot[510:512]=b'\x55\xaa'
    image[VOLUME_BASE:VOLUME_BASE+SECTOR]=boot
    fat=bytearray(2*SECTOR); fat[:6]=bytes.fromhex('f8ffffffffff')
    for start in (1,3):image[VOLUME_BASE+start*SECTOR:VOLUME_BASE+(start+2)*SECTOR]=fat
    def entry(name,cluster):
        item=bytearray(32); item[:11]=name.ljust(11,b' '); item[11]=0x10
        struct.pack_into('<H',item,26,cluster)
        return item
    root=bytearray(4*SECTOR); root[:32]=entry(b'RHYTHM',2)
    image[VOLUME_BASE+5*SECTOR:VOLUME_BASE+9*SECTOR]=root
    for index,parent,name in ((9,0,b'00_INIT'),(10,2,None)):
        directory=bytearray(SECTOR); cluster=index-7
        directory[:32]=entry(b'.',cluster); directory[32:64]=entry(b'..',parent)
        if name:directory[64:96]=entry(name,3)
        image[VOLUME_BASE+index*SECTOR:VOLUME_BASE+(index+1)*SECTOR]=directory
    return bytes(image)


class MissingNORData(RuntimeError):
    pass


class MediaStartup(SPIStartup):
    def __init__(self,image,*,medium=None,data_enabled=True,**options):
        super().__init__(image,**options)
        self.medium = SparseNOR(fat12_fixture()) if medium is None else medium
        self.data_enabled = data_enabled
        self.qspi_transfers,self.qspi_dma_irqs,self.mounts,self.bindings,self.sync_calls,self.scratch_uses = [],[],[],[],[],[]
        self.u.hook_add(UC_HOOK_MEM_WRITE,self._dma2_clear,begin=DMA+12,end=DMA+15)
        self.u.hook_add(UC_HOOK_CODE,self._media_code)

    def _dma2_clear(self,u,kind,address,size,value,_):
        assert size==4
        self.word(DMA+4,self.read(DMA+4)&~value)

    def _code(self,u,pc,size,data):
        required = 0x20000 if pc==0x08041C2E else 0x80000 if pc==0x08041C68 else None
        if required is not None and (not self.read(QSPI)&required
                or u.reg_read(UC_ARM_REG_PRIMASK) or u.reg_read(UC_ARM_REG_BASEPRI)):
            old=self.qspi_complete; self.qspi_complete=False
            try:return super()._code(u,pc,size,data)
            finally:self.qspi_complete=old
        return super()._code(u,pc,size,data)

    def _media_code(self,u,pc,size,_):
        if self.in_service:return
        if pc==0x0802E4BA:
            self.mounts.append(dict(root=u.reg_read(UC_ARM_REG_R4),ready=u.reg_read(UC_ARM_REG_R5)))
        if pc==0x0802E2F6:
            self.bindings.append(dict(owner=u.reg_read(UC_ARM_REG_R0),root=u.reg_read(UC_ARM_REG_R1)))
        if pc==sync.SITE:
            self.sync_calls.append(dict(drive=u.reg_read(UC_ARM_REG_R0),command=u.reg_read(UC_ARM_REG_R1),
                                        buffer=u.reg_read(UC_ARM_REG_R2),sp=u.reg_read(UC_ARM_REG_SP)))
        if pc==sync.CODE_BASE+8:
            self.scratch_uses.append(dict(sp=u.reg_read(UC_ARM_REG_SP),command=u.reg_read(UC_ARM_REG_R5),
                                         buffer_before=u.reg_read(UC_ARM_REG_R2)))

    def _service(self,pc):
        if self.reason!='qspi':return super()._service(pc)
        cr,ccr=self.read(QSPI),self.read(QSPI+0x14)
        opcode,address=ccr&255,self.read(QSPI+0x18)
        assert opcode in (0xF5,0x35,0xB7,0xAF,0xEC,6,0x21,5,0x12),hex(opcode)
        event=dict(opcode=opcode,address=address,dma=bool(cr&4),interrupt='match' if pc==0x08041C68 else 'transfer')
        if cr&4:
            dcr,count,peripheral,target = (self.read(STREAM+off) for off in (0,4,8,12))
            assert dcr in (0x06010415,0x06010455) and peripheral==QSPI+0x20
            assert count==self.read(QSPI+0x10)+1 and 0 < count <= SECTOR
            assert 0x20000000 <= target < target+count <= 0x20050000
            assert not (target < 0x2004F760 and target+count > 0x2004F320)
            if not self.data_enabled:raise MissingNORData('DMA data must precede completion')
            if opcode==0xEC:
                assert not dcr&0x40
                payload=self.medium.read(address,count)
                self.u.mem_write(target,payload)
            else:
                assert opcode==0x12 and dcr&0x40
                self.medium.program(address,bytes(self.u.mem_read(target,count)))
            self.word(STREAM,dcr&~1); self.word(STREAM+4,0)
            self.word(DMA+4,self.read(DMA+4)|(1<<27))
            event.update(length=count,ram=target,direction='read' if opcode==0xEC else 'program')
            self._dma_irq()
        elif opcode==6:self.medium.wel=True
        elif opcode==0x21:self.medium.erase(address)
        elif opcode==5:
            assert pc==0x08041C68 and self.read(QSPI+0x24)&1
            assert self.read(QSPI+0x28)&1==0  # mask24/match28;WIP==0
        self._qspi_irq(pc)
        self.qspi_transfers.append(event); self.qspi_irqs+=1
        self.events.append(dict(kind='qspi',interrupted_pc=pc))

    def _qspi_irq(self,pc):
        context=self.u.context_save(); self.in_service=True
        try:
            self.u.reg_write(UC_ARM_REG_CONTROL,0)
            self.word(QSPI+8,8 if pc==0x08041C68 else 2)
            result=self.call(0x080645E0)
            assert result['pc']==STOP and result['error'] is None,result
        finally:
            self.u.context_restore(context); self.in_service=False
    def _dma_irq(self):
        assert self.read(0x08010000+86*4)==0x080645EF
        context=self.u.context_save(); self.in_service=True
        try:
            self.u.reg_write(UC_ARM_REG_CONTROL,0)
            result=self.call(0x080645EE)
            assert result['pc']==STOP and result['error'] is None,result
            assert not self.read(DMA+4)&(1<<27)
            self.qspi_dma_irqs.append(dict(handler=0x080645EE))
        finally:
            self.u.context_restore(context); self.in_service=False
