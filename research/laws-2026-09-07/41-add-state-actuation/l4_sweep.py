#!/usr/bin/env python
"""Does a longer stability filter kill the flaky witness? Sweep REPEATS."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import difftest
D = os.path.join(HERE, "limits_runs", "L4_nondeterministic")
CANDS = [(6, "    return n + random.randint(0, 3)"),
         (6, "    return n + random.randint(1, 3)")]
for k in (2, 3, 5, 10):
    difftest.REPEATS = k
    hits = sum(1 for _ in range(20)
               if difftest.differentiate(D, "jitter.py", 6, CANDS,
                                         HERE).get("separated"))
    print(f"REPEATS={k:<3} witnesses emitted on a nondeterministic pair: {hits}/20")
