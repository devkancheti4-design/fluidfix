"""Exhaustive: every one of the 256 observation bytes, what the engine law
rules, with the REFUTED bit isolated. Read-only over src/fluidfix/engine.py."""
import sys
sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix.engine import decide, situation, BITS, ACTS
from collections import Counter

def sit(x):  # raw byte -> law input (job bits added as engine.situation does)
    return situation(**{b: bool(x >> i & 1) for i, b in enumerate(BITS)})

R = BITS.index("REFUTED")
harvest = [x for x in range(256) if decide(sit(x)) == "HARVEST_COUNTEREXAMPLE"]
print("inputs ruling HARVEST_COUNTEREXAMPLE:", len(harvest), "of 256")
for x in harvest:
    print(f"  x={x:3d} bits={[b for i,b in enumerate(BITS) if x>>i&1]}")
print()
print("REFUTED set (128 inputs): ruling distribution")
c = Counter(decide(sit(x)) for x in range(256) if x >> R & 1)
for k, v in c.most_common():
    print(f"  {k:24s} {v}")
print()
print("REFUTED alone:", decide(situation(REFUTED=True)))
print("REFUTED+CAPPED:", decide(situation(REFUTED=True, CAPPED=True)))
print("REFUTED+BUILT:", decide(situation(REFUTED=True, BUILT=True)))
print("REFUTED+UNREAD:", decide(situation(REFUTED=True, UNREAD=True)))
print("REFUTED+AMB:", decide(situation(REFUTED=True, AMB=True)))
print("REFUTED+HIDDEN:", decide(situation(REFUTED=True, HIDDEN=True)))
print("REFUTED+NOTWIN:", decide(situation(REFUTED=True, NOTWIN=True)))
print("REFUTED+SELF:", decide(situation(REFUTED=True, SELF=True)))
print("nothing set:", decide(situation()))
print()
# Which bits, when added to REFUTED-alone, keep HARVEST? (masking order)
print("REFUTED + one other bit:")
for i, b in enumerate(BITS):
    if b == "REFUTED": continue
    print(f"  REFUTED+{b:7s} -> {decide(situation(REFUTED=True, **{b: True}))}")
print()
# Which inputs WITHOUT REFUTED rule HARVEST?
print("HARVEST without REFUTED:", [x for x in harvest if not x >> R & 1])
