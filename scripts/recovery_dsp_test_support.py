"""Finite external DSP input scripts; not an auxiliary processor emulator.

Every consumed MISO value is an explicit test input. There is no default RAM
value, automatic mailbox completion or DSP code execution. The MCU executes
its native polling loops and SPI IRQs. Writes are observed only after their
wire transfer completes; read scripts can require an earlier observed write.
"""
from dataclasses import dataclass
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2
from recovery_media_test_support import MediaStartup
from recovery_spi_test_support import UnmodeledSPIResponse


@dataclass(frozen=True)
class DSPRead:
    address: int
    value: int
    bank: int = 0
    after_write: tuple | None = None  # (bank,address,24-bit wire value)

    def __post_init__(self):
        assert self.bank in (0,1) and 0 <= self.address < 0x40000
        assert 0 <= self.value < 0x1000000
        if self.after_write is not None:
            bank,address,value = self.after_write
            assert bank in (0,1) and 0 <= address < 0x80000 and 0 <= value < 0x1000000


class ScriptedDSPPeer:
    def __init__(self, reads):
        self.script = tuple(reads)
        assert all(isinstance(r,DSPRead) for r in self.script)
        self.reset()

    def reset(self):
        self.active = False
        self.position = 0
        self.writes = {}
        self.reads = []

    def write(self,bank,address,payload):
        assert bank in (0,1) and 0 <= address < 0x80000 and len(payload)==3
        self.writes[bank,address] = int.from_bytes(payload,'big')

    def peek(self,bank,address):
        if not self.active or self.position >= len(self.script):
            raise UnmodeledSPIResponse(f'DSP script inactive/exhausted at {bank}:{address:05X}')
        row = self.script[self.position]
        if (bank,address)!=(row.bank,row.address):
            raise UnmodeledSPIResponse(f'DSP script expects {row.bank}:{row.address:05X}, got {bank}:{address:05X}')
        if row.after_write is not None:
            wb,wa,wv = row.after_write
            if self.writes.get((wb,wa)) != wv:
                raise UnmodeledSPIResponse(f'DSP reply requires completed write {row.after_write}')
        return row.value.to_bytes(3,'big')

    def commit(self,bank,address,payload):
        assert self.peek(bank,address)==payload
        self.reads.append(dict(bank=bank,address=address,reply=payload.hex(),script_index=self.position))
        self.position += 1


def mailbox_script(*,initial_busy=2,command_busy=2):
    """Explicit idle/command-completion scenario, not inferred DSP behavior."""
    assert isinstance(initial_busy,int) and 0 <= initial_busy <= 16
    assert isinstance(command_busy,int) and 0 <= command_busy <= 16
    required = (0,0x372FB,1)
    # Native64416/64540 reads the command word once, then loops on R5=37300.
    # Keep this observed address change; do not rewrite the native loop.
    command = ([DSPRead(0x372FB,1,after_write=required)]
               + [DSPRead(0x37300,1,after_write=required)]*(command_busy-1)
               + [DSPRead(0x37300,0,after_write=required)]) if command_busy else [DSPRead(0x372FB,0,after_write=required)]
    return [DSPRead(0x37300,1)]*initial_busy + [DSPRead(0x37300,0)] + command


def empty_sample_lengths():
    """Exactly128 synthetic zero lengths; not a decoded DSP initialization."""
    return [DSPRead(0x30001+4*slot,0) for slot in range(128)]


class DSPStartup(MediaStartup):
    def __init__(self,image,*,dsp_peer=None,**options):
        super().__init__(image,**options)
        assert dsp_peer is None or isinstance(dsp_peer,ScriptedDSPPeer)
        self.dsp_peer = dsp_peer
        self.dsp_read = self.dsp_write = None
        self.dsp_writes = []
        self.dsp_selector = None
        self.u.hook_add(UC_HOOK_CODE,self._dsp_code)

    def _dsp_code(self,u,pc,size,_):
        if not self.cooperative or self.in_service:
            return
        if pc == 0x08031110:
            self.dsp_read = self.dsp_write = self.dsp_selector = None
            if self.dsp_peer is not None:self.dsp_peer.reset()
        if pc == 0x08031228:
            assert self.dsp_write is None
            self.dsp_write = dict(bank=u.reg_read(UC_ARM_REG_R0),
                address=u.reg_read(UC_ARM_REG_R2)&0x7FFFF,
                value=u.reg_read(UC_ARM_REG_R1)>>8,completed=False)
        if pc == 0x08031266:
            assert self.dsp_write and self.dsp_write['completed']
            self.dsp_write = None
        if pc == 0x080314D6:
            self.dsp_read = dict(bank=u.reg_read(UC_ARM_REG_R0),
                                 address=u.reg_read(UC_ARM_REG_R1)&0x3FFFF)

    def _wire_response(self,rc,n,data):
        if rc&0x400 and self.command and self.command['caller']==0x080310A8 and self.dsp_write is not None:
            assert not self.dsp_write['completed']
            assert self.dsp_write['address']==self.dsp_selector
            assert int.from_bytes(data,'big')==self.dsp_write['value']
        if (rc&0x400 and self.command and self.command['caller']==0x0803151A
                and self.dsp_peer is not None):
            detail = dict(caller=hex(self.command['caller']),command=data.hex(),
                          read=self.dsp_read,memory_selector=self.memory_selector,
                          policy='finite_explicit_DSP_input')
            try:
                assert n==3 and data==bytes.fromhex('400000')
                assert self.dsp_read and self.dsp_read['address']==self.memory_selector
                payload = self.dsp_peer.peek(**self.dsp_read)
            except UnmodeledSPIResponse as error:
                self.unmodeled_response = dict(**detail,error=str(error))
                raise
            return payload,'explicit_DSP_input',None
        return super()._wire_response(rc,n,data)

    def complete_spi_dma(self,**options):
        # Parent resolves/rejects response before RAM/TC and executes native IRQs.
        event = super().complete_spi_dma(**options)
        command = event['command']
        data = bytes.fromhex(event['tx_hex'])
        if event['peer_status'] and event['peer_status']['ready'] and self.dsp_peer is not None:
            self.dsp_peer.active = True
        if command and command['caller']==0x08031416:
            self.dsp_selector = int.from_bytes(data,'big')-0x080000
        if command and command['caller']==0x080310A8 and self.dsp_write is not None:
            write = self.dsp_write
            assert not write['completed'] and write['address']==self.dsp_selector
            assert int.from_bytes(data,'big')==write['value']
            write['completed'] = True
            self.dsp_writes.append(dict(write))
            if self.dsp_peer is not None:self.dsp_peer.write(write['bank'],write['address'],data)
            self.dsp_selector += 1
        if event['meaning']=='explicit_DSP_input':
            payload = self.dsp_peer.peek(**self.dsp_read)
            self.dsp_peer.commit(**self.dsp_read,payload=payload)
        return event
