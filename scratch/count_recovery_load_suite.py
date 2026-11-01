import sys,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'src'),str(ROOT/'tests')]
import verify_recovery_candidate as verifier
class Collected(Exception):
    pass
counts={}
def collect(self,suite):raise Collected(suite.countTestCases())
unittest.TextTestRunner.run=collect
for key in ('full','core'):
    try:verifier.verify(ROOT/f'logs/recovery-load-short-read-20261031/collect-{key}',core_only=key=='core')
    except Collected as e:counts[key]=e.args[0]
assert counts==dict(full=170,core=155),counts
(ROOT/'logs/recovery-load-short-read-20261031/suite-layout.json').write_text(json.dumps(dict(**counts,executed=False,long_tests_excluded=15),indent=2))
print(counts)
