#!/usr/bin/env python
"""Which of the ranking law's 8 priority classes can the BODY actually reach?

Pure analysis of src/fluidfix/rank.py plus the constants the body pins
(guard.py rank_observations): SIGNALED = bool(obs.kinds), FAILONLY never
measured (documented in the docstring), RETRIED never passed by either
call site (proved by dead_lanes.py). No suite runs.
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent.parent / "src"))
from fluidfix.rank import BITS, rank   # noqa: E402

B = {b: 1 << i for i, b in enumerate(BITS)}


def bits_of(x):
    return "+".join(b for b in BITS if x & B[b]) or "-"


print("== all 256 inputs ==")
allp = Counter(rank(x) for x in range(256))
print("priority histogram over all 256:", dict(sorted(allp.items())))
print("distinct priorities over all 256:", sorted(allp))

print("\n== the body's pinned lanes ==")
print("SIGNALED: guard.py:409  signaled=bool(obs.kinds)  -> 1 whenever an observation exists")
print("FAILONLY: never measured (guard.py:351-354 docstring)          -> always 0")
print("RETRIED : neither rank_observations call site passes retried=   -> always 0")

FREE = ["FRAME", "NAMED", "RECENT", "CHEAP", "DENSE"]
reach = {}
for m in range(32):
    x = B["SIGNALED"]
    for i, b in enumerate(FREE):
        if m >> i & 1:
            x |= B[b]
    reach[x] = rank(x)
print(f"\nbytes the body can construct today: {len(reach)}")
print("their priority histogram:", dict(sorted(Counter(reach.values()).items())))
print("distinct priorities reachable today:", sorted(set(reach.values())))
for p in sorted(set(reach.values())):
    ex = sorted(bits_of(x) for x in reach if reach[x] == p)
    print(f"  priority {p}: {len(ex)} bytes, e.g. {ex[0]} ... {ex[-1]}")

print("\n== which free lanes can move the priority at all, given SIGNALED=1 ==")
for b in FREE:
    moved = [x for x in reach if (x ^ B[b]) in reach and reach[x] != reach[x ^ B[b]]]
    print(f"  {b:9s}: flipping it changes rank() on {len(moved):2d} of the {len(reach)} reachable bytes")

print("\n== what measuring FAILONLY would add (SIGNALED=1, RETRIED=0) ==")
with_fo = {}
for x in list(reach):
    with_fo[x] = rank(x)
    with_fo[x | B["FAILONLY"]] = rank(x | B["FAILONLY"])
print("bytes:", len(with_fo), "distinct priorities:", sorted(set(with_fo.values())))
sep = sum(1 for x in reach if rank(x) != rank(x | B["FAILONLY"]))
print(f"reachable bytes whose priority FAILONLY would change: {sep}/{len(reach)}")
for x in sorted(reach):
    if rank(x) != rank(x | B["FAILONLY"]):
        print(f"   {bits_of(x):40s} {rank(x)} -> {rank(x | B['FAILONLY'])}")

print("\n== what passing RETRIED would add (the veto) ==")
vet = sum(1 for x in reach if rank(x) != rank(x | B["RETRIED"]))
print(f"reachable bytes whose priority RETRIED would change: {vet}/{len(reach)}")
print("rank(x|RETRIED) values:", sorted({rank(x | B["RETRIED"]) for x in reach}),
      "(7 = the floor; the veto sends every reachable byte there)")

print("\n== the law's own tie structure ==")
print("The law returns a CLASS, not a score. Inside one class guard.py:425-427 orders by")
print("  (priority, -shared name tokens, input index)  -- i.e. line order when tokens tie.")
