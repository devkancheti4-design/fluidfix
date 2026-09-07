#!/usr/bin/env python
"""Where the PAIR law's CHEAP threshold sits, and who decides it today.

CHEAP is defined (pair.py:18, PAIR_LAW_PROMPT.md:49) as "the candidate space
is small enough that pairs are affordable under the remaining budget".
That definition is an inequality with two free parameters:

    C(n,2) * t  <=  B        n = single-edit candidates
                             t = seconds per candidate
                             B = remaining budget in seconds

so the threshold on n is  n* = the largest n with n(n-1)/2 * t <= B.

Run under the timeout wrapper.
"""
from __future__ import annotations

import math
import sys

sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")

from fluidfix.pair import ACTS, BITS, pair_law, situation  # noqa: E402

EXH, PAR, DIS, COU, CHE, TAU, CAN, CAP = (1, 2, 4, 8, 16, 32, 64, 128)


def p(*a):
    print(*a)


def n_star(B, t):
    """Largest n whose naive pair space fits in budget B at t s/candidate."""
    if t <= 0:
        return float("inf")
    k = B / t                      # affordable candidate evaluations
    return int((1 + math.isqrt(1 + 8 * int(k))) // 2)


p("=" * 74)
p("1. WHAT THE LAW DOES WITH CHEAP  (exhaustive over all 256 inputs)")
pairs_reached = [x for x in range(256) if ACTS[pair_law(x)] == "PAIR"]
p(f"  inputs whose ruling is PAIR                  : {len(pairs_reached)}/256"
  f"  {[bin(x) for x in pairs_reached]}")
p(f"  ... every one has CHEAP set                  : "
  f"{all(x & CHE for x in pairs_reached)}")
no_cheap = [x for x in range(256) if not x & CHE]
p(f"  inputs with CHEAP clear                      : {len(no_cheap)}/256")
p(f"  ... any of them ruling PAIR                  : "
  f"{any(ACTS[pair_law(x)] == 'PAIR' for x in no_cheap)}")
from collections import Counter  # noqa: E402
p(f"  rulings reachable with CHEAP forced 0        : "
  f"{dict(Counter(ACTS[pair_law(x)] for x in no_cheap))}")
p(f"  rulings reachable with CHEAP free            : "
  f"{dict(Counter(ACTS[pair_law(x)] for x in range(256)))}")

p()
p("=" * 74)
p("2. THE DOCUMENTED BOX2D BYTE, AS THE DOCS STATE IT")
for name, byte in (("PAIR_LAW_PROMPT.md incident 2 as written "
                    "(EXH, no CHEAP/PARTIAL/DISJOINT)", EXH),
                   ("the same byte with TAUGHT, as tests/test_pair_law.py "
                    "pins it", EXH | TAU),
                   ("what a 30-minute budget stop actually measures "
                    "(CAPPED, not EXHAUSTED)", CAP | TAU),
                   ("...with a taught class and partial progress",
                    CAP | TAU | PAR)):
    b = pair_law(byte)
    on = [n for i, n in enumerate(BITS) if byte >> i & 1]
    p(f"  {name}\n      byte={byte:3d} {'|'.join(on) or '0'}  ->  "
      f"{b} {ACTS[b]}")

p()
p("=" * 74)
p("3. THE THRESHOLD  n* = largest n with C(n,2)*t <= B")
budgets = [("--escalate-budget default", 600),
           ("--suite-timeout default", 300),
           ("the recorded cguard run", 3600),
           ("one working day", 8 * 3600),
           ("one week", 7 * 86400),
           ("the 23 days the docs quote", 23 * 86400)]
ts = [("0.20 s  Python fixture (measured, agent 23)", 0.20),
      ("3.46 s  Box2D, CHANGELOG 1479s/428 runs", 1479 / 428),
      ("3.41 s  Box2D, CHANGELOG 116s/34 runs", 116 / 34),
      ("18.80 s Box2D pre-gcov, CHANGELOG", 18.8),
      ("10.80 s Box2D, RE-MEASURED here (loaded machine)", 10.80)]
p(f"  {'budget':32s} " + " ".join(f"{lbl.split()[0]:>8s}" for lbl, _ in ts))
for blbl, B in budgets:
    row = " ".join(f"{n_star(B, t):8d}" for _, t in ts)
    p(f"  {blbl+f' ({B}s)':32s} {row}")
p("  (columns are seconds per candidate; cells are the largest CHEAP n)")
for lbl, t in ts:
    p(f"    t = {lbl}")

p()
p("=" * 74)
p("4. THE MEASURED n VALUES AGAINST THAT THRESHOLD")
meas = [("tests/test_guard.py count_above fixture", 5, 0.20),
        ("tests/test_span_edits.py budget fixture", 110, 0.20),
        ("Box2D contact_solver.c, packet-capped (what cguard builds)",
         438, 1479 / 428),
        ("Box2D contact_solver.c, coverage-anchored packet", 463, 10.80),
        ("Box2D contact_solver.c, whole file uncapped", 5041, 1479 / 428),
        ("Box2D 38 richest files, packet-capped", 13523, 1479 / 428),
        ("the 1,063 the docs quote", 1063, 3.5)]
for lbl, n, t in meas:
    c = n * (n - 1) // 2
    secs = c * t
    p(f"  n={n:6d}  C(n,2)={c:12,d}  at {t:.2f}s = {secs:14,.0f}s "
      f"= {secs/86400:9.2f} d   {lbl}")
p()
p("  CHEAP verdict at the 600s escalate budget:")
for lbl, n, t in meas:
    ns = n_star(600, t)
    p(f"    n={n:6d} vs n*={ns:4d}  ->  "
      f"{'CHEAP' if n <= ns else 'NOT cheap'}   {lbl}")

p()
p("=" * 74)
p("5. THE DOCUMENTED ARITHMETIC, AND ITS SOURCES")
n = 1063
c = n * (n - 1) // 2
p(f"  C(1063,2)                        = {c}   "
  f"(docs/PAIR_LAW_PROMPT.md:34 says 564,453 -> "
  f"{'reproduces' if c == 564453 else 'DOES NOT'})")
p(f"  {c} x 3.5s                  = {c*3.5:,.0f}s = {c*3.5/86400:.2f} days "
  f"(docs say 'about 23 days' -> reproduces)")
p(f"  1063 x 3.5s                      = {1063*3.5:,.0f}s = "
  f"{1063*3.5/60:.0f} min (docs:33 say '~1 hour')")
p( "  BUT the run that produced 1,063 is recorded as refusing after")
p( "  30 MINUTES (ghpages/games.html:728-732), i.e. 1800/1063 = "
  f"{1800/1063:.2f}s per candidate, not 3.5s.")
p( "  The 3.5s figure comes from DIFFERENT runs in CHANGELOG.md:")
p(f"    1479s / 428 runs = {1479/428:.3f}s   (CHANGELOG.md:227)")
p(f"     116s /  34 runs = {116/34:.3f}s   (CHANGELOG.md:201)")
