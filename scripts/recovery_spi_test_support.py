"""Native SPI DMA completion with an explicit, optional external peer model.

Default strict policy rejects the first consumed MISO response. 'ready' and
'busy' model only bank0/register802B after the native80802B selector. They
are environmental assumptions, not execution/proof of the auxiliary DSP.
No CPU return value or completion RAM is supplied. Native DMA IRQs publish
the two completion tokens. Inherited basic-frame/clock/media limits apply.
"""
import struct
from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB
from capstone.arm_const import ARM_REG_R0, ARM_INS_BL
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
from recovery_input_test_support import InputStartup, MAIN_INPUT_READY
from recovery_worker_test_support import SAVED_REGS
from recovery_boot_test_support import STOP

DMA1 = 0x40026000
RX, TX = DMA1+0x58, DMA1+0x70
SPI_WAIT = 0x0802B66C
MEDIA_GATE = 0x0802E4C0
USED_RESPONSE_CALLER = 0x08031296
IGNORED_RESPONSE_CALLERS = (0x080310A8,0x080311CC,0x08031306,0x0803128C,
                            0x08031416,0x0803146E,0x0803147A,0x08031510)
IRQS = {'rx':(0x08064732,30,DMA1,1<<27),
        'tx':(0x08064708,31,DMA1+4,32)}


class UnmodeledSPIResponse(RuntimeError):
    pass


class NativeMediaUnavailable(RuntimeError):
    pass


