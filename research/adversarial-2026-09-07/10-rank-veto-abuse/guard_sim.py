#!/usr/bin/env python
"""End-to-end counterfactual: guard_once's budget arithmetic, one delta.

Replays guard.py:guard_once for the single-candidate-file case exactly as
shipped -- same third-of-budget first pass, same full-sight escalation, same
half-the-remaining-clock file share -- using fluidfix's OWN unmodified
build_packet / rank_observations / repair. The ONLY difference between the
two arms is whether the escalation's rank call is given `retried=`, the
argument rank.py documents as a veto and guard.py:511/585 never pass.

usage: guard_sim.py <victim-root> <budget-seconds> <mode: shipped|veto>
"""
import os
import shutil
import sys
import time

from fluidfix.guard import rank_observations
from fluidfix.localize import build_packet
from fluidfix.loop import repair
from fluidfix.observers import MechanicalObserver
from fluidfix.oracle import Oracle

root, budget, mode = sys.argv[1], float(sys.argv[2]), sys.argv[3]
REL = "pkg/core.py"

o = Oracle(root, python=sys.executable, timeout=300)
t0 = time.time()
total_deadline = t0 + budget
first_deadline = t0 + budget / 3

fails, out = o.failing_output()
assert fails

# ---- pass 0 -------------------------------------------------------------
pkt = build_packet(o, REL)
obs = MechanicalObserver().observe([pkt])[0]
src = "\n".join(pkt.src_lines)
ordered = rank_observations(src, list(obs), out, root=root, rel=REL)
r0 = repair(o, REL, ordered, deadline=first_deadline)
tried0 = {int(a["at"].split(":")[1]) for a in r0.tried_log}
print(f"pass 0   : capped={pkt.truncated} repaired={r0.repaired} "
      f"runs={r0.suite_runs} {r0.seconds:.1f}s "
      f"rejected {len(tried0)} distinct lines")
if r0.repaired:
    raise SystemExit("pass 0 already repaired -- budget too generous")

# ---- escalation (engine law: CAPPED -> RAISE_BUDGET, depth-first) --------
pkt2 = build_packet(o, REL, max_lines=990)
if pkt2.truncated:
    pkt2 = build_packet(o, REL, max_lines=10 ** 9)
obs2 = MechanicalObserver().observe([pkt2])[0]
src2 = "\n".join(pkt2.src_lines)
retried = tried0 if mode == "veto" else set()
ordered2 = rank_observations(src2, list(obs2), out, root=root, rel=REL,
                             retried=retried)
file_share = (total_deadline - time.time()) / 2
r1 = repair(o, REL, ordered2, deadline=min(total_deadline,
                                           time.time() + file_share))
new = [a for a in r1.tried_log
       if int(a["at"].split(":")[1]) not in tried0]
print(f"escalate : mode={mode} share={file_share:.1f}s repaired={r1.repaired} "
      f"runs={r1.suite_runs} {r1.seconds:.1f}s")
print(f"           logged {len(r1.tried_log)} rejections, of which "
       f"{len(r1.tried_log) - len(new)} were lines pass 0 had ALREADY rejected "
       f"({100 * (len(r1.tried_log) - len(new)) / max(1, len(r1.tried_log)):.0f}%)")
print(f"VERDICT  : {'REPAIRED ' + str(r1.lineno) + ': ' + r1.new_line.strip() if r1.repaired else 'REFUSED — ' + r1.reason[:120]}")
print(f"total    : {time.time() - t0:.1f}s of a {budget:.0f}s budget")
