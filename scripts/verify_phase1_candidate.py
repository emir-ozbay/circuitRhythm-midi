"""Comprehensive verification of the Phase 1 Consolidated Sequencer Candidate.

Verifies:
1. SysEx & Image Integrity:
   - SysEx round-trip decoding, size, and MPEG-2 CRC-32 match.
   - ARM Cortex-M Vector table and identity header [0x08010000..0x08010200) 100% preserved.
   - All patch ranges match the manifest and fall strictly inside allowed application flash.
2. Unicorn ARM Emulation of the 6 Acceptance Criteria:
   - Criterion 1: stopped/idle same-project mode toggle, no project I/O.
   - Criterion 2: 32-pad step toggle (0..31), pattern commit & page overflow protection (view + 0xB4 == 0) in grid_mode == 0.
   - Criterion 3: 32-step LED compositing & playhead (cursor) seamless flow (0..31) in grid_mode == 0.
   - Criterion 4: Velocity (mode 2) and Gate (mode 3) bottom pads & 1-16 page button preserved; 1-16 button locked in mode 0.
   - Criterion 5: shared64 stock project slots/pages; Projects/Save/Packs byte identity.
   - Criterion 6: Internal sample engine (0x08046780) muted (MIDI-Only) in Sequencer Mode and active in Normal Mode.

Saves report to logs/phase1-verification-<timestamp>/report.json.
No physical device or MIDI port is accessed.
"""
from __future__ import annotations

import datetime
import hashlib
import json
from pathlib import Path
import struct
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

try:
    import seq_Patch  # noqa: F401
except ImportError:
    pass

from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB, CS_MODE_MCLASS
from inspect_ui import load_image, BASE
from patch_firmware import (
    APP_BASE,
    APP_END,
    APP_WRITABLE_START,
    FLASH_END,
    STOCK_IMAGE_SHA256,
    STOCK_IMAGE_SIZE,
    STOCK_SYX_SHA256,
    VECTOR_TABLE_SIZE,
    crc32_mpeg2,
    unpack_syx,
)
from seq_patch import (
    CODE_CAVE_BASE,
    HEAP_CUR_PTR,
    HEAP_LIMIT,
    HEAP_LIMIT_PTR,
    HOOK_BUTTON_MODE,
    HOOK_CHECK_PACKS,
    HOOK_COMP_BOTTOM_MEMCPY,
    HOOK_COMP_TOP_LEDS,
    HOOK_GRID_MODE_CLEANUP,
    HOOK_GRID_PRESS_RESOLVE,
    HOOK_GRID_PRESS_TRANSFORM,
    HOOK_GRID_RELEASE_RESOLVE,
    HOOK_GRID_RELEASE_TRANSFORM,
    HOOK_PAGE_BTN_MODE0,
    HOOK_PROJ_ENTER_PAGE,
    HOOK_PROJ_PAGE_LOCK,
    HOOK_SAMPLE_TRIGGER_GATE,
    HOOK_STEP_PRESS_PAGE,
    HOOK_STEP_RELEASE_PAGE,
    OFF_GRID_PTR,
    OFF_SEQ_ENABLED,
    SEQ_STATE_ADDR,
    SEQ_STATE_MAGIC,
    STOCK_GRID_PRESS,
    STOCK_GRID_RELEASE,
    arm_code,
)
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_THUMB, UC_MODE_MCLASS, UC_HOOK_CODE
from unicorn.arm_const import (
    UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3,
    UC_ARM_REG_R4, UC_ARM_REG_R5, UC_ARM_REG_R6,
    UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_PC,
)

STOP = 0x0800F000


