"""Cost of measuring CHEAP (guard.py:398-404) on the 135-observation fixture,
when SIGNALED=1 means the law can never read it. No suite runs. Run:
  /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python cheap_cost.py
"""
import os, sys, time
sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
import fluidfix.acts as acts
from fluidfix import MechanicalObserver
from fluidfix.guard import rank_observations
from fluidfix.localize import Packet

HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, "fixture_repay", "mod.py")).read()
src_lines = src.split("\n")
pk = Packet(defect_file="mod.py", failure="", mode="coverage",
            lines=[i + 1 for i, l in enumerate(src_lines) if l.strip()],
            src_lines=src_lines)
obs = MechanicalObserver().observe([pk])[0]
out = "FAILED test_mod.py::test_count_above - assert 3 == 1"

cand_t = [0.0]; cand_n = [0]
_c = acts.candidates
def timed(*a, **k):
    t = time.perf_counter(); r = _c(*a, **k); cand_t[0] += time.perf_counter() - t
    cand_n[0] += 1; return r
acts.candidates = timed

best = None
for _ in range(5):
    cand_t[0] = 0.0; cand_n[0] = 0
    t = time.perf_counter(); rank_observations(src, obs, out); tot = time.perf_counter() - t
    if best is None or tot < best[0]:
        best = (tot, cand_t[0], cand_n[0])
tot, ct, cn = best
print(f"observations ranked: {len(obs)}")
print(f"rank_observations total (best of 5): {tot*1000:.1f} ms")
print(f"  of which candidates() for CHEAP:   {ct*1000:.1f} ms in {cn} calls ({ct/tot*100:.0f}%)")
