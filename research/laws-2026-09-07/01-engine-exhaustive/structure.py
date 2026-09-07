#!/usr/bin/env python
"""Closed-form re-derivation of the engine law, checked against decide() on all 256.

Claim: with x the observation byte (bit i = BITS[i]),
    second term  ntzb(x + (x & 128)) = position of the LOWEST set bit among
                 bits 1..6 (AMB, UNREAD, NOTWIN, HIDDEN, CAPPED, REFUTED); 0 if
                 none. SELF (bit 7) is erased: 128 + 128 = 256 clears bit 7 and
                 ntzb masks bit 0, so BUILT is ignored here too.
    first term   4 & ntzb(x - 7) == 4  iff  (x - 7) mod 256 has bits 1..3 clear
                 and some bit in 4..7 set  iff  x mod 16 in {7, 8} and x >= 23.
So the ruling index = lowbit(bits 1..6) + 4 * [x mod 16 in {7,8} and x >= 23].
Run: /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python structure.py
"""
import sys
sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix.engine import ACTS, BITS, decide, situation  # noqa: E402


def lowbit_1_to_6(x):
    for i in range(1, 7):
        if (x >> i) & 1:
            return i
    return 0


def closed_form(x):
    plus4 = 4 if (x % 16 in (7, 8) and x >= 23) else 0
    return lowbit_1_to_6(x) + plus4


def law(x):
    return ACTS.index(decide(situation(**{b: True for i, b in enumerate(BITS) if x >> i & 1})))


bad = [x for x in range(256) if closed_form(x) != law(x)]
print(f"closed form vs decide(), 256 inputs: {256 - len(bad)}/256 agree" + (f" BAD={bad}" if bad else ""))
print(f"max ruling index seen: {max(law(x) for x in range(256))} (so ACTS[...%8] never wraps)")

fam7 = [x for x in range(256) if x % 16 == 7 and x >= 23]
fam8 = [x for x in range(256) if x % 16 == 8 and x >= 24]
print(f"+4 family A (x%16==7, x>=23: BUILT+AMB+UNREAD set, NOTWIN clear, >=1 of HIDDEN/CAPPED/REFUTED/SELF): {len(fam7)} inputs, all rule {set(decide(situation(**{b: True for i, b in enumerate(BITS) if x >> i & 1})) for x in fam7)}")
print(f"+4 family B (x%16==8, x>=24: NOTWIN set, BUILT/AMB/UNREAD clear, >=1 of HIDDEN/CAPPED/REFUTED/SELF): {len(fam8)} inputs, all rule {set(decide(situation(**{b: True for i, b in enumerate(BITS) if x >> i & 1})) for x in fam8)}")
print("without the +4 term the ruling is the lowest set bit, i.e. precedence "
      "AMB > UNREAD > NOTWIN > HIDDEN > CAPPED > REFUTED; BUILT and SELF never change a ruling except through the +4 term.")

# bits that never change any ruling on their own
for name in ("BUILT", "SELF"):
    i = BITS.index(name)
    changed = [x for x in range(256) if not (x >> i) & 1 and law(x) != law(x | (1 << i))]
    print(f"setting {name} changes the ruling on {len(changed)}/128 inputs: {changed}")

# refusal -> SHIP by adding one bit? (any x whose ruling is not SHIP, plus one bit, becomes SHIP)
flips = [(x, b) for x in range(256) for b in range(8)
         if not (x >> b) & 1 and law(x) != 0 and law(x | (1 << b)) == 0]
print(f"one added bit turning a non-SHIP ruling into SHIP: {len(flips)} pairs {flips}")
ship = [x for x in range(256) if law(x) == 0]
print(f"SHIP inputs: {ship} = {[('+'.join(b for i, b in enumerate(BITS) if x >> i & 1) or '(none)') for x in ship]}")
