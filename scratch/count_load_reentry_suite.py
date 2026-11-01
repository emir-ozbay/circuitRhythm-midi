"""Collect only; do not imply execution of the full/core test suites."""
import sys,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'src'),str(ROOT/'tests')]
import verify_recovery_candidate as verifier
class Collected(Exception):pass
def collect(self,suite):raise Collected(suite.countTestCases())
unittest.TextTestRunner.run=collect
counts={}
for key in ('full','core'):
    try:verifier.verify(ROOT/f'logs/recovery-load-reentry-20261101/collect-{key}',core_only=key=='core')
    except Collected as e:counts[key]=e.args[0]
assert counts==dict(full=172,core=155),counts
(ROOT/'logs/recovery-load-reentry-20261101/suite-layout.json').write_text(json.dumps(dict(**counts,executed=False,long_tests_excluded=17),indent=2))
print(counts)