class EmulatorHarness:
    """Helper harness for Unicorn ARM Cortex-M emulation of patched firmware."""

    def __init__(self, patched_image: bytes, labels: dict[str, int]):
        self.patched_image = patched_image
        self.labels = labels
        self.u = Uc(UC_ARCH_ARM, UC_MODE_THUMB | UC_MODE_MCLASS)
        self.u.mem_map(0x08000000, 0x80000)  # 512 KB flash
        self.u.mem_write(BASE, self.patched_image)
        self.u.mem_map(0x20000000, 0x50000)  # 320 KB RAM

        # Stop address stub (bx lr)
        self.u.mem_write(STOP, bytes.fromhex("7047"))

        # Stubs for timers (0x08046dde, 0x08046e2a)
        self.u.mem_write(0x08046DDE, bytes.fromhex("7047"))
        self.u.mem_write(0x08046E2A, bytes.fromhex("7047"))

        # Initialize bump allocator limits
        self.word(HEAP_LIMIT_PTR, HEAP_LIMIT)
        self.word(HEAP_CUR_PTR, 0x2004EA98)

        # Initialize Sequencer Mode state block via c_seq_state()
        state_addr = self.call(self.labels["c_seq_state"])
        if state_addr != SEQ_STATE_ADDR:
            raise RuntimeError(f"c_seq_state returned {state_addr:#x}, expected {SEQ_STATE_ADDR:#x}")

        self.next_store = 0x20008000

    def word(self, addr: int, val: int) -> None:
        self.u.mem_write(addr, struct.pack("<I", val))

    def readword(self, addr: int) -> int:
        return struct.unpack("<I", self.u.mem_read(addr, 4))[0]

    def store(self, data: bytes, active: int = 0) -> int:
        obj = self.next_store
        self.next_store += 0x200
        self.u.mem_write(
            obj,
            struct.pack(
                "<5I", len(data) // 4, active, 0, obj + 0x40, obj + 0xC0
            ),
        )
        self.u.mem_write(obj + 0x40, data)
        self.u.mem_write(obj + 0xC0, data)
        return obj

    def call(self, addr: int, *args: int) -> int:
        regs = [UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3]
        for reg, val in zip(regs, args):
            self.u.reg_write(reg, val)
        self.u.reg_write(UC_ARM_REG_SP, 0x20040000)
        self.u.reg_write(UC_ARM_REG_LR, STOP | 1)
        self.u.emu_start(addr | 1, STOP, count=20000)
        assert self.u.reg_read(UC_ARM_REG_PC) == STOP, "Emulation budget exhausted before return"
        assert self.u.reg_read(UC_ARM_REG_SP) == 0x20040000, "Unbalanced stack at return"
        return self.u.reg_read(UC_ARM_REG_R0)

    def setup_step_view_environment(self, active_pattern: int = 0) -> dict:
        """Sets up a complete synthetic step view, stores, listener and pattern memory."""
        view, led_cell, leds = 0x20002000, 0x20003000, 0x20003100
        listener, listeners, patterns = 0x20001000, 0x20001100, 0x20010000
        view_listeners = 0x20001200
        empty_pattern = bytes([0, 6, 0, 0, 7, 255, 0, 0]) * 32 + bytes([0xA5]) * (0xA28 - 256)

        st1 = self.store(bytes(32) + bytes([7]) * 32 + bytes(32) + bytes([255]) * 32)
        st2 = self.store(bytes(32) + bytes([6]) * 32 + bytes(32))
        selection = self.store(bytes([active_pattern, 0, 0, 0]))
        note = self.store(bytes([60, 0, 0, 0]))
        held = self.store(bytes([255, 0, 0, 0]) * 2)
        pressed = self.store(bytes(8))
        page = self.store(bytes(4))
        zero_mod = self.store(bytes(4))

        self.word(listener, 0x080696A0)  # real stock vtable -> 0x08048208
        for offset, val in ((4, patterns), (0x1C, st1), (0x20, st2), (0x28, selection)):
            self.word(listener + offset, val)

        self.word(listeners, listener)
        self.word(listeners + 4, 0xFFFFFFFF)
        self.word(listeners + 8, view + 8)
        self.word(listeners + 12, 0xFFFFFFFF)

        self.word(view_listeners, view + 8)
        self.word(view_listeners + 4, 0xFFFFFFFF)

        for s, count, l_list in ((st1, 2, listeners), (st2, 1, listeners),
                                 (pressed, 1, view_listeners), (held, 1, view_listeners)):
            self.u.mem_write(s + 1, bytes([count]))
            self.word(s + 0x14, l_list)

        self.word(led_cell, leds)
        for offset, val in (
            (0, 0x080682CC), (4, led_cell), (8, 0x080682F8),
            (0xC, st1), (0x10, st2), (0x18, held), (0x20, pressed),
            (0x34, zero_mod), (0x3C, zero_mod), (0x40, zero_mod), (0x44, zero_mod),
            (0x5C, note), (0x60, page), (0x64, held), (0x70, zero_mod)
        ):
            self.word(view + offset, val)

        self.u.mem_write(patterns, empty_pattern * 8)
        self.u.mem_write(view + 0xB4, bytes(16))  # clean control block
        self.u.mem_write(leds, bytes([0xA5]) * 64)

        return {
            "view": view,
            "leds": leds,
            "patterns": patterns,
            "page": page,
            "st1": st1,
            "st2": st2,
        }

    def setup_grid_and_step_view(self, seq_enabled: int = 1, grid_mode: int = 0, track: int = 0) -> dict:
        env = self.setup_step_view_environment(active_pattern=0)
        view = env["view"]
        page = env["page"]

        grid = 0x20005000
        track_store = self.store(bytes([track, 0, 0, 0]))
        self.word(grid + 0x25C, track_store)
        self.u.mem_write(grid + 0x264, bytes([grid_mode]))
        self.u.mem_write(grid + 0x228, bytes(4))

        page_obj = 0x20005400
        self.word(page_obj + 0x10, page)
        self.word(grid + 0x19C + track * 4, page_obj)

        self.word(grid + 0x74 + track * 4, view)

        bottom_views = {}
        bottom_events = []

        press_cb = 0x0800E100
        release_cb = 0x0800E104
        self.u.mem_write(press_cb, bytes.fromhex("7047"))
        self.u.mem_write(release_cb, bytes.fromhex("7047"))

        for mode_id, offset, b_addr in ((0, 0x14, 0x20006000), (2, 0x9C, 0x20006100), (3, 0xBC, 0x20006200)):
            vt_addr = b_addr + 0x40
            self.word(b_addr, vt_addr)
            self.word(vt_addr + 0, press_cb | 1)
            self.word(vt_addr + 4, release_cb | 1)
            self.word(grid + offset + track * 4, b_addr)
            bottom_views[mode_id] = b_addr

        def on_bottom_cb(uc, addr, size, data):
            if addr == press_cb:
                bottom_events.append(("press", uc.reg_read(UC_ARM_REG_R0), uc.reg_read(UC_ARM_REG_R1), uc.reg_read(UC_ARM_REG_R2)))
            elif addr == release_cb:
                bottom_events.append(("release", uc.reg_read(UC_ARM_REG_R0), uc.reg_read(UC_ARM_REG_R1)))

        self.u.hook_add(UC_HOOK_CODE, on_bottom_cb)

        self.u.mem_write(SEQ_STATE_ADDR + OFF_SEQ_ENABLED, bytes([seq_enabled]))

        env["grid"] = grid
        env["bottom_views"] = bottom_views
        env["bottom_events"] = bottom_events
        return env


