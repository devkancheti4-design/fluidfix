#!/usr/bin/env python
"""47-reshape-actuation, part 1: what RESHAPE is, per the law and the docstring.

Pure analysis of src/fluidfix/engine.py. No repo mutation, no suite runs.
Run:  .venv/bin/python reshape_exhaustive.py
"""
import re
import sys

sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")

from fluidfix.engine import ACTS, BITS, decide, situation  # noqa: E402
import fluidfix.engine as eng                              # noqa: E402


def byte_kwargs(x):
    return {BITS[i]: bool(x >> i & 1) for i in range(8)}


def names(x):
    n = [BITS[i] for i in range(8) if x >> i & 1]
    return "+".join(n) if n else "(empty)"


table = {x: decide(situation(**byte_kwargs(x))) for x in range(256)}

print("=" * 72)
print("A. Does the engine DOCSTRING define RESHAPE or NOTWIN at all?")
print("=" * 72)
doc = eng.__doc__
print(f"  occurrences of 'RESHAPE' in engine.py __doc__ : {doc.count('RESHAPE')}")
print(f"  occurrences of 'NOTWIN'  in engine.py __doc__ : {doc.count('NOTWIN')}")
for line in doc.splitlines():
    if "NOTWIN" in line or "RESHAPE" in line:
        print(f"  the only line mentioning either: {line.strip()!r}")
# the docstring's explicit bit -> act table
pairs = re.findall(r"^\s{4}(\w+)\s+.*?->\s+([A-Z_]+)$", doc, re.M)
print(f"  bit -> act pairs the docstring states outright: {pairs}")
print(f"  bits with NO stated act: "
      f"{[b for b in BITS if b not in [p[0] for p in pairs]]}")

print()
print("=" * 72)
print("B. The law's own pairing: single bit i  ->  ACTS[i]?")
print("=" * 72)
same_index = []
for i in range(8):
    r = decide(situation(**{BITS[i]: True}))
    same_index.append(r == ACTS[i])
    print(f"  {BITS[i]:8} (bit {i}) -> {r:22} ACTS[{i}]={ACTS[i]:22} "
          f"{'same-index' if r == ACTS[i] else 'DIFFERS'}")
print(f"  same-index holds for {sum(same_index)}/8 single-bit inputs")

print()
print("=" * 72)
print("C. Every byte that rules RESHAPE")
print("=" * 72)
resh = [x for x in range(256) if table[x] == "RESHAPE"]
print(f"  count: {len(resh)} of 256")
print(f"  all have NOTWIN set: {all(x >> 3 & 1 for x in resh)}")
print(f"  all have AMB clear:  {all(not (x >> 1 & 1) for x in resh)}")
print(f"  all have UNREAD clear: {all(not (x >> 2 & 1) for x in resh)}")
for x in resh:
    print(f"    x={x:3}  {names(x)}")

print()
print("=" * 72)
print("D. Every byte that MENTIONS NOTWIN, and what it rules")
print("=" * 72)
nw = [x for x in range(256) if x >> 3 & 1]
hist = {}
for x in nw:
    hist[table[x]] = hist.get(table[x], 0) + 1
print(f"  bytes with NOTWIN set: {len(nw)}")
print(f"  their rulings: {hist}")
print("  -> RESHAPE requires NOTWIN, but NOTWIN does not imply RESHAPE:")
print("     AMB and UNREAD outrank it (lowest set bit among bits 1..6 wins).")

print()
print("=" * 72)
print("E. What NOTWIN would do to the bytes the body actually builds")
print("=" * 72)
# The ruling site that ships: loop.py:217  decide(situation(BUILT, AMB, CAPPED))
body = []
for amb in (0, 1):
    for cap in (0, 1):
        body.append(("loop.py:217 _rule", dict(BUILT=True, AMB=bool(amb),
                                               CAPPED=bool(cap))))
body += [("loop.py:391 HIDDEN", dict(HIDDEN=True)),
         ("guard.py:491 UNREAD", dict(UNREAD=True)),
         ("guard.py:612/618", dict(REFUTED=True))]
for c in (0, 1):
    for r in (0, 1):
        body.append(("guard.py:539", dict(CAPPED=bool(c), REFUTED=bool(r))))
seen = set()
print(f"  {'site':22} {'byte':34} {'ruling':22} -> with NOTWIN")
for site, kw in body:
    x = situation(**kw) & 0xFF
    if x in seen:
        continue
    seen.add(x)
    y = x | 8
    print(f"  {site:22} {names(x):34} {table[x]:22} -> {table[y]}")
print(f"  distinct body-constructible bytes here: {len(seen)}")
flips = sum(1 for x in seen if table[x] != table[x | 8])
print(f"  bytes whose ruling CHANGES when NOTWIN is added: {flips}/{len(seen)}")

print()
print("=" * 72)
print("F. The one that matters: the shipping byte")
print("=" * 72)
ship = situation(BUILT=True) & 0xFF
print(f"  BUILT            -> {table[ship]}")
print(f"  BUILT+NOTWIN     -> {table[ship | 8]}")
print(f"  BUILT+AMB        -> {table[ship | 2]}")
print(f"  BUILT+AMB+NOTWIN -> {table[ship | 2 | 8]}   "
      f"(AMB outranks NOTWIN: NOTWIN is INVISIBLE once AMB holds)")
print(f"  BUILT+CAPPED        -> {table[ship | 32]}")
print(f"  BUILT+NOTWIN+CAPPED -> {table[ship | 8 | 32]}")
