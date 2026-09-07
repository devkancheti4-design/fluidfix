#!/usr/bin/env python
"""Closed form of the engine law, checked against the vendored formula on
all 1024 inputs (256 observation bytes x 4 job values).

    act = (4 & ntzb(x - 7)) + ntzb(x + (x & 128))

ntzb(v) in the authored text = number of trailing zeros of (v & 254), i.e.
bits 1..7 only (BUILT, bit 0, is masked out), and 0 when no such bit is set.

Claimed closed form:
    second = index of the LOWEST set bit among bits 1..6 of x   (0 if none)
             -- SELF (bit 7) is EXCLUDED: x + (x & 128) carries it into bit 8
    first  = 4  iff  (x & 15) in {7, 8}  and  (x & 0xF0) != 0
             -- i.e. the low nibble is exactly BUILT+AMB+UNREAD or exactly
                NOTWIN, AND at least one of HIDDEN/CAPPED/REFUTED/SELF is set
    act    = (first + second) % 8

So SELF's ENTIRE effect: it is one of four bits that can turn
  BUILT+AMB+UNREAD  ADD_STATE(1) -> RAISE_BUDGET(5)      and
  NOTWIN            RESHAPE(3)   -> AUTHOR_SUCCESSOR(7).
Rerun: .venv/bin/python algebra_check.py
"""
import sys
sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix.engine import ACTS, BITS, _CODE, _s32

def law(x):
    return _s32(eval(_CODE, {"__builtins__": {}}, {"x": _s32(x)})) % 8

def closed(x):
    low = x & 0x7E                       # bits 1..6, SELF excluded
    second = (low & -low).bit_length() - 1 if low else 0
    first = 4 if (x & 15) in (7, 8) and (x & 0xF0) else 0
    return (first + second) % 8

bad = [(x, law(x), closed(x)) for x in range(1024) if law(x) != closed(x)]
print(f"inputs checked: 1024 (256 bytes x job 0..3); mismatches: {len(bad)}")
for x, a, b in bad[:20]:
    print(f"  x={x}: law={ACTS[a]} closed={ACTS[b]}")

# Where does SELF matter, by the closed form? Only through `first`.
sel = 1 << BITS.index("SELF")
flips = [x for x in range(128) if law(x | sel) != law(x)]
print(f"bytes where SELF flips the ruling: {len(flips)} -> {flips}")
for x in flips:
    on = [b for i, b in enumerate(BITS) if (x | sel) >> i & 1]
    print(f"  {x | sel:>3} {'+'.join(on):<30} {ACTS[law(x)]} -> {ACTS[law(x | sel)]}")

# SELF on its own, and with BUILT: does the law ever brake on SELF?
print("SELF alone         ->", ACTS[law(sel | 512)])
print("BUILT+SELF         ->", ACTS[law(1 | sel | 512)])
print("BUILT+AMB+SELF     ->", ACTS[law(3 | sel | 512)])
print("SELF+REFUTED       ->", ACTS[law(64 | sel | 512)])
# Which bit is "equivalent" to SELF in the first term?
for b in ("HIDDEN", "CAPPED", "REFUTED", "SELF"):
    i = 1 << BITS.index(b)
    print(f"NOTWIN+{b:<8} -> {ACTS[law(8 | i | 512)]:<18} "
          f"BUILT+AMB+UNREAD+{b:<8} -> {ACTS[law(7 | i | 512)]}")
