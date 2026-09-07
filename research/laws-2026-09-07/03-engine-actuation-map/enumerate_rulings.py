#!/usr/bin/env python
"""Exhaustive engine-law enumeration for target 03-engine-actuation-map.

Part A: all 256 observation bytes -> ruling (job bits fixed at DEBUG = 2<<8,
        as engine.situation() always does).
Part B: the exact situations each body call site can construct
        (loop.py:217, loop.py:391, guard.py:491, guard.py:539,
         guard.py:612/618, cli.py:474) and what the law rules on each.
Part C: which of the 8 ACTS are reachable from ANY body call site at all.

Run:  /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python enumerate_rulings.py
"""
import sys
sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix.engine import ACTS, BITS, decide, situation  # noqa: E402

from collections import Counter

# ---------------------------------------------------------------- Part A --
print("== Part A: all 256 bytes -> ruling (job=DEBUG) ==")
hist = Counter()
by_act = {a: [] for a in ACTS}
for x in range(256):
    obs = {b: bool(x >> i & 1) for i, b in enumerate(BITS)}
    r = decide(situation(**obs))
    hist[r] += 1
    by_act[r].append(x)
for a in ACTS:
    print(f"  {a:<22} {hist[a]:3d}/256")
print("  single-bit rulings:")
for i, b in enumerate(BITS):
    print(f"    {b:<8} -> {decide(situation(**{b: True}))}")
print(f"    (none)   -> {decide(situation())}")

# ---------------------------------------------------------------- Part B --
print()
print("== Part B: situations the body can construct, per call site ==")
sites = {
    "loop.py:217 _rule(): BUILT=True, AMB=set_amb|sites>1, CAPPED=capped": [
        dict(BUILT=True, AMB=a, CAPPED=c) for a in (False, True) for c in (False, True)],
    "loop.py:391 confirm-runs disagree: HIDDEN=True": [dict(HIDDEN=True)],
    "guard.py:491 no candidates & no pytest-cov: UNREAD=True": [dict(UNREAD=True)],
    "guard.py:539 escalation gate: CAPPED=capped0, REFUTED=acts0": [
        dict(CAPPED=c, REFUTED=r) for c in (False, True) for r in (False, True)],
    "guard.py:612/618 refusal wording: REFUTED=True": [dict(REFUTED=True)],
    "cli.py:474 selfcheck: each of BUILT/AMB/UNREAD/CAPPED/REFUTED alone": [
        dict(BUILT=True), dict(AMB=True), dict(UNREAD=True),
        dict(CAPPED=True), dict(REFUTED=True)],
}
reachable = set()
for site, sits in sites.items():
    print(f"  {site}")
    for s in sits:
        on = "+".join(k for k, v in s.items() if v) or "(none)"
        r = decide(situation(**s))
        reachable.add(r)
        print(f"      {on:<22} -> {r}")

# ---------------------------------------------------------------- Part C --
print()
print("== Part C: acts the body can ever receive from a decide() call ==")
for a in ACTS:
    print(f"  {a:<22} {'REACHABLE' if a in reachable else 'never returned to the body'}")

# Which observation bytes rule each never-reached act (for section 4/5 of REPORT)
print()
print("== bytes that rule each act the body never receives ==")
for a in ACTS:
    if a in reachable:
        continue
    xs = by_act[a]
    print(f"  {a}: {len(xs)} bytes; e.g. " + ", ".join(
        "+".join(b for i, b in enumerate(BITS) if x >> i & 1) or "(none)"
        for x in xs[:6]))
