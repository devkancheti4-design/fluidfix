#!/usr/bin/env python
"""Counterfactual for the dead RETRIED lane.

Replays guard.py's ESCALATION stage on a fresh copy of the victim, using
fluidfix's OWN unmodified functions, with exactly one difference: the
`retried=` argument that rank.py documents as a veto and that guard.py's two
call sites (guard.py:511, guard.py:585) never pass.

The set handed to `retried=` is not invented -- it is read out of the real
refused run's .fluidfix/last_refusal.json, i.e. the lines fluidfix itself
had already tried and rejected earlier in the SAME pass.

No fluidfix source is modified and no defence is disabled.

usage: counterfactual.py <fresh-victim-root> <refusal-json> <escalation-seconds>
"""
import json
import sys
import time

from fluidfix.guard import rank_observations
from fluidfix.localize import build_packet
from fluidfix.loop import repair
from fluidfix.observers import MechanicalObserver
from fluidfix.oracle import Oracle

root, refusal_json, secs = sys.argv[1], sys.argv[2], float(sys.argv[3])

att = json.load(open(refusal_json))["rejected_candidates"]
lines = [int(a["at"].split(":")[1]) for a in att]
drops = [i for i in range(1, len(lines)) if lines[i] < lines[i - 1]]
pass0_rejected = set(lines[:drops[0]]) if drops else set(lines)
print(f"pass-0 rejected {len(pass0_rejected)} distinct lines (from the real run)")

o = Oracle(root, python=sys.executable, timeout=300)
fails, out = o.failing_output()
assert fails, "victim suite must be red"

# guard.py's escalation stage, verbatim in shape: full-sight packet, observe,
# rank, repair under the file's share of the clock.
pkt = build_packet(o, "pkg/core.py", max_lines=990)
obs = MechanicalObserver().observe([pkt])[0]
src = "\n".join(pkt.src_lines)

import os
path = os.path.join(root, "pkg/core.py")
pristine = open(path, "rb").read()

for tag, retried in (("guard.py as shipped  (retried never passed)", set()),
                     ("with the RETRIED veto fed  (rank.py's contract)",
                      pass0_rejected)):
    open(path, "wb").write(pristine)          # both arms start identical
    o.clear_pyc()
    ordered = rank_observations(src, list(obs), out, root=root,
                                rel="pkg/core.py", retried=retried)
    t0 = time.time()
    res = repair(o, "pkg/core.py", ordered, deadline=t0 + secs)
    print(f"\n{tag}")
    print(f"   -> {'REPAIRED' if res.repaired else 'refused'} "
          f"in {res.suite_runs} suite runs / {res.seconds:.1f}s "
          f"(escalation share was {secs:.0f}s)")
    if res.repaired:
        print(f"      line {res.lineno}: {res.old_line.strip()}  ->  "
              f"{res.new_line.strip()}")
    else:
        print(f"      reason: {res.reason[:160]}")

open(path, "wb").write(pristine)               # leave the fixture as found
o.clear_pyc()