def verify_image_and_manifest(syx_path: Path, manifest_path: Path, stock_path: Path, *, patch_builder=None) -> dict:
    """Performs deep binary, hash, CRC, vector table and boundary verification."""
    if not syx_path.exists():
        raise FileNotFoundError(f"Candidate SysEx file not found: {syx_path}")
    if not manifest_path.exists():
        raise FileNotFoundError(f"Candidate manifest file not found: {manifest_path}")
    if not stock_path.exists():
        raise FileNotFoundError(f"Stock SysEx file not found: {stock_path}")

    raw_syx = syx_path.read_bytes()
    stock_syx = stock_path.read_bytes()
    assert hashlib.sha256(stock_syx).hexdigest() == STOCK_SYX_SHA256, "Stock SHA-256 pin mismatch"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    # 1. Unpack candidate SysEx
    parsed = unpack_syx(raw_syx, allow_extended=True)
    image = parsed["image"]
    size = len(image)
    crc = crc32_mpeg2(image)
    sha256 = hashlib.sha256(raw_syx).hexdigest()
    image_sha256 = hashlib.sha256(image).hexdigest()

    # 2. Unpack stock SysEx for vector comparison
    stock_parsed = unpack_syx(stock_syx)
    stock_image = stock_parsed["image"]
    assert hashlib.sha256(stock_image).hexdigest() == STOCK_IMAGE_SHA256

    # Assertions
    assert sha256 == manifest["output"]["sha256"], "SysEx SHA-256 does not match manifest"
    assert image_sha256 == manifest["output"]["image_sha256"], "Image SHA-256 does not match manifest"
    assert crc == parsed["crc"], f"Computed CRC32 {crc:#x} != SysEx header CRC32 {parsed['crc']:#x}"
    assert f"{crc:#010x}" == manifest["output"]["image_crc32_mpeg2"], "CRC32 does not match manifest"
    assert size == manifest["output"]["image_size"], "Image size does not match manifest"

    # Vector table and identity preservation check (first 512 bytes)
    assert image[:VECTOR_TABLE_SIZE] == stock_image[:VECTOR_TABLE_SIZE], (
        "Cortex-M Vector table or identity region modified! Forbidden!"
    )

    # Patch ranges check
    for p in manifest["patches"]:
        addr = int(p["address"], 16)
        length = p["length"]
        end_addr = addr + length
        assert addr >= APP_WRITABLE_START, f"Patch {p['name']} touches vector table / bootloader: {addr:#x}"
        assert end_addr <= FLASH_END, f"Patch {p['name']} exceeds flash boundary: {end_addr:#x}"
        assert image[addr-APP_BASE:end_addr-APP_BASE].hex() == p['replacement_hex']

    from patch_firmware import apply_patches
    from seq_patch import build_phase1_patches
    expected, _, _ = apply_patches(stock_image, (patch_builder or build_phase1_patches)())
    assert image == expected, "Packaged image differs from current audited source"

    return {
        "syx_path": str(syx_path),
        "syx_size": len(raw_syx),
        "syx_sha256": sha256,
        "image_size": size,
        "image_sha256": image_sha256,
        "image_crc32_mpeg2": f"{crc:#010x}",
        "vector_table_preserved": True,
        "identity_preserved": True,
        "bounds_preserved": True,
        "patches_count": len(manifest["patches"]),
        "total_bytes_changed": manifest["total_bytes_changed"],
        "image": image,
    }


def run_criterion_1_mode_toggle(image: bytes, labels: dict[str, int]) -> dict:
    """Real button dispatch, no deferred Load completion or storage API stubs."""
    from shared_project_test_support import SharedModeFixture
    h = EmulatorHarness(image, labels)
    f = SharedModeFixture(h)
    calls = []
    for address in (0x08047038, 0x08037BD6, 0x08037ED0, 0x08047288, 0x080472E2):
        h.u.hook_add(UC_HOOK_CODE, lambda u,a,z,d: calls.append(a), begin=address, end=address)
    before = bytes(h.u.mem_read(f.meta, 0x100))
    for mode in (1, 0):
        f.press()
        assert h.u.mem_read(SEQ_STATE_ADDR + 4, 1) == bytes([mode])
        assert bytes(h.u.mem_read(f.meta, 0x100)) == before
        f.release()
    f.set_byte(f.transport, 0, 1)
    f.press()
    assert h.u.mem_read(SEQ_STATE_ADDR + 4, 1) == bytes(1)
    assert calls == []
    return {"status": "PASS", "details": "Same-project toggle through real stock button ownership; metadata preserved; zero project actions. Running transport refuses toggle."}

def run_criterion_2_32pad_step_toggle(image: bytes, labels: dict[str, int]) -> dict:
    """Criterion 2: 32-pad step toggle (0..31), pattern commit & page overflow protection (view + 0xB4 == 0)."""
    h = EmulatorHarness(image, labels)
    env = h.setup_grid_and_step_view(seq_enabled=1, grid_mode=0, track=0)
    grid = env["grid"]
    view = env["view"]
    patterns = env["patterns"]
    page = env["page"]
    bottom_events = env["bottom_events"]

    # Force page_store to 1 (steps 17..32) to prove page lock to 0 in grid_mode == 0
    h.u.mem_write(page + 0x40, bytes([1, 0, 0, 0]))
    assert h.u.mem_read(view + 0xB4, 4) == bytes(4)

    # --- Turn ON all 32 steps (0..31) ---
    for pad in range(32):
        h.call(STOCK_GRID_PRESS, grid, pad, 96)
        assert h.readword(SEQ_STATE_ADDR + OFF_GRID_PTR) == grid
        assert h.readword(grid + 0x228) == (1 << pad)
        st_press = struct.unpack("<H", h.u.mem_read(view + 0x74 + 2 * pad, 2))[0]
        assert st_press == 8, f"Step {pad} held status expected 8, got {st_press}"
        assert h.u.mem_read(view + 0xB4, 4) == bytes(4), f"view+0xB4 corrupted on press pad {pad}"

        h.call(STOCK_GRID_RELEASE, grid, pad)
        assert h.readword(grid + 0x228) == 0
        st_rel = struct.unpack("<H", h.u.mem_read(view + 0x74 + 2 * pad, 2))[0]
        assert st_rel == 2, f"Step {pad} hit status expected 2, got {st_rel}"
        assert h.u.mem_read(view + 0xB4, 4) == bytes(4), f"view+0xB4 corrupted on release pad {pad}"

    assert bottom_events == [], "Bottom subview improperly called in grid_mode == 0"

    # Verify pattern memory
    pattern_data = h.u.mem_read(patterns, 32 * 8)
    for step in range(32):
        step_bytes = pattern_data[step * 8 : (step + 1) * 8]
        assert step_bytes[0] == 60 and step_bytes[3] == 96, f"Step {step} pattern mismatch: {step_bytes.hex()}"

    # --- Turn OFF all 32 steps (0..31) ---
    for pad in range(32):
        h.call(STOCK_GRID_PRESS, grid, pad, 96)
        h.call(STOCK_GRID_RELEASE, grid, pad)
        st_off = struct.unpack("<H", h.u.mem_read(view + 0x74 + 2 * pad, 2))[0]
        assert st_off == 0, f"Step {pad} off status expected 0, got {st_off}"
        assert h.u.mem_read(view + 0xB4, 4) == bytes(4), f"view+0xB4 corrupted on turn-off pad {pad}"

    pattern_data_off = h.u.mem_read(patterns, 32 * 8)
    for step in range(32):
        step_bytes = pattern_data_off[step * 8 : (step + 1) * 8]
        assert step_bytes[3] == 0, f"Step {step} velocity not cleared: {step_bytes.hex()}"

    return {
        "status": "PASS",
        "details": "All 32 pads (0..31) toggle ON/OFF with clean pattern commit and 100% protection of view+0xB4.",
    }


