from pathlib import Path

path = Path('scripts/verify_phase1_candidate.py')
text = path.read_text(encoding='utf-8')

old_line = 'print(f"6 SCOPED HOST CHECKS PASSED ({elapsed:.2f}s); HARDWARE RELEASE: NO-GO")'
new_line = 'print(f"6 SCOPED HOST CHECKS PASSED ({elapsed:.2f}s); HARDWARE RELEASE: " + ("NO-GO" if blockers else "REVIEW_REQUIRED (ALL HOST CHECKS PASS)"))'

assert old_line in text
text = text.replace(old_line, new_line)
path.write_text(text, encoding='utf-8')
print("Successfully updated print line")
