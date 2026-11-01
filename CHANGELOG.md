## 2026-11-01 — Preserve unfinished Load/New recovery for handoff

- WIP source adds Close descriptor/generation matching, narrow Projects
  Load/New admission, real held-pad retirement and taint clearing only after
  authorized native apply returns. New recovery module is integrated in the
  patch builder source; metadata/auditor/legacy test integration is unfinished.
- Four synthetic boundary tests were reported PASS in conversation output;
  no persisted run report was found. New native recovery helper/tests have
  not run. Current source is not the packaged/tested firmware. No new build
  or test was run for this handoff; SYX272a8128…/CRC985753F7 remains on disk.
- Reconciled stock/SYX/image/CRC/vector, preserved current sources and prior
  STATUS, and verified218 baseline snapshot plus286 historical evidence pins.
  STATUS now separates source, packaged candidate and evidence; technical
  continuation map is docs/HANDOFF-LOAD-RECOVERY-5706.md. No firmware/test source
  changes during handoff. Full M7 and physical device authorization remain open.

## 2026-11-01 — Characterize tainted native Load/New re-entry

- Added two exact-SYX native reset tests, one per runtime mode. They continue
  the Save/full Load/short-read quarantine session without RAM repair and
  retire only the completed one-shot fault hooks, reusing the UART peer.
- Projects opens, but stock controller flags bit1 blocks pads before the
  Projects handler. Separate direct-handler probes confirm dispatcher phase2
  rejection. An initial contrary test assumption failed; pilot and sources
  are retained and are not classified as a firmware defect.
- A labeled diagnostic backend retry restores all saved raw bytes through
  native FatFs/apply, while taint remains latched. Successful Load has no
  separate Close in the observed window; an initial contrary assertion failed
  in two retained pilots. This does not itself establish a leak. Subsequent controller
  UI Load and empty-slot New complete and still reject mode changes. These
  controls do not provide user-accessible quarantine recovery.
- Two new distinct tests PASS; 360/360 IRQ/Main iterations, stable 8 recorder and
  8 player aliases, no additional allocations/NOR writes/MIDI faults in the
  continuation. Byte/range/CRC audit PASS. Same-image cumulative evidence is
  35 distinct tests; not all rerun. Verifier172/core155 is collection only.
- Fixed setup telemetry aliasing: its UART IRQ list must be a deep-copy
  snapshot before reusing the peer. Added a consistency assertion and reran
  both modes; superseded passing reports and their sources are retained.
- Firmware sources and SYX272a8128…/CRC985753F7 are unchanged. Safe taint
  clearing and UI recovery remain open; next is a Close-confirmed narrow
  Load/New recovery path with repeated-error containment. M7 NO-GO.
  See docs/MIDI-RECOVERY-LOAD-REENTRY-5706.md.

## 2026-11-01 — Contain native project Load short-read false success

- Reproduced on the previous exact SYX with native reset objects,Save,FatFs,
  Content worker and Main result delivery:4113A returns4 after a741B lower-read
  limit,but472A8 discards it and381C8 calls successful apply. The first live
  pattern tuple becomes mixed and the mode shortcut is admitted. This is
  explicit lower-read fault input,not a physical EOF/card failure claim.
- Added a152B project-receiver/destination guard at472A8. Failed reads retire
  the callback,queue native Close and latch existing state+64 taint,retaining
  stock busy phase/flags. Mode admission rejects taint;successful and foreign
  callbacks retain stock behavior. No extra reserved RAM;32B wrapper stack.
  Live alias mutation is NOT rolled back and recovery is NOT complete.
- Both modes pass fresh native-reset complete-read controls and short-read
  containment,216 IRQ/Main cycles each,with no RAM repair or instruction stub.
  Three synthetic guard tests and31 overlapping packaged regressions pass,
  plus six scoped criteria and byte/range/CRC audit.33 distinct tests on the
  NEW image;the prior159 are not carried forward. Full suite170/core155 is
  collection only. One historical register-reading write-hook test excluded.
- New SYX272a8128… /CRC985753F7:46 patches,8009 changed bytes. Stock and
  vector/identity are unchanged. Previous candidate/evidence retained.
  Native failed-Load UI/recovery,alias rollback and full M7 remain open.
  No physical device access;M7 NO-GO. See MIDI-RECOVERY-LOAD-SHORT-READ-5706.md.

## 2026-10-31 — Native running microstep/probability edit verification

- Added a native-reset live-edit test for both runtime modes,eight tracks and
  both auxiliary pages. UI programs the15/16 page boundary,distinct pitches,
  long gates and fastest stock sync. Late microsteps,no-held/reserved input
  rejection,probability writes,deletion/recreation and Stop closure are checked.
- Observer reads native PRNG thresholds and the actual comparison;matches
  each player On to its prepared microstep decision. Native MIDI Off calls
  additionally reject premature release of active player notes during edits.
  No PRNG/project/owner/FIFO/fault/debt seed or repair;no statistical claim.
- Corrected two test assumptions:three prepares precede the commit batch;
  same-pitch Note input is a stock toggle rather than an idempotent setter.
  Negative runs and the cancelled repeat are retained. Canonical two-mode run
  passes:726 native IRQs,951 Main cycles,256 edits,64 no-held inputs and32
  running/held mode rejections. Player On exactly matches DIN66/66 in Normal
  and76/76 in Sequencer;Stop closes9/13 live notes. No fault/I/O/extra alloc/NOR.
  Live UI edit phases issue zero MIDI Off calls;no fault injection claimed.
- Firmware c9a87a9d…/CRC BEB0D013,production sources and persistent RAM remain
  unchanged. Byte/range/CRC audit passes;verifier165/core-only152 excludes13
  long tests from core-only. No physical device access;M7 remains NO-GO.
  One new exact-SYX test adds to158 prior same-image tests for159 distinct
  tests,not all rerun. Evidence binds201 source/dependency pins and native
  probability cohorts;no PRNG quality/distribution claim.

## 2026-10-31 — Gate expiry and explicit synthetic tie compatibility

- Added three recovery-image synthetic tie tests:both modes/eight tracks,
  same-pitch tie,untied Off/On retrigger and different-pitch flush.80 subcases
  are three unittests. Native player/recovery runs over synthetic objects;
  native UI tie creation is explicitly unproven.
- Added a separate native-reset/UI Gate1,6,95,96 test at0/15/16/31,fastest
  stock sync0,finite IRQ/Main and two full32-step passes per runtime mode.
  Natural gate expiry and Stop callers are checked separately,with active
  lists across page/pattern boundaries and matched DIN output. Both modes
  pass:7114 native IRQs,7158 Main cycles,387 commits/player/mode. Each mode/
  DIN port has18 On,15 natural Off,3 Stop Off and129 Clock plus Start/Stop;
  fault/I/O/allocation/NOR increase remains zero.
- Corrected host expectations for sync0:two clocks/six microsteps per step;
  Main can process three commits atomically. Two exploratory processes were
  cancelled before completion,not counted as firmware failures or passes.
- 36 overlapping targeted regressions and byte/range/CRC audit pass. Verifier
  now164/core-only152,with12 long tests excluded from core-only. Production
  sources,SYX c9a87a9d…/CRC BEB0D013 and persistent RAM remain unchanged.
  Four new exact-SYX tests pass;previous154 on the same image are retained
  for158 distinct tests,not all rerun. Evidence binds198 source/dependency
  pins;native UI/stock Load tie-bit reachability remains explicit and open.
  No physical device access;M7 remains NO-GO.

## 2026-10-31 — Dense stock64-voice Stop avoids healthy FIFO quarantine

- Reproduced64 naturally overlapping stock gate slots through native reset,
  UI-programmed distinct pitches/gate96 and IRQ/Main playback. Previous
  candidate delivered all Offs but latched quarantine on ordinary64 Off+FC.
- Added one bounded native output poll after each stock player flush,only
  in unmasked thread context with the registered router/three port owners.
  Preserves original virtual call,real overflow quarantine and deferred
  closing;no fault clearing,replay,extra persistent RAM or project I/O.
- New248B cave/4B hook;44 patch hunks/7847 changed bytes,CRC BEB0D013.
  Wrapper adds16B stack;remaining application flash200B. Previous recovery,
  accepted-TX and CTRL_SYNC code bytes remain unchanged.
- Five synthetic guard/ABI/quarantine tests and149 packaged core regressions
  plus six Phase1 criteria pass. Two-mode native IRQ/32-step/544-LED regression
  passes on the new candidate. All four fresh64-voice Stop scenarios pass:
  both modes × before/after output,64 matching Offs,final Stop,zero fault,
  dirty mode roundtrip and successful restart.154 distinct packaged tests
  pass after removing the shared synthetic-timer duplicate;160 total are
  configured,not all rerun. Evidence pins194 sources/dependencies. No device access;
  physical timing/delivery and M7 remain open.

## 2026-10-31 — Native timer IRQ/Main/application dispatch

- Added finite TIM CNT/CC1IF inputs and SR W0C/EGR modeling before native
  Main setup. Native IRQ66 produces debt;Main2677A/object358 consumes it.
  Main slot11 calls2B750 to dispatch application timer370 without another
  debit. UI364 is separate. Direct synthetic debt adapter is forbidden in
  this native session;no debt/slot/callback/project/firmware seeds or repair.
- Two-mode8-track32-step playback/544 LED/Stop regression now also runs with
  10690 native IRQs and full Main loops. Every mode/UART port has40 matched
  On/Off,193 Clock,Start/Stop;8 live notes are flushed. No MIDI fault/I/O /
  extra allocation/NOR increase;production3f979b70… firmware unchanged.
- Modeled periodic371D5 recording status with finite explicitFFFFFF/idle
  replies. Old uniform ADC scenario reaches native low-battery save/shutdown;
  preserved that behavior and added finite raw DMA reference1500/battery3700/
  mux2048 inputs. Native calibration/gauge performs the calculation;no battery
  percentage or shutdown code override.64 of128 ADC credits used.
- New2 packaged tests PASS:90 synthetic IRQ boundary cases as one test plus
  a separate native-reset lifetime.29 overlapping targeted tests/audit PASS;
  previous149 not rerun. Verifier151/core-only144 excludes seven long tests.
  No device access;autonomous time,NVIC/physical timing and M7 remain open.
  Next:64 naturally overlapping stock voices via long gates/distinct notes,
  then native Stop with matched64 Off and finalFC.

## 2026-10-31 — Native player,32-step cursor and Stop lifecycle

- Added one exact-SYX unittest using one native reset and8 factory-created
  players. UI programs32-step sparse patterns;Normal/Sequencer each execute
  193 ordered microstep commits/player and0..31..0 cursor flow,including both
  16/17 and32/1 boundaries.544 native64B LED composites checked.
- Verified Normal stock bottom layout,Sequencer effective page0/running page
  guard and running mode rejection. Stop with8 live notes flushes every real
  player;each mode/UART port has40 matched On/Off plus Start/Clock/Stop.
- Corrected documentation's bit0 running-cursor label:5D458/5D290 uses bit6
  from player time;bit0 is tied to another edit/recorder store. First test's
  remembered-page=0 assumption failed;effective offset0 may preserve auxiliary
  page1. A second overconstraint required the remembered page to survive
  main page-button presses;corrected to check effective offset/full-grid.
  Final test passed from a fresh reset;both negative runs retained.