def run_criterion_3_32step_led_compositor(image: bytes, labels: dict[str, int]) -> dict:
    """Criterion 3: 32-step LED compositing & playhead (cursor) seamless flow (0..31) in grid_mode == 0."""
    h = EmulatorHarness(image, labels)

    grid = 0x20001000
    grid_led_cell = 0x20001080
    grid_led_buf = 0x20001400
    h.u.mem_write(grid_led_buf, bytes(0x60))
    h.word(grid_led_cell, grid_led_buf)
    h.word(grid + 4, grid_led_cell)

    selected_track = h.store(bytes([0, 0, 0, 0]))
    h.word(grid + 0x25C, selected_track)
    h.u.mem_write(grid + 0x264, bytes([0]))  # Mode 0

    store_22c = h.store(bytes([0, 0, 0, 0]))
    h.word(grid + 0x22C, store_22c)

    track_array = 0x20002800
    track_prop_store = h.store(bytes([0] * 16))
    for t in range(8):
        h.word(track_array + t * 4, track_prop_store)
    h.word(grid + 0x258, track_array)

    stub_led = 0x0800E100
    h.u.mem_write(stub_led, bytes.fromhex("4068 0068 7047"))  # ldr r0, [r0, #4]; ldr r0, [r0]; bx lr

    page_obj = 0x20002000
    page_vt = 0x20002100
    page_led_cell = 0x20002080
    page_led_buf = 0x20002400
    h.u.mem_write(page_led_buf, bytes([0x55] * 16))
    h.word(page_led_cell, page_led_buf)
    h.word(page_obj + 0, page_vt)
    h.word(page_obj + 4, page_led_cell)
    h.word(page_vt + 0x1C, stub_led | 1)

    page_store = h.store(bytes([0, 0, 0, 0]))
    h.word(page_obj + 0x10, page_store)
    h.word(grid + 0x19C, page_obj)

    step_view = 0x20003000
    step_led_cell = 0x20003500
    step_led_buf = 0x20003600
    h.u.mem_write(step_led_buf, bytes(64))
    h.word(step_led_cell, step_led_buf)

    held = h.store(bytes([255, 0, 0, 0]) * 2)
    st1 = h.store(bytes(32) + bytes([7]) * 32 + bytes(32) + bytes([255]) * 32)
    st2 = h.store(bytes(32) + bytes([6]) * 32 + bytes(32))
    note = h.store(bytes([60, 0, 0, 0]))

    for offset, value in ((0, 0x080682CC), (4, step_led_cell), (8, 0x080682F8),
                          (0xC, st1), (0x10, st2), (0x18, held),
                          (0x5C, note), (0x60, page_store), (0x64, held)):
        h.word(step_view + offset, value)

    h.word(grid + 0x74, step_view)

    # Note View (bottom view for mode 0)
    note_view = 0x20004000
    note_vt = 0x20004100
    note_led_cell = 0x20004500
    note_led_buf = 0x20004600
    note_bytes = bytes([0x40 + (i % 32) for i in range(64)])
    h.u.mem_write(note_led_buf, note_bytes)
    h.word(note_led_cell, note_led_buf)
    h.word(note_view + 0, note_vt)
    h.word(note_view + 4, note_led_cell)
    h.word(note_vt + 0x1C, stub_led | 1)
    h.word(grid + 0x14, note_view)

    # Sequencer state init
    h.word(SEQ_STATE_ADDR, SEQ_STATE_MAGIC)
    h.u.mem_write(SEQ_STATE_ADDR + OFF_SEQ_ENABLED, bytes([1]))
    h.word(SEQ_STATE_ADDR + OFF_GRID_PTR, grid)

    # 1. Setup 32-step logical buffer
    for s in range(32):
        status = 2 if (s % 2 == 0) else 0
        h.u.mem_write(step_view + 0x74 + s * 2, struct.pack("<H", status))
        h.call(0x0805CF24, step_view, s)

    step_buf_data = h.u.mem_read(step_led_buf, 64)

    # Composite through real 0x0804DD1C
    h.call(0x0804DD1C, grid)
    grid_data = h.u.mem_read(grid_led_buf, 64)

    assert grid_data[:32] == step_buf_data[:32], "Top 16 pads do not match steps 0..15"
    assert grid_data[32:64] == step_buf_data[32:64], "Bottom 16 pads do not match steps 16..31"

    # 2. Continuous playhead flow across all 32 steps (0 to 31)
    for cursor in range(32):
        prev_cursor = (cursor - 1) % 32
        prev_status = 2 if (prev_cursor % 2 == 0) else 0
        h.u.mem_write(step_view + 0x74 + prev_cursor * 2, struct.pack("<H", prev_status))
        h.call(0x0805CF24, step_view, prev_cursor)

        curr_status = (2 if (cursor % 2 == 0) else 0) | 1
        h.u.mem_write(step_view + 0x74 + cursor * 2, struct.pack("<H", curr_status))
        h.call(0x0805CF24, step_view, cursor)

        h.call(0x0804DD1C, grid)
        frame = h.u.mem_read(grid_led_buf, 64)

        for pad in range(32):
            color = struct.unpack_from("<H", frame, pad * 2)[0]
            is_hit = (pad % 2 == 0)
            if pad == cursor:
                expected = 0x001A if is_hit else 0x001B
                assert color == expected, f"Pad {pad} playhead expected {expected:#x}, got {color:#x}"
            else:
                expected = 0x0018 if is_hit else 0x0019
                assert color == expected, f"Pad {pad} non-playhead expected {expected:#x}, got {color:#x}"

    return {
        "status": "PASS",
        "details": "Grid compositor displays steps 0..15 on top 16 pads, steps 16..31 on bottom 16 pads, and playhead flows seamlessly across 0..31.",
    }


