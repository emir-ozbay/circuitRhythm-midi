"""Bounded TXE credits through native UART IRQ53/54 and the FPU frame shim.

No FIFO/cursor or instruction is replaced. Only ISR.TXE peripheral input is
supplied;native26042 consumes its FIFO and writes TDR. No RX,NVIC or baud timing
is modeled,and the captured TDR bytes are not physical delivery evidence.
"""
from unicorn import UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_PRIMASK,UC_ARM_REG_BASEPRI,UC_ARM_REG_PC
from recovery_input_test_support import MAIN_LOOP

UARTS={0x40011000:(53,0x080646FC),0x40004400:(54,0x08064702)}


class ExhaustedUARTCredits(RuntimeError):pass


class NativeUARTPeer:
    def __init__(self,s,*,txe_credits):
        assert isinstance(txe_credits,int) and txe_credits>0
        self.s=s;self.h=s.h;self.remaining=txe_credits;self.initial_credits=txe_credits
        self.current=None;self.ports=[];self.interrupts=[]
        for driver in s.objects(0x08068C84):
            raw=self.h.read(driver+4);device=self.h.read(raw+4)
            base=self.h.read(self.h.read(self.h.read(device)))
            assert base in UARTS
            vector,handler=UARTS[base]
            assert int.from_bytes(s.image[vector*4:vector*4+4],'little')==handler|1
            port=dict(driver=driver,device=device,base=base,vector=vector,handler=handler,bytes=[])
            self.ports.append(port)
            self.h.u.hook_add(UC_HOOK_MEM_WRITE,self._write,begin=base+0x28,end=base+0x2B)
        assert sorted(p['base'] for p in self.ports)==sorted(UARTS)

    def _write(self,u,kind,address,size,value,_):
        # Register reads stay out of write hooks (Unicorn M-class ITSTATE).
        assert self.current is not None and address==self.current['base']+0x28
        assert size==4 and 0<=value<=255
        self.current['bytes'].append(value)

    def service(self):
        h=self.h;u=h.u
        assert u.reg_read(UC_ARM_REG_PC)==MAIN_LOOP and not h.in_service
        assert not u.reg_read(UC_ARM_REG_PRIMASK) and not u.reg_read(UC_ARM_REG_BASEPRI)
        for port in self.ports:
            base=port['base']
            for _ in range(65):  # native64B TX FIFO plus its empty/disable IRQ
                if not h.read(base)&0x80:break
                if not self.remaining:raise ExhaustedUARTCredits('finite UART TXE peer input exhausted')
                assert h.read(base+0x1C)==0,'RX/error/other UART input is not modeled'
                self.remaining-=1;h.word(base+0x1C,0x80)
                before=len(port['bytes']);self.current=port
                try:h._irq_call(port['handler'],port['vector'])
                finally:self.current=None
                assert len(port['bytes'])-before in (0,1)
                h.word(base+0x1C,0)  # withdraw this peer credit,not firmware RAM
                self.interrupts.append(dict(vector=port['vector'],wrote_byte=len(port['bytes'])!=before))
            assert not h.read(base)&0x80,'native UART TXEIE did not retire within FIFO bound'

    def report(self):
        return dict(initial_credits=self.initial_credits,used_credits=self.initial_credits-self.remaining,
            ports=[dict(**{k:v for k,v in p.items() if k!='bytes'},bytes_hex=bytes(p['bytes']).hex()) for p in self.ports],
            interrupts=self.interrupts,scope='Finite explicit TXE inputs/native IRQ/FPU frames/TDR writes;no native FIFO clearing,RX,NVIC,baud timing or physical delivery proof')
