#!/usr/bin/env python
"""The CAPPED-escalation fixture (tests/test_engine_fusion.py
test_capped_escalation_raises_budget_and_repairs, pad=0): rank the
observations of the first-pass packet (max_lines=110) and of the
escalation packet (max_lines=990, then unbounded) WITHOUT running the
repair, and report where the true defect line sits. Costs: one failing
run + coverage runs, no candidate suite runs."""
import shutil
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent.parent / "src"))
sys.path.insert(0, str(HERE))
from rank_winners import _capped_files   # noqa: E402
from fluidfix import MechanicalObserver, Oracle   # noqa: E402
from fluidfix.guard import find_candidate_files, rank_observations   # noqa: E402
from fluidfix.localize import build_packet   # noqa: E402
import fluidfix.rank as R   # noqa: E402

d = HERE / "runs" / "heavy_rank_only"
if d.exists():
    shutil.rmtree(d)
d.mkdir(parents=True)
files = _capped_files()
for rel, text in files.items():
    (d / rel).write_text(text)
BUG = next(i + 1 for i, l in enumerate(files["mod.py"].split("\n")) if l.strip() == "if v > limit:")
print(f"defect line: {BUG}  ({files['mod.py'].split(chr(10))[BUG-1].strip()!r})")
oracle = Oracle(str(d), python=sys.executable)
fails, out = oracle.failing_output()
cands = find_candidate_files(oracle, out)
print(f"candidate files: {cands}")
for max_lines in (110, 990, 10 ** 9):
    pk = build_packet(oracle, "mod.py", max_lines=max_lines)
    obs = MechanicalObserver().observe([pk])[0]
    calls = []
    orig = R.rank
    R.rank = lambda x: (calls.append(x), orig(x))[1]
    try:
        ranked = rank_observations("\n".join(pk.src_lines), obs, out, root=str(d), rel="mod.py")
    finally:
        R.rank = orig
    prio = {o.lineno: orig(b) for o, b in zip(obs, calls)}
    bits = {o.lineno: b for o, b in zip(obs, calls)}
    order = [o.lineno for o in ranked]
    pos = order.index(BUG) + 1 if BUG in order else None
    kinds_c = Counter(k for o in obs for k in o.kinds)
    print(f"\nmax_lines={max_lines}: packet lines={len(pk.lines)} truncated={pk.truncated} "
          f"observations={len(obs)} kinds histogram={dict(kinds_c)}")
    print(f"  priority histogram: {dict(sorted(Counter(prio.values()).items()))}")
    if pos:
        ahead = order[:pos - 1]
        print(f"  defect line {BUG} in packet: yes; ranked position {pos}/{len(order)}; "
              f"priority {prio[BUG]} bits={R.BITS and '+'.join(b for i,b in enumerate(R.BITS) if bits[BUG]>>i&1)}; "
              f"same-priority lines ahead: {sum(1 for l in ahead if prio[l] == prio[BUG])}; "
              f"candidate sets (one suite run each, all red) ahead of it: {sum(len([k for k in o.kinds]) for o in ranked[:pos-1])}")
        print(f"  defect line kinds: {[o.kinds for o in obs if o.lineno == BUG]}")
    else:
        print(f"  defect line {BUG} in packet: NO (outside the spread sample) -> first pass cannot repair; CAPPED lane")
