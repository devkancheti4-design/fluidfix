#!/usr/bin/env python
"""Which measured bits can ever DECIDE, and what the inert ones cost.

rank() returns the index of the LOWEST set evidence bit (cli.py:479-491 spells
the spec out). MechanicalObserver only emits an Observation when kinds != []
(observers.py:36-41), so SIGNALED (bit 3) is always 1 on the zero-token path.
Everything above bit 3 therefore cannot reach the ruling. This script proves
that exhaustively and then times what computing the inert CHEAP bit costs.

  ./run.sh /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python inert_bits.py
"""
from __future__ import annotations

import os
import sys
import time

sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

import fluidfix.acts as A            # noqa: E402
import fluidfix.guard as G           # noqa: E402
from fluidfix.acts import Observation  # noqa: E402
from fluidfix.rank import BITS, rank  # noqa: E402

print("== 1. exhaustive: with SIGNALED forced on and FAILONLY/RETRIED forced")
print("      off (the mechanical path's constraint set), can RECENT, CHEAP or")
print("      DENSE ever change the ruling?")
FRAME, FAILONLY, NAMED, SIGNALED = 0, 1, 2, 3
RECENT, CHEAP, DENSE, RETRIED = 4, 5, 6, 7
changed = []
for base in range(256):
    if (base >> FAILONLY) & 1 or (base >> RETRIED) & 1:
        continue
    if not (base >> SIGNALED) & 1:
        continue
    for b in (RECENT, CHEAP, DENSE):
        if not (base >> b) & 1:
            if rank(base | (1 << b)) != rank(base):
                changed.append((base, b))
print(f"   bytes checked: 32   (byte, bit) pairs where flipping RECENT/CHEAP/"
      f"DENSE changes rank(): {len(changed)}")
print(f"   -> {'NONE. all three are inert on this path.' if not changed else changed[:5]}")
print()
print("   and the same three CAN decide when SIGNALED is off (Claude observer,")
print("   kinds=[]):")
for b in (RECENT, CHEAP, DENSE):
    print(f"     rank(0)={rank(0)}  rank(1<<{b})={rank(1 << b)}  "
          f"({BITS[b]})")
print()

print("== 2. cost of computing CHEAP, which cannot decide on the mechanical path")
SRC = "\n".join(["def f(n):"] + [f"    n = n + {i}" for i in range(1, 111)]
                + ["    return n"]) + "\n"
OBS = [Observation(lineno=i + 2, kinds=[1, 3]) for i in range(110)]
OUT = "FAILED test_m.py::test_f - AssertionError\n"

t0 = time.perf_counter()
G.rank_observations(SRC, OBS, OUT, rel="m.py")
t_full = time.perf_counter() - t0

_orig_cand = A.candidates


def _boom(*a, **k):
    raise RuntimeError("skip CHEAP")


A.candidates = _boom     # guard's priority() does `from .acts import ...`
                         # inside the try, so this makes cheap=False for free
t0 = time.perf_counter()
G.rank_observations(SRC, OBS, OUT, rel="m.py")
t_nocheap = time.perf_counter() - t0
A.candidates = _orig_cand

print(f"   110 observations, kinds=[1,3]")
print(f"   rank_observations WITH CHEAP measured : {t_full * 1000:.1f} ms")
print(f"   same call with candidates() raising   : {t_nocheap * 1000:.1f} ms")
print(f"   share of the ranking call spent on a bit that cannot decide: "
      f"{(t_full - t_nocheap) / t_full:.0%}")
print()
print("   NOTE: guard.py:399-405 wraps the CHEAP measurement in a bare")
print("   `except Exception: cheap = False`, so a genuine failure inside")
print("   candidates() is indistinguishable from 'this line is not cheap'.")
