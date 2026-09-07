#!/usr/bin/env python
"""How much does each SIGHT bit change the ruling?

For every bit b: over all 128 bytes with b clear, count how many change
priority when b is set, and the worst promotion (priority drop) it causes.
Also reported over the 64 bytes the body can actually reach on the law path
(FRAMED clear -- see finding 1 -- and never FAILONLY&UBIQUITOUS together,
since one specificity cannot be both >= 0.9 and < 0.25).

Usage:  .venv/bin/python bit_influence.py
"""
import sys

sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix.sight import BITS, sight            # noqa: E402

FRAMED, FAILONLY, UBIQ = 1 << 0, 1 << 3, 1 << 7


def report(name, universe):
    print(f"\n== {name}: {len(universe)} bytes ==")
    print(f"{'bit':11} {'flips ruling':>12} {'of':>4}  {'best promotion':>14}"
          f"  {'ever demotes':>12}")
    for i, b in enumerate(BITS):
        pool = [x for x in universe if not x >> i & 1 and (x | 1 << i) in universe]
        ch = [(sight(x), sight(x | 1 << i)) for x in pool]
        flips = sum(1 for a, c in ch if a != c)
        best = min((c - a for a, c in ch), default=0)
        dem = sum(1 for a, c in ch if c > a)
        print(f"{b:11} {flips:12d} {len(pool):4d}  {best:14d}  {dem:12d}")


ALL = list(range(256))
REACHABLE = [x for x in ALL
             if not x & FRAMED and not (x & FAILONLY and x & UBIQ)]

report("all 256 inputs", ALL)
report("bytes the body reaches on the law path", REACHABLE)

print("\n== priorities emitted ==")
print("  all 256 inputs                :", sorted({sight(x) for x in ALL}))
print("  law-path-reachable bytes      :", sorted({sight(x) for x in REACHABLE}))
print("  FRAMED-carrying bytes         :",
      sorted({sight(x) for x in ALL if x & FRAMED}))
