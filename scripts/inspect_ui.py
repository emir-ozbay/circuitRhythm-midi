"""Read-only 5706 disassembly windows; no device, patching or upstream builds.

Usage: python scripts/inspect_ui.py ADDRESS:SIZE [...]
Addresses and sizes are hexadecimal. Output is diagnostic, not a CFG proof.
"""
import hashlib
import importlib.util
import sys
from pathlib import Path

from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB, CS_MODE_MCLASS

ROOT = Path(__file__).resolve().parents[1]
BASE = 0x08010000
EXPECTED = "11d604a6b6bef0d41378da03718658c7fe9c959ac24e7fef6563796b9932afaf"


def load_image():
    raw = (ROOT / "stock/circuitrhythm-firmware-5706.syx").read_bytes()
    if hashlib.sha256(raw).hexdigest() != EXPECTED:
        raise ValueError("Stock hash mismatch")
    spec = importlib.util.spec_from_file_location(
        "stock_syx", ROOT / "analysis/sources/arrhythmia/tools/syx.py")
    codec = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(codec)
    decoded = codec.parse(raw)
    if not decoded["crc_ok"] or decoded["device"] != 0x63 or decoded["header_prefix"][0] != 0:
        raise ValueError("Unexpected CRC, product or update target")
    return decoded["image"]


def main():
    image = load_image()
    md = Cs(CS_ARCH_ARM, CS_MODE_THUMB | CS_MODE_MCLASS)
    for arg in sys.argv[1:]:
        address, size = (int(part, 16) for part in arg.split(":"))
        offset = address - BASE
        if address % 2 or size <= 0 or not 0 <= offset < offset + size <= len(image):
            raise ValueError("Window outside stock application or unaligned")
        print(f"\nWINDOW {address:#010x}:{size:x} (may include literal data)")
        for ins in md.disasm(image[offset:offset + size], address):
            print(f"{ins.address:08x} {ins.bytes.hex():10} {ins.mnemonic:10} {ins.op_str}")


if __name__ == "__main__":
    main()