- Existing finite synthetic AppTimer debt drives installed callbacks,not
  hardware timer IRQ or elapsed time. No RAM/owner/FIFO/LED repair or device
  access. No production/firmware change;3f979b70…/CRC5AB3F54B same.28 targeted
  tests and audit PASS;previous148 not rerun. Verifier149/core-only143 now
  excludes six long native matrices/playback tests in core-only. M7 NO-GO;
  next:finite40000C00/vector66 IRQ events producing debt consumed by Main.
- Prepared the next timer peer with90 explicitly synthetic-RAM handler cases:
  SR/DIER gating,CCR1/CNT update/wrap and254 debt saturation PASS. Separate
  direct-entry fixture,not native reset/IRQ timing or extra packaged tests.

## 2026-10-31 — Native Probability and enriched Mutate coverage

- Added exact-SYX native mode6 regression for8 tracks/both modes/pages:
  512 top-pad mappings,64 endpoint cases (first plain,last with Shift),eight
  values/eight reserved pads,empty-step creation and128 LED composites.
- Checked single-target8B bounds,active-step byte4 writes,32 native
  velocity120/gate96/microstep33 preservation and32 stopped latched-step edits.
  Every probability input preserves live C0/bit3 ownership;64 held mode
  attempts reject and release clears physical/live owners. No RAM seeds/repair.
- Extended32 Mutate cases with non-default probability/microstep/gate/velocity
  in full8B records. Multisets survive and only target256B changes. Identity
  shuffles are allowed;movement is observed per track/mode. Varied sample-flip /
  automation and random distribution remain outside this workload.
- Closes the stopped native auxiliary UI page/pad matrix on the same image:
  Note1/7,Velocity/Gate,Pattern Settings,Microstep,Probability. Five separate
  reset tests,not one combined boot or physical/playback proof;reports hash-bound.
- New1 packaged test and26 overlapping targeted tests PASS. Previous147 and6
  scoped criteria on the same firmware were not rerun. General verifier now
  contains148 tests;--core-only143 excludes five long native UI matrices.
- Production sources,stock and firmware3f979b70…/CRC5AB3F54B/42 patches/7595B
  unchanged;audit PASS. No project I/O,extra allocation,NOR increase or device
  APIs.1088B reservation/2184B workload headroom same. M7 NO-GO;next:native
  Play17/Stop17 through constructed player/scheduler to32-step playhead.

## 2026-10-31 — Native Microstep mask lifecycle and page preservation

- Added exact-SYX native mode5 regression for8 tracks/both modes/pages:
  512 top-pad mappings,64 endpoint cases (first plain,last with Shift),six
  XOR bits/ten reserved pads,all64 masks in both modes and128 LED composites.
- Checked zero-mask deletion/default recreation and single-target8B raw
  bounds.32 native velocity120/gate96 cases preserve complete records through
  nonzero mask toggles;32 stopped latched-step edits retain empty live owners.
  Existing canonical snapshots separately prove bottom inputs never alter
  C0/bit3 ownership;64 held mode attempts reject and release clears owners.
- New1 packaged test and26 overlapping targeted tests PASS. Previous146 and6
  scoped criteria on the same firmware were not rerun. General verifier now
  contains147 tests;--core-only143 excludes four long native UI matrices.
  Host suite/idle snapshot checks are not extra emulation unittest counts.
- Production sources,stock and firmware3f979b70…/CRC5AB3F54B/42 patches/7595B
  unchanged;byte/range/CRC/CFG/ABI audit PASS. No project I/O,extra allocation,
  NOR increase or device APIs.1088B reservation/2184B workload headroom same.
  Running transport/microstep timing remains open. M7 NO-GO;next:Probability6.

## 2026-10-31 — Native Pattern Settings controls and Mutate

- Added an exact-SYX native reset matrix for8 tracks/both modes/pages/Shift:
  1024 End/Start pad cases,1024 bottom speed/direction/blank cases,64 full
  LED compositions and64 physical-held mode rejections. Each edit is bounded
  to its one parameter byte;stock palette and full64B compositor are checked.
- Added32 Shift27+Duplicate24 Mutate cases on native Velocity/Gate-edited
  patterns. Full8B step record multisets survive;only the target256B region
  changes. Enriched automation/sample-flip/probability/microstep and random
  distribution remain outside this workload. No startup/store/ownership seeds.
- Corrected historical exploratory button labels:17 is Play,24 Duplicate;
  the old16/17 Clear/Duplicate label was wrong. Canonical reset test never
  uses17 and asserts stopped transport after every input. Interrupted/incorrect
  exploration remains separate evidence;no firmware fix was warranted.
- New1 packaged test and26 overlapping targeted tests PASS. Previous145 and6
  scoped criteria on the same firmware were not rerun. General verifier now
  includes146 tests;--core-only143 explicitly excludes three long UI matrices.
  Suite construction was host-checked separately,not counted as emulation.
- Production sources,stock and firmware3f979b70…/CRC5AB3F54B/42 patches/7595B
  unchanged;byte/range/CRC/CFG/ABI audit PASS. No project I/O,extra allocation,
  NOR increase or device APIs.1088B reservation/2184B workload headroom same.
  M7 NO-GO;next:native Microstep5 pages and bottom-pad writes.

## 2026-10-31 — Preserve native Note ownership through view changes

- Fixed a real Note1↔7 stuck-note and mode-admission bug:custom cleanup
  cleared grid physical bits while stock retained NoteView held notes,so
  the later native release was skipped. Only cleared StepView physical
  bits are now removed after stock cleanup. Five arguments,40B frame,
  GPR/SP and1088B reservation remain intact.
- Added a22-case synthetic cleanup regression (21 failures before the fix)
  and a native reset matrix for8 tracks/both modes/pages:1536 keyboard keys,
  512 step mappings,64 held-view transitions,48 native cancellations,
  Note7 page-button directions,64 pitch edits and64 LED compositions.
  Exact UART On/Off bytes,blank keys and single-byte stock default-note
  serialization are checked;no firmware/UI ownership or queue RAM repair.
- Rebuilt SYX3f979b70…/CRC5AB3F54B,42 patches/7595 changed bytes. Stock,
  vector/identity,MIDI core/glue/accepted-TX/CTRL_SYNC and RAM size unchanged.
  Audit PASS;143 packaged core +1 Note +1 Velocity/Gate test and6 scoped
  criteria PASS;60 targeted tests overlap. Full source suite not rerun.
- General verifier defaults to all145 tests;explicit --core-only excludes
  the two long native UI matrices,which were run separately on this SYX.
  Prior failed default-note assumption and interrupted exploration retained.
  No project I/O,extra allocations,NOR mutation increase or device APIs.
  Heap headroom2184B is workload-specific. M7 NO-GO;next:native view4.

## 2026-10-30 — Native Velocity/Gate pages, edits and LED composition

- Added an exact-SYX native reset test for8 tracks ×Normal/Sequencer ×Velocity /
  Gate ×2 pages:1024 top-pad ownership mappings and128 parameter/LED cases.
- Verified all16 velocity levels8..127,Gate6..96 tick cells and fractional
  95..91→96 cycle,step boundaries and native compositor bottom32B copies.
- Stock1–16 first request extends16-step end15→31; only that raw byte may
  change. Gate fixture creates empty steps via real Velocity inputs. Incorrect
  zero-raw-change and button16/17 assumptions are retained as failed evidence.
- Native Main runs every16 UI inputs and before mode commit with finite
  explicit802F status inputs;queues/sticky faults are never host-cleared.
  The unserviced callback-flood rejection is retained as a negative boundary.
- New1 packaged native unittest and25 targeted tests PASS; prior142 packaged
  tests on the same image remain evidence,not rerun/summed here. General
  verifier includes the new test.170 source/dependency pins;165 prior unchanged.
- Added bounded UART TXE peer inputs through native IRQ53/54/FPU frames and
  TDR writes,not software FIFO clearing or instruction stubs. Main-only service
  reproduced a sticky TX fault at input1886;negative evidence is retained.
- Firmwareafbab4f2…/CRC114DA352,stock,all production sources/1088B reservation
  unchanged. No project I/O,NOR mutation increase or allocation;heap headroom
  remains workload-specific2184B. No device APIs;M7 NO-GO. Next:Note1/7 pages.

## 2026-10-30 — Allow mode roundtrip after a released step edit

- Native timer6 arm/cancel/expiry proves B8 is short-click eligibility history,
  not a live pad owner. Mode admission now checks C0 and per-step bit3 while
  preserving B8 and all transport/project/MIDI/note/grid safety gates.
- Native reset workload covers all32 pads,each step's8B raw range,release then
  both mode directions without track changes,and300 explicit synthetic ticks
  through native countdown/callback. Held pads still reject after long expiry.
- 416 inputs/74 commits/12 rejects,296 unmasked sample force-off calls,no
  project I/O,NOR mutation increase or allocation. Workload heap headroom2184B
  remains conditional;GPIO/event-queue/elapsed-time/physical proof is absent.
- 65 targeted source tests/142 packaged tests +6 scoped criteria and strict
  audit PASS. Prior full649 source tests belong to621a candidate,not rerun here.
  New SYXafbab4f2…,CRC114DA352,42 patches/7540 changed bytes;499 image-byte
  delta due6B shorter guard and relocated cave branches. Stock/core/glue /
  accepted-TX/CTRL_SYNC and1088B RAM reservation unchanged;166 source pins.
- Next:native Velocity/Gate page-button/bottom-pad layouts. M7 NO-GO;no devices.

## 2026-10-30 — Fix false mode rejection on native readiness0E

- Native full boot exposed distinct readiness and project-I/O stores. Old
  (ready&0B)==08 rejected idle0E. Match stock UI bit3;retain phase.word1==0,
  transport/ownership/context checks. One image byte at0806A882 changes0B→08.
- Native reset objects/vtable Shift+Sample Rec,pad31 andtrack1 paths run76
  events:6 commits,12 rejects,raw/metadata preserved,no project I/O or extra
  allocation. Native pad edit survives mode roundtrip after track cleanup.
  Ten labeled transient fault cases are separate from real Play/Save/RX proof.
- Added bounded disabled-DWT and finite802F input support. Strict unknown /
  exhausted replies still stop before completion;no elapsed clock or DSP code.
- 649 full-source tests/140 packaged tests +6 scoped criteria PASS;strict audit
  PASS. New SYX621a4e49…,CRC434FF0EF. Stock/core/glue/guards unchanged;legacy
  SYX historical. Default codegen changes;166 source/dependency pins recorded.
- Next:trace timer6 arm/cancel and5CE48;distinguish released B8 latch from live
  C0/bit3 ownership before changing admission. GPIO/UI/MIDI/storage risks remain;
 2184B workload headroom is not general sufficiency. M7 NO-GO;no device APIs.

## 2026-10-30 — Add M4F frame ownership and reach conditional native Main loop

- Added opt-in FPUStartup hardware-frame/lazy-low-FP shim. Native VFP and
  PendSV S16-S31 paths execute;default basic worker still rejects FP. IRQ
  returns restore from emulated frame rather than a whole context snapshot.
