"""Native29714/29736 boot router+ports over controlled final driver methods.

No test recovery code,state seeding,registration calls or copied RAM vtables.
The packaged firmware performs reservation,registration and dispatch itself.
"""
from types import SimpleNamespace
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1
from midi_output_test_support import MidiOutputFixture


class IntegratedMidiFixture:
    def __init__(self,h):
        self.h=h;self.router,self.adapter=0x20001B00,0x20001A00
        self.drivers=[0x20001E00+n*0x20 for n in range(3)];self.delivered=[[] for _ in range(3)]
        self.descriptor,self.data=0x20001F40,0x20001F60
        vt,drivers=0x20001F00,0x20001B80
        for p,code in ((0x0800EB00,'00797047'),(0x0800EB04,'40797047'),(0x0800EB08,'7047'),(0x0800EB0C,'7047')):
            h.u.mem_write(p,bytes.fromhex(code)) # final driver readiness/full/accept/flush boundary
        for off,p in ((0,0x0800EB08),(4,0x0800EB0C),(8,0x0800EB04),(12,0x0800EB00)):
            h.word(vt+off,p|1)
        for n,driver in enumerate(self.drivers):
            h.word(driver,vt);h.u.mem_write(driver+4,b'\x01');h.word(drivers+4*n,driver)
        h.word(drivers+12,0)
        def delivered(u,p,n,d):
            driver=u.reg_read(UC_ARM_REG_R0);packet=u.reg_read(UC_ARM_REG_R1)
            self.delivered[self.drivers.index(driver)].append(bytes(u.mem_read(packet,4)))
        h.u.hook_add(UC_HOOK_CODE,delivered,begin=0x0800EB08,end=0x0800EB08)
        # Native SysEx success notifies the callback object passed to29714.
        # Supply its documented vtable slot1 as a no-op boundary.
        callback,callback_vt=0x20003200,0x20003220
        h.word(callback,callback_vt);h.word(callback_vt+4,0x0800EB0D)
        h.call(0x08029714,self.router,drivers,callback,0)
        self.port_array=h.read(self.router+0x14)
        self.ports=[h.read(self.port_array+4*n) for n in range(3)]
        h.assertEqual(h.u.mem_read(self.router+0x18,1),b'\x03')
        h.word(0x20006F04,self.router);h.word(0x20000A7C,0)
        h.call(0x08031F08,self.adapter);h.u.mem_write(self.adapter+0x18,b'\x09')
    pending=MidiOutputFixture.pending
    poll=MidiOutputFixture.poll
    note=MidiOutputFixture.note
    def send(self,port,packet):
        self.h.u.mem_write(self.data,bytes(packet));obj=self.ports[port]
        return self.h.call(self.h.read(self.h.read(obj)+8),obj,self.data)
