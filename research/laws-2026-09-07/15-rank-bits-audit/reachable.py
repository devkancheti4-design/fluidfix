#!/usr/bin/env python
"""Exhaustive: which of the ranking law's 8 priorities can the BODY reach,
given which bits it can and cannot set (from reading guard.rank_observations
and observers.MechanicalObserver)?

  /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python reachable.py

Constraints (each one is cited to a line in REPORT.md):
  FAILONLY  never passed to observe_bits         -> always 0
  RETRIED   never passed by either call site     -> always 0
  SIGNALED  MechanicalObserver emits an Observation only when kinds != []
            -> always 1 on the mechanical path; can be 0 only for a
               ClaudeObserver observation with kinds=[] (which the repair
               loop then refuses anyway)
"""
import sys

sys.dont_write_bytecode = True
from fluidfix.rank import BITS, rank  # noqa: E402

FAILONLY, RETRIED, SIGNALED = (BITS.index("FAILONLY"), BITS.index("RETRIED"),
                               BITS.index("SIGNALED"))


def constructible(x, mechanical):
    if (x >> FAILONLY) & 1 or (x >> RETRIED) & 1:
        return False
    if mechanical and not (x >> SIGNALED) & 1:
        return False
    return True


for label, mech in (("mechanical observer", True), ("claude observer", False)):
    xs = [x for x in range(256) if constructible(x, mech)]
    prios = sorted({rank(x) for x in xs})
    print(f"{label}: {len(xs)}/256 bytes constructible by the body; "
          f"priorities reachable = {prios}; unreachable = "
          f"{sorted(set(range(8)) - set(prios))}")
    by = {}
    for x in xs:
        by.setdefault(rank(x), []).append(x)
    for p in sorted(by):
        ex = by[p][0]
        names = "+".join(n for i, n in enumerate(BITS) if (ex >> i) & 1) or "(none)"
        print(f"   p={p}: {len(by[p]):2d} bytes, e.g. 0x{ex:02x} = {names}")

# and: the bit that decides, for every constructible byte on the mechanical path
print("\nOn the mechanical path the ruling is decided by:")
print("   FRAME set            -> p=0")
print("   else NAMED set       -> p=2")
print("   else (SIGNALED)      -> p=3   (RECENT/CHEAP/DENSE never reach the ruling)")
check = all(rank(x) == (0 if x & 1 else 2 if x & 4 else 3)
            for x in range(256) if constructible(x, True))
print("   verified exhaustively over the constructible bytes:", check)