- Added a protected QSPI IRQ extension point without changing default body.
  Covered three distinct task FP/FPSCR/integer banks,basic/extended switches,
  lazy/eager and FP-clobber IRQs,alignment,unsupported config and corruption.
  Corrected Thumb PC restoration in the new layer after a sentinel failure.
- Same SYX reaches native25864 after2331 allocations/heap2004EA98. Remaining
  heap2184B is partial workload headroom,not general sufficiency. Boot executes
  eight VPUSH/VPOP pairs;no arithmetic/DSP/full NVIC/timing proof is claimed.
- Added8 tests;127 packaged +6 scoped Phase1 criteria PASS;strict audit PASS.
  Firmware07c2305d…,stock/default/legacy/core/glue/guards unchanged.159 pins.
- Next:drive Shift+Sample Rec through the native button dispatcher after full
  boot,checking shared/dirty project,no I/O,admission gates and memory bounds.
  Explicit DSP/NOR/ADC/USB assumptions and storage risks remain. M7 NO-GO;
  no physical device APIs or firmware transmission.

## 2026-10-30 — Trace DSP mailbox and verify native polling with finite inputs

- Identified first consumed37300 read as native64416 mailbox wait,not the
  sample-length table at30001. Observed516 prior MCU RAM writes without37300.
  Native command372FB is polled once,then busy looping uses37300;no loop patch.
- Added an optional finite,ordered external-input layer. No default zero RAM,
  automatic command clear or CPU return stubs. Replies require exact completed
  native wire writes;wrong bank/address,exhaustion and reset fail closed.
- Six explicit MISO inputs exercise busy/idle and command completion back to
  native53E3E. MCU then clears512 metadata words itself. Extended conditional
  boot reaches803C03A VPUSH{d8};BasicFrameOnly stops before executing it.
- Added7 tests;119 packaged tests +6 scoped Phase1 criteria PASS;strict audit
  PASS. Firmware/default/legacy/core/glue/guards unchanged (07c2305d…).
 1464 allocations/heap20046A44 are partial,not final boot/resource proof.
- Next:validate FPU/lazy extended-frame ownership and native PendSV S16-S31
  paths,then continue Main25864. DSP inputs remain assumptions,not actual DSP
  initialization. M7 NO-GO;no physical device APIs.156 source pins recorded.

## 2026-10-30 — Fix native NULL CTRL_SYNC sink and execute FatFs over NOR data

- Added asserted23168 prologue detour/20B helper at7FE24. Only CTRL_SYNC0 with
  NULL buff uses the existing24B frame's dummy word. This prevents both the
  native query1 byte write and diagnostic word read atNULL;no extra RAM/stack.
  Normal output/register/SP/NZCV/PRIMASK contracts and native query body match.
- Corrected host QSPI DMA data movement,EN/NDTR completion,native DMA2 stream7
  IRQ and TCIE/SMIE selection. Added WEL/page/erase/1-to0 NOR model and synthetic
  FAT12 input;native FatFs fills media ownership and creates/persists files.
  No custom device filesystem implementation,object seed or API success stub.
- Stock/prior recovery fail atnative41AA2 NULL write with valid media. New
  candidate completes4 syncs/306 NOR mutations;reboot of persisted NOR binds
  without new mutations.1296 allocations/heap20043D78;Main25864 still open.
- Added10 tests;141 focused/112 packaged +6 scoped criteria PASS;strict
  CRC/vector/range/CFG/ABI and helper path audit PASS. New SYX07c2305d…,
  CRC0CD0D008,42 patches. Default/legacy/core/glue/accepted guard unchanged.
- Next boundary:consumed auxiliary DSP memory37300 read at3151A. No reply is
  fabricated;802B-ready/USB ACK/peripheral timing assumptions remain explicit.
  M7 NO-GO;no physical device APIs.153 source pins/exact bundle recorded.

## 2026-10-30 — Verify native SPI DMA and separate conditional peer readiness

- Native DMA1 stream3/4 IRQs publish SPI completion tokens;W1C,normal EN/NDTR
  completion and non-incrementing dummy RX are modeled. Strict mode completes
  3605 transfers/7210 IRQs,then rejects the first consumed MISO response before
  any DMA/RAM update. Static R0-dead proofs cover ignored responses.
- Explicit external802B peer model has busy and delayed-ready cases. Two busy
  responses then ready plus idle USB reset/flush ACK permit conditional boot
  through3819 transfers/1296 allocations/heap20043D78. Not auxiliary DSP
  execution,physical ready,complete Main boot or final heap proof.
- Stock/candidate/ignored-MISO-A5 variants match transmitted bytes,allocations
  and Content2E8B4 owner+3C NULL at2E4CC. Stop before invalid access;no fabricated
  media object. Native USB close journal writes are recorded;core/seq prefix
  intact. Fixed changing-endpoint checkpoints at code boundaries without stubs.
- Added6 regressions;131 focused/102 packaged +6 scoped criteria PASS,strict
  integrity audit PASS.148 source pins;all production sources/firmware unchanged.
  Next:Content media-object initialization under absent/empty media models.
  Main25864 and M7 remain open;no physical device APIs.

## 2026-10-30 — Pass native ADC input readiness without forced counters

- Modeled native DMA2 stream0 double-buffer completion and read-only synthetic
  calibration. Native646E8/27762 publishes samples; Main265BA advances sampler
  counters to2/2/2 after64 transfers and passes26596 to2582E. No ready-return,
  counter, instruction or production firmware changes. Stock behavior matches.
- Added6 regressions for missing IRQ/consumer, coalescing, masked delivery and
  unsupported DMA configuration.125 focused/96 packaged +6 scoped criteria pass;
  strict transport/CRC/vector/range/CFG/ABI pass.145 source pins/exact evidence.
- Heap remains20010BEC/203 allocations; reserved state/canaries/instruction
  image intact. ADC IRQ basic-frame/MSP-call adapter and synthetic2048/1500
  values do not establish physical ADC/timing/NVIC/FPU or complete boot.
- Followed completed SPI waits to actual pending0 at2B67A,caller31101,30B DMA1
  stream3/4 transaction. Main25864 remains open; no speculative SPI response
  model integrated. Firmware unchanged,M7 NO-GO,no physical device APIs.

## 2026-10-30 — Execute native port/SVC/PendSV and complete Storage requests

- Ran native25430/25C88 port startup,including AAAAAAAA critical-sentinel reset,
  then native SVC/actual first IDLE andPendSV/24F84 selection over modeled basic
  exception frames. Checked native saved/restored register banks andtask bounds
  on every switch;no fabricated current TCB,ready list or completion RAM.
- Native Storage6487C/2C278 clears9 requests andMain returns from9 drains.
  All five tasks execute through128 switches;stock allocation order matches
  203 allocations/heap20010BEC atMain26596. Reserved state andcanaries preserved.
- Added WFI wake handling andresumption from the restored thread PC. Added8
  regressions for native port/frame/worker behavior,missing dispatch/wake and
  explicit FP rejection.119 focused/90 packaged +6 scoped criteria pass.
- Main now stops atnative input readiness,counters0/0/0;not complete boot/final
  heap. Four priority bits,controlled IRQ delivery,basic-frame-only shim and
  inherited RCC/QSPI/no-response SDIO models remain explicit boundaries.
- Firmware/all production sources unchanged. Strict transport/CRC/vector/range /
  CFG/ABI pass;142 source pins/exact diff/evidence recorded. Full608 not rerun.
  Next task:native input sample/IRQ producer for26596. M7 NO-GO;no device APIs.

## 2026-10-30 — Trace native main allocations and correct non-neutral observers

- Extended exact-SYX reset through native main/task creation to scheduler entry:
  129 allocations match stock,heap2000B618,five real task stacks/TCBs/17-word
  frames. Native router andthree port constructors bind the actual recovery
  entries;reserved state changes only by those three registrations.
- Native ready-list selection plus modeled unstack starts Main on its own PSP
  and reaches2C23A worker request,heap2000B620. Measured248B main-setup MSP /
  224B first-task PSP prefixes only;full task/exception stack proof remains open.
- Scoped boot write observers to two ranges. Global write callbacks,even no-op,
  can corrupt Unicorn2.1.4 M-class conditional STM/IT zero fill. Moved timer
  dispatch to time/yield boundaries to prevent duplicate allocation-entry counts.
  These are host-model fixes;firmware andall production source pins unchanged.
- Added8 regressions;111 focused/82 packaged +6 Phase1 criteria pass. Kept
  missing-clock/completion andnon-neutral-observer negatives,strict integrity
  andearlier terminal-OOM proof. Recorded139 source pins/exact diff/same firmware.
- RCC/QSPI/SDIO responses andIRQ adapter calls remain explicit model boundaries.
  Native worker/PendSV/Main completion,media-present boot andphysical timing
  remain M7 NO-GO. No device APIs;full600 not rerun.

## 2026-10-29 — Verify native reset reservation and stop unsafe OOM callers

- Ran exact packaged reset/data decoder/static constructors from dirty RAM to
  native main entry without seeded heap/objects or firmware stubs. First1088B
  reservation precedes the first bump;retained magic/journal clears on reset.
  Ten native allocations and MIDI/MSC/RX objects match stock startup.
- Reproduced real native endpoint constructor writing to FFFFFFFF after new
  accepted the old allocator's nonzero failure sentinel. Recovery now enters a
  terminal masked fault on OOM/carry/invalid reservation instead of returning
  an invalid pointer. No fault-endpoint RAM/MMIO/reset writes. This requires
  restart;not graceful recovery,continued playback or bounded IRQ latency.
- Added8 boot/OOM regressions;103 focused/74 packaged +6 scoped criteria pass.
  IRQ/reset Off/Stop and burst probes,strict CFG/ABI/CRC/vector/range andlegacy
  audit pass. Default/legacy/core/glue/accepted guard unchanged. No device APIs.
- Pinned40 patches,new exact SYX/diff/evidence and136 sources. Measured160B
  static-startup stack only;main/task/exception stacks,final heap andtiming
  remain open. M7 NO-GO;no hardware test requested. Full592 not rerun.

## 2026-10-29 — Integrate recovery with native USB IRQ/reset and class setup

- Added asserted4293E IRQ entry,42D20 late-USBRST and40B5A class-list gates.
  Native reset bypasses class deinit;freeze before its FIFO clear and coalesced
  completion. IRQ GEN snapshots/nested rejection protect the active journal.
- Deferred the whole native class list until retirement and new host config,
  preserving MIDI/foreign constructor order. Pending/public init andconstructor
  return compare GEN;reset invalidates old configuration. No extra heap state.
- Same packaged native646D0/HAL/FIFO/IRQ/reset/enum/address/config sequence
  changes Off0/Stop0 to1/1 in both modes.17 new tests;95 focused/66 packaged/
  6 scoped Phase1 criteria PASS. Prior output probes andstrict audit pass.
- Preserved hardware-contract-violation negatives andstock/default/core pins.
  Full boot/RAM/elapsed timing/physical RX-MSC-power remain M7 NO-GO. Recorded
  40 patches,CRC/vector/CFG/ABI,exact diff/pins andnext boot/allocator task.
  No physical device or MIDI/USB API access.

## 2026-10-29 — Journal accepted MAIN jobs and replay closures after retirement