class SPIStartup(InputStartup):
    def __init__(self, image, *, peer_policy='strict', busy_reads=2, discarded_byte=0):
        assert peer_policy in ('strict','ready','busy')
        assert isinstance(busy_reads,int) and busy_reads >= 0 and 0 <= discarded_byte <= 255
        self.spi_checkpoint = None
        super().__init__(image)
        self.peer_policy, self.busy_reads, self.discarded_byte = peer_policy,busy_reads,discarded_byte
        self.spi_enabled = self.spi_skip = False
        self.spi_transfers, self.spi_irqs, self.status_reads = [], [], []
        self.media_calls = []
        self.command = self.read_register = self.selector = self.unmodeled_response = None
        self.memory_selector = None
        self.ignored_return_proofs = self._prove_ignored_returns(image)
        self.usb_resets = []
        # Quiescent, unattached USB core. GRSTCTL reset/flush ACK is immediate;
        # no host configuration,endpoint traffic or real bus timing is modeled.
        self.u.mem_map(0x40040000,0x3000)
        self.u.hook_add(UC_HOOK_MEM_READ,self._usb_reset_read,begin=0x40040010,end=0x40040013)
        self.u.hook_add(UC_HOOK_MEM_WRITE,self._usb_reset_write,begin=0x40040010,end=0x40040013)
        self.u.hook_add(UC_HOOK_MEM_WRITE,self._dma1_clear,begin=DMA1+8,end=DMA1+15)
        self.u.hook_add(UC_HOOK_CODE,self._spi_code)

    @staticmethod
    def _prove_ignored_returns(image):
        md = Cs(CS_ARCH_ARM,CS_MODE_THUMB)
        md.detail = True
        proofs = {}
        for caller in IGNORED_RESPONSE_CALLERS:
            evidence = []
            for ins in md.disasm(image[caller-0x08010000:caller-0x08010000+12],caller):
                evidence.append(f'{ins.address:08X} {ins.mnemonic} {ins.op_str}')
                if ins.id == ARM_INS_BL:
                    assert ins.operands[0].imm == 0x08046414
                    first = next(md.disasm(image[0x36414:0x36418],0x08046414))
                    reads,writes = first.regs_access()
                    assert ARM_REG_R0 in writes and ARM_REG_R0 not in reads
                    evidence.append(f'{first.address:08X} {first.mnemonic} {first.op_str}')
                    break
                assert not ins.mnemonic.startswith(('b','it','pop'))
                reads,writes = ins.regs_access()
                assert ARM_REG_R0 not in reads, evidence
                if ARM_REG_R0 in writes:
                    break
            else:
                raise AssertionError(f'R0 not dead after {caller:#x}')
            proofs[hex(caller)] = evidence
        return proofs

    def _usb_reset_read(self,u,kind,address,size,value,_):
        assert size == 4
        self.word(address,(self.read(address)&~0x31)|0x80000000)

    def _usb_reset_write(self,u,kind,address,size,value,_):
        self.usb_resets.append(value)

    def _dma1_clear(self,u,kind,address,size,value,_):
        assert address in (DMA1+8,DMA1+12) and size == 4
        self.word(address-8,self.read(address-8)&~value)

    def _spi_code(self,u,pc,size,_):
        if not self.cooperative or self.in_service:
            return
        # A previously translated Thumb block can pass an emu_start(until)
        # address after the requested endpoint changes. Stop at the code
        # boundary too;do not patch an instruction to create a breakpoint.
        if pc == self.spi_checkpoint:
            self.reason = 'spi_checkpoint'
            u.emu_stop()
            return
        if pc == MEDIA_GATE:
            self.media_calls.append(dict(argument=u.reg_read(UC_ARM_REG_R0),
                                         caller=u.reg_read(UC_ARM_REG_LR)))
        if pc == 0x0802E4CC and not u.reg_read(UC_ARM_REG_R0):
            # Stop at the code boundary before the native LDRB. Do not map
            # page zero or provide a fabricated media object to continue.
            raise NativeMediaUnavailable('native2E4CC would read NULL+4')
        if self.command and pc == self.command['caller']:
            self.command = None
        if pc == 0x08031268:
            self.read_register = dict(bank=u.reg_read(UC_ARM_REG_R0),register=u.reg_read(UC_ARM_REG_R1))
        if pc == 0x08046510:
            self.command = dict(caller=u.reg_read(UC_ARM_REG_LR)&~1,
                bytes=bytes(u.reg_read(r)&255 for r in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2)).hex())
        if pc != SPI_WAIT or not self.spi_enabled or self.reason is not None:
            return
        if self.spi_skip:
            self.spi_skip = False
            return
        if not (self.read(RX)&1 and self.read(TX)&1):
            return
        if not u.reg_read(UC_ARM_REG_PRIMASK) and not u.reg_read(UC_ARM_REG_BASEPRI):
            assert not u.reg_read(UC_ARM_REG_XPSR)&0x0600FC00
            self.reason = 'spi_dma'
            u.emu_stop()

    def start_spi(self):
        assert self.u.reg_read(UC_ARM_REG_PC) == MAIN_INPUT_READY
        self.input_enabled = False
        self.spi_enabled = True
        return self

    def first_spi_wait(self):
        """Run native completed waits/preceding setup to the first empty wait."""
        self.spi_enabled = False
        for _ in range(8):
            self.checkpoint(0x0802B67A,budget=600000)
            if not self.u.reg_read(UC_ARM_REG_R1):
                self._spi_configuration()
                self.checkpoint(SPI_WAIT,budget=16)
                return self
            self.checkpoint(self.u.reg_read(UC_ARM_REG_LR)&~1,budget=10000)
        raise AssertionError('empty native SPI wait not reached')

    def _spi_configuration(self):
        rc,tc,n = self.read(RX),self.read(TX),self.read(RX+4)
        assert rc in (0x10015,0x10415) and tc == 0x10455, (hex(rc),hex(tc))
        assert 0 < n <= 512 and n == self.read(TX+4)
        assert self.read(RX+8) == self.read(TX+8) == 0x4000380C
        source,target = self.read(TX+12),self.read(RX+12)
        # Read-only DMA sources may include the stock vector/identity bytes;
        # application patch bounds are not DMA read bounds.
        assert (0x08010000 <= source < source+n <= 0x08080000
                or 0x20000000 <= source < source+n <= 0x20050000
                and not (source < 0x2004F760 and source+n > 0x2004F320)), (hex(source),n)
        if rc&0x400:
            assert n == 3 and source == 0x200058B8 and target == 0x20005AB8
        else:
            assert target == 0x20000184  # SPI context+14, MINC disabled
        for handler,vector,_,_ in IRQS.values():
            assert self.read(0x08010000+4*vector) == handler|1
        return rc,tc,n,source,target

    def _wire_response(self,rc,n,data):
        if not rc&0x400:
            return bytes([self.discarded_byte]), 'discarded', None
        assert self.command and self.command['bytes'] == data.hex()
        caller = self.command['caller']
        if caller in IGNORED_RESPONSE_CALLERS:
            return bytes([self.discarded_byte])*3, 'ignored_return', None
        detail = dict(caller=hex(caller),command=data.hex(),register=self.read_register if caller==USED_RESPONSE_CALLER else None,
                      selector=self.selector,memory_selector=self.memory_selector,policy=self.peer_policy)
        if (caller != USED_RESPONSE_CALLER or data != bytes.fromhex('400000')
                or self.read_register != dict(bank=0,register=0x802B)
                or self.selector != '80802b' or self.peer_policy == 'strict'):
            self.unmodeled_response = detail
            raise UnmodeledSPIResponse(str(detail))
        ready = self.peer_policy == 'ready' and len(self.status_reads) >= self.busy_reads
        payload = bytes.fromhex('000001') if ready else bytes(3)
        return payload, 'assumed_peer_register', dict(**detail,reply=payload.hex(),ready=ready)

    def complete_spi_dma(self, *, deliver=('rx','tx')):
        assert len(set(deliver)) == len(deliver) and all(x in IRQS for x in deliver)
        rc,tc,n,source,target = self._spi_configuration()
        data = bytes(self.u.mem_read(source,n))
        # Resolve/reject a consumed response BEFORE writes or completion flags.
        response,meaning,status = self._wire_response(rc,n,data)
        command = dict(self.command) if self.command else None
        self.u.mem_write(target,response)
        self.word(RX,rc&~1); self.word(TX,tc&~1)
        self.word(RX+4,0); self.word(TX+4,0)
        self.word(DMA1,self.read(DMA1)|(1<<27))
        self.word(DMA1+4,self.read(DMA1+4)|32)
        event = dict(length=n,source=source,target=target,rx_bytes_written=len(response),
                     rx_increment=bool(rc&0x400),tx_hex=data.hex(),meaning=meaning,
                     command=command,irq_order=list(deliver),peer_status=status)
        if status:
            self.status_reads.append(status)
        if command and command['caller'] == 0x0803128C:
            self.selector = data.hex()
        if command and command['caller'] == 0x08031510:
            assert data[0]&0xFC==0x88
            self.memory_selector = ((data[0]&3)<<16)|(data[1]<<8)|data[2]
        for direction in deliver:
            self.deliver_spi_irq(direction)
        event['tokens_after'] = list(self.u.mem_read(0x20000170,4))
        self.spi_transfers.append(event)
        return event

    def deliver_spi_irq(self,direction):
        handler,vector,status,flag = IRQS[direction]
        u = self.u
        assert self.cooperative and not self.in_service
        assert self.read(status)&flag and not u.reg_read(UC_ARM_REG_PRIMASK) and not u.reg_read(UC_ARM_REG_BASEPRI)
        assert not u.reg_read(UC_ARM_REG_CONTROL)&4
        context = u.context_save()
        pc,sp = u.reg_read(UC_ARM_REG_PC),u.reg_read(UC_ARM_REG_PSP)
        bank = [u.reg_read(r) for r in SAVED_REGS]
        frame_sp,frame = self._hardware_frame(pc,sp)
        msp = u.reg_read(UC_ARM_REG_MSP)
        self.thread_min[self.running_tcb] = min(self.thread_min[self.running_tcb],frame_sp)
        self.in_service = True
        try:
            u.reg_write(UC_ARM_REG_PSP,frame_sp)
            u.reg_write(UC_ARM_REG_CONTROL,0)
            u.reg_write(UC_ARM_REG_XPSR,(frame[7]&~0x1FF)|vector)
            result = self.call(handler)
            assert result['pc'] == STOP and result['error'] is None, result
            assert u.reg_read(UC_ARM_REG_MSP) == msp and [u.reg_read(r) for r in SAVED_REGS] == bank
            assert bytes(u.mem_read(frame_sp,32)) == struct.pack('<8I',*frame)
            assert not self.read(status)&flag
            self.spi_irqs.append(dict(direction=direction,handler=handler,exception=vector,frame_sp=frame_sp))
        finally:
            u.context_restore(context)
            self.in_service = False

    def _service(self,pc):
        if self.reason != 'spi_dma':
            return super()._service(pc)
        self.complete_spi_dma()
        self.spi_skip = True

    def run(self,start,end,*,budget=600000):
        previous = self.spi_checkpoint
        self.spi_checkpoint = end
        try:
            return super().run(start,end,budget=budget)
        finally:
            self.spi_checkpoint = previous
