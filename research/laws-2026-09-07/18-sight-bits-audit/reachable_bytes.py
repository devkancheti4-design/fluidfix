#!/usr/bin/env python
"""Which of the 256 SIGHT observation bytes can guard.py:281-288 construct?

Static consequences of the measurement expressions (no suite run):
  FAILONLY   = specificity >= 0.9        (guard.py:284)
  UBIQUITOUS = specificity < 0.25        (guard.py:288)
      -> both set is impossible: one number cannot satisfy both.
  FRAMED     = basename(rel) in framed_files   (guard.py:281), but the law is
      only consulted when NO traceback mention resolved to a non-test project
      file (guard.py:146-150 returns before the law otherwise). So on the law
      path FRAMED can only be set by a basename coincidence with a test-path
      or out-of-root mention; it is never a true frame.
  SMALL      = 0 < n_fail < 80; n_fail > 0 is guaranteed by guard.py:188-189,
      so SMALL is simply n_fail < 80 — every value reachable.
"""
import sys

sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix.sight import BITS, sight   # noqa: E402

FRAMED, FAILONLY, UBIQ = 1 << 0, 1 << 3, 1 << 7

unconstructible = [x for x in range(256) if x & FAILONLY and x & UBIQ]
constructible = [x for x in range(256) if x not in unconstructible]
framed_only_by_coincidence = [x for x in constructible if x & FRAMED]
honest = [x for x in constructible if not x & FRAMED]

print(f"bytes the body can never build (FAILONLY & UBIQUITOUS): {len(unconstructible)}")
print(f"bytes buildable at all:                               {len(constructible)}")
print(f"  of which FRAMED set (only via basename coincidence): {len(framed_only_by_coincidence)}")
print(f"  of which honestly measurable (FRAMED clear):         {len(honest)}")
prios = sorted({sight(x) for x in honest})
print(f"priorities the honest bytes reach: {prios}")
print(f"priorities reached by ANY byte:    {sorted({sight(x) for x in range(256)})}")
# per-bit: how many honest bytes carry it
for i, b in enumerate(BITS):
    n = sum(1 for x in honest if x >> i & 1)
    print(f"  {b:11} set in {n:3d} of {len(honest)} honest bytes")