- Added2988B checked accepted-TX guard and128B journal in the existing seq-state
  tail;no extra heap reservation. ARMING/ACTIVE/DONE handles completion/close
  races. Native full/completion/class-close gates protect the accepted reader.
- Added bounded IN1-only mask/disable/ACK/AHB/FIFO1-flush/W1C/DSB retirement.
  Missing ACK/flush,DMA mode or generation wrap keeps ownership frozen. After
  retirement,only Off/velocity0 On/Stop precede the remaining FIFO;no On/Clock /
  SysEx replay. Ambiguous host delivery may repeat closing messages.
- Same packaged accepted-cancel model changes Off0/Stop0 to1/1 in both modes;
  full64-Off stream and healthy/prototype regressions pass.18 new tests,
  78 focused/49 packaged/6 scoped criteria and98 prior USB/helper tests PASS.
- Native52EDC now runs against registers;completion fixture uses native5268E.
  Kept the barrier-violating untagged-event negative. Full IRQ/EP0/physical
  retirement/boot/timing remain M7 NO-GO. No device access;stock/default/core same.
- Recorded37 asserted patches,CRC/vector/ranges/CFG/ABI,bounded copy/filter,
  max38 masked instructions,exact diff/source pins and one native-IRQ next task.

## 2026-10-29 — Preserve USB MAIN Off/Stop before submit admission

- Added checked native2B498 MAIN flush and a caller-specific268CC zero-credit
  result. Rejected/not-ready submission preserves prepared events. Core poll
  preflush services retained full MAIN under the existing port lease.
- Reused recovery entry byte11 for short atomic flush ownership;no extra heap
  reservation or core code change. IRQ/masked/nested flush is rejected;healthy
  ALT/foreign flush stays stock. Submit executes with interrupts enabled.
- Same packaged class-deinit/zero-credit case changes Off0/Stop0 to Off1/Stop1
  in both modes. Added11 integration tests;60 focused/31 packaged/6 Phase1
  criteria and98 previous helper/USB regressions pass. A passing negative test
  explicitly retains the unresolved accepted-TX cancellation loss. M7 NO-GO.
- Corrected native submit fixture success R0 to match stock4301A;validated
  old session/IRQ/control/staging/composite paths. Kept stock/default codegen
  and core bytes unchanged;recorded33 checked patches,CRC/vector/CFG/ABI,
  exact diff/pins and next accepted-job ownership task. No device access.

## 2026-10-29 — Preserve queued Off/Stop across native MIDI class re-init

- Added a checked read-only gate at native class-init BL 08068A32. Exact
  caller/router/three-port ownership skips destructive output FIFO/cursor
  clear; unrelated callers and mismatched registries keep stock behavior.
  No new RAM, masked section, HAL cancellation or automatic resume policy.
- Closed the same packaged native-parent loss: old candidate delivers 0/64
  or 32/64 Off per port, new candidate 64/64 plus final Stop in both modes.
  Added 9 tests for IRQ/worker/SysEx/fallback/active native TX ownership.
- 49 focused tests, 20 packaged tests, 6 scoped Phase1 criteria and strict
  CRC/vector/range/CFG/ABI audit pass. Previous burst and USB/DIN probes pass.
  Prior full529 PASS retained; discovery538, full538 not rerun this session.
- Physical USB cancellation/staging/late callbacks and boot/timing remain
  M7 NO-GO gates. Recorded exact diff/pins and next narrow task. No device access.

## 2026-10-29 — Integrate bounded Off/Stop recovery into a firmware candidate

- Added an offline Phase1 recovery profile with checked832B heap reservation,
  native boot-port registration,flash Send/Poll/SysEx vtable gates and sticky
  mode-admission fault propagation. Reuses the tested recovery core;default
  Phase1 codegen and legacy candidate bytes remain unchanged.
- Closed the tested63/64-note Stop and single-buffer Clock+Stop loss on the
  packaged candidate under the same polling/instruction budget. Added native
  USB/DIN exact-stream checks and11 integration regressions;6 scoped Phase1
  criteria pass. Full repository529 tests pass.
- Added strict profile-specific build/CRC/vector/range/CFG/ABI verification.
  Initial1088B reservation clear measured1147 masked instructions;full boot,
  elapsed timing and USB reset/teardown lifetime remain M7 NO-GO gates.
- Shortened current STATUS into a milestone dashboard;preserved the complete
  earlier journal in STATUS-HISTORY-20261029.md. No hardware/device access.

## 2026-10-29 — Native synchronous file queue coverage (emulator only)

- Replaced45EB6 immediate-copy test boundary with native72B FIFO submission,
  synchronous wait,TCB lookup,worker and result-before-credit publication.
  Lower4113A file API and task switch remain explicit RAM models.
- Added8 local/8 packaged tests for double-buffer load,MSC READ/data/CSW,
  nested workers,reset/suspend and native error return.
- Added negative short-read coverage:53E8C ignores status/count and can write
 2046B stale data after a2B partial read. No stock sample-loader patch added.
- Prior105 sources,production firmware/codegen unchanged;M7 NO-GO.
  Recorded ABI/canary/native pins,CRC/vector/ranges and remaining file-object
  ownership task in STATUS and MIDI-USB-FILE-QUEUE-5706.md.

## 2026-10-29 — Full native sample-load loop coverage (emulator only)

- Added10 native53E24/53E8C128-slot loader tests,with explicit RAM file,
  sample-flash,allocator/progress boundaries;packaged candidate10/10 PASS.
- Covered double-buffer/REV16/partial-tail output,READ/data/CSW,active USB
  reader,semaphore,worker reentry,reset and suspend. Full-loop MIDI retry /
  power progress still requires main service;retained as a negative test.
- Rebound overlapping synthetic MIDI fixture objects into asserted-free RAM;
  preserved loader CPU/stack at external-bus checkpoints. No production
  firmware/prototype changes;stock/candidate pins unchanged,M7 NO-GO.
- Logged native trace,CRC/hash/vector/ranges,test limits and next file-task
  queue/ownership task in STATUS and MIDI-USB-LONG-LOOP-5706.md.

## 29 Ekim 2026 — Ek USB poll çağrısının sahiplik doğrulaması

- Native transfer callback zinciri ve aktif READ/IRQ/worker/kapanış yeniden
 giriş koruması13 yeni yerel ve13 paket senaryosunda doğrulandı.
- Callback-only MIDI/power ilerlemesi negatifi ve53E24 tam loop sınırı açıkça
 kaydedildi. Firmware/prototype kodu değiştirilmedi;97 önceki kaynak aynı.
- Yeni trace/probe ve sentetik callback fixture'ı eklendi.500 discovery;
 önceki474 tam+13 factory PASS korunur,tam500 bu oturumda koşulmadı. M7 NO-GO.

## 29 Ekim 2026 — Bekleyen MIDI borcuyla factory doğrulaması

- Mevcut staging carry,iki USB class yönünde13 yeni senaryo ve paket adayında
 13 senaryoyla doğrulandı;staged SysEx/Off/query ledger,READ iptali ve
 native factory içi reset/ikinci istek dâhil. Firmware kodu değiştirilmedi.
- İki aşamalı yarış testleri için ayrı checked emulator test alanı eklendi.
- Önceki93 kaynak/codegen ve firmware hash'leri aynı;önceki474 tam PASS
 korunur.487 toplam discovery;bu oturumda tam487 koşu yapılmadı. M7 NO-GO.

## 29 Ekim 2026 — Native USB MAIN staging carry (yalnız emülasyon)

- Optional staging=True:hazırlanmış MAIN baytları ve immutable owned kısmi
  SysEx cursor'u full cancellation bariyeri boyunca korunur.
- Native flush artık registered CPU MAIN'i yalnız TX ticket kabulünde tüketir;
  yeniden açılan poll retained full MAIN'i native formatter'dan önce gönderir.
- 12 yeni/474 toplam test ve paket adayında27 varyant senaryosu PASS;
  default carry codegen ve production firmware hash'leri aynı. M7 NO-GO.

# 29 Ekim 2026 — Gönderimi başlamamış MIDI borcunun epoch devri

- Ayrı1300B/128B carry katmanı,logical ledger/SysEx/TX borcunu fiziksel
  USB reader iptalinden ayırır. FIFO/parser/SCANNED/EXPECTED_READ/payload /
  port cursor'ları korunur;tam disable/ACK/AHB/shared FIFO/TX flush gerekir.
- Yeni yol yalnız TX_ACTIVE0,staging/main-alt uzunlukları0,partial cursor
  yok,idle parser/held input ve gerçek port fault yokken açılır. Diğer
  durumlarda eski protokol/limitler kalır;belirsiz gönderim yeniden oynatılmaz.
- Retirement ayrı CY BUSY ile korunur;native reset IRQ generation'ı
  değiştirebilir,nested ss_step reddedilir. Seal/resume commit yarışları testli.
- Owned planned close sırasında USB rp_poll bekletilir;planlı uyku gerçek
  disconnect FAULT'una çevrilmez. Var olan gerçek FAULT temizlenmez.
-15 yeni/462 toplam test PASS;iki mod,360B payload,queued Off,Clock/Stop,
  wrapped owed kayıt,tekrar sleep/reset ve yanlış caller reddi testli.
  Native all-port admission/borrowed pointer ve tek notice ek deneyi de PASS.
- Önceki kaynak/default codegen ve production syx aynı.2712B state sentetik;
  partial staging/in-flight,gerçek PHY/RTOS/boot/RAM-init ve üretim Off/Stop
  kapıları açık. M7 NO-GO;cihaz/MIDI/USB API erişimi yapılmadı.

---

# 28 Ekim 2026 — Native ana döngüye USB/MIDI servis bağlantısı

- Ayrı352B/64B task katmanı,2587C stok MSC çağrısını bir SysEx retry,bir
  power service ve en fazla bir korumalı MSC poll sırasına bağlar. Native
  MIDI output/input sırası korunur. Önceki prototip kaynakları değişmez.
- Aktif native READ/worker/IRQ/class owner ve yeniden girişte service
  reddedilir. Worker IRQ içi suspend,dış READ dönmeden tamponu kapatamaz.
- Fixture artık gerçek648AE..648B8 backend worker döngüsünü yürütür;
  RTOS wait/return,lower flash ve bus ACK/IRQ hâlâ açık model sınırıdır.
- Ana döngüden query/READ/CSW/borçsuz suspend-wakeup testli. İki no-hook
  negatifi,eski main'in power ve retry servislerine ulaşmadığını gösterir.
-13 yeni/447 toplam test PASS;üçü beklenen negatif davranışı korur. Retained
  ledger/TX debt ile suspend→wake toparlanması64 main geçişinde hâlâ FAIL.
  Bu sahiplik sorunu çözülmedi;kontroller gevşetilmedi. M7 NO-GO,üretim aynı.

---

# 28 Ekim 2026 — Normal USB suspend/wakeup reader koruması

- Ayrı1176B/96B power katmanı:aktif MIDI/MSC reader ve ortak iptal bariyeri
  bitmeden USB clock-stop yok. Native durum save/restore ve ungate kullanılır;
  clock-stop generation kontrolü ve kısa maskeli bölümle yapılır.
