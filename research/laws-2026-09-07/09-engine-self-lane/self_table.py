#!/usr/bin/env python
"""Exhaustive SELF-lane derivation of the engine law.

For every one of the 128 observation bytes with SELF (bit 7) set, print the
ruling; alongside it, the ruling for the same byte with SELF cleared, so the
effect of SELF on each situation is visible. Pure arithmetic — no repo, no
suite run. Rerun: .venv/bin/python self_table.py
"""
import sys
sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
from collections import Counter
from fluidfix.engine import decide, situation, BITS, ACTS

SELF = BITS.index("SELF")
assert SELF == 7

def name(byte):
    on = [b for i, b in enumerate(BITS) if byte >> i & 1]
    return "+".join(on) if on else "(none)"

def rule(byte):
    return decide(situation(**{b: bool(byte >> i & 1) for i, b in enumerate(BITS)}))

rows = []
changed = []
for low in range(128):                 # bits 0..6
    b0 = low
    b1 = low | (1 << SELF)
    r0, r1 = rule(b0), rule(b1)
    rows.append((b1, name(b1), r1, r0))
    if r0 != r1:
        changed.append((b1, name(b1), r0, r1))

print("=== every SELF=1 byte: ruling, and the ruling with SELF cleared ===")
print(f"{'byte':>5}  {'ruling(SELF=1)':<24} {'ruling(SELF=0)':<24} bits")
for b, n, r1, r0 in rows:
    mark = "" if r1 == r0 else "   <-- SELF changes it"
    print(f"{b:>5}  {r1:<24} {r0:<24} {n}{mark}")

print()
print("=== distribution of rulings over the 128 SELF=1 bytes ===")
for act, k in sorted(Counter(r for _, _, r, _ in rows).items(), key=lambda t: -t[1]):
    print(f"  {act:<24} {k:>3}")
print()
print("=== distribution of rulings over the 128 SELF=0 bytes ===")
for act, k in sorted(Counter(r for _, _, _, r in rows).items(), key=lambda t: -t[1]):
    print(f"  {act:<24} {k:>3}")
print()
print(f"=== bytes where setting SELF changes the ruling: {len(changed)} of 128 ===")
for b, n, r0, r1 in changed:
    print(f"  {b:>3}  {n:<45} {r0} -> {r1}")

print()
print("=== which bytes rule AUTHOR_SUCCESSOR, over all 256 ===")
succ = [(x, name(x)) for x in range(256) if rule(x) == "AUTHOR_SUCCESSOR"]
print(f"  count: {len(succ)}")
for x, n in succ:
    print(f"  {x:>3}  {n}")

print()
print("=== job-invariance check for the SELF half: bits 8-9 swept 0..3 ===")
# situation() hardcodes job=2; re-derive with each job value directly
from fluidfix.engine import _CODE, _s32
def raw_decide(x):
    return ACTS[_s32(eval(_CODE, {"__builtins__": {}}, {"x": _s32(x)})) % 8]
diff = 0
for low in range(256):
    base = raw_decide(low | (2 << 8))
    for job in range(4):
        if raw_decide(low | (job << 8)) != base:
            diff += 1
print(f"  bytes whose ruling differs across job values: {diff} of 256")
