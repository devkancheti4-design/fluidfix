#!/usr/bin/env python
"""Properties of the PAIR law that the exhaustive table alone does not show:
bit relevance, monotonicity under added evidence, the scope of the authored
R2 claim, the semantically contradictory region of the observation byte, and
the arithmetic behind the two documented cost numbers.

Run:  research/laws-2026-09-07/21-pair-exhaustive/run.sh \
        /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python \
        research/laws-2026-09-07/21-pair-exhaustive/props.py
"""
import sys

sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix.pair import ACTS, BITS, pair_law                  # noqa: E402

EXH, PAR, DIS, COU, CHE, TAU, CAN, CAP = (1 << i for i in range(8))
R = range(256)
out = []
p = out.append


def bits(x):
    on = [BITS[i] for i in range(8) if x >> i & 1]
    return "|".join(on) if on else "-none-"


p("=" * 74)
p("A. BIT RELEVANCE — on how many inputs does SETTING each bit change the")
p("   ruling, and in which direction (lower index = attempted sooner)")
p("=" * 74)
for i, name in enumerate(BITS):
    lower = higher = same = 0
    for x in R:
        if x >> i & 1:
            continue
        a, b = pair_law(x), pair_law(x | (1 << i))
        if b < a:
            lower += 1
        elif b > a:
            higher += 1
        else:
            same += 1
    p(f"  bit {i} {name:<10} of 128 base inputs: "
      f"{lower:>3} sooner  {higher:>3} later  {same:>3} unchanged")

p("")
p("=" * 74)
p("B. CAN ADDED EVIDENCE EVER REACH THE TWO ACTING LANES (PARTITION/PAIR)?")
p("=" * 74)
for i, name in enumerate(BITS):
    hits = [x for x in R if not (x >> i & 1) and pair_law(x) > 1
            and pair_law(x | (1 << i)) <= 1]
    p(f"  setting {name:<10} moves {len(hits):>3} inputs into "
      f"PARTITION/PAIR")
esc = [(x, i) for x in R for i in range(8)
       if not (x >> i & 1) and pair_law(x) == 7 and pair_law(x | (1 << i)) <= 1]
p(f"  single-bit jumps from REFUSE straight to an acting lane: {len(esc)}")
for x, i in esc:
    p(f"     x={x} {bits(x)}  + {BITS[i]} -> {ACTS[pair_law(x | (1 << i))]}")
p("  (NOTE: the list above REFUTES the hypothesis this script started with —")
p("   a refusal IS one measured bit away from an acting lane, including the")
p("   quadratic PAIR lane at x=57 + PARTIAL)")

p("")
p("=" * 74)
p("C. SCOPE OF THE AUTHORED R2 CLAIM")
p("   pair.c / pair.py: 'ctz returns the partition whenever one exists,")
p("   whatever else is true'")
p("=" * 74)
dis = [x for x in R if x & DIS]
notpart = [x for x in dis if pair_law(x) != 0]
p(f"  inputs with DISJOINT set                     : {len(dis)}")
p(f"  of those, NOT ruled PARTITION                : {len(notpart)}")
for label, sel in (("because EXHAUSTED is clear (R1 gate)",
                    lambda x: not (x & EXH)),
                   ("because CANCELING is set (R3 veto)",
                    lambda x: (x & EXH) and (x & CAN)),
                   ("because CAPPED is set (budget spent)",
                    lambda x: (x & EXH) and not (x & CAN) and (x & CAP))):
    xs = [x for x in notpart if sel(x)]
    p(f"     {label:<40} {len(xs):>3}")
    if xs and len(xs) <= 3:
        for x in xs:
            p(f"        x={x:3d} {bits(x)} -> {ACTS[pair_law(x)]}")
witness = [x for x in notpart if (x & EXH) and not (x & CAN) and (x & CAP)]
p(f"  smallest counterexample to the literal claim: x={min(witness)} "
  f"{bits(min(witness))} -> {ACTS[pair_law(min(witness))]}")

p("")
p("=" * 74)
p("D. SEMANTICALLY CONTRADICTORY REGION OF THE OBSERVATION BYTE")
p("   DISJOINT = 'the failing tests partition into disjoint sites'")
p("   COUPLED  = 'every failing test touches the same site'")
p("=" * 74)
both = [x for x in R if (x & DIS) and (x & COU)]
p(f"  inputs asserting BOTH (cannot both be measured true): {len(both)}/256")
from collections import Counter                                  # noqa: E402
c = Counter(ACTS[pair_law(x)] for x in both)
p(f"  what the law rules on that region: {dict(c)}")
safe = [x for x in both if pair_law(x) == 1]
p(f"  of those, how many reach a PAIR search: {len(safe)}  "
  f"(quadratic lane is NOT entered from a contradictory byte)")
p("  and with EXHAUSTED set and no veto, the contradictory region rules:")
c2 = Counter(ACTS[pair_law(x)] for x in both
             if (x & EXH) and not (x & CAN) and not (x & CAP))
p(f"     {dict(c2)}")

p("")
p("=" * 74)
p("E. THE TWO DOCUMENTED COST NUMBERS, RECOMPUTED")
p("=" * 74)
n = 1063
pairs = n * (n - 1) // 2
p(f"  single-edit candidates measured on Box2D contact_solver.c : {n}")
p(f"  naive pair combinations C({n},2)                        : {pairs}")
p(f"  docs/PAIR_LAW_PROMPT.md claims                            : 564453  "
  f"({'reproduces' if pairs == 564453 else 'DOES NOT reproduce'})")
secs = pairs * 3.5
p(f"  at the documented 3.5 s per candidate                     : "
  f"{secs:.0f} s = {secs / 86400:.2f} days (doc says 'about 23 days')")
p(f"  single-edit pass at 3.5 s                                 : "
  f"{n * 3.5 / 3600:.2f} h (doc says '~1 hour')")

p("")
p("=" * 74)
p("F. ACTUATION REACH — where pair_law is called in the shipped body")
p("=" * 74)
import subprocess                                                # noqa: E402
grep = subprocess.run(
    ["grep", "-rn", "pair_law", "/Users/kanchetidevieswar/neo/fluidfix/src"],
    capture_output=True, text=True).stdout.strip()
for line in grep.splitlines():
    p("  " + line)

text = "\n".join(out)
print(text)
with open("/Users/kanchetidevieswar/neo/fluidfix/research/laws-2026-09-07/"
          "21-pair-exhaustive/props_output.txt", "w") as fh:
    fh.write(text + "\n")
