"""ONE real guard run on a fixture built here, with the ranking law spied.

Builds a tiny project under ./fixture_ties/, runs guard_once with the
MechanicalObserver, and logs every byte the law was asked, its priority,
the tie-break keys, the `retried` kwarg each caller passed, and how many
suite runs were spent on tied-but-wrong lines before the defect.

Nothing under src/ is edited: rank.rank and guard.rank_observations are
wrapped in THIS process only. Run (one at a time, nice/timeout):
  nice -n 15 timeout 300 /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python guard_tie_log.py
"""
import os
import shutil
import sys

sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
import fluidfix.guard as guardmod  # noqa: E402
import fluidfix.rank as rankmod  # noqa: E402
from fluidfix import MechanicalObserver, Oracle, guard_once  # noqa: E402
from fluidfix.rank import BITS  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "fixture_ties")

# Four `>=` decoys in the SAME def as the defect (line 12), all in the
# failing test's name tokens (count, above), pure assertion failure -> no
# FRAME. Every signaled line lands on the same byte.
MOD = "\n".join([
    "def count_above(xs, t):",       # 1
    "    n = 0",                      # 2
    "    lo = 0",                     # 3
    "    if t >= 1000:",              # 4  decoy
    "        lo = 1",                 # 5
    "    if t >= 2000:",              # 6  decoy
    "        lo = 2",                 # 7
    "    if t >= 3000:",              # 8  decoy
    "        lo = 3",                 # 9
    "    if t >= 4000:",              # 10 decoy
    "        lo = 4",                 # 11
    "    for x in xs:",               # 12
    "        if x >= t:",             # 13 DEFECT: should be >
    "            n += 1",             # 14 signaled (kind 9)
    "    return n + lo",              # 15 signaled (kind 3)
    "",
])
TEST = ("from mod import count_above\n\n"
        "def test_count_above():\n"
        "    assert count_above([1, 5, 5, 9], 5) == 1\n")

if os.path.exists(ROOT):
    shutil.rmtree(ROOT)
os.makedirs(ROOT)
open(os.path.join(ROOT, "mod.py"), "w").write(MOD)
open(os.path.join(ROOT, "test_mod.py"), "w").write(TEST)

# ---- spies (this process only) --------------------------------------------
byte_log = []
_rank = rankmod.rank


def spy_rank(x):
    p = _rank(x)
    byte_log.append((x, p))
    return p


rankmod.rank = spy_rank

calls = []
_ro = guardmod.rank_observations


def spy_ro(src, observations, failing_output, **kw):
    start = len(byte_log)
    out = _ro(src, observations, failing_output, **kw)
    calls.append({"rel": kw.get("rel"), "retried": kw.get("retried"),
                  "n_obs": len(observations),
                  "bytes": byte_log[start:start + len(observations)],
                  "in_order": [o.lineno for o in observations],
                  "out_order": [o.lineno for o in out]})
    return out


guardmod.rank_observations = spy_ro

oracle = Oracle(ROOT, python=sys.executable)
report = guard_once(oracle, MechanicalObserver())

print("== guard result ==")
print(f"  status={report.status} file={report.file} seconds={report.seconds:.1f}")
print("== rank_observations calls ==")
for i, c in enumerate(calls):
    print(f"  call {i}: rel={c['rel']} retried kwarg={c['retried']!r} n_obs={c['n_obs']}")
    print(f"    incoming order: {c['in_order']}")
    for ln, (x, p) in zip(c['in_order'], c['bytes']):
        bits = "+".join(b for j, b in enumerate(BITS) if x >> j & 1) or "(none)"
        print(f"    line {ln:2d}: byte={x:08b} priority={p}  [{bits}]")
    print(f"    law order:      {c['out_order']}")
    from collections import Counter
    sizes = Counter(p for _, p in c['bytes'])
    print(f"    tie classes (priority -> members): {dict(sorted(sizes.items()))}")

res = report.result
if res is not None:
    log = res.tried_log
    print("== suite runs spent (rejected candidates) ==")
    before = [e for e in log if int(e['at'].rsplit(':', 1)[1]) != 13]
    at13 = [e for e in log if int(e['at'].rsplit(':', 1)[1]) == 13]
    print(f"  rejected total: {len(log)} (+{res.tried_more} unlogged)")
    print(f"  rejected on tied-but-wrong lines: {len(before)} "
          f"on lines {sorted({e['at'].rsplit(':',1)[1] for e in before})}")
    print(f"  rejected on the defect line 13:  {len(at13)}")
    print(f"  repaired: {res.repaired}  reason: {res.reason[:120]}")