def run_criterion_4_velocity_gate_preservation(image: bytes, labels: dict[str, int]) -> dict:
    """Criterion 4: Velocity (mode 2) and Gate (mode 3) bottom pads & 1-16 page button preserved; 1-16 button locked in mode 0."""
    # Part A: 1-16 Page button lock / preservation test via 0x0804DCB2
    h1 = EmulatorHarness(image, labels)
    grid = 0x20005000
    page_btn_store = h1.store(bytes([0, 0, 0, 0]))
    h1.word(grid + 0x22C, page_btn_store)

    subview_mode0 = 0x20008000
    subview_other = 0x20009000
    h1.word(grid + 0x19C, subview_mode0)
    h1.word(grid + 0x13C, subview_other)

    h1.u.mem_write(0x0805800E, bytes.fromhex("00207047"))  # track 0
    h1.u.mem_write(0x0805888C, bytes.fromhex("01207047"))  # mode supported

    def call_page_btn(seq_en: int, mode_val: int) -> int:
        h1.u.mem_write(SEQ_STATE_ADDR + OFF_SEQ_ENABLED, bytes([seq_en]))
        h1.u.mem_write(grid + 0x264, bytes([mode_val]))
        h1.u.reg_write(UC_ARM_REG_R0, grid)
        h1.u.reg_write(UC_ARM_REG_SP, 0x20040000)
        h1.u.reg_write(UC_ARM_REG_LR, STOP | 1)
        h1.u.emu_start(0x0804DCB2 | 1, STOP)
        return h1.u.reg_read(UC_ARM_REG_R0)

    # 1. Sequencer Mode, grid_mode == 0: locked out (returns 0)
    assert call_page_btn(1, 0) == 0, "1-16 page button not locked in Sequencer grid_mode == 0"

    # 2. Normal Mode, grid_mode == 0: stock subview returned
    assert call_page_btn(0, 0) == subview_mode0, "Normal mode 1-16 page button not returning subview"

    # 3. Sequencer Mode, Velocity (mode 2): valid subview returned
    assert call_page_btn(1, 2) == subview_other, "Velocity mode 1-16 button not preserved"

    # 4. Sequencer Mode, Gate (mode 3): valid subview returned
    assert call_page_btn(1, 3) == subview_other, "Gate mode 1-16 button not preserved"

    # Part B: Top/Bottom pad routing preservation in Velocity & Gate modes
    for gm in (2, 3):
        h2 = EmulatorHarness(image, labels)
        env = h2.setup_grid_and_step_view(seq_enabled=1, grid_mode=gm, track=0)
        g = env["grid"]
        p = env["page"]
        v = env["view"]
        bottom_v = env["bottom_views"][gm]
        bottom_evs = env["bottom_events"]

        # 1. Top pads 0..15 on Page 0 (steps 0..15) and Page 1 (steps 16..31)
        for page_val, step_off in ((0, 0), (1, 16)):
            h2.u.mem_write(p + 0x40, bytes([page_val, 0, 0, 0]))
            for pad in range(16):
                exp_step = pad + step_off
                h2.call(STOCK_GRID_PRESS, g, pad, 96)
                st_p = struct.unpack("<H", h2.u.mem_read(v + 0x74 + 2 * exp_step, 2))[0]
                assert st_p == 8, f"Top pad {pad} press step {exp_step} expected status 8, got {st_p}"
                h2.call(STOCK_GRID_RELEASE, g, pad)
                st_r = struct.unpack("<H", h2.u.mem_read(v + 0x74 + 2 * exp_step, 2))[0]
                assert st_r == 2, f"Top pad {pad} release step {exp_step} expected status 2, got {st_r}"

        # 2. Bottom pads 16..31 route to mode bottom subview with local pad 0..15
        bottom_evs.clear()
        for pad in range(16, 32):
            local_pad = pad - 16
            h2.call(STOCK_GRID_PRESS, g, pad, 100)
            h2.call(STOCK_GRID_RELEASE, g, pad)

        assert len(bottom_evs) == 32, f"Expected 32 bottom events (16 press + 16 release), got {len(bottom_evs)}"
        for i in range(16):
            press_ev = bottom_evs[i * 2]
            rel_ev = bottom_evs[i * 2 + 1]
            assert press_ev[0] == "press" and press_ev[1] == bottom_v and press_ev[2] == i and press_ev[3] == 100
            assert rel_ev[0] == "release" and rel_ev[1] == bottom_v and rel_ev[2] == i

    return {
        "status": "PASS",
        "details": "1-16 page button locked strictly in grid_mode == 0, and 100% functional with bottom pads preserved in Velocity (mode 2) and Gate (mode 3).",
    }