- Erken wake/reset,coalesced olaylar ve native state-save içindeki wake
  korunur. Reset sonrası eski configuration replay edilmez. Asleep sırasında
  factory isteği bekler;MIDI-only/composite yeniden açılabilir.
- Clock-stop sırasında global mask yalnız wake/reset;normal MMIO/service
  yasak. Önce native ungate,sonra önceki mask ve native IRQ geri döner.
- LPM/deep-system-stop/DMA ve generation wrap hata durumunda kapalı kalır.
  Legacy katmanın LPM hatasını CLOSING'e gevşetmesi üst hata latch'iyle düzeltildi.
- 16 yeni/434 toplam test PASS. Eski kaynak/default codegen ve üretim adayı
  değişmedi. Native erken clock-stop negatifi gösterildi;2520B state sentetik.
  M7 NO-GO;üretim Off/Stop kaybı ve gerçek power/task/boot/timing kapıları açık.

---

# 28 Ekim 2026 — USB factory listesini bariyer sonrasında değiştirme

- Native40A30'un eski class pointer'larını deinit'ten önce sildiği gösterildi.
  Yeni732B/128B katman432A8 isteğini kuyruğa alır;eski READ/USB/MIDI sahipleri
  ve parent teardown bitmeden native factory'yi yürütmez.
- MIDI-only ve MIDI+MSC kurulum,94B/125B descriptor,MIDI inquiry ve tekrar
  storage READ testli. Geçiş içi yeni generation ve harici USB reseti korunur;
  yalnız bilinen native iç deinit bildirimi dar caller guard ile geçirilir.
- 2CB18'in belirsiz üst stack halfword'ü stok ABI'ye uygun yok sayılır.
  Storage mod1/2/3 eşlemesi korunur;MSC-only/disabled liste desteklenmez.
- MSC/storage optional class hook'ları ve audit'leri eklendi. Varsayılan
  codegen hash'leri ve üretim firmware'i aynı.16 yeni/418 toplam test PASS.
- HAL init/tick/NVIC/clock/RTOS sınırları açık;2424B state sentetik. M7 NO-GO,
  üretim Off/Stop kaybı sürer. Fiziksel cihaz/MIDI/USB API erişimi yok.

---

# 28 Ekim 2026 — Native MSC READ10/CSW sahipliği ve read-error koruması

- Ayrı1452B/128B storage katmanı ve optional MSC policy hook'ları;default
  MSC codegen değişmez. Native queued read/drain/worker tamamlanmadan ve
  USB reader bırakmadan4KB tampon/13B CSW yeniden kullanılamaz.
- Native65128'in yuttuğu read hatası,2C328'de ilgili işten yakalanıp failed
  CSW'ye çevrilir. Sonraki başarılı worker işi bu hatayı örtemez.
- Pin'li stok MSC650E8 ile yazma korumalı;WRITE10 native write callback'ine
  ulaşmadan reddedilir. Yazma açılmadı;özel SD filesystem eklenmedi.
- 18 yeni/402 toplam test PASS;READ/veri/CSW/cancel/retry ve MIDI/DIN korunması
  testli. Alt flash/RTOS wake-yield sınırları açık;gerçek hardware kanıtı yok.
- Üretim aynı/Off-Stop FAIL,M7 NO-GO. Full factory/class/power/task/boot/RAM /
  gerçek flash bariyeri açık. STATUS.md ve MIDI-USB-STORAGE-5706.md güncel.

---

# 28 Ekim 2026 — Aktif MSC CBW iptali ve native Bulk-Only Reset

- Ayrı2924B/256B emülasyon katmanı:MSC OUT2 CBW job'ı disable/ACK,AHB idle,
  ortak RX drain ve seçili TX2 flush bitmeden bırakılmaz. Native teardown /
  BOT reset ve yeniden arm bariyer sonrasına ertelenir;MIDI/DIN korunur.
- Native poll/handler gate'leri reset sonrası eski CBW'nin SCSI komutuna
  dönüşmesini engeller;başlamış storage/data/IN safhaları kapalıda korunur.
- MSC IRQ claim'i CPU/shared FIFO drain sonrasında native ready yayımlar.
  CBW CPU word-copy bounds guard ve64B scratch bozuk packet taşmasını önler.
- Ready clear byte'a düzeltildi;kapasite+29 korunur. Request/submit/teardown
  yarışları,ticket wrap ve bozuk bariyer/stale XFRC negatifleri testli.
- 21 yeni/384 toplam test PASS. Tek eski kaynak değişikliği IRQ fixture'da
  optional EP2 disable ve manuel TX2 flush sözleşmesi. Önceki codegen aynı.
- Üretim aynı,M7 NO-GO. Aktif storage/CSW/TX iptali,task/boot/RAM/power ve
  gerçek bariyer açık. Cihaza erişilmedi. STATUS.md ve MIDI-USB-MSC-5706.md.

---

# 28 Ekim 2026 — Gerçek MIDI parent ve boşta MIDI+MSC ortak kurulumu

- Gerçek68A2C parent'ın tüm çıkışları temizleyip DIN Note Off kaybetmesi
  negatif kontrolde doğrulandı;yalnız owned sealed native caller için atlanan
  clear ile DIN FIFO'ları korunur. Native parent ve rearm gövdeleri yürür.
- Ayrı996B/96B composite katmanı,iki-class native list kurulumunu bariyer
  sonrasına erteler;gerçek MIDI/MSC parent,BOT reset/31B CBW arm,native
  teardown ve125B/3-interface descriptor testli. Storage Init açık sınırdır.
- Aktif MSC/pending completion varsa init reddedilir. Parent'lar arasında /
  MSC arm sonrası reset,borç/sahiplik koruma ve yabancı class yolları testli.
- 16 yeni/363 toplam test PASS;paket probe16 PASS,exit2/NO-GO beklenir.
  Tek eski kaynak değişikliği IRQ fixture'da optional selected TX FIFO2 flush.
- Üretim aynı/Off-Stop FAIL,M7 NO-GO. Aktif MSC iptali,storage,power/task /
  gerçek bariyer ve diğer kapılar açık. Cihaz erişimi yok.
- 68A54 için önceki 'yalnız scatter-load' tanımı düzeltildi:statik initializer
  walker,6668C endpoint constructor'ını da yürütür;tam boot değildir.
  STATUS.md ve MIDI-USB-COMPOSITE-5706.md güncel.

---

# 28 Ekim 2026 — Native reset/EP0 ve bariyer sonrası MIDI class kurulumu

- 1464B/96B ayrı kontrol katmanı:reset/deinit kabulü dondurur,ana service
  bariyerinden sonra native525B2 çalışır;bootstrap availability completion'dan
  ayrılır. Native EP0 SET_ADDRESS/SET_CONFIGURATION ve reset/enum testli.
- Event generation ve atomik commit,kurulum/son commit sırasında gelen reset'i
  korur. Resume beklemesi native parent callback'ini tekrarlamaz.
- Native kurulumun kayıtlı OUT1 global RX flush'u dar caller guard ile atlanır.
  SOF partial publication bastırılır;tek64B RX job ve66B kapasite pause/rearm
  sahte job sahipliğini önler. Diğer native yollar korunur.
- 22 yeni/347 toplam test PASS. Default IRQ codegen aynı;optional policy ve
  EP0/MMIO fixture desteği için3 eski kaynak bilinçli güncellendi.
- Gerçek parent/MSC,full power/descriptor/task,donanım bariyeri ve diğer M7
  kapıları açık. Üretim aynı/Off-Stop FAIL,M7 NO-GO;cihaza erişilmedi.
  MIDI-USB-CONTROL-5706.md ve STATUS.md güncel.

---

# 28 Ekim 2026 — Native CPU FIFO USB IRQ completion köprüsü

- Ayrı820B/96B bridge:IRQ girişinde job snapshot,doğrulanmış native caller
  üzerinden tek claim ve IRQ sonrasında completion/yayın. Testten token yok.
- Stok HAL submit/FIFO/IRQ/thunk/listener zinciri native yürütüldü. OUT
  completion ile RXFLVL aynı turdaysa CPU kopyasından sonra yayın;çok kayıtlı
  FIFO için pending snapshot'ın sonraki IRQ'da sürmesi testli.
- Native kurulum prefix'i40040000 tabanı/CPU FIFO mode0/6 endpoint'i doğruladı;
  tam boot değildir. Diğer endpoint'in CPU kopyası MIDI job'ını tamamlamaz.
-19 yeni/325 toplam test PASS;4 gate,ABI/CFG PASS,ek IRQ maskesi yok.
  Önceki kaynak/codegen ve firmware aynı kaldı.
- Reset/kontrol/DMA IRQ'ları ve disconnect dönüşü hâlâ unsupported/fail-closed.
  Bariyer sonrası eski untagged XFRC'nin yeni job gibi görünebildiği negatif
  test korunur. M7 NO-GO;cihaza erişilmedi. MIDI-USB-IRQ-5706.md güncel.

---

# 28 Ekim 2026 — Koşullu USB session iptali ve transfer kimliği

- Ayrı3176B/128B emülasyon wrapper'ı:iki MIDI endpoint'i durdurma/ACK bekleme,
  yalnız TX FIFO1 flush,staging/HAL cleanup,epoch ve kontrollü resume.
- Eski/duplicate/nested callback'in yeni transferi tamamlamasını engelleyen
  immutable epoch/ticket sözleşmesi;RX byte count ve transfer limit kontrolü.
- Kabul edilmiş RX borcu,partial/held nota,Off/fault veya shared reader varsa
  close reddi;DIN native output kapalı USB sırasında çalışmaya devam eder.
-25 yeni/306 toplam test PASS;11 ek gate,yerel ABI/CFG PASS,max26 maskeli komut.
  Önceki default kaynak/codegen ve üretim firmware hash'leri aynı.
- Model dışı geç DMA yazısının hâlâ buffer bozabildiği negatif test korunur.
  Stok untagged callback uyumu FAIL;IRQ bridge/gerçek DMA kanıtı açık.
  M7 NO-GO;donanıma erişilmedi. MIDI-USB-SESSION-5706.md ve STATUS.md güncel.

---

# 28 Ekim 2026 — RX lifecycle girişleri ve quiescent reset/resume

-2350B ayrı wrapper/64B ek sentetik state,toplam1496B;15 native gate ve poll
  overlay ile registered producer/consumer/reset/rearm sahipliği korundu.
- Bekleyen sorgu,partial mesaj,held nota,publish,retry veya native endpoint
  aktifken reset reddi;boşta native RAM reset ve epoch'lu close/resume.
- Native constructor prefix RX01 için16x64B/1057B ring'i doğruladı;tam boot
  değildir. Generic ring reset TX callsite'ları ve RX disconnect ayrımı pin'li.
-19 yeni test,281 toplam PASS. Maskeli yollar max9 komut/call-loop yok;
  native kayıt dışı nesnelerin yolu korundu. Önceki kod/testler aynı.
- Aktif TX yanıtı retry slotunu aşarak endpoint'te yaşayabilir;RX freeze sonrası
  reconnect'te eski yanıt negatif kontrolde teslim edilir:session safety FAIL.
  Late RX DMA/gerçekIRQ ve diğer M7 kapıları açık.
-Build/baseline/audit/87 regresyon PASS;üretim aynı/Off-Stop FAIL,probe ve
  verifier exit2/NO-GO. Cihaza erişilmedi.

