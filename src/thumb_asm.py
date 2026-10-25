"""Minimal Thumb / Thumb-2 machine code assembler for Circuit Rhythm 5706 patches.

Retains upstream MIT License from CIRCUIT-REMIX (tools/thumb.py):

MIT License

Copyright (c) 2026 Ghillermo

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
from __future__ import annotations

import builtins
import struct
from typing import Iterable, Union

COND = {
    "eq": 0, "ne": 1, "hs": 2, "cs": 2, "lo": 3, "cc": 3,
    "mi": 4, "pl": 5, "vs": 6, "vc": 7, "hi": 8, "ls": 9,
    "ge": 10, "lt": 11, "gt": 12, "le": 13, "al": 14,
}


def h(v: int) -> bytes:
    """Packs a 16-bit halfword in little-endian format."""
    return struct.pack("<H", v & 0xFFFF)


def _lo(*regs: int) -> None:
    for r in regs:
        if not 0 <= r <= 7:
            raise ValueError(f"r{r} is not a low register (expected r0..r7)")


def _reg(*regs: int, allow_sp_pc: bool = False) -> None:
    upper = 15 if allow_sp_pc else 12
    for r in regs:
        if not 0 <= r <= upper:
            raise ValueError(f"r{r} is out of valid register range (0..{upper})")


# ---- Load / Store (Word, Byte, Halfword, Stack, Literal) -------------------

def ldr_imm(rt: int, rn: int, imm: int = 0) -> bytes:
    """LDR Rt, [Rn, #imm] (T1, 16-bit, imm in 0..124, multiple of 4)."""
    _lo(rt, rn)
    assert imm % 4 == 0 and 0 <= imm <= 124, f"ldr_imm offset out of range: {imm}"
    return h(0x6800 | (imm // 4) << 6 | rn << 3 | rt)


def str_imm(rt: int, rn: int, imm: int = 0) -> bytes:
    """STR Rt, [Rn, #imm] (T1, 16-bit, imm in 0..124, multiple of 4)."""
    _lo(rt, rn)
    assert imm % 4 == 0 and 0 <= imm <= 124, f"str_imm offset out of range: {imm}"
    return h(0x6000 | (imm // 4) << 6 | rn << 3 | rt)


def ldr_w(rt: int, rn: int, imm12: int = 0) -> bytes:
    """LDR.W Rt, [Rn, #imm12] (T3, 32-bit, imm12 in 0..4095)."""
    _reg(rt, rn, allow_sp_pc=True)
    assert 0 <= imm12 < 4096, f"ldr_w offset out of range: {imm12}"
    return h(0xF8D0 | rn) + h(rt << 12 | imm12)


def str_w(rt: int, rn: int, imm12: int = 0) -> bytes:
    """STR.W Rt, [Rn, #imm12] (T3, 32-bit, imm12 in 0..4095)."""
    _reg(rt, rn, allow_sp_pc=True)
    assert 0 <= imm12 < 4096, f"str_w offset out of range: {imm12}"
    return h(0xF8C0 | rn) + h(rt << 12 | imm12)


def ldr(rt: int, rn: int, imm: int = 0) -> bytes:
    """LDR Rt, [Rn, #imm] — chooses 16-bit T1 when eligible, else 32-bit LDR.W T3."""
    if 0 <= rt <= 7 and 0 <= rn <= 7 and imm % 4 == 0 and 0 <= imm <= 124:
        return ldr_imm(rt, rn, imm)
    return ldr_w(rt, rn, imm)


def str_mem(rt: int, rn: int, imm: int = 0) -> bytes:
    """STR Rt, [Rn, #imm] — chooses 16-bit T1 when eligible, else 32-bit STR.W T3."""
    if 0 <= rt <= 7 and 0 <= rn <= 7 and imm % 4 == 0 and 0 <= imm <= 124:
        return str_imm(rt, rn, imm)
    return str_w(rt, rn, imm)


def ldr_reg(rt: int, rn: int, rm: int) -> bytes:
    """LDR Rt, [Rn, Rm] (T1, 16-bit)."""
    _lo(rt, rn, rm)
    return h(0x5800 | rm << 6 | rn << 3 | rt)


def str_reg(rt: int, rn: int, rm: int) -> bytes:
    """STR Rt, [Rn, Rm] (T1, 16-bit)."""
    _lo(rt, rn, rm)
    return h(0x5000 | rm << 6 | rn << 3 | rt)


def str_sp(rt: int, imm: int = 0) -> bytes:
    """STR Rt, [SP, #imm] (T2, 16-bit, imm in 0..1020, multiple of 4)."""
    _lo(rt)
    assert imm % 4 == 0 and 0 <= imm <= 1020
    return h(0x9000 | rt << 8 | imm // 4)


def ldr_sp(rt: int, imm: int = 0) -> bytes:
    """LDR Rt, [SP, #imm] (T2, 16-bit, imm in 0..1020, multiple of 4)."""
    _lo(rt)
    assert imm % 4 == 0 and 0 <= imm <= 1020
    return h(0x9800 | rt << 8 | imm // 4)


def ldrb_imm(rt: int, rn: int, imm: int = 0) -> bytes:
    """LDRB Rt, [Rn, #imm] (T1, 16-bit, imm in 0..31)."""
    _lo(rt, rn)
    assert 0 <= imm <= 31
    return h(0x7800 | imm << 6 | rn << 3 | rt)


def strb_imm(rt: int, rn: int, imm: int = 0) -> bytes:
    """STRB Rt, [Rn, #imm] (T1, 16-bit, imm in 0..31)."""
    _lo(rt, rn)
    assert 0 <= imm <= 31
    return h(0x7000 | imm << 6 | rn << 3 | rt)


def ldrb_w(rt: int, rn: int, imm12: int = 0) -> bytes:
    """LDRB.W Rt, [Rn, #imm12] (T2, 32-bit, imm12 in 0..4095)."""
    _reg(rt, rn, allow_sp_pc=True)
    assert 0 <= imm12 < 4096
    return h(0xF890 | rn) + h(rt << 12 | imm12)


def strb_w(rt: int, rn: int, imm12: int = 0) -> bytes:
    """STRB.W Rt, [Rn, #imm12] (T2, 32-bit, imm12 in 0..4095)."""
    _reg(rt, rn, allow_sp_pc=True)
    assert 0 <= imm12 < 4096
    return h(0xF880 | rn) + h(rt << 12 | imm12)


def ldrb(rt: int, rn: int, imm: int = 0) -> bytes:
    """LDRB Rt, [Rn, #imm] — chooses 16-bit T1 when eligible, else 32-bit LDRB.W T2."""
    if 0 <= rt <= 7 and 0 <= rn <= 7 and 0 <= imm <= 31:
        return ldrb_imm(rt, rn, imm)
    return ldrb_w(rt, rn, imm)


def strb(rt: int, rn: int, imm: int = 0) -> bytes:
    """STRB Rt, [Rn, #imm] — chooses 16-bit T1 when eligible, else 32-bit STRB.W T2."""
    if 0 <= rt <= 7 and 0 <= rn <= 7 and 0 <= imm <= 31:
        return strb_imm(rt, rn, imm)
    return strb_w(rt, rn, imm)


def ldrb_reg(rt: int, rn: int, rm: int) -> bytes:
    """LDRB Rt, [Rn, Rm] (T1, 16-bit)."""
    _lo(rt, rn, rm)
    return h(0x5C00 | rm << 6 | rn << 3 | rt)


def strb_reg(rt: int, rn: int, rm: int) -> bytes:
    """STRB Rt, [Rn, Rm] (T1, 16-bit)."""
    _lo(rt, rn, rm)
    return h(0x5400 | rm << 6 | rn << 3 | rt)


def ldrh_imm(rt: int, rn: int, imm: int = 0) -> bytes:
    """LDRH Rt, [Rn, #imm] (T1, 16-bit, imm in 0..62, multiple of 2)."""
    _lo(rt, rn)
    assert imm % 2 == 0 and 0 <= imm <= 62
    return h(0x8800 | (imm // 2) << 6 | rn << 3 | rt)


def strh_imm(rt: int, rn: int, imm: int = 0) -> bytes:
    """STRH Rt, [Rn, #imm] (T1, 16-bit, imm in 0..62, multiple of 2)."""
    _lo(rt, rn)
    assert imm % 2 == 0 and 0 <= imm <= 62
    return h(0x8000 | (imm // 2) << 6 | rn << 3 | rt)


def ldrh_w_imm(rt: int, rn: int, imm12: int = 0) -> bytes:
    """LDRH.W Rt, [Rn, #imm12] (T2, 32-bit, imm12 in 0..4095)."""
    _reg(rt, rn, allow_sp_pc=True)
    assert 0 <= imm12 < 4096
    return h(0xF8B0 | rn) + h(rt << 12 | imm12)


def strh_w_imm(rt: int, rn: int, imm12: int = 0) -> bytes:
    """STRH.W Rt, [Rn, #imm12] (T2, 32-bit, imm12 in 0..4095)."""
    _reg(rt, rn, allow_sp_pc=True)
    assert 0 <= imm12 < 4096
    return h(0xF8A0 | rn) + h(rt << 12 | imm12)


def ldrh_reg(rt: int, rn: int, rm: int) -> bytes:
    """LDRH Rt, [Rn, Rm] (T1, 16-bit)."""
    _lo(rt, rn, rm)
    return h(0x5A00 | rm << 6 | rn << 3 | rt)


def strh_reg(rt: int, rn: int, rm: int) -> bytes:
    """STRH Rt, [Rn, Rm] (T1, 16-bit)."""
    _lo(rt, rn, rm)
    return h(0x5200 | rm << 6 | rn << 3 | rt)


def strh_w_reg_lsl1(rt: int, rn: int, rm: int) -> bytes:
    """STRH.W Rt, [Rn, Rm, LSL #1] (T2, 32-bit)."""
    return h(0xF820 | rn) + h(rt << 12 | 1 << 4 | rm)


def ldr_lit_n(rt: int, off: int) -> bytes:
    """LDR Rt, [PC, #off] (T1, 16-bit, off from Align(PC, 4) in 0..1020)."""
    _lo(rt)
    assert off % 4 == 0 and 0 <= off <= 1020, off
    return h(0x4800 | rt << 8 | off // 4)


def ldr_lit_w(rt: int, off: int) -> bytes:
    """LDR.W Rt, [PC, #+-off] (T2, 32-bit, off in -4095..4095)."""
    assert -4095 <= off <= 4095 and rt < 13, off
    return h(0xF85F | (0x80 if off >= 0 else 0)) + h(rt << 12 | abs(off))


def adr(addr: int, target: int, rd: int) -> bytes:
    """ADR Rd, label (T1, 16-bit, word-aligned forward offset 0..1020 from Align(PC, 4))."""
    _lo(rd)
    base_pc = (addr + 4) & ~3
    off = target - base_pc
    assert off % 4 == 0 and 0 <= off <= 1020, hex(off)
    return h(0xA000 | rd << 8 | (off // 4))


# ---- Move / Immediate / Arithmetic / Logical -------------------------------

def movs_imm(rd: int, imm: int) -> bytes:
    """MOVS Rd, #imm8 (T1, 16-bit)."""
    _lo(rd)
    assert 0 <= imm <= 255
    return h(0x2000 | rd << 8 | imm)


def movw(rd: int, imm16: int) -> bytes:
    """MOVW Rd, #imm16 (T3, 32-bit)."""
    assert 0 <= imm16 <= 0xFFFF and 0 <= rd < 13
    i = (imm16 >> 11) & 1
    imm4 = imm16 >> 12
    imm3 = (imm16 >> 8) & 7
    imm8 = imm16 & 0xFF
    return h(0xF240 | i << 10 | imm4) + h(imm3 << 12 | rd << 8 | imm8)


def movt(rd: int, imm16: int) -> bytes:
    """MOVT Rd, #imm16 (T1, 32-bit)."""
    assert 0 <= imm16 <= 0xFFFF and 0 <= rd < 13
    i = (imm16 >> 11) & 1
    imm4 = imm16 >> 12
    imm3 = (imm16 >> 8) & 7
    imm8 = imm16 & 0xFF
    return h(0xF2C0 | i << 10 | imm4) + h(imm3 << 12 | rd << 8 | imm8)


def mov_reg(rd: int, rm: int) -> bytes:
    """MOV Rd, Rm (T1, 16-bit, no flag update)."""
    return h(0x4600 | (rd >> 3) << 7 | rm << 3 | (rd & 7))


def cmp_imm(rn: int, imm: int) -> bytes:
    """CMP Rn, #imm8 (T1, 16-bit)."""
    _lo(rn)
    assert 0 <= imm <= 255
    return h(0x2800 | rn << 8 | imm)


def cmp_w_imm(rn: int, imm: int) -> bytes:
    """CMP.W Rn, #imm8 (T2, 32-bit)."""
    assert 0 <= imm <= 255 and 0 <= rn < 15
    return h(0xF1B0 | rn) + h(0x0F00 | imm)


def cmp_reg(rn: int, rm: int) -> bytes:
    """CMP Rn, Rm (T1 for low regs, T2 when either is high)."""
    if rn < 8 and rm < 8:
        return h(0x4280 | rm << 3 | rn)
    return h(0x4500 | (rn >> 3) << 7 | rm << 3 | (rn & 7))


def subs_imm8(rdn: int, imm: int) -> bytes:
    """SUBS Rdn, #imm8 (T2, 16-bit)."""
    _lo(rdn)
    assert 0 <= imm <= 255
    return h(0x3800 | rdn << 8 | imm)


def adds_imm8(rdn: int, imm: int) -> bytes:
    """ADDS Rdn, #imm8 (T2, 16-bit)."""
    _lo(rdn)
    assert 0 <= imm <= 255
    return h(0x3000 | rdn << 8 | imm)


def subs_imm3(rd: int, rn: int, imm: int) -> bytes:
    """SUBS Rd, Rn, #imm3 (T1, 16-bit)."""
    _lo(rd, rn)
    assert 0 <= imm <= 7
    return h(0x1E00 | imm << 6 | rn << 3 | rd)


def adds_imm3(rd: int, rn: int, imm: int) -> bytes:
    """ADDS Rd, Rn, #imm3 (T1, 16-bit)."""
    _lo(rd, rn)
    assert 0 <= imm <= 7
    return h(0x1C00 | imm << 6 | rn << 3 | rd)


def adds_reg(rd: int, rn: int, rm: int) -> bytes:
    """ADDS Rd, Rn, Rm (T1, 16-bit)."""
    _lo(rd, rn, rm)
    return h(0x1800 | rm << 6 | rn << 3 | rd)


def subs_reg(rd: int, rn: int, rm: int) -> bytes:
    """SUBS Rd, Rn, Rm (T1, 16-bit)."""
    _lo(rd, rn, rm)
    return h(0x1A00 | rm << 6 | rn << 3 | rd)


def tst_reg(rn: int, rm: int) -> bytes:
    """TST Rn, Rm (T1, 16-bit)."""
    _lo(rn, rm)
    return h(0x4200 | rm << 3 | rn)


def ands_reg(rdn: int, rm: int) -> bytes:
    """ANDS Rdn, Rm (T1, 16-bit)."""
    _lo(rdn, rm)
    return h(0x4000 | rm << 3 | rdn)


def orrs_reg(rdn: int, rm: int) -> bytes:
    """ORRS Rdn, Rm (T1, 16-bit)."""
    _lo(rdn, rm)
    return h(0x4300 | rm << 3 | rdn)


def eors_reg(rdn: int, rm: int) -> bytes:
    """EORS Rdn, Rm (T1, 16-bit)."""
    _lo(rdn, rm)
    return h(0x4040 | rm << 3 | rdn)


def bics_reg(rdn: int, rm: int) -> bytes:
    """BICS Rdn, Rm (T1, 16-bit)."""
    _lo(rdn, rm)
    return h(0x4380 | rm << 3 | rdn)


def lsls_imm(rd: int, rm: int, imm: int) -> bytes:
    """LSLS Rd, Rm, #imm5 (T1, 16-bit)."""
    _lo(rd, rm)
    assert 0 <= imm <= 31
    return h(0x0000 | imm << 6 | rm << 3 | rd)


def lsrs_imm(rd: int, rm: int, imm: int) -> bytes:
    """LSRS Rd, Rm, #imm5 (T1, 16-bit)."""
    _lo(rd, rm)
    assert 1 <= imm <= 31
    return h(0x0800 | imm << 6 | rm << 3 | rd)


def lsls_reg(rdn: int, rm: int) -> bytes:
    """LSLS Rdn, Rm (T2, 16-bit)."""
    _lo(rdn, rm)
    return h(0x4080 | rm << 3 | rdn)


def lsrs_reg(rdn: int, rm: int) -> bytes:
    """LSRS Rdn, Rm (T2, 16-bit)."""
    _lo(rdn, rm)
    return h(0x40C0 | rm << 3 | rdn)


def muls(rdm: int, rn: int) -> bytes:
    """MULS Rdm, Rn, Rdm (T1, 16-bit)."""
    _lo(rdm, rn)
    return h(0x4340 | rn << 3 | rdm)


def add_sp_imm(imm: int) -> bytes:
    """ADD SP, SP, #imm (T2, 16-bit, imm in 0..508, multiple of 4)."""
    assert imm % 4 == 0 and 0 <= imm <= 508
    return h(0xB000 | imm // 4)


def sub_sp_imm(imm: int) -> bytes:
    """SUB SP, SP, #imm (T1, 16-bit, imm in 0..508, multiple of 4)."""
    assert imm % 4 == 0 and 0 <= imm <= 508
    return h(0xB080 | imm // 4)


# ---- Stack Push / Pop ------------------------------------------------------

def push_lr() -> bytes:
    """PUSH {LR} (T1, 16-bit)."""
    return h(0xB500)


def pop_pc() -> bytes:
    """POP {PC} (T1, 16-bit)."""
    return h(0xBD00)


def push_list(regs: Iterable[int], lr: bool = False) -> bytes:
    """PUSH {regs, [lr]} (T1, 16-bit, low registers r0..r7)."""
    m = 0
    for r in regs:
        _lo(r)
        m |= 1 << r
    assert m or lr, "push_list requires at least one register"
    return h(0xB400 | (0x100 if lr else 0) | m)


def pop_list(regs: Iterable[int], pc: bool = False) -> bytes:
    """POP {regs, [pc]} (T1, 16-bit, low registers r0..r7)."""
    m = 0
    for r in regs:
        _lo(r)
        m |= 1 << r
    assert m or pc, "pop_list requires at least one register"
    return h(0xBC00 | (0x100 if pc else 0) | m)


def push(regs: Union[Iterable[int], int] = (), lr: bool = False) -> bytes:
    """PUSH helper supporting r0..r7 (16-bit T1) or r0..r12 (32-bit PUSH.W T2)."""
    if isinstance(regs, int):
        reg_list = [regs]
    else:
        reg_list = list(regs)
    if all(0 <= r <= 7 for r in reg_list):
        return push_list(reg_list, lr=lr)
    m = 0
    for r in reg_list:
        _reg(r)
        m |= 1 << r
    if lr:
        m |= 1 << 14
    assert m != 0, "push requires at least one register"
    return h(0xE92D) + h(m)


def pop(regs: Union[Iterable[int], int] = (), pc: bool = False, lr: bool = False) -> bytes:
    """POP helper supporting r0..r7 (16-bit T1) or r0..r12/lr (32-bit POP.W T2)."""
    if isinstance(regs, int):
        reg_list = [regs]
    else:
        reg_list = list(regs)
    if not lr and all(0 <= r <= 7 for r in reg_list):
        return pop_list(reg_list, pc=pc)
    m = 0
    for r in reg_list:
        _reg(r)
        m |= 1 << r
    if lr:
        m |= 1 << 14
    if pc:
        m |= 1 << 15
    assert m != 0, "pop requires at least one register"
    return h(0xE8BD) + h(m)


# ---- Branches, IT & Control Flow -------------------------------------------

def nop() -> bytes:
    """NOP (T1, 16-bit)."""
    return h(0xBF00)


def bx_lr() -> bytes:
    """BX LR (T1, 16-bit)."""
    return h(0x4770)


def blx_reg(rm: int) -> bytes:
    """BLX Rm (T1, 16-bit)."""
    return h(0x4780 | rm << 3)


def it(firstcond: builtins.str, mask_pattern: builtins.str = "") -> bytes:
    """IT block instruction. mask_pattern: '' (IT), 't'/'e' for 2nd..4th instructions."""
    fc = COND[firstcond]
    bits = [((fc & 1) if c == "t" else (fc & 1) ^ 1) for c in mask_pattern]
    mask = 0
    for i, b_bit in enumerate(bits):
        mask |= b_bit << (3 - i)
    mask |= 1 << (3 - len(bits))
    return h(0xBF00 | fc << 4 | mask)


def b_cond(addr: int, target: int, cond: builtins.str) -> bytes:
    """B<c> label (T1, 16-bit, range -256..+254)."""
    off = target - (addr + 4)
    assert off % 2 == 0 and -256 <= off <= 254, hex(off)
    return h(0xD000 | COND[cond] << 8 | (off >> 1) & 0xFF)


def b_cond_w(addr: int, target: int, cond: builtins.str) -> bytes:
    """B<c>.W label (T3, 32-bit, range -1MB..+1MB)."""
    off = target - (addr + 4)
    assert off % 2 == 0 and -(1 << 20) <= off < (1 << 20), hex(off)
    s = (off >> 20) & 1
    j2 = (off >> 19) & 1
    j1 = (off >> 18) & 1
    imm6 = (off >> 12) & 0x3F
    imm11 = (off >> 1) & 0x7FF
    return h(0xF000 | s << 10 | COND[cond] << 6 | imm6) + h(0x8000 | j1 << 13 | j2 << 11 | imm11)


def b(addr: int, target: int) -> bytes:
    """B label (T2, 16-bit, range -2048..+2046)."""
    off = target - (addr + 4)
    assert off % 2 == 0 and -2048 <= off <= 2046, hex(off)
    return h(0xE000 | (off >> 1) & 0x7FF)


def b_w(addr: int, target: int) -> bytes:
    """B.W label (T4, 32-bit, range -16MB..+16MB)."""
    off = target - (addr + 4)
    assert off % 2 == 0 and -(1 << 24) <= off < (1 << 24), hex(off)
    s = (off >> 24) & 1
    i1 = (off >> 23) & 1
    i2 = (off >> 22) & 1
    imm10 = (off >> 12) & 0x3FF
    imm11 = (off >> 1) & 0x7FF
    j1 = (~i1 ^ s) & 1
    j2 = (~i2 ^ s) & 1
    return h(0xF000 | s << 10 | imm10) + h(0x9000 | j1 << 13 | j2 << 11 | imm11)


def cbz(addr: int, target: int, rn: int, nz: bool = False) -> bytes:
    """CBZ / CBNZ Rn, label (T1, 16-bit, forward offset 0..126)."""
    _lo(rn)
    off = target - (addr + 4)
    assert off % 2 == 0 and 0 <= off <= 126, hex(off)
    i = (off >> 6) & 1
    imm5 = (off >> 1) & 0x1F
    return h(0xB100 | (0x800 if nz else 0) | i << 9 | imm5 << 3 | rn)


def cbnz(addr: int, target: int, rn: int) -> bytes:
    """CBNZ Rn, label (T1, 16-bit, forward offset 0..126)."""
    return cbz(addr, target, rn, nz=True)


def bl(addr: int, target: int) -> bytes:
    """BL target (T1, 32-bit, range -16MB..+16MB)."""
    off = target - (addr + 4)
    assert off % 2 == 0 and -(1 << 24) <= off < (1 << 24), hex(off)
    s = (off >> 24) & 1
    i1 = (off >> 23) & 1
    i2 = (off >> 22) & 1
    imm10 = (off >> 12) & 0x3FF
    imm11 = (off >> 1) & 0x7FF
    j1 = (~i1 ^ s) & 1
    j2 = (~i2 ^ s) & 1
    return h(0xF000 | s << 10 | imm10) + h(0xD000 | j1 << 13 | j2 << 11 | imm11)


def raw(data: bytes) -> bytes:
    """Emits raw pre-encoded instruction or literal bytes."""
    return bytes(data)


# Expose `str` helper as requested for Thumb STR instruction encoding
str = str_mem  # noqa: A001

_PC_REL_BRANCHES = {b_cond: 2, b: 2, cbz: 2, cbnz: 2, adr: 2, bl: 4, b_w: 4, b_cond_w: 4}
_FIXED_SIZE_4 = {
    bl, cmp_w_imm, b_w, b_cond_w, movw, movt,
    ldr_w, str_w, ldrb_w, strb_w, ldrh_w_imm, strh_w_imm, strh_w_reg_lsl1,
    ldr_lit_w,
}


def _ins_size(fn, args, kw) -> int:
    if fn is raw:
        return len(args[0])
    if fn in _PC_REL_BRANCHES:
        return _PC_REL_BRANCHES[fn]
    if fn in _FIXED_SIZE_4:
        return 4
    if not any(isinstance(a, builtins.str) for a in args):
        return len(fn(*args, **kw))
    return 2


class Asm:
    """Two-pass sequential Thumb/Thumb-2 assembler with symbolic labels."""

    def __init__(self, base: int):
        self.base = base
        self.items: list[tuple[builtins.str, object]] = []

    def label(self, name: builtins.str) -> None:
        self.items.append(("label", name))

    def emit(self, fn, *args, **kw) -> None:
        self.items.append(("ins", (fn, args, kw)))

    def imm32(self, rd: int, val: int) -> None:
        """Emits MOVW + MOVT pair to load a 32-bit constant into rd."""
        self.emit(movw, rd, val & 0xFFFF)
        self.emit(movt, rd, (val >> 16) & 0xFFFF)

    def assemble(self, external: dict[builtins.str, int] | None = None) -> tuple[bytes, dict[builtins.str, int]]:
        labels: dict[builtins.str, int] = dict(external or {})

        # Pass 1: compute label addresses
        addr = self.base
        for kind, p in self.items:
            if kind == "label":
                labels[p] = addr  # type: ignore[index]
            else:
                fn, args, kw = p  # type: ignore[misc]
                addr += _ins_size(fn, args, kw)

        # Pass 2: encode instructions
        out = bytearray()
        addr = self.base
        for kind, p in self.items:
            if kind == "label":
                continue
            fn, args, kw = p  # type: ignore[misc]
            names = args
            resolved_args = [
                labels[a] if isinstance(a, builtins.str) and a in labels else a
                for a in args
            ]
            for a in resolved_args:
                if isinstance(a, builtins.str) and fn is not it and not (fn in (b_cond, b_cond_w) and a is resolved_args[-1]):
                    raise KeyError(f"Unresolved label '{a}' at {hex(addr)}")
            try:
                if fn in _PC_REL_BRANCHES:
                    enc = fn(addr, *resolved_args, **kw)
                else:
                    enc = fn(*resolved_args, **kw)
            except AssertionError as ex:
                raise AssertionError(
                    f"{ex} ({getattr(fn, '__name__', fn)} at {hex(addr)}, operands {names})"
                ) from None
            out += enc
            addr += len(enc)

        return bytes(out), labels
