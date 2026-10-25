# Project instructions for Codex

## Read first
Read START-HERE.md, docs/SCOPE.md, docs/STATUS.md, docs/ROADMAP.md, docs/RECOVERY.md and docs/UI-TRACE-5706.md. Current scope overrides historical reports. Communicate with the user in Turkish, plainly and concisely.

## Goal and phase
Build an additional **32-Step MIDI Sequencer Only** mode for Novation Circuit Rhythm stock build 5706:
- **Phase 1 (Current Target - Consolidated First Hardware Test):**
  1. Display and edit all **32 steps simultaneously** across the 32 pads when in the main Step/Sample view (`grid_mode == 0`), with continuous playhead flow across steps 1–32.
  2. Lock the `1–16` page offset to `0` in `grid_mode == 0` (preventing `+16` overflow), while **fully preserving** the `1–16` page button (`1–16 / 17–32` toggle) and bottom-half pad layouts in `Note` (`mode 1/7`), `Velocity` (`mode 2`), `Gate` (`mode 3`), `Pattern Settings` (`mode 4`), `Microstep` (`mode 5`), and `Probability` (`mode 6`).
  3. Clean up held step ownership masks (`view + 0xB8`, `view + 0xC0`, `view + 0x74` bit 3) on track or view mode changes.
  4. Provide **32 independent Sequencer Projects** using the stock Projects View's second page (`[proj_view + 0x36] = 1`, slots `32..63`) in Sequencer Mode and locking Normal Mode to the first page (`[proj_view + 0x36] = 0`, slots `0..31`), while disabling Up/Down project page switching and disabling the `Packs` view (`Shift + Projects`, `0x0803DB54`) in Sequencer Mode. Stock Load, New (empty pad), Save, Duplicate, and Clear (Delete) work natively.
  5. Toggle between Normal Mode and Sequencer Only Mode via a safe button combination, muting internal sample playback in Sequencer Mode while keeping MIDI Note On/Off and Clock active.
- **Phase 2 (Later):** Root Note + Macro Knob Chord/Triad generator (Mono, 5th, Maj, Min, Sus2/4, 7ths with Note Off tracking) and `1–16` + Pad length shortcut.
- **Permanently Out of Scope:** 64/128 steps, independent multi-note polyphony, Elektron extensions, custom synth/DSP engines, or custom SD filesystem code.

## Work authorization
Proceed autonomously with local read-only analysis, source edits, host tests, documentation and build preparation within this project. Do not ask permission for each reversible edit. This handoff does not authorize sending firmware or other modifying commands to the physical device. Prepare the exact build, diff, hashes, test instructions and recovery plan before asking for a specific hardware test. Never access any MIDI/USB device without explicit user authorization.

## Firmware boundaries
- Keep `stock/circuitrhythm-firmware-5706.syx` unchanged. Never overwrite or replace its bytes.
- Pin SHA-256 `11d604a6b6bef0d41378da03718658c7fe9c959ac24e7fef6563796b9932afaf`. Reject other bases instead of disabling validation.
- No bootloader changes, flash option-byte changes, erase-all operations, debug unlock/readout-protection changes, or bootloader-target update packets.
- No blind patching: each in-place edit must assert original bytes, reject overlapping ranges, check application bounds (`[0x08010200, 0x08080000)`), recompute MPEG-2 CRC-32 checksums and produce a changed-range manifest. Code cave extensions may be appended in the free application flash region `[0x0806A570, 0x08080000)` (word-aligned).
- Preserve vector table (`[0x08010000, 0x08010200)`) in the patch scope.
- Do not redistribute Novation binaries publicly. Retain upstream MIT notices for reused code.

## Evidence and testing
Distinguish byte/disassembly verification, synthetic-RAM emulation, host-model tests, upstream claims and physical tests. Do nearly all development and testing in Unicorn ARM emulation first; only propose flashing to the physical device when a complete milestone bundle (M7) is verified in emulation.
Never run Python with `-O`; current tests use assertions. Capstone 5.0.9 and Unicorn 2.1.4 are pinned in `requirements.txt`.

## Session handoff
Update `docs/STATUS.md` with the current milestone, changed files, commands and results, failed hypotheses, open risks and one concrete next task. Update `CHANGELOG.md` for meaningful implementation changes. Do not spawn agents unless the user asks.