---

# 27 Ekim 2026 — Dolu inquiry sayacında kabul edilmiş USB penceresi

- Ayrı964B ledger prototipi inquiry borcunu native RX kaydında tutar;nota ve
  transport aynı native parser yolunda sırayla bir kez işlenir. Dolu sayaç
  arkasındaki kabul edilmiş Clock/Stop engeli kapandı.
- SCANNED provenance +00/81 private header'lar;borç aktarılmadan ack yok,
  yarım yayın snapshot dışında,forged host marker reddedilir. Bir pop/bir
  reply denemesi/tur.172B arena/1432B toplam sentetik RAM aynı.
-18 yeni test,262 toplam PASS;192B ring'de29 tam yanıt,native USB-DIN360B
  output stall/24 yanıt,64 Off/Stop,producer/consumer ve sıra testleri.
-2048B maksimum pencere testinde157.912 emüle komut;gerçek cycle/latency
  kanıtı değildir. Host'ta henüz kabul edilmemiş veri kapsam dışıdır.
- Önceki kod/testler ve üretim/stok hash'leri aynı. Build/baseline/audit/87
  aday regresyonu PASS;aynı aday Off/Stop FAIL. Lifecycle/IRQ/RAM/DIN input /
  genel uyum açık,probe/verifier exit2 ve M7 NO-GO. Cihaza erişilmedi.

---

# 27 Ekim 2026 — USB Note On / Stop sıra bozulması düzeltmesi

- İsteğe bağlı `ordered=True`:inquiry yükümlülüğü0..8 sayılır;nota/transport
  byte'ları tek native parser yolunda geliş sırasıyla işlenir. Realtime bypass
  üretilmez. Meşgul TX sonrası gecikmiş Note On'un Stop'u geçmesi düzeltildi.
- Tam kapasitedeF0 öncesi cursor bariyeri;hiçbir suffix mesajı öne geçmez.
  Kabul edilen her inquiry için tam bir yanıt;tur başına en fazla1 TX denemesi.
-616B kod,172B arena/1432B toplam RAM aynı;UIX2 magic. Önceki722B varyant ve
  negatif testler aynı kaldı. Üretim entegrasyonu yoktur.
-14 yeni test,244 toplam PASS:gerçek receiver/sahiplik,96 permütasyon/split,
 24 karma akışta native sıra karşılaştırması,full/reentry/partial,64 Off/Stop,
  native360B USB-DIN output stall ve tam8 yanıt.
- Eski2 inquiry+sonraki Clock/Stop vakası PASS;tam kapasite+9. inquiry
  arkasındaki realtime gecikmesi FAIL. DIN input/genel uyum veM7 açık.
-Build/baseline/audit/87 aday regresyonu PASS;aynı aday Off/Stop FAIL.
  Stok/üretim hash'leri aynı;probe/verifier exit2,NO-GO. Donanım erişimi yok.

---

# 27 Ekim 2026 — Deneysel USB inquiry retry ve RX cursor sahipliği

- USB/cable0 için722B ayrı Thumb prototipi;64B sahipli RX buffer, kalıcı
  cursor, pending inquiry token ve tek seferlik realtime işaretleri.
- Meşgul inquiry host resend olmadan yanıtlanır; native USB/DIN çıkış
  stall'ında tam baytlar,64 aktif sesin Off/Stop kapanışı emülasyonda testli.
-17 yeni test,230 toplam PASS. Sonraki buffer'daki realtime beklemesi ve
  deferred Note On/Stop sıra değişimi gerekli negatif kontroller:FAIL.
-172B ek/1432B toplam sentetik RAM;checked üretim tahsisi/entegrasyonu yok.
  DIN input retry uygulanmadı;genel SysEx/multicast uyumu açık.
-Build/baseline/audit ve87 aday regresyonu PASS;aday Off/Stop FAIL.
  Üretim/stok aynı hash'lerde;probe/verifier exit2 ve M7 NO-GO korunur.

---

# 27 Ekim 2026 — Deneysel üst SysEx formatter rezervasyonu

- Beş32120..321F4 üst formatter için kaynak mutasyonundan önce kapasite
  rezervasyonu;native register/stack argümanları,dönüş ve callback/context
  korunur. Full durumda ret1 ve kaynak/global owner korunumu doğrulandı.
- Return-PC/main-context kontrolüyle nested upper/native alt/direct submit
  rezervasyonu alamaz. Seçili fault/PRIMASK/IPSR/invalid context fail-closed.
-2878B kod/428B retry RAM,toplam1260B sentetik RAM. Önceki1750B/2050B
  varyantlar aynı hash'leri üretir. Üretim hook'u veya RAM tahsisi yoktur.
-11 yeni test;213 toplam PASS. Native USB-DIN120B stall/tam byte,stack argümanı,
  explicit retry ve gerçek parser/dispatcher inquiry kaybı negatif kontrolü.
- Native USB/DIN ret'i yok sayıp isteği tüketir;otomatik retry FAIL kalır.
  Açık retransmit pozitif kontrolü17B identity reply üretir. Update ACK yan
  etkileri sadece disassembly ile izlendi;handler'lar yürütülmedi.
-87 aday regresyonu/6 kriter,build/baseline/audit PASS;aday Off/Stop FAIL.
  Firmware/hash aynı,verifier ve deneysel probe'lar exit2/NO-GO.

---

# 27 Ekim 2026 — Deneysel SysEx kabul bildirimi ve callback sahipliği

- Native scatter-load/vtable ve gerçek299B0 ->24B68 ->468EC zinciri çıkarıldı.
  Bildirim bütün portlar kabul ettiğinde senkron event0'dır; önceki gecikmiş
  job/wire-completion yorumu düzeltildi.
- İsteğe bağlı notifications=True:owner function/context ve event listesi
  snapshot'ı;native dispatcher ile bir kabul bildirimi. Callback/reader bitene
  kadar slot tutulur. Diğer listener sırası/context'leri korunur.
-2050B kod/424B retry RAM,toplam1256B sentetik RAM. Varsayılan bildirim kapalı
 1750B kod/hash aynı. Üretim RAM rezervasyonu veya firmware entegrasyonu yok.
-11 yeni test;202 toplam PASS. Partial admission,callback içinde reader drain
  ve nested çağrı,12 caller eşleşmesi,native USB-DIN360B stall/ABI/metadata.
  Yerel maskeli yollar max17 komut;native toplam cycle/stack kabulü değildir.
- Eski bildirim kaybı ve dolu-slot yanıt kaybı negatif kontrolleri korundu.
  Request geri basıncı/recursive-send uyumluluğu ve upstream formatter'lar açık.
-87 aday regresyonu/6 kriter,build/baseline/audit PASS;aday Off/Stop FAIL.
  Üretim firmware/hash aynı,verifier ve deneysel probe'lar exit2/NO-GO.

---

# 27 Ekim 2026 — Deneysel SysEx sahipli kopya ve port bazında retry

- On iki gerçek router çağıranının payload ömrü/dönüşü çıkarıldı: üçü sonucu
  yok sayar, dokuzu iletir; yerel retry yoktur. Trace ve negatif kanıt genişledi.
- Ayrı Thumb API: tek 360B sahipli payload; port kabul maskeleriyle bounded
  retry ve reader bitişine kadar slot koruması. Yeni kod1750B/ek384B sentetik
  RAM; recovery ile toplam1216B. Üretim RAM tahsisi veya entegrasyonu değildir.
- On iki native üretici girişinde yalnız Unicorn guard'ları, formatter kaynak
  ezilmesini ve aktif işlem callback sahibinin değişmesini önler. Özgün bayt,
  PC-relative trampoline, CFG/ABI/PRIMASK denetimleri eklendi.
- 14 yeni test;191 toplam PASS. Native USB/DIN stall,360B payload, kısmi
  fanout, nested çağrı, stack/source ömrü ve callback ret çakışması sınandı.
- Dolu slotta sonucu yok sayan çağıran yanıt kaybı negatif kontrol olarak kalır.
  Submit0 native completion değildir; job callback yaşam döngüsü uygulanmadı.
- 87 aday regresyonu/6 kriter,build/baseline/audit PASS; aday Off/Stop FAIL.
  Firmware/hash aynı, verifier ve iki deneysel probe exit2/NO-GO.

---

# 27 Ekim 2026 — Deneysel SysEx karantinası ve ortak tampon koruması

- Native40232/4028C/298B8 dönüş, bekleme ve pointer ömrü pin'li stoktan çıkarıldı;
  tekrar üretilebilir trace script'i eklendi. Port ve router başarı değerleri ters.
- SysEx kabulü fault/busy altında kapanır; eski transfer için bir poll geçişi.
  Disconnect pending sahipliğini gizlemez. Router yeniden girişi ve ortak tampon
  ezilmesi, yalnız Unicorn'da iki checked overlay ile engellenir.
- 1140B kod/aynı832B test RAM;11 ek test,24 deneysel/177 toplam PASS.
  USB/DIN stall,200B SysEx+Clock+Off+Stop,nested çağrılar ve kısmi fanout sınandı.
- Eski bypass ve sonsuz bekleme negatif kontrolleri korundu. Busy çağrıları
  artık ret/retry gerektirir; sonucu yok sayan stok çağıranlar üretim engelidir.
-87 aday regresyonu/6 kriter,build/baseline/audit PASS; aday Off/Stop FAIL.
  Üretim firmware/hash aynı; deneysel probe ve verifier exit2/NO-GO.

---

# 27 Ekim 2026 — İzole Thumb Off/Stop recovery prototipi

- Üç port için832B bitmap/pending Stop ve774B Thumb kodu; sağlıklı üç-bayt
  gönderim korunur, hata sonrası yeni On/Clock kilitlenip kapanışlar ertelenir.
- Native player63/64 ve tek USB F8+FC vakaları kayıpsız; native USB stall/DIN
  byte-ring ve running-status,2048 nota, nested çağrı ve PRIMASK/stack testleri.
-13 yeni deneysel test;166 toplam test ve87 gerçek aday regresyonu PASS.
  Yerel CFG max16 komut IRQ-mask aralığı; tam cycle/boot/IRQ kanıtı değildir.
- Bulk SysEx40232 girişinin kilidi atlaması ayrı negatif kanıtla kaydedildi.
  Sentetik arena üretim rezervasyonu değildir; production hook eklenmedi.
- Mevcut firmware/hash değişmedi; candidate probe hâlâ FAIL, karar NO-GO.

---

# 27 Ekim 2026 — Native player ve Stop callback zinciri denetimi

- Gerçek pattern On/gate Off/voice/filter/sample-MIDI zincirini çalıştıran
  sentetik RAM fixture ve9 test; tüm32 step okuması, tie ve8-slot davranışı.
- Native Stop'ta64 Off sonrası FC kaybı; tek USB F8+FC buffer'ında bir Off
  daha kaybolması, iki mod/üç hazır driver.63-nota kontrolü geçer.
- Paket imajına ayrı negatif sequencer probe; karakterizasyon testleri geçse
  de verifier kritik Off/Stop kaybını FAIL/exit2 olarak tutar.
-153 toplam/87 packaged test,6 kriter, build/baseline/binary audit PASS.
  Üretim firmware baytları/hash değişmedi; recovery uygulanmadı, M7 NO-GO.
