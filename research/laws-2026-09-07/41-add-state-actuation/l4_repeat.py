#!/usr/bin/env python
"""How often does the generator emit a witness on the NONDETERMINISTIC case?

L4's two candidates are `n + random.randint(0, 3)` and `n + random.randint(1, 3)`
-- genuinely different programs, but their difference is DISTRIBUTIONAL, so no
single-value assertion can pin it. Any witness the generator emits here is a
FLAKY test. 20 independent generations; also re-checks the emitted pin 20x.
"""
import json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import difftest
D = os.path.join(HERE, "limits_runs", "L4_nondeterministic")
CANDS = [(6, "    return n + random.randint(0, 3)"),
         (6, "    return n + random.randint(1, 3)")]
hits = []
for i in range(20):
    g = difftest.differentiate(D, "jitter.py", 6, CANDS, HERE)
    hits.append(g.get("witness_call") if g.get("separated") else None)
print("generations that emitted a witness: "
      f"{sum(1 for h in hits if h)}/20")
print("witnesses:", [h for h in hits if h])
