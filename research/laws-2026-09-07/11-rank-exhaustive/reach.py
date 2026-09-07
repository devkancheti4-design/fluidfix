#!/usr/bin/env python
"""11-rank-exhaustive: which of the 256 inputs the BODY can construct today.

Static reading of src/fluidfix/guard.py (rank_observations and its two call
sites) plus src/fluidfix/coracle.py.  Run:
  /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python reach.py
"""
import re
import sys
sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix.rank import BITS, rank  # noqa: E402

ROOT = "/Users/kanchetidevieswar/neo/fluidfix/src/fluidfix/"
guard = open(ROOT + "guard.py").read()
coracle = open(ROOT + "coracle.py").read()
loop = open(ROOT + "loop.py").read()

print("1. kwargs passed to observe_bits() inside guard.rank_observations:")
m = re.search(r"_rank\(observe_bits\((.*?)\n\s*\)\)", guard, re.S)
passed = sorted(set(re.findall(r"(\w+)=", m.group(1))))
print("   ", passed)
never = [b.lower() for b in BITS if b.lower() not in passed]
print("   bits never passed (law reads 0):", never)

print("2. call sites of rank_observations(...) and whether they pass retried=:")
for mm in re.finditer(r"rank_observations\((.*?)\)\n", guard, re.S):
    if "def rank_observations" in guard[max(0, mm.start() - 5):mm.start() + 25]:
        continue
    line = guard[:mm.start()].count("\n") + 1
    print(f"   guard.py:{line}  retried= passed: {'retried=' in mm.group(1)}")

print("3. does the C path (coracle.py) consult the ranking law?")
print("   'rank_observations' in coracle.py:", "rank_observations" in coracle)
print("   'observe_bits' in coracle.py    :", "observe_bits" in coracle)
print("   'from .rank' in coracle.py      :", "from .rank" in coracle)
print("   'from .rank' in loop.py         :", "from .rank" in loop)

print("4. constructible inputs given the bits the body can set")
free = [BITS.index(b.upper()) for b in passed if b != "retried" or False]
# retried= IS passed inside rank_observations, but the callers never supply
# a `retried` set, so the bit is identically 0 in the body (section 2).
forced0 = {BITS.index("FAILONLY"), BITS.index("RETRIED")}
reach = [x for x in range(256) if not any((x >> b) & 1 for b in forced0)]
print(f"   forced-zero bits: {[BITS[b] for b in sorted(forced0)]}")
print(f"   constructible inputs: {len(reach)}/256")
ranks = sorted({rank(x) for x in reach})
print(f"   reachable rulings: {ranks}")
print(f"   unreachable rulings: {sorted(set(range(8)) - set(ranks))}"
      f"  (rank 1 needs FAILONLY; rank 7 reachable only as no-evidence,"
      f" never as the veto)")
print(f"   inputs where the veto WOULD change the ruling if RETRIED were "
      f"measured: {sum(1 for x in reach if rank(x) != 7)}/{len(reach)}")
