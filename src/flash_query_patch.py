"""Give native disk_ioctl CTRL_SYNC a scratch sink when buff is NULL.

FatFs sync passes CTRL_SYNC0/buff=NULL. The native adapter forwards it as
query1 (writes one byte),then its diagnostic also reads a word from buff.
Use the existing dummy R3 word in its24B frame;it lives through the native
Storage handshake. Query/diagnostic code and all non-sync calls stay native.
No filesystem implementation,additional stack,heap or reserved state.
"""
from patch_firmware import PatchHunk
from thumb_asm import movs_imm,mov_reg,cbnz,push,str_sp,b_w,nop

SITE = 0x08023168
EXPECTED = bytes.fromhex('f8b50d46')
CODE_BASE = 0x0807FE24


def arm_code():
    code = (push([3,4,5,6,7],lr=True)+mov_reg(5,1)
        +cbnz(CODE_BASE+4,CODE_BASE+14,5)+cbnz(CODE_BASE+6,CODE_BASE+14,2)
        +mov_reg(2,13)+movs_imm(3,0)+str_sp(3,0)+b_w(CODE_BASE+14,SITE+4)+nop())
    assert len(code)==20 and CODE_BASE%4==0 and CODE_BASE+len(code)<=0x08080000
    return code


def build_patches():
    code=arm_code()
    return [PatchHunk(SITE,EXPECTED,b_w(SITE,CODE_BASE),'flash_sync_null_scratch'),
            PatchHunk(CODE_BASE,b'\xff'*len(code),code,'flash_sync_null_scratch_guard')]
