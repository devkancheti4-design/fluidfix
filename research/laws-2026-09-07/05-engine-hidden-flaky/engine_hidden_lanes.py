"""Every engine-law ruling with HIDDEN set (128 of the 256 situations), plus
the one situation the body actually constructs (loop.py:391, HIDDEN alone).
Run: .venv/bin/python engine_hidden_lanes.py
"""
from collections import Counter
from fluidfix.engine import decide, situation, BITS

print("situation the body constructs (loop.py:391): HIDDEN alone ->",
      decide(situation(HIDDEN=True)))
c = Counter()
print(f"\n{'x':>4} {'bits':40s} ruling")
for x in range(256):
    if not (x >> BITS.index("HIDDEN")) & 1:
        continue
    obs = {b: bool(x >> i & 1) for i, b in enumerate(BITS)}
    r = decide(situation(**obs))
    c[r] += 1
    print(f"{x:>4} {'+'.join(b for b in BITS if obs[b]):40s} {r}")
print("\nrulings over the 128 HIDDEN=1 situations:", dict(c))
print("HIDDEN with BUILT and nothing else ->", decide(situation(BUILT=True, HIDDEN=True)))
print("HIDDEN with REFUTED ->", decide(situation(HIDDEN=True, REFUTED=True)))
print("HIDDEN with AMB ->", decide(situation(AMB=True, HIDDEN=True)))
print("HIDDEN with CAPPED ->", decide(situation(HIDDEN=True, CAPPED=True)))
