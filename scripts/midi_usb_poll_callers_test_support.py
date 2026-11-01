"""Native transfer callback/dispatch slice over synthetic object bindings."""
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R6,UC_ARM_REG_SP
import hashlib
from seq_Patch import SEQ_STATE_ADDR


class UsbPollCallerFixture:
    def __init__(self,h):
        self.h=h;self.view,self.callback=0x20003200,0x20003260;self.events=[]
        assert not any(h.u.mem_read(self.view,0x80))
        # Constructor2DE9A pins this8B callback object and43B2C stores it at+48.
        # Only this binding is synthetic; the dispatch and callback code run.
        h.word(self.callback,0x08069628);h.word(self.callback+4,0x0802DE91)
        h.word(self.view+0x48,self.callback)
        # Count the native continuation, not2EF5A's readiness entry: an injected
        # CPU detour revisits that entry after returning, without a second poll.
        for name,pc in (('dispatch',0x08043FA0),('adapter',0x08025652),('callback',0x0802DE90),
                        ('bot_poll',0x0802762A),('scsi',0x080458D0)):
            def event(u,p,n,d,name=name):self.events.append(name)
            h.u.hook_add(UC_HOOK_CODE,event,begin=pc,end=pc)
    def poll(self):return self.h.call(0x08025652,self.callback,0)
    def dispatch(self):
        h=self.h;old=h.u.reg_read(UC_ARM_REG_R6);h.u.reg_write(UC_ARM_REG_R6,self.view+0x30)
        try:
            result=h.call(0x08043FA0,end=0x08043FAC)
            h.assertEqual(h.u.reg_read(UC_ARM_REG_SP),0x20040000)
            h.assertEqual(h.u.reg_read(UC_ARM_REG_R6),self.view+0x30)
            return result
        finally:h.u.reg_write(UC_ARM_REG_R6,old)
    def snapshot(self):
        h=self.h
        return dict(reads=h.sd.status()['reads'],done=h.sd.status()['done'],msc=h.mc.status(),session=h.ss.status(),
                    submitted=len(h.ss.tx_jobs),storage_job=h.sd.job,bot_polls=self.events.count('bot_poll'))
    def record(self,name):
        h=self.h
        if hasattr(type(h),'evidence'):
            type(h).evidence.append(dict(test=name,mode=h.u.mem_read(SEQ_STATE_ADDR+4,1)[0],
                callbacks=self.events.count('callback'),native_bot_polls=self.events.count('bot_poll'),
                scsi_entries=self.events.count('scsi'),reads=h.sd.status()['reads'],done=h.sd.status()['done'],
                storage_packets=[dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest()) for b in h.sd.sent],
                msc_phase=h.mc.status()['phase'],session_phase=h.ss.status()['phase'],
                power_asleep=h.pw.status()['asleep'],main_frames=h.ut.status()['frames']))