def run_criterion_5_shared_projects(image: bytes, labels: dict[str, int]) -> dict:
    from shared_project_test_support import SharedModeFixture
    h = EmulatorHarness(image, labels)
    f = SharedModeFixture(h)
    h.u.mem_write(0x0804F27E, bytes.fromhex("7047"))  # LED output boundary
    h.word(f.view + 0x1C, h.store(bytes(4)))
    for mode in (0, 1):
        h.u.mem_write(SEQ_STATE_ADDR + 4, bytes([mode]))
        for slot in range(64):
            f.set_byte(f.meta, 44, slot)
            h.call(0x0804F080, f.view)
            assert h.u.mem_read(f.view + 0x36, 1)[0] == slot >> 5
            for button, page in ((19, 1), (20, 0)):
                h.call(0x0804F12C, f.view, button)
                assert h.u.mem_read(f.view + 0x36, 1)[0] == page
    stock = load_image()
    assert image[0x2DB54:0x2DB60] == stock[0x2DB54:0x2DB60]
    assert image[0x3ED60:0x3F3F0] == stock[0x3ED60:0x3F3F0]
    return {"status": "PASS", "details": "Both modes share64 stock project slots; page selection follows active slot, both page buttons work; Projects/Save/Packs code is byte-identical to stock."}

def run_criterion_6_sample_engine_muting(image: bytes, labels: dict[str, int]) -> dict:
    """Criterion 6: Internal sample engine (0x08046780) muted (MIDI-Only) in Sequencer Mode and active in Normal Mode."""
    h = EmulatorHarness(image, labels)

    engine_calls = []

    def on_engine(uc, addr, size, user_data):
        engine_calls.append((
            uc.reg_read(UC_ARM_REG_R0),
            uc.reg_read(UC_ARM_REG_R1),
            uc.reg_read(UC_ARM_REG_R2),
            uc.reg_read(UC_ARM_REG_R3),
        ))

    h.u.mem_write(0x08046780, bytes.fromhex("55207047"))  # movs r0, #0x55; bx lr
    h.u.hook_add(UC_HOOK_CODE, on_engine, begin=0x08046780, end=0x08046780)

    def trigger_sample(seq_en: int, sample_id: int, note: int, vel: int) -> int:
        h.u.mem_write(SEQ_STATE_ADDR + OFF_SEQ_ENABLED, bytes([seq_en]))
        engine_calls.clear()
        h.u.reg_write(UC_ARM_REG_R0, 0)
        h.u.reg_write(UC_ARM_REG_R1, sample_id)
        h.u.reg_write(UC_ARM_REG_R2, note)
        h.u.reg_write(UC_ARM_REG_R3, vel)
        h.u.reg_write(UC_ARM_REG_SP, 0x20040000)
        h.u.reg_write(UC_ARM_REG_LR, STOP | 1)
        h.u.emu_start(0x08031A18 | 1, STOP)
        return h.u.reg_read(UC_ARM_REG_R0)

    # 1. Sequencer Mode: engine muted, returns 0
    ret_seq = trigger_sample(1, 12, 60, 96)
    assert ret_seq == 0, f"Trigger sample returned {ret_seq}, expected 0"
    assert len(engine_calls) == 0, "Internal sample engine was called in Sequencer Mode"

    # 2. Normal Mode: engine called, returns 0x55 with original args
    ret_norm = trigger_sample(0, 12, 60, 96)
    assert ret_norm == 0x55, f"Trigger sample returned {ret_norm}, expected 0x55"
    assert len(engine_calls) == 1, "Internal sample engine was NOT called in Normal Mode"
    assert engine_calls[0] == (12, 60, 96, 96), f"Arguments mismatch: {engine_calls[0]}"

    return {
        "status": "PASS",
        "details": "The 0x08031A18 Note On adapter is gated; normal arguments are preserved. Other sample paths and MIDI/Clock integration are NOT tested by this criterion.",
    }


def release_blockers(image: bytes, labels: dict[str, int]) -> list[dict]:
    """Honest remaining obligations; shared mode no longer triggers project I/O."""
    return [
        {'id': 'runtime_midi_transport_unproven',
         'risk': 'USB RX yielding fixes the tested incoming-Clock burst. Native pattern players now generate notes through real ownership/sample/MIDI routing. Native Stop synchronously flushes64 player notes before FC; the64-slot queues drop FC with ready drivers (63-note control passes). F8+FC in one USB buffer also loses a player Off. FIFO loss latches state+7A and blocks mode changes, but does not recover delivery. Driver stalls/USB disconnect loss also remain. Full UI/preview/tied ownership, IRQ/DMA/timer/USB-service scheduling, receiver lifetime/count and latency are unproven.'},
        {'id': 'stock_storage_failure_behavior_unresolved',
         'risk': 'Project/storage code is restored byte-for-byte to stock and mode toggle performs zero I/O. The previously demonstrated stock partial-read/live-pattern alias is not repaired; stock error/recovery behavior remains an inherited data-loss risk.'},
        {'id': 'allocator_boot_timing_unproven',
         'risk': 'Heap reservation and overflow guards pass isolated tests; full boot/OOM caller handling and the PRIMASK timing budget on the actual task/ISR graph remain unproven.'},
    ]

