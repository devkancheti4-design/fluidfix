#!/usr/bin/env python
"""Exhaustive counterfactual for the CANCELING veto, plus the engine law's
ruling on the pair fixture E would have produced. Pure computation."""
from collections import Counter

from fluidfix.engine import decide
from fluidfix.engine import situation as esit
from fluidfix.pair import ACTS, pair_law

CAN = 1 << 6

print("== 1. the veto's reach: pair_law(x) vs pair_law(x without CANCELING)")
changed = [x for x in range(256) if x & CAN
           and pair_law(x) != pair_law(x & ~CAN)]
same = [x for x in range(256) if x & CAN and pair_law(x) == pair_law(x & ~CAN)]
print(f"   inputs with CANCELING set:            128")
print(f"   ...where the veto CHANGES the ruling: {len(changed)}")
print(f"   ...where it changes nothing:          {len(same)} "
      f"(already REFUSE without it)")
c = Counter(ACTS[pair_law(x & ~CAN)] for x in changed)
print("   what those would have been ruled without CANCELING:")
for k, v in sorted(c.items(), key=lambda kv: -kv[1]):
    print(f"     {k:<10} {v}")
pairs = [x for x in range(256) if x & CAN and ACTS[pair_law(x & ~CAN)] == "PAIR"]
print(f"   inputs where the veto overrules an actual PAIR: {len(pairs)} "
      f"-> bytes {pairs}")

print("\n== 2. bytes measured on the fixtures in this directory")
for name, byte in (("A_unity        (CHEAP=1,TAUGHT=1)", 56),
                   ("C_canceling    (CHEAP=1,TAUGHT=1)", 121),
                   ("D_partition... (CHEAP=1,TAUGHT=1)", 57),
                   ("E_only_cancel  (CHEAP=1,TAUGHT=1)", 121)):
    print(f"   {name}: byte={byte:3d} -> {ACTS[pair_law(byte)]:<9} "
          f"| without CANCELING -> {ACTS[pair_law(byte & ~CAN)]}")

print("\n== 3. what the ENGINE law would rule on fixture E's single green pair")
print("   fixture E has exactly ONE jointly-green pair and it corrupts "
      "Vec3.__add__;")
print("   one green at one site is not ambiguous, so:")
print(f"   decide(BUILT=1, AMB=0) = {decide(esit(BUILT=True, AMB=False))}")
print(f"   decide(BUILT=1, AMB=1) = {decide(esit(BUILT=True, AMB=True))}"
      "   (fixture A and C: two greens at two sites)")
