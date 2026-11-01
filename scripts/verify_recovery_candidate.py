"""Scoped Phase1 criteria and packaged integration regressions for new SYX."""
import json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'scripts'),str(ROOT/'src')]
import test_integrated_midi_recovery as tests
import test_integrated_midi_reset as reset_tests
import test_integrated_usb_tx as usb_tests
import test_integrated_accepted_tx as accepted_tests
import test_integrated_usb_irq as irq_tests
import test_recovery_boot as boot_tests
import test_recovery_main as main_tests
import test_recovery_worker as worker_tests
import test_recovery_input as input_tests
import test_recovery_spi as spi_tests
import test_recovery_media as media_tests
import test_flash_query as query_tests
import test_recovery_dsp as dsp_tests
import test_recovery_fpu as fpu_tests
import test_shared_project as shared_tests
import test_recovery_live_mode as live_tests
import test_recovery_views as view_tests
import test_note_cleanup as cleanup_tests
import test_recovery_notes as note_tests
import test_recovery_pattern_settings as pattern_tests
import test_recovery_microstep as microstep_tests
import test_recovery_probability as probability_tests
import test_recovery_playback as playback_tests
import test_recovery_timer as timer_tests
import test_recovery_dense_stop as dense_tests
import test_dense_stop_patch as dense_patch_tests
import test_recovery_tie as tie_tests
import test_recovery_gates as gate_tests
import test_recovery_running_edits as running_edit_tests
import test_project_load_guard as load_guard_tests
import test_project_load_recovery as load_recovery_tests
import test_recovery_load as load_tests
import test_recovery_load_reentry as load_reentry_tests
import midi_recovery_patch as fixed
import verify_phase1_candidate as phase
from patch_firmware import unpack_syx