def main() -> int:
    start_time = time.time()
    timestamp_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    syx_path = ROOT / "build" / "circuitrhythm-5706-phase1-sequencer.syx"
    manifest_path = ROOT / "build" / "circuitrhythm-5706-phase1-sequencer.manifest.json"
    stock_path = ROOT / "stock" / "circuitrhythm-firmware-5706.syx"

    log_dir = ROOT / "logs" / f"phase1-verification-{timestamp_str}"
    log_dir.mkdir(parents=True, exist_ok=True)
    report_file = log_dir / "report.json"

    print("================================================================================")
    print("PHASE 1 CANDIDATE FIRMWARE VERIFICATION (Step 7)")
    print("================================================================================")
    print(f"Candidate SysEx:  {syx_path}")
    print(f"Manifest Path:    {manifest_path}")
    print(f"Log / Report:     {report_file}")
    print("--------------------------------------------------------------------------------")

    # Step 1: Binary & SysEx Integrity
    print("[1/7] Verifying SysEx format, CRC-32/MPEG-2, Vector Table & Boundaries...")
    try:
        integrity_info = verify_image_and_manifest(syx_path, manifest_path, stock_path)
        print(f"      SysEx Size:       {integrity_info['syx_size']} bytes")
        print(f"      SysEx SHA-256:    {integrity_info['syx_sha256']}")
        print(f"      Image Size:       {integrity_info['image_size']} bytes")
        print(f"      Image SHA-256:    {integrity_info['image_sha256']}")
        print(f"      Image CRC-32:     {integrity_info['image_crc32_mpeg2']}")
        print(f"      Vector Table:     100% Preserved [0x08010000..0x08010200)")
        print(f"      Total Patches:    {integrity_info['patches_count']} (Changed bytes: {integrity_info['total_bytes_changed']})")
        print("      --> PASS")
    except Exception as ex:
        print(f"      --> FAIL: {ex}", file=sys.stderr)
        return 1

    patched_image = integrity_info["image"]
    _, labels = arm_code(CODE_CAVE_BASE)

    # Step 2: Emulation Criteria
    criteria_results = {}

    print("[2/7] Testing Criterion 1: Shift + Sample Rec Mode Toggle & Cleanup...")
    try:
        criteria_results["criterion_1_mode_toggle"] = run_criterion_1_mode_toggle(patched_image, labels)
        print("      --> PASS")
    except Exception as ex:
        print(f"      --> FAIL: {ex}", file=sys.stderr)
        return 1

    print("[3/7] Testing Criterion 2: 32-Pad Step Toggle & Overflow Protection (grid_mode == 0)...")
    try:
        criteria_results["criterion_2_32pad_step_toggle"] = run_criterion_2_32pad_step_toggle(patched_image, labels)
        print("      --> PASS")
    except Exception as ex:
        import traceback
        traceback.print_exc()
        print(f"      --> FAIL: {ex}", file=sys.stderr)
        return 1

    print("[4/7] Testing Criterion 3: 32-Step LED Compositor & Playhead Flow (grid_mode == 0)...")
    try:
        criteria_results["criterion_3_32step_led_compositor"] = run_criterion_3_32step_led_compositor(patched_image, labels)
        print("      --> PASS")
    except Exception as ex:
        import traceback
        traceback.print_exc()
        print(f"      --> FAIL: {ex}", file=sys.stderr)
        return 1

    print("[5/7] Testing Criterion 4: Velocity & Gate Bottom Pads & 1-16 Page Button Protection...")
    try:
        criteria_results["criterion_4_velocity_gate_preservation"] = run_criterion_4_velocity_gate_preservation(patched_image, labels)
        print("      --> PASS")
    except Exception as ex:
        import traceback
        traceback.print_exc()
        print(f"      --> FAIL: {ex}", file=sys.stderr)
        return 1

    print("[6/7] Testing Criterion 5: Shared64 Stock Projects & Page Buttons...")
    try:
        criteria_results["criterion_5_independent_projects_and_packs_lock"] = run_criterion_5_shared_projects(patched_image, labels)
        print("      --> PASS")
    except Exception as ex:
        print(f"      --> FAIL: {ex}", file=sys.stderr)
        return 1

    print("[7/7] Testing Criterion 6: Internal Sample Engine Muting (MIDI-Only)...")
    try:
        criteria_results["criterion_6_sample_engine_muting"] = run_criterion_6_sample_engine_muting(patched_image, labels)
        print("      --> PASS")
    except Exception as ex:
        print(f"      --> FAIL: {ex}", file=sys.stderr)
        return 1

    elapsed = time.time() - start_time

    # Run auditor regressions AGAINST THE ACTUAL PACKAGED IMAGE, not a rebuilt fixture.
    import unittest
    sys.path.insert(0, str(ROOT / 'tests'))
    from test_phase1_safety import SafetyTests
    from test_reaudit_abi import ReauditABI
    from test_shared_project import SharedProjectTests
    from test_midi_mode_ownership import MidiModeOwnershipTests
    from test_midi_ingress_transport import MidiIngressTransportTests
    from test_midi_output_transport import MidiOutputTransportTests
    from test_midi_task_schedule import MidiTaskScheduleTests
    from test_midi_tx_fault import MidiTxFaultTests
    from test_native_midi_drivers import NativeMidiDriverTests
    from test_sequencer_playback import SequencerPlaybackTests
    class PackagedSafetyTests(SafetyTests):
        @classmethod
        def setUpClass(cls):
            cls.image, cls.labels = patched_image, labels
    class PackagedReauditABI(ReauditABI):
        @classmethod
        def setUpClass(cls):
            cls.image, cls.labels = patched_image, labels
    class PackagedSharedProject(SharedProjectTests):
        @classmethod
        def setUpClass(cls):
            cls.image, cls.labels = patched_image, labels
    class PackagedMidiModeOwnership(MidiModeOwnershipTests):
        @classmethod
        def setUpClass(cls):
            cls.image, cls.labels = patched_image, labels
    class PackagedMidiIngressTransport(MidiIngressTransportTests):
        @classmethod
        def setUpClass(cls):
            cls.image, cls.labels = patched_image, labels
    class PackagedMidiOutputTransport(MidiOutputTransportTests):
        @classmethod
        def setUpClass(cls):
            cls.image, cls.labels = patched_image, labels
    class PackagedMidiTaskSchedule(MidiTaskScheduleTests):
        @classmethod
        def setUpClass(cls):
            cls.image, cls.labels = patched_image, labels
    class PackagedMidiTxFault(MidiTxFaultTests):
        @classmethod
        def setUpClass(cls):
            cls.image, cls.labels = patched_image, labels
    class PackagedNativeMidiDrivers(NativeMidiDriverTests):
        @classmethod
        def setUpClass(cls):
            cls.image, cls.labels = patched_image, labels
    class PackagedSequencerPlayback(SequencerPlaybackTests):
        @classmethod
        def setUpClass(cls):
            cls.image, cls.labels = patched_image, labels
    suite = unittest.TestSuite([
        unittest.defaultTestLoader.loadTestsFromTestCase(PackagedSafetyTests),
        unittest.defaultTestLoader.loadTestsFromTestCase(PackagedReauditABI),
        unittest.defaultTestLoader.loadTestsFromTestCase(PackagedSharedProject),
        unittest.defaultTestLoader.loadTestsFromTestCase(PackagedMidiModeOwnership),
        unittest.defaultTestLoader.loadTestsFromTestCase(PackagedMidiIngressTransport),
        unittest.defaultTestLoader.loadTestsFromTestCase(PackagedMidiOutputTransport),
        unittest.defaultTestLoader.loadTestsFromTestCase(PackagedMidiTaskSchedule),
        unittest.defaultTestLoader.loadTestsFromTestCase(PackagedMidiTxFault),
        unittest.defaultTestLoader.loadTestsFromTestCase(PackagedNativeMidiDrivers),
        unittest.defaultTestLoader.loadTestsFromTestCase(PackagedSequencerPlayback),
    ])
    safety_result = unittest.TextTestRunner(verbosity=1).run(suite)
    blockers = release_blockers(patched_image, labels)
    if not safety_result.wasSuccessful():
        blockers.insert(0, {'id': 'packaged_regression_failure', 'severity': 'critical',
                            'risk': 'A regression failed against the packaged image. Release acceptance is blocked; inspect the recorded test failures.'})

    # Passing a regression which characterizes stock queue loss is not safety
    # acceptance. Independently replay the negative probe on the exact image.
    from probe_midi_output_queue import probe as probe_midi_queue
    from probe_midi_task import probe as probe_task_schedule
    from probe_sequencer_stop import probe as probe_sequencer_stop
    try:
        queue_probe = probe_midi_queue(patched_image, labels)
    except Exception as exc:
        queue_probe = {'note_off_delivery': 'ERROR', 'error': f'{type(exc).__name__}: {exc}'}
    try:
        task_probe = probe_task_schedule(patched_image, labels)
    except Exception as exc:
        task_probe = {'error': f'{type(exc).__name__}: {exc}'}
    try:
        sequencer_probe = probe_sequencer_stop(patched_image, labels)
    except Exception as exc:
        sequencer_probe = {'stop_delivery': 'ERROR', 'note_off_delivery': 'ERROR',
                           'error': f'{type(exc).__name__}: {exc}'}
    task_probe_failed = any(task_probe.get(k, {}).get('stop_delivery') != 'PASS'
                            for k in ('bounded_usb_ready_driver', 'bounded_usb_stalled_driver'))
    queue_probe_failed = (queue_probe['note_off_delivery'] != 'PASS' or task_probe_failed
                          or sequencer_probe['stop_delivery'] != 'PASS'
                          or sequencer_probe['note_off_delivery'] != 'PASS')
    if queue_probe_failed:
        runtime_blocker = next(b for b in blockers if b['id'] == 'runtime_midi_transport_unproven')
        runtime_blocker['runtime_probe_evidence'] = queue_probe
        runtime_blocker['sequencer_stop_evidence'] = sequencer_probe

    # Generate Report
    report = {
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "elapsed_seconds": round(elapsed, 3),
        "overall_status": ("CRITICAL_REGRESSION_FAILED" if any(b.get("severity") == "critical" for b in blockers)
                           else "CRITICAL_RUNTIME_PROBE_FAILED" if queue_probe_failed
                           else "HOST_CHECKS_PASS"),
        "test_scope_warning": "Synthetic controller/store RAM, real button ownership; no Load-completion injection. Projects/storage byte identity is not proof against inherited stock media failures or full boot.",
        "hardware_release": "NO-GO" if blockers else "REVIEW_REQUIRED",
        "release_blockers": blockers,
        "auditor_regression_tests": safety_result.testsRun,
        "auditor_regression_failures": len(safety_result.failures),
        "auditor_regression_errors": len(safety_result.errors),
        "runtime_safety_probes": {"midi_output_queue": queue_probe, "midi_task_schedule": task_probe,
                                  "sequencer_stop": sequencer_probe},
        "firmware_integrity": {
            "syx_path": integrity_info["syx_path"],
            "syx_size": integrity_info["syx_size"],
            "syx_sha256": integrity_info["syx_sha256"],
            "image_size": integrity_info["image_size"],
            "image_sha256": integrity_info["image_sha256"],
            "image_crc32_mpeg2": integrity_info["image_crc32_mpeg2"],
            "vector_table_preserved": True,
            "identity_preserved": True,
            "bounds_preserved": True,
            "patches_count": integrity_info["patches_count"],
            "total_bytes_changed": integrity_info["total_bytes_changed"],
        },
        "acceptance_criteria": criteria_results,
    }

    report_file.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("================================================================================")
    print(f"6 SCOPED HOST CHECKS PASSED ({elapsed:.2f}s); HARDWARE RELEASE: " + ("NO-GO" if blockers else "REVIEW_REQUIRED (ALL HOST CHECKS PASS)"))
    print(f"MIDI OUTPUT NOTE OFF SAFETY PROBE: {queue_probe['note_off_delivery']}")
    print('USB TASK STOP PROBES: ready=' + task_probe.get('bounded_usb_ready_driver', {}).get('stop_delivery', 'ERROR')
          + ', stalled=' + task_probe.get('bounded_usb_stalled_driver', {}).get('stop_delivery', 'ERROR'))
    print('NATIVE SEQUENCER PROBE: Stop=' + sequencer_probe['stop_delivery']
          + ', Off=' + sequencer_probe['note_off_delivery'])
    for item in blockers:
        print(f"  BLOCKER {item['id']}: {item['risk']}")
    print(f"Report written to: {report_file}")
    print("================================================================================")
    return 2 if blockers else 0


if __name__ == "__main__":
    sys.exit(main())
