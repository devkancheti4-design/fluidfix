"""ONE guard run that forces escalation to re-search the same file, to
measure what the unwired RETRIED veto costs: suite runs re-paid on
(line, candidate) pairs pass 0 already rejected.

Fixture: 130 decoy `if t >= K:` lines inside the failing test's function,
the defect at the end. The pass-0 packet (max_lines=110) is truncated ->
CAPPED -> RAISE_BUDGET -> escalation rebuilds full sight and calls
rank_observations again with NO retried kwarg. `--budget` bounds the whole
thing (pass 0 gets a third).

Nothing under src/ is edited: rank_observations is wrapped in THIS process.
Run (one at a time, nice + 300s alarm):
  nice -n 15 perl -e 'alarm 300; exec @ARGV' -- \
    /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python retried_repay.py
"""
import os
import shutil
import sys
import time
from collections import Counter

sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
import fluidfix.guard as guardmod  # noqa: E402
from fluidfix import MechanicalObserver, Oracle, guard_once  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "fixture_repay")
N_DECOY = 130
BUDGET = 90

lines = ["def count_above(xs, t):", "    n = 0", "    lo = 0"]
for k in range(N_DECOY):
    lines.append(f"    if t >= {1000 + k}:")
    lines.append(f"        lo = {k + 1}")
lines += ["    for x in xs:", "        if x >= t:", "            n += 1",
          "    return n + lo", ""]
MOD = "\n".join(lines)
DEFECT_LINE = 3 + 2 * N_DECOY + 2
TEST = ("from mod import count_above\n\n"
        "def test_count_above():\n"
        "    assert count_above([1, 5, 5, 9], 5) == 1\n")

if os.path.exists(ROOT):
    shutil.rmtree(ROOT)
os.makedirs(ROOT)
open(os.path.join(ROOT, "mod.py"), "w").write(MOD)
open(os.path.join(ROOT, "test_mod.py"), "w").write(TEST)

calls = []
_ro = guardmod.rank_observations


def spy_ro(src, observations, failing_output, **kw):
    out = _ro(src, observations, failing_output, **kw)
    calls.append({"t": time.time(), "retried": kw.get("retried"),
                  "n_obs": len(observations),
                  "first10": [o.lineno for o in out][:10],
                  "defect_rank": ([o.lineno for o in out].index(DEFECT_LINE) + 1
                                  if any(o.lineno == DEFECT_LINE for o in out)
                                  else None)})
    return out


guardmod.rank_observations = spy_ro

t0 = time.time()
oracle = Oracle(ROOT, python=sys.executable)
report = guard_once(oracle, MechanicalObserver(), budget=BUDGET)

print("== guard result ==")
print(f"  status={report.status} file={report.file} seconds={report.seconds:.1f} "
      f"budget={BUDGET} defect_line={DEFECT_LINE}")
print(f"  hint: {(report.hint or '')[:160]}")
print("== rank_observations calls ==")
for i, c in enumerate(calls):
    print(f"  call {i} at +{c['t'] - t0:5.1f}s: retried kwarg={c['retried']!r} "
          f"n_obs={c['n_obs']} defect at position {c['defect_rank']} "
          f"first10={c['first10']}")

att = report.attempts or []
keys = [(a["at"], a["tried"]) for a in att]
dup = Counter(keys)
repaid = sum(n - 1 for n in dup.values() if n > 1)
print("== suite runs across both passes (report.attempts, capped 64/pass) ==")
print(f"  logged rejected candidates: {len(att)}")
print(f"  distinct (line, candidate) pairs: {len(dup)}")
print(f"  RE-PAID: same (line, candidate) rejected again in a later pass: {repaid}")
lines_p = Counter(a["at"] for a in att)
print(f"  lines touched: {len(lines_p)}; most-hit: {lines_p.most_common(3)}")
