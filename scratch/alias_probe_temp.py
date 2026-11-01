import sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'scripts'))
from inspect_ui import load_image
from capstone import *
b=load_image();m=Cs(CS_ARCH_ARM,CS_MODE_THUMB|CS_MODE_MCLASS)
rows=[]
for a,z in [(0x8036fa8,0x8036fde),(0x8033120,0x803314a),(0x8036950,0x8036a02),(0x8048ae0,0x8048b78),(0x802819c,0x802820c),(0x80283cc,0x80283fa)]:
 rows.append(f'RANGE {a:08X}..{z:08X}')
 rows.extend(f'{i.address:08X} {i.bytes.hex():12s} {i.mnemonic} {i.op_str}' for i in m.disasm(b[a-0x8010000:z-0x8010000],a))
(root/'logs'/'project-alias-constructors.txt').write_text('\n'.join(rows))
print('constructor disassembly saved')
