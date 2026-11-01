from pathlib import Path

path = Path('scripts/verify_phase1_candidate.py')
text = path.read_text(encoding='utf-8')

old_code = """    # Complete load via stock completion callback
    h.word(P + 0x44, target_slot)
    h.call(labels['c_proj_load_complete'], P, target_slot)"""

new_code = """    # Complete load via stock completion callback
    from unicorn.arm_const import UC_ARM_REG_R4, UC_ARM_REG_R5
    store_44 = h.store(bytes(64))
    h.word(P + 0x44, store_44)
    h.u.reg_write(UC_ARM_REG_R4, P)
    h.u.reg_write(UC_ARM_REG_R5, target_slot)
    h.call(labels['c_proj_load_complete'], P, target_slot)"""

assert old_code in text
text = text.replace(old_code, new_code)
path.write_text(text, encoding='utf-8')
print("Updated verify3 successfully")
