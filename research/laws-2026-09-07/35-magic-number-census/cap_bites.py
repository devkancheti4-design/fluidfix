#!/usr/bin/env python
"""Does acts._CAP_DEFAULT (32) silently drop candidates on REAL source
lines, and is that drop ever reported to the engine law as CAPPED?

acts.py:406 slices the candidate list to candidate_cap().  Nothing in
loop.py or guard.py learns that the slice dropped anything: the only
CAPPED=True the law is ever given comes from a wall-clock deadline
(loop.py:271, 291) or a truncated packet / truncated file list
(guard.py:508, 538).  So a candidate set that was cut is an UNCAPPED
situation as far as the law is concerned.
"""
import os
import re
import sys
sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix.acts import (ACTS, Observation, act_for, candidate_cap,  # noqa
                           candidates)

SC = ("/private/tmp/claude-501/-Users-kanchetidevieswar-neo/"
      "a9bf7d26-7aef-4c1e-a919-68bc40ac2e97/scratchpad")

print(f"candidate_cap() = {candidate_cap()}  (acts.py:376 _CAP_DEFAULT)")
print("Scanning real source lines for sets the cap would truncate.\n")

# uncapped candidate count == what the applier returned before the slice
def uncapped(line, kind, obs):
    fn = ACTS.get(act_for(kind))
    if fn is None:
        return 0
    out = fn(line, obs)
    return 1 if isinstance(out, str) else len(out)

KINDS_TO_TRY = [0, 1, 3, 8, 9, 10, 12]
worst = []
scanned = 0
for repo, sub in (("box2d", "src"), ("cglm", "include")):
    root = os.path.join(SC, repo, sub)
    if not os.path.isdir(root):
        print(f"{repo}: MISSING"); continue
    for dp, dn, fns in os.walk(root):
        dn[:] = [d for d in dn if d != ".git"]
        for fn in fns:
            if not fn.endswith((".c", ".h")):
                continue
            p = os.path.join(dp, fn)
            try:
                src = open(p, encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            for i, line in enumerate(src.split("\n"), 1):
                if len(line) < 40:
                    continue
                scanned += 1
                obs = Observation(lineno=i, kinds=[])
                for k in KINDS_TO_TRY:
                    n = uncapped(line, k, obs)
                    if n > candidate_cap():
                        worst.append((n, f"{repo}/{os.path.relpath(p, os.path.join(SC, repo))}:{i}", k, line.strip()[:70]))

worst.sort(reverse=True)
print(f"lines scanned: {scanned}")
print(f"candidate sets a cap of {candidate_cap()} truncates: {len(worst)}")
for n, where, k, txt in worst[:10]:
    print(f"  kind {k:>2}: {n:>4} candidates -> {candidate_cap()} kept "
          f"({n - candidate_cap()} dropped)  {where}")
    print(f"           {txt}")
if not worst:
    print("  none on these two trees at the default cap.")
print("\nAnd the truncation is invisible to the law: `grep -n 'CAPPED=' "
      "src/fluidfix/*.py` returns only guard.py:539, loop.py:219 and "
      "pair.py:157 -- none of them fed by candidate_cap().")
