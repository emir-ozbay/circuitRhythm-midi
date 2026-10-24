"""Reproduce M1 stock-code evidence and tests; never accesses a device."""
import datetime
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import struct
import subprocess
import sys

from inspect_ui import BASE, EXPECTED, ROOT, load_image

# Bounded diagnostic windows; embedded literal/table data is not executable proof.
WINDOWS = ["080295b4:1a", "08040108:22", "0803d7fe:5c", "0804d7a0:86",
           "0804dc50:62", "0804df3e:44", "0805800e:10", "0804dd1c:13a",
           "0805cb04:64", "0805ccf0:9c", "0805ce48:3c", "0805cffe:22",
           "0805d3f8:26", "0805d588:b6", "0805cf24:da",
           "0805d094:328", "0805d3bc:1a", "0803fbec:58", "08048208:1bc"]


def main():
    if sys.flags.optimize:
        raise RuntimeError("Do not use Python -O")
    for name, version in (("capstone", "5.0.9"), ("unicorn", "2.1.4")):
        if importlib.metadata.version(name) != version:
            raise RuntimeError("Install pinned requirements.txt")
    image = load_image()
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    out = ROOT / "logs" / ("ui-audit-" + stamp)
    out.mkdir(parents=True)
    env = dict(os.environ, PYTHONUTF8="1")
    env.pop("PYTHONOPTIMIZE", None)
    for name, args in (("tests.txt", ["tests/test_ui_contracts.py"]),
                       ("disassembly.txt", ["scripts/inspect_ui.py", *WINDOWS])):
        result = subprocess.run([sys.executable, *args], cwd=ROOT, env=env,
                                capture_output=True, text=True, encoding="utf-8", timeout=60)
        (out / name).write_text(result.stdout + result.stderr, encoding="utf-8")
        if result.returncode:
            raise RuntimeError(f"{name} failed; inspect {out}")
    provenance = json.loads((ROOT / "analysis/provenance.json").read_text(encoding="utf-8"))
    for entry in provenance:
        path = ROOT / "analysis" / entry["local_path"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
            raise RuntimeError(f"Upstream snapshot changed: {path}")
    report = {
        "result": "PASS", "utc": stamp, "python": sys.version, "platform": platform.platform(),
        "stock_sha256": EXPECTED, "image_sha256": hashlib.sha256(image).hexdigest(),
        "upstream_snapshots_verified": len(provenance),
        "tests": "7 behavior tests; stock functions in synthetic RAM; dispatch callbacks mocked only in dispatch test; timer start/stop stubbed to isolate RTOS queues",
        "not_tested": ["physical pads/LEDs/MIDI", "RTOS concurrency and timer queues",
                       "save/load", "gate/tie lifetime", "Mutate", "bootloader/recovery"],
        "physical_device_accessed": False, "custom_firmware_built": False,
        "firmware_uploaded": False, "patch_applied": False,
        "windows": [{"window": w, "sha256": hashlib.sha256(image[int(w.split(':')[0], 16) - BASE:
                       int(w.split(':')[0], 16) - BASE + int(w.split(':')[1], 16)]).hexdigest()} for w in WINDOWS],
        "candidate_only": {"instruction_address": "0x0805cf68", "image_offset": "0x4cf68",
                           "stock_instruction": image[0x4CF68:0x4CF6A].hex(),
                           "proposed_instruction": "1e22", "original_palette_index": 31,
                           "proposed_palette_index": 30,
                           "palette_31_word": hex(struct.unpack_from('<H', image, 0x08062AB0 - BASE + 62)[0]),
                           "palette_30_word": hex(struct.unpack_from('<H', image, 0x08062AB0 - BASE + 60)[0]),
                           "status": "DESIGN ONLY; no patch, compilation or SysEx output"}}
    (out / "summary.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("UI AUDIT PASS (synthetic RAM and static evidence only)")
    print(out)


if __name__ == "__main__":
    main()
