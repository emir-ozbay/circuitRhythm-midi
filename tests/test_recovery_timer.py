"""Synthetic TIM boundary cases and a separate native-reset IRQ/Main lifetime."""
import struct,unittest
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_THUMB,UC_MODE_MCLASS
from unicorn.arm_const import UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC
import test_phase1_safety as base
import midi_recovery_patch as fixed
from patch_firmware import apply_patches
from recovery_playback_test_support import exercise_native_playback
from recovery_timer_test_support import NativeTimerPeer,boot_timer_session,ExhaustedTimerCredits,BASE,HANDLER


class TimerPeripheralTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.image=apply_patches(base.load_image(),fixed.build_patches())[0]

    def test_native_irq_gate_compare_wrap_and_debt_saturation_synthetic_ram(self):
        # Explicit synthetic fixture,not a native boot or architectural IRQ.
        class Memory:
            def __init__(self):
                self.u=Uc(UC_ARCH_ARM,UC_MODE_THUMB|UC_MODE_MCLASS)
                self.u.mem_map(0x08000000,0x80000);self.u.mem_map(0x20000000,0x50000)
                self.u.mem_map(0x40000000,0x20000)
            def read(self,a):return struct.unpack('<I',self.u.mem_read(a,4))[0]
            def word(self,a,v):self.u.mem_write(a,struct.pack('<I',v&0xFFFFFFFF))
        h=Memory();u=h.u;u.mem_write(0x08010000,self.image)
        peer=NativeTimerPeer(h,compare_credits=1);driver=0x200001D0
        h.word(driver+4,BASE);h.word(driver+8,10|(254<<24))
        cases=[]
        for dier in (0,2):
            for flags in (0,1,2,3,64):
                for debt in (0,253,254):
                    for cnt,compare in ((0,100),(200,100),(0xFFFFFFF0,0xFFFFFFFC)):
                        peer.flags=flags;peer.pending_status=False
                        h.word(BASE+0x0C,dier);h.word(BASE+0x10,flags)
                        h.word(BASE+0x24,cnt);h.word(BASE+0x34,compare)
                        u.mem_write(driver+10,bytes([debt]))
                        u.reg_write(UC_ARM_REG_SP,0x2004FC00);u.reg_write(UC_ARM_REG_LR,0x0800F001)
                        u.emu_start(HANDLER|1,0x0800F000,count=10000);peer._flush_status()
                        self.assertEqual(u.reg_read(UC_ARM_REG_PC),0x0800F000)
                        self.assertEqual(u.reg_read(UC_ARM_REG_SP),0x2004FC00)
                        fired=bool(dier&flags&2)
                        expected=min(254,debt+1) if fired else debt
                        next_compare=(((compare if ((compare+10)&0xFFFFFFFF)>=cnt else cnt)+10)&0xFFFFFFFF) if fired else compare
                        self.assertEqual(u.mem_read(driver+10,1)[0],expected)
                        self.assertEqual(h.read(BASE+0x34),next_compare)
                        self.assertEqual(h.read(BASE+0x10),flags&~2 if fired else flags)
                        cases.append(dict(dier=dier,flags=flags,debt=debt,cnt=cnt,compare=compare,
                            fired=fired,after_debt=expected,after_compare=next_compare))
        self.assertEqual(bytes(u.mem_read(0x08010000,len(self.image))),self.image)
        self.assertEqual(len(cases),90)
        type(self).report=dict(cases=cases,native_reset_executed=False,physical_test=False,
            scope='Explicit synthetic RAM/debt/peripheral seeds,direct native handler entry,shared SR W0C model. No native constructor,FPU IRQ/NVIC or elapsed-time claim.')


class RecoveryTimerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.image=apply_patches(base.load_image(),fixed.build_patches())[0]

    def test_native_timer_irq_main_32step_and_stop_both_modes(self):
        if hasattr(type(self),'progress'):type(self).progress(dict(stage='native_boot'))
        s,timer=boot_timer_session(self.image,sample_status=(0,)*12000,compare_credits=12000,
            record_status=(0xFFFFFF,)*4096,adc_scan=(1500,3700,2048),adc_frame_credits=128)
        type(self).session=s;timer.spurious()
        r=exercise_native_playback(s,timer_peer=timer,progress=getattr(type(self),'progress',None))
        expected=sum(c['count'] for c in r['timer_inputs'])
        self.assertEqual(len(timer.events),expected)
        self.assertEqual(sum(w['pc']==0x08064846 for w in timer.writes),expected)
        self.assertEqual(sum(w['pc']==0x0802679E for w in timer.writes),expected)
        self.assertEqual(len(timer.dispatches),expected)
        self.assertEqual(len(timer.consumers),r['main_cycles'])
        self.assertEqual(sum(c['debt']>0 for c in timer.consumers),expected)
        self.assertEqual(len(timer.record_idle_reads),expected//3)
        self.assertEqual(len(timer.battery_results),expected//1000)
        self.assertEqual(timer.debt(),0)
        self.assertEqual(len(r['leds']),544)
        self.assertEqual([c['steps'] for c in r['runs']],[list(range(32))+[0]]*2)
        self.assertEqual(r['midi_faults'],'000000');self.assertEqual(r['project_io'],[])
        self.assertEqual(len(r['sample_status_inputs']),r['main_cycles'])
        before=(len(timer.events),len(timer.writes),timer.debt())
        with self.assertRaises(ExhaustedTimerCredits):timer.deliver(timer.remaining+1)
        self.assertEqual((len(timer.events),len(timer.writes),timer.debt()),before)
        type(self).report=r


if __name__=='__main__':unittest.main()
