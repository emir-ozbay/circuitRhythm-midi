"""Check initial handoff file hashes. No network/device access."""
import hashlib,json,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
def check(root):
    manifest=json.loads((root/'PACKAGE-MANIFEST.json').read_text(encoding='utf-8'))
    errors=[]
    for entry in manifest['files']:
        rel=Path(entry['path'])
        if rel.is_absolute() or '..' in rel.parts:
            errors.append('Unsafe manifest path: '+entry['path']);continue
        p=root/rel
        if not p.is_file():errors.append('Missing: '+entry['path']);continue
        data=p.read_bytes()
        if len(data)!=entry['bytes'] or hashlib.sha256(data).hexdigest()!=entry['sha256']:
            errors.append('Changed: '+entry['path'])
    return errors,len(manifest['files'])
if __name__=='__main__':
    errors,count=check(root)
    if errors:
        print('\n'.join(errors));print('Intentional edits also cause differences; do not blindly replace modified work.');sys.exit(1)
    print(f'PACKAGE PASS: {count} files match initial manifest.')