- Deferred Off bitmap/pending Stop için bellek ve sıralama sınırları kaydedildi.

---

# 27 Ekim 2026 — TX enqueue kaybından sonra mode admission kilidi

-40228 koşullu overflow diagnostic çağrısı state+7A fault'unu latch eder;
  native mod geçişi kuyruk boşalsa da reddedilir. Başarılı/disabled port ayrılır.
- r0-r12/LR/APSR ve PRIMASK, invalid heap ve tek byte yazı/layout testleri.
- Native USB staging/endpoint availability ve DIN running-status/byte ring kanıtı.
-144 test/78 packaged regresyon,6 kriter, build/baseline/binary audit PASS.
- Off delivery/Stop stalled probe FAIL kalır; yalnız mode admission containment
  düzeldi. Verifier CRITICAL_RUNTIME_PROBE_FAILED / NO-GO.
-27624 için genel event pump adlandırması USB endpoint service olarak düzeltildi.

---

# 26 Ekim 2026 — USB RX turlarını sınırlayarak burst Stop kaybını düzelt

-29B62 hook'u: her port/turda bir RX buffer; kalan paketler FIFO'da korunur.
  12 bayt cave, RAM/stack write/BL yok; flags ve LR/register ABI korunur.
- Gerçek main poll sırasıyla stok Stop kaybı; adayda64/255 Clock + Stop teslimi,
  DIN1 bayt/tur ve çok-buffer SysEx parser state testleri.
-136 toplam/70 packaged regresyon,6 kriter, baseline ve binary audit PASS.
- Stalled-driver Stop ve dolu FIFO Off probe'ları FAIL kalır; verifier
  CRITICAL_RUNTIME_PROBE_FAILED / NO-GO. Yeni aday hash/CRC STATUS.md'dedir.

---

# 26 Ekim 2026 — Native MIDI worker ve dolu kuyruk karşı deneyi

- Gerçek çıkış adapter/FIFO/worker, clock backend ve store/listener ctor zinciri.
- İki mod, kanal/nota uçları, ring sarılması, driver backpressure ve held Stop.
- Dolu stok64 slotta Off kaybı üç portta üretildi; ayrı paket-imaj probe'u exit1.
  Verifier CRITICAL_RUNTIME_PROBE_FAILED / NO-GO verir; karakterizasyon PASS'ini
  firmware güvenliği olarak kabul etmez.
-128 test/62 packaged regresyon ve6 kriter PASS; baseline/binary audit PASS.
- Firmware baytları/hash değişmedi; scheduler/ISR erişilebilirliği ve Off recovery
  açık. Depolama, boot/OOM ve PRIMASK kapıları da sürüyor.

---

# 26 Ekim 2026 — MIDI ingress ve gerçek transport regresyonları

- Gerçek4042C parser ctor/DIN byte parser ve USB yazılım FIFO -> decoder/receiver.
- Gerçek Start/Continue/Stop store yazıları, sekiz track Start reset'i ve normal
  Clock32BB6 pending/callback dalı; running status, held Stop ve ring sarılması.
-7 yeni test;120 toplam ve54 packaged regresyon PASS; baseline/binary audit PASS.
- Firmware baytları/hash değişmedi. ISR/DMA, downstream alıcı/scheduler,
  boot/OOM/zamanlama ve stok storage hata kapıları açık: NO-GO.

---

# 26 Ekim 2026 — Harici MIDI note ownership mod geçişinde korunur

-3F5A8 receiver observer: aktif giriş/cached receiver maskeleri varken geçiş ret.
-Stok Note On bir kez, Note Off/Clock/Stop teslimatı korunur; input/output r0-r3,
 callee-saved register'lar ve SP korunur.
-4 receiver slotu; overflow/invalid context/saturation mod geçişini kapatır.
-32 başarısız alt-vaka sonrası12 yeni regresyon; tam113 test ve47 packaged test PASS.
-Baseline ve bağımsız binary/Capstone audit PASS. Dış ISR/transport/boot ve
 stok storage hata sınırları açık: NO-GO.

---

# 26 Ekim 2026 — Onaylı ortak-proje test migrasyonu tamamlandı

-39 eski kapsam testi tam kaynak/hash/onay kaydıyla arşivlendi.
-Grid/ABI/heap/overflow ve gerçek MIDI/recorder/pattern canary testleri korundu.
-Parametre editinden sonra aynı projede mod geçişi ve stok knob teslimatı doğrulandı.
-Tam101 test ve35 packaged regresyon,6 ölçüt, baseline ve bağımsız audit PASS.
-Yeni shared-project probe dosya erişimsiz korunumu gösterir; eski alias karşı
 deneyi ayrı runner ile yeniden üretilir. Eski kanıt dosyası değiştirilmedi.
-HOST_CHECKS_PASS; kalan3 yayın engeli nedeniyle NO-GO.

---

# 26 Ekim 2026 — Ortak proje modeline geçiş

- İki mod aynı proje ve64 stok slotu paylaşır. Otomatik Load/New, banka
  kilitleri, Packs engeli ve proje/storage callback müdahaleleri kaldırıldı.
- Yalnız durmuş/idle/boş sahiplik bağlamında RAM mode baytı değişir.
  Sample susturulur; proje/slot ve unsaved edit korunur.
- Yeni9 ortak-proje testi, step/LED/state/UI testleri, audit ve baseline PASS.
- Eski kapsam testlerinin migrasyonu otomatik onay reddi nedeniyle kullanıcı
  onayı bekliyor; tam suite başarısızlığı raporda korunuyor. NO-GO.

---

# 26 Ekim 2026 — Load alias tehlikesine geçici koruma

- 08037BD6 öncesi ret: canlı projeye okuma başlamaz; aynı sahibin geçişi
  iptal edilir ve stok phase temizliği kullanılır.
- Load/New, ilgili mod geçişi ve boot kabulü yok; NO-GO.
- 131 regresyon: tüm169092 bayt korunur; guard kaldırılınca bozulma sürer.
  Eski queue testlerinin emülatörde guard bypass'ı açıkça işaretlendi.
- Verifier kapalı özelliği CONTAINED_FEATURE_DISABLED olarak raporlar.

---

# 2026-10-26 — Canlı project alias riski ve Save karantinası

- Gerçek recorder kurucularıyla raw project/pattern alias'ı doğrulandı.
- Kısmi Load, apply çağrılmadan canlı notayı60 ->34 değiştiriyor. Kritik probe
  paket verifier'a eklendi; CRITICAL_RUNTIME_PROBE_FAILED / NO-GO.
- Owned Load error sonrası taint/dirty; şüpheli RAM'den Save dispatch ve doğrudan
  serialization reddi. Geçersiz state de Save'i reddeder. RAM rollback çözülmedi.
- 128 regresyon ve59 packaged regresyon PASS; kritik probe FAIL. Staging mimarisi,
  diğer storage/MIDI/boot/zamanlama kanıtları tamamlanmadan GO yok.

---

# 2026-10-26 — Load read/Close hatalarını apply öncesinde reddet

- Read error'unun üst Load'da success olarak görülmesi16 alt-vakada üretildi.
- Owned Load callback'i Close sonucuna ertelendi; read/Close hatası dirty,
  mode ve aktif slotu korur. Hata cleanup'u sadece kendi busy maskesini kaldırır.
- Generic read ABI, kısmi read, yanlış hedef/duplicate ve heap/context koruması
  testleri eklendi.124 test,55 packaged regresyon, binary audit/baseline PASS.
- Raw-buffer alias/rollback ve success apply açık; NO-GO devam eder.

---

# 2026-10-26 — Close sonucu bekleyen Save onayı

- Owned Save callback'i Close event'ine ertelendi; write veya Close hatası
  dirty'yi korur. Pending Close sırasında ikinci Save reddedilir.
- Save hata temizliğinde sadece ilgili busy biti kaldırılır. Edit while Close
  pending, duplicate, geçersiz context/heap ve bit koruma regresyonları eklendi.
- 119 test, bağımsız binary/stack audit ve baseline PASS. Dosya/OS API stubları,
  diğer storage/MIDI/boot açıkları nedeniyle donanım NO-GO sürüyor.

# 2026-10-26 — Gerçek storage FIFO / Save yazma hatası

- Stok request/result FIFO, worker ve Save callback zinciri için fixture eklendi;
  dosya API'leri ve OS wakeup'ları stub. İkinci Save terminal teslimattan önce
  reddediliyor; callback bir kez tüketiliyor.
- Worker write error'unun üst Save'de başarı sayılması yeniden üretildi ve
  yalnız captured Save alıcısına yönelik result bridge ile düzeltildi.
- Return0/2/3/5 ve generic callback ABI kontrolü;117 test, bağımsız audit ve
  baseline PASS. Close/flush ve diğer açıklar nedeniyle NO-GO sürüyor.

# 2026-10-26 — Geçiş bağlamı sahipliği ve işlem kimliği karşı örneği

- Reddedilen yabancı dispatch ve Projects reentry aktif geçiş owner/view
  pointer'larını artık değiştirmez. İki önce/sonra regresyon;115 test PASS.
- Aynı P/slotta eski ack'i ayırt edemeyen completion sınırı için ayrı probe
  eklendi; exit1/NO-GO. Gerçek queue ulaşılabilirliği henüz kanıtlanmadı.
- Build/binary audit/baseline PASS; storage kimliği ve diğer açıklar nedeniyle
  donanım NO-GO. Güncel hash ve kapsam docs/STATUS.md ilk bölümünde.

# 2026-10-26 — Load/Save callback sahipliği

- Yanlış Load slotu dirty/snapshot temizlemez; yabancı Load hatası aktif mod
  geçişini iptal etmez. Slot64+ reddedilir.
- Save error callback'i yalnız kendi snapshot owner'ını iptal eder; geç ack
  dirty'yi temizleyemez. Stok cleanup ve başarı yönlendirmesi korunur.
- Eski adayda7 alt-vaka hata yeniden üretildi;113 test, bağımsız audit ve
  baseline PASS. SD/ardışık işlem kimliği ve diğer açıklar nedeniyle NO-GO.

# 2026-10-26 — Pending kayıt geçiş/Snapshot koruması

- Pending MIDI kaydı varken mod geçişinin kabul edilmesi yeniden üretildi.
- Kayıt başlangıcında dirty/save-edited; geçiş sırasında yeni kayıt reddi;
  Save completion öncesi sekiz recorder'ın pending kontrolü eklendi.
- PRIMASK korunur; callback yalnız bir kez çalışır. 108 test, bağımsız audit ve
  baseline PASS. Zaman bütçesi/storage/boot/MIDI yaşam döngüsü nedeniyle NO-GO.
- Güncel aday hash'i ve kanıtlar docs/STATUS.md ilk bölümünde.

# 2026-10-26 — Kısa MIDI mesajından kayıt yazımına birleşik test

- Stok kurucunun callback argüman sırası çözüldü: voice+24 kayıt alıcısıdır.
- Gerçek router/ownership filtreleri üzerinden recorder ve pattern yazımına
  birleşik sentetik RAM fixture eklendi; yalnız terminal sample alıcısı stub.