def verify(out,*,core_only=False):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    path=ROOT/'build/circuitrhythm-5706-phase1-recovery.syx';image=unpack_syx(path.read_bytes(),allow_extended=True)['image']
    labels=fixed.seq_code()[1]
    class PackagedRecovery(tests.IntegratedRecoveryTests):
        @classmethod
        def setUpClass(cls):cls.image,cls.labels=image,labels
    class PackagedReset(reset_tests.IntegratedResetTests):
        @classmethod
        def setUpClass(cls):cls.image,cls.labels=image,labels
    class PackagedUsbTx(usb_tests.IntegratedUsbTxTests):
        @classmethod
        def setUpClass(cls):cls.image,cls.labels=image,labels
    class PackagedAcceptedTx(accepted_tests.AcceptedTxTests):
        @classmethod
        def setUpClass(cls):cls.image,cls.labels=image,labels
    class PackagedIrq(irq_tests.IntegratedUsbIrqTests):
        @classmethod
        def setUpClass(cls):cls.image,cls.labels=image,labels
    class PackagedBoot(boot_tests.RecoveryBootTests):
        @classmethod
        def setUpClass(cls):cls.stock,cls.image,cls.labels=boot_tests.base.load_image(),image,labels
    class PackagedMain(main_tests.RecoveryMainTests):
        @classmethod
        def setUpClass(cls):cls.stock,cls.image,cls.labels=main_tests.base.load_image(),image,labels
    class PackagedWorker(worker_tests.RecoveryWorkerTests):
        @classmethod
        def setUpClass(cls):cls.stock,cls.image,cls.labels=worker_tests.base.load_image(),image,labels
    class PackagedInput(input_tests.RecoveryInputTests):
        @classmethod
        def setUpClass(cls):cls.stock,cls.image,cls.labels=input_tests.base.load_image(),image,labels
    class PackagedSPI(spi_tests.RecoverySPITests):
        @classmethod
        def setUpClass(cls):cls.stock,cls.image,cls.labels=spi_tests.base.load_image(),image,labels
    class PackagedMedia(media_tests.RecoveryMediaTests):
        @classmethod
        def setUpClass(cls):cls.stock,cls.image,cls.labels=media_tests.base.load_image(),image,labels
    class PackagedQuery(query_tests.FlashQueryTests):
        @classmethod
        def setUpClass(cls):cls.stock,cls.image,cls.labels=query_tests.base.load_image(),image,labels
    class PackagedDSP(dsp_tests.RecoveryDSPTests):
        @classmethod
        def setUpClass(cls):cls.stock,cls.image,cls.labels=dsp_tests.base.load_image(),image,labels
    class PackagedFPU(fpu_tests.RecoveryFPUTests):
        @classmethod
        def setUpClass(cls):cls.stock,cls.image,cls.labels=fpu_tests.base.load_image(),image,labels
    class PackagedShared(shared_tests.SharedProjectTests):
        @classmethod
        def setUpClass(cls):cls.image,cls.labels=image,labels
    class PackagedLive(live_tests.RecoveryLiveModeTests):
        @classmethod
        def setUpClass(cls):cls.stock,cls.image,cls.labels=live_tests.base.load_image(),image,labels
    class PackagedViews(view_tests.RecoveryViewsTests):
        @classmethod
        def setUpClass(cls):cls.image=image
    class PackagedCleanup(cleanup_tests.NoteCleanupTests):
        @classmethod
        def setUpClass(cls):cls.image,cls.labels=image,labels
    class PackagedNotes(note_tests.RecoveryNotesTests):
        @classmethod
        def setUpClass(cls):cls.image=image
    class PackagedPatternSettings(pattern_tests.RecoveryPatternSettingsTests):
        @classmethod
        def setUpClass(cls):cls.image=image
    class PackagedMicrostep(microstep_tests.RecoveryMicrostepTests):
        @classmethod
        def setUpClass(cls):cls.image=image
    class PackagedProbability(probability_tests.RecoveryProbabilityTests):
        @classmethod
        def setUpClass(cls):cls.image=image
    class PackagedPlayback(playback_tests.RecoveryPlaybackTests):
        @classmethod
        def setUpClass(cls):cls.image=image
    class PackagedTimerBoundary(timer_tests.TimerPeripheralTests):
        @classmethod
        def setUpClass(cls):cls.image=image
    class PackagedTimer(timer_tests.RecoveryTimerTests):
        @classmethod
        def setUpClass(cls):cls.image=image
    class PackagedDensePatch(dense_patch_tests.DenseStopPatchTests):
        @classmethod
        def setUpClass(cls):cls.image,cls.labels=image,labels
    class PackagedTie(tie_tests.RecoveryTieTests):
        @classmethod
        def setUpClass(cls):cls.image,cls.labels=image,labels
    class PackagedGate(gate_tests.RecoveryGateTests):
        @classmethod
        def setUpClass(cls):cls.image=image
    class PackagedRunningEdit(running_edit_tests.RecoveryRunningEditTests):
        @classmethod
        def setUpClass(cls):cls.image=image
    class PackagedLoadGuard(load_guard_tests.ProjectLoadGuardTests):
        @classmethod
        def setUpClass(cls):
            cls.image,cls.labels=image,labels
            cls.g=load_guard_tests.guard.arm_code(labels['c_seq_state'],fixed.STATE_BASE)[1]
    class PackagedLoadRecovery(load_recovery_tests.ProjectLoadRecoveryTests):
        @classmethod
        def setUpClass(cls):
            super().setUpClass();assert cls.image==image;cls.image=image
    def load_case(mode):
        return type(f'PackagedLoad{mode}',(load_tests.RecoveryLoadTests,),
            dict(mode=mode,setUpClass=classmethod(lambda cls:setattr(cls,'image',image))))
    def load_reentry_case(mode):
        return type(f'PackagedLoadReentry{mode}',(load_reentry_tests.RecoveryLoadReentryTests,),
            dict(mode=mode,setUpClass=classmethod(lambda cls:setattr(cls,'image',image))))
    def dense_case(mode,before_output):
        return type(f'PackagedDenseStop{mode}{"Before" if before_output else "After"}',(dense_tests.RecoveryDenseStopTests,),
            dict(mode=mode,before_output=before_output,setUpClass=classmethod(lambda cls:setattr(cls,'image',image))))
    with (out/'tests.txt').open('w',encoding='utf-8') as f:
        suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(PackagedRecovery),
                                 unittest.defaultTestLoader.loadTestsFromTestCase(PackagedReset),
                                 unittest.defaultTestLoader.loadTestsFromTestCase(PackagedUsbTx),
                                 unittest.defaultTestLoader.loadTestsFromTestCase(PackagedAcceptedTx),
                                 unittest.defaultTestLoader.loadTestsFromTestCase(PackagedIrq),
                                 unittest.defaultTestLoader.loadTestsFromTestCase(PackagedBoot),
                                 unittest.defaultTestLoader.loadTestsFromTestCase(PackagedMain),
                                 unittest.defaultTestLoader.loadTestsFromTestCase(PackagedWorker),
                                 unittest.defaultTestLoader.loadTestsFromTestCase(PackagedInput),
                                 unittest.defaultTestLoader.loadTestsFromTestCase(PackagedSPI),
                                 unittest.defaultTestLoader.loadTestsFromTestCase(PackagedMedia),
                                 unittest.defaultTestLoader.loadTestsFromTestCase(PackagedQuery),
                                 unittest.defaultTestLoader.loadTestsFromTestCase(dsp_tests.DSPInputTests),
                                 unittest.defaultTestLoader.loadTestsFromTestCase(PackagedDSP),
                                 unittest.defaultTestLoader.loadTestsFromTestCase(PackagedFPU),
                                 unittest.defaultTestLoader.loadTestsFromTestCase(PackagedShared),
                                 unittest.defaultTestLoader.loadTestsFromTestCase(PackagedLive),
                                 unittest.defaultTestLoader.loadTestsFromTestCase(PackagedCleanup),
                                 unittest.defaultTestLoader.loadTestsFromTestCase(PackagedTimerBoundary),
                                 unittest.defaultTestLoader.loadTestsFromTestCase(PackagedDensePatch),
                                 unittest.defaultTestLoader.loadTestsFromTestCase(PackagedTie),
                                 unittest.defaultTestLoader.loadTestsFromTestCase(PackagedLoadGuard),
                                 unittest.defaultTestLoader.loadTestsFromTestCase(PackagedLoadRecovery),
                                 *([] if core_only else [unittest.defaultTestLoader.loadTestsFromTestCase(PackagedViews),
                                                        unittest.defaultTestLoader.loadTestsFromTestCase(PackagedNotes),
                                                        unittest.defaultTestLoader.loadTestsFromTestCase(PackagedPatternSettings),
                                                        unittest.defaultTestLoader.loadTestsFromTestCase(PackagedMicrostep),
                                                        unittest.defaultTestLoader.loadTestsFromTestCase(PackagedProbability),
                                                        unittest.defaultTestLoader.loadTestsFromTestCase(PackagedPlayback),
                                                        unittest.defaultTestLoader.loadTestsFromTestCase(PackagedTimer),
                                                        unittest.defaultTestLoader.loadTestsFromTestCase(PackagedGate),
                                                        unittest.defaultTestLoader.loadTestsFromTestCase(PackagedRunningEdit),
                                                        *(unittest.defaultTestLoader.loadTestsFromTestCase(load_case(m)) for m in (0,1)),
                                                        *(unittest.defaultTestLoader.loadTestsFromTestCase(load_reentry_case(m)) for m in (0,1)),
                                                        *(unittest.defaultTestLoader.loadTestsFromTestCase(dense_case(m,b)) for m in (0,1) for b in (True,False))])])
        result=unittest.TextTestRunner(stream=f,verbosity=2).run(suite)
    assert result.wasSuccessful()
    criteria={}
    for number,name in enumerate(('run_criterion_1_mode_toggle','run_criterion_2_32pad_step_toggle','run_criterion_3_32step_led_compositor',
                                  'run_criterion_4_velocity_gate_preservation','run_criterion_5_shared_projects','run_criterion_6_sample_engine_muting'),1):
        criteria[str(number)]=getattr(phase,name)(image,labels);assert criteria[str(number)]['status']=='PASS'
    integrity=phase.verify_image_and_manifest(path,path.with_suffix('.manifest.json'),ROOT/'stock/circuitrhythm-firmware-5706.syx',patch_builder=fixed.build_patches)
    assert integrity.pop('image')==image
    r=dict(hardware_release='NO-GO',firmware_integrated=True,packaged_tests=result.testsRun,criteria=criteria,integrity=integrity,
        scope=f'Six scoped Phase1 criteria plus{result.testsRun} packaged tests. Native full-boot inputs cover all32 pad edits and released mode roundtrips;all8 tracks in both modes/Velocity/Gate pages with parameter values and bottom LED composition. View tests run native Main with finite DSP status inputs and finite UART TXE credits/native IRQs;no FIFO/fault clearing. No project I/O or allocation;mode commits preserve raw/metadata. B8 history is retained;C0/bit3 held owners reject. Synthetic timer debt drives native timer6 expiry,not elapsed time. Transient transport/phase/note-owner injections are separate. Readiness bit3 matches stock UI;I/O uses actual phase word1. Strict SPI,disabled DWT,NOR/ADC/USB/non-nested FPU assumptions remain. GPIO scan,event-queue,NVIC,baud timing,other views and physical behavior are not proved. Hardware release remains NO-GO.')
    r['native_ui_included']=not core_only
    if core_only:
        r['scope']=f'Six scoped Phase1 criteria plus{result.testsRun} packaged core tests,including synthetic nonstep-ownership cleanup,90 synthetic TIM IRQ boundary cases,five synthetic dense Stop ABI/context/quarantine tests,three synthetic tie-bit/expiry/retrigger tests and synthetic failed-Load,Close identity,admission,release and authorized apply tests. Full-boot live-mode tests remain included. Seventeen long native tests are excluded:Velocity/Gate,Note1/7,Pattern Settings,Microstep,Probability,direct-debt playback,timer-IRQ playback,native gate expiry,running parameter edits,four64-voice Stop scenarios,two short-read Load scenarios and two Close-confirmed Projects Load/New recovery scenarios. Run their exact-SYX probe scripts separately for those claims. Tie-bit fixture data is not native UI creation. Existing peripheral/timing limits remain. Hardware release NO-GO.'
    else:
        r['scope']+=' Native Note1/7 keymap,blank keys,pages,pitch toggles,LED RAM and retained note release are included;physical note bits survive1<->7 and reject mode commit until release. Synthetic cleanup covers old modes0..10 in both runtime modes.'
        r['scope']+=' Native Pattern Settings includes both pages/Shift,all32 pads,sync/direction,endpoint writes and LED RAM plus Shift27+Duplicate24 Mutate with complete8B record multiset preservation;default automation/sample-flip values limit that claim.'
        r['scope']+=' Native Microstep covers both pages/six bits/ten reserved pads,mask-zero deletion and default recreation,64 masks in both runtime modes,non-default velocity/gate preservation,stopped latched-step edits and LED RAM;running transport is not covered.'
        r['scope']+=' Native Probability covers eight values/eight reserved pads,both pages,empty creation,velocity/gate/microstep preservation,stopped latched-step edits and LED RAM. Enriched Mutate cases preserve full8B record multisets with non-default probability/microstep/gate/velocity;sample-flip/automation values remain default and random probability statistics are not tested.'
        r['scope']+=' Native playback uses one reset and UI-programmed32-step patterns on8 tracks in both runtime modes. Finite synthetic timer debt drives installed callbacks and193 ordered microstep commits/player/mode,live bit6 cursor/LED RAM,Normal bottom layout,Sequencer page lock,running mode rejection and Stop with8 live notes. UART Start/Clock/40 On/40 Off/Stop is checked per mode/port;hardware elapsed time and timer IRQ scheduling remain unmodeled.'
        r['scope']+=' Separate native TIM IRQ playback supplies finite CNT/CC1IF events through IRQ66/FPU frames. Main timer358 consumes the native-produced debt;its slot11 calls2B750 to dispatch application timer370. Direct debt adapter is forbidden in that session. The same32-step/544 LED/Stop/MIDI invariants run with a full Main iteration per event. Autonomous elapsed time,rate,NVIC arbitration and physical timing remain unmodeled.'
        r['scope']+=' Four fresh native resets test64 concurrent stock gate slots in both runtime modes,with Stop before or after the Main output phase. UI-programmed distinct pitches/gate96,64 matching Offs,final Stop,zero quarantine,dirty mode roundtrip and a new Play/Stop are checked. This does not add independent polyphony or prove physical delivery.'
        r['scope']+=' Native gate expiry separately programs Gate1,6,95,96 and fastest stock sync0 through UI,then follows two complete32-step passes in both modes. Page/pattern wrap,matched DIN On/Off,natural expiry and Stop are checked. Three synthetic tests cover tie-bit same/different pitch and untied retrigger at15/16 and31/0;native UI tie creation is not claimed.'
        r['scope']+=' Running parameter edits separately use native reset/UI on8 tracks,both auxiliary pages and both runtime modes. Late microsteps,deletion/recreation,held/no-held input gates and active-note closure are checked through native IRQ/Main. Probability decisions use read-only native PRNG thresholds and exact player-On comparison;no statistical distribution or physical timing claim.'
        r['scope']+=' Two native reset Load tests use native Save and complete-read controls before limiting one lower file read to741B. FatFs supplies the bytes/count;stock4113A returns short-read4. Live alias mutation remains,but no success apply occurs;native Close and taint keep mode admission closed until an authorized recovery completes. No RAM repair,rollback or native/physical EOF cause is claimed.'
        r['scope']+=' Two additional native reset tests exercise Close-confirmed Projects recovery:repeat short-read quarantine,full UI Load,held-pad mode rejection and real release,another normal UI short-read,and page1 slot33 New/defaults. Taint clears only after authorized complete native apply;stale Close checks are synthetic unless separately reported. No RAM repair or physical storage claim.'
    (out/'report.json').write_text(json.dumps(r,indent=2),encoding='utf-8');return r


if __name__=='__main__':
    assert len(sys.argv) in (2,3) and (len(sys.argv)==2 or sys.argv[2]=='--core-only')
    r=verify(sys.argv[1],core_only=len(sys.argv)==3);print(json.dumps(dict(packaged_tests=r['packaged_tests'],criteria='6 PASS',native_ui_included=r['native_ui_included'],hardware_release=r['hardware_release'])));raise SystemExit(2)
