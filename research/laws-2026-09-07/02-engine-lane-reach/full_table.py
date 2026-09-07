#!/usr/bin/env python
"""All 256 engine-law rulings, one row each, with the reachable ones marked.
Run:  .venv/bin/python full_table.py
"""
import sys

sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix.engine import ACTS, BITS, decide  # noqa: E402

REACHABLE = {0, 1, 3, 4, 16, 32, 33, 64, 96}     # from enumerate_reach.py


def names(x):
    return "+".join(b for i, b in enumerate(BITS) if x >> i & 1) or "<empty>"


rows = [(x, names(x), decide(x | 512)) for x in range(256)]
for x, n, a in rows:
    print(f"{x:3d}  {n:55} {a:22} {'REACHABLE' if x in REACHABLE else ''}")

print("\n=== situations per act, with NOTWIN/SELF involvement ===")
for act in ACTS:
    xs = [x for x, _, a in rows if a == act]
    no_ns = [x for x in xs if not (x & 8) and not (x & 128)]
    print(f"{act:22} {len(xs):3d} total; {len(no_ns):3d} without NOTWIN/SELF: {no_ns}")

print("\n=== the 15 AUTHOR_SUCCESSOR and 17 RESHAPE situations ===")
for act in ("AUTHOR_SUCCESSOR", "RESHAPE"):
    for x, n, a in rows:
        if a == act:
            print(f"  {act:17} x={x:3d} {n}")

print("\n=== every SELF combination ===")
for x, n, a in rows:
    if x & 128:
        print(f"  x={x:3d} {n:55} -> {a}")