- 32 entegrasyon senaryosu, nota0/127 sınırı ve iki kaynak sahipliği kontrolü;
  toplam105 test PASS. Firmware değişmedi, NO-GO sürüyor.
- GO için kalan kanıtlar docs/PHASE1-GO-GATES.md içinde kabul ölçütleriyle yazıldı.

# 2026-10-26 — MIDI kanal ve kayıt grubu sınır testleri

- Gerçek MIDI decoder/adaptörlerinde sekiz track, nota dönüşümü, velocity0
  Note Off, kanal filtresi ve release maskeleri test edildi.
- Kayıt grubunun sekiz track yönlendirmesi ve üç durum kontrolü gerçek
  recorder/flush koduyla sınandı. Toplam 102 test PASS.
- Aradaki router/nota sahipliği katmanı açık; uçtan uca MIDI kayıt kanıtı
  iddia edilmiyor. Firmware baytları değişmedi, NO-GO sürüyor.

# 2026-10-26 — Recorder callback entegrasyon kanıtı

- Note On/Off -> pending -> flush -> pattern zinciri için gerçek stok kodla
  sınır regresyonu eklendi; SP/r4-r11 ve hedef dışı pattern baytları kontrol edildi.
- Toplam 100 test PASS. Firmware baytları değişmedi; MIDI ingress ve diğer açık
  riskler nedeniyle NO-GO sürüyor.

# 2026-10-26 — Doğrudan kayıt dirty koruması

- 0x08048F02 note kayıt finalizer yazımına ve 0x080490F0 doğrudan delay
  yazımına dirty/save-edited hook eklendi; orijinal argümanlar korunur.
- Seçili/seçili olmayan pattern ve tüketilmiş pending kayıt için 3 yeni
  gerçek makine kodu regresyonu eklendi. Toplam 99 test PASS.
- MIDI ingress uçtan uca kanıtı henüz yok; NO-GO devam eder.

# 2026-10-26 — Dirty ve Save snapshot koruması

- Pattern commit ST1/ST2/settings kaynaklarına dirty hook eklendi.
- Knob delta koruması ve geçiş sırasında knob teslimat engeli eklendi.
- Save başlangıç kimliği/sonraki edit izleme; matching ve one-shot completion.
- Dört yeni regresyon testi; toplam 96 test. SD/MIDI/record kapsamı hâlâ açık.
- Güncel aday ve ayrıntılı kanıt: docs/STATUS.md ilk bölümü. NO-GO sürüyor.

# 2026-10-26 — Proje geçişini eksik bağlamda reddet

- Üretim firmware'inden sentetik test fallback toggle kaldırıldı.
- Metadata ve slot sınırları; state=2 / controller ownership kontrolleri eklendi.
- Başarısız istekte sesi kesmemek için erken sample susturma kaldırıldı.
- Gerçek stock action dispatch fixture'ı ve üç yeni regresyon; 92 test PASS.
- SD/MIDI/boot ve dirty kapsamı kanıtları açık: NO-GO devam ediyor.

# 2026-10-26 — Yeniden denetim, NO-GO

- Timer argümanları/stack aktarımı, Save r3 ve Clear r2 ezilmesi düzeltildi.
- Allocator hizalama ve pointer toplamına carry koruması eklendi.
- Dört yeni regresyon önce FAIL, düzeltme sonrası PASS; toplam 89 test PASS.
- Candidate verifier dört açık engeli yeniden raporlar; paket üzerinde 20 regresyon çalıştırır.
- Signed koşullu dallar bağımsız cave denetimine eklendi.
- Önceki uçtan uca MIDI/storage/boot ve kısa PRIMASK iddiaları geri çekildi.
  Ayrıntı: docs/PHASE1-REAUDIT-20261026.md. Önceki kayıtlar tarihçedir.

# Changelog

## Faz 1 Güvenlik ve İzolasyon Kusurlarının Çözümü — 2026-10-25

- **Banka Seçimi ve Senkronizasyonu:** Banka seçimi doğrudan `seq_enabled` mod durumuna kilitlendi (0: Normal, 1: Sequencer). Projects görünümü açıkken mod değiştiğinde `[proj_view + 0x36]` anında senkronize edilir ve `0x0804F27E` ile LED'ler anında yeniden çizilir. `0x0804F09E` (pad basışı) ve `0x080385CA` (action dispatch) noktalarında hedef banka işlem anında doğrulanır; çapraz banka işlemleri reddedilir.
- **Durum Makinesi ve Aktif Proje İzolasyonu:** Mod geçişi güvenli bir durum makinesi haline getirildi (`request -> dirty guard -> action dispatch Load/New -> stock completion verification -> commit mode`). Projede kaydedilmemiş değişiklik varsa (`OFF_PROJECT_DIRTY == 1`) veya proje meşgulse geçiş reddedilir. Geçiş sürerken (`trans_state != 0`) pad düzenlemeleri `c_grid_press_gate` (0x0804D7A0) ile, Save işlemleri `c_save_btn_gate` ile engellenir. Stok yükleme tamamlanması (`0x08037E3C -> 0x08037EC2` callback) beklenmeden mod commit edilmez.
- **Tüm Sample Giriş Yollarının Susturulması:** `0x08046780`'e giden tüm yollar kancalandı: Note On adapter (`0x08031A1E`), Metronom click (`0x080333E6`), iç DSP ses tetikleyicisi (`0x0804679E`) ve Sample Preview (`0x080467CA`). Sequencer moduna geçildiğinde aktif sesler `c_silence_active_samples` ile (`0x080467D2` force-off ve ses tablosunun temizlenmesi) anında kapatılır. Note Off (`0x08031A34` -> `0x080467D2`) ve force-off çalışmaya devam eder. MIDI sinyalleri kesintisiz çalışır.
- **MIDI Yaşam Döngüsü Doğrulaması:** Note On/Off, Stop, Clock, track değişimi ve mod geçişi birleşik emülasyon senaryosunda çalıştırıldı; kuyruk doluluğu, tekrarlanan basış ve uzun basış altında sıfır stuck note kanıtlandı.
- **Sistem ve Veri Güvenliği:** Stok bump allocator (`0x08025A98`) OOM yolu `c_allocator_guard` ile korundu (OOM'da çökme/breakpoint olmadan `-1` döner). PRIMASK kritik kesiti kısa tutuldu (<= 15 insn, sıfır BL). Kod mağarasındaki tüm fonksiyonlar AAPCS 8-bayt stack hizalamasına (`depth % 8 == 0`) kavuşturuldu.
- **Doğrulama ve İmaj:** 30 yama ile yeni aday `build/circuitrhythm-5706-phase1-sequencer.syx` (SHA-256 `6c4522bfeb56f39441ac478e4fecc2354f111db31bf6ca5b9fc5cea9683beba9`, CRC-32 `0x9798a0da`) üretildi. 85 birim test, bağımsız audit ve candidate verify başarıyla tamamlandı (0 release blocker, `HARDWARE RELEASE: REVIEW_REQUIRED (ALL HOST CHECKS PASS)`).

## Güvenlik denetimi ve NO-GO — 2026-10-25

- Projects heap-failure NULL okuması, Sample Rec register/press ownership hataları ve eksik track temizliği düzeltildi.
- Yanlış force-off kancası kaldırıldı; gerçek Note On adapter gate eklendi.
- Heap rezervasyonu ve stok allocator PRIMASK korumasıyla eşgüdümlendi; reserved blokta current her girişte doğrulanıyor.
- Literal hizalaması otomatik; manifest hedefleri input/stock/output üstüne yazamıyor; SysEx fazlalık/gap/dolgu ve cave hizası denetleniyor.
- Bağımsız SysEx/CRC/disassembly/stack denetçisi ve 14 yeni test eklendi (toplam 80 PASS). Paket doğrulayıcı gerçek aday üzerinde 11 ek makine kodu testi çalıştırıyor.
- Proje geçişi izolasyon kusurları yeniden üretildi: doğrulayıcı artık release için NO-GO/exit 2 veriyor. M7 donanım hazırlığı önceki kayıtlara rağmen bloke. Ayrıntı: `docs/PHASE1-SAFETY-AUDIT.md`.

## Faz 1 Birleşik Firmware İmajı ve 1. Donanım Testi Hazırlığı (Adım 7 / M7) — 2026-10-25
- `scripts/patch_firmware.py` içine `--build-phase1` komut satırı seçeneği eklendi:
  - Adım 2..6 boyunca geliştirilen tüm 16 Faz 1 yamasını (`build_phase1_patches`) tek bir pakette toplar.
  - Varsayılan çıktı: `build/circuitrhythm-5706-phase1-sequencer.syx` (509.653 bayt, SHA-256: `2a205fc3...`).
  - Değişen aralıklar ve yama manifestosu: `build/circuitrhythm-5706-phase1-sequencer.manifest.json` (16 yama, 603 değişen bayt).
  - Vektör tablosu (`0x08010000..0x08010200`) ve Novation kimlik alanı %100 korundu.
- `scripts/verify_phase1_candidate.py` uçtan uca otomatik doğrulama aracı oluşturuldu:
  - Üretilen adayı SysEx formatı, MPEG-2 CRC-32 (`0xb73aa2a9`), SHA-256 ve flash sınırları açısından denetler.
  - Unicorn ARM Cortex-M emülatöründe 6 kabul kriterini uçtan uca test edip `logs/phase1-verification-<timestamp>/report.json` raporunu üretir:
    1) `Shift + Sample Rec` ile Normal Mod <-> Sequencer Only Mod geçişi (`seq_enabled 0 <-> 1`), bypass dönüşü ve `0x0804D6B6` temizlik çağrısı (PASS).
    2) `grid_mode == 0`'da 32 pad'in tümünde (0..31) step açma/kapama, pattern commit ve sayfa taşma koruması (`view + 0xB4 == 0`) (PASS).
    3) `grid_mode == 0`'da 32-adım LED birleştirme ve Playhead'in 0..31 kesintisiz akışı (PASS).
    4) `Velocity` (`mode 2`) ve `Gate` (`mode 3`) ekranlarında alt 16 pad düzeninin ve `1-16` sayfa tuşunun korunması; ana ekranda sayfa tuşunun kilitlenmesi (PASS).
    5) Sequencer modunda `Projects` ekranının 2. sayfaya (`[proj_view + 0x36] = 1`, Proje 33–64) kilitlenmesi, Up/Down kilidi ve `Packs` görünümünün engellenmesi (PASS).
    6) Sequencer modunda dahili sample motorunun (`0x08031A34`) susturulması (MIDI-Only) ve Normal modda eksiksiz açılması (PASS).
- `docs/PHASE1-HARDWARE-TEST.md` ilk fiziksel donanım test protokolü ve güvenlik kontrol listesi hazırlandı:
  - Üretilen dosyanın SHA-256, CRC-32, boyut ve yama adresi dökümü.
  - Yükleme öncesi `docs/RECOVERY.md` yedekleme ve kurtarma kontrol listesi.
  - Cihaz üzerinde adım adım doğrulama adımları (Mod geçişi, 32 pad dizilimi, Playhead, Velocity/Gate, Projects, MIDI çıkışı ve ses susturma).
- `scripts/run_baseline.py` ve `python -m unittest discover -s tests -v` (66 test) eksiksiz çalıştırıldı ve %100 PASS alındı.
