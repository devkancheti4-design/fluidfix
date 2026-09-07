"""Which of the 256 observation bytes rule RAISE_BUDGET, and what the law
can/cannot express about MAGNITUDE. Pure arithmetic, no suite runs."""
import sys
sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix.engine import decide, situation, BITS, ACTS
import collections
tab = {}
for x in range(256):
    obs = {b: bool(x >> i & 1) for i, b in enumerate(BITS)}
    tab[x] = decide(situation(**obs))
c = collections.Counter(tab.values())
print("ruling census over all 256 observation bytes:")
for a in ACTS:
    print("  %-24s %3d" % (a, c[a]))
rb = [x for x in tab if tab[x] == "RAISE_BUDGET"]
print("\nRAISE_BUDGET bytes: %d" % len(rb))
for x in rb:
    print("  x=%3d  %s" % (x, "+".join(b for i, b in enumerate(BITS)
                                       if x >> i & 1) or "(none)"))
print("\nis CAPPED necessary for RAISE_BUDGET? ",
      all(x & (1 << BITS.index("CAPPED")) for x in rb))
print("is CAPPED sufficient? ",
      all(tab[x] == "RAISE_BUDGET" for x in range(256)
          if x & (1 << BITS.index("CAPPED"))))
bad = [(x, tab[x]) for x in range(256)
       if x & (1 << BITS.index("CAPPED")) and tab[x] != "RAISE_BUDGET"]
print("CAPPED bytes that rule something else: %d" % len(bad))
for x, a in bad[:40]:
    print("  x=%3d %-24s %s" % (x, a, "+".join(b for i, b in enumerate(BITS)
                                               if x >> i & 1)))
print("\nthe two bytes the body actually constructs at guard.py:539")
for cap in (0, 1):
    for ref in (0, 1):
        s = situation(CAPPED=bool(cap), REFUTED=bool(ref))
        print("  CAPPED=%d REFUTED=%d -> sit=%d -> %s"
              % (cap, ref, s, decide(s)))
print("\nthe act ALPHABET has no magnitude: ACTS =", ACTS)
