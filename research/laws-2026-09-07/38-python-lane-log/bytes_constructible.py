#!/usr/bin/env python3
"""Agent 38 — the set of engine-law observation bytes the BODY can construct.

Static enumeration from the six decide(situation(...)) call sites in
loop.py/guard.py, plus the law's ruling on each, plus the rulings on the
bytes the body would need but never builds.
"""
import itertools
import sys

sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix.engine import ACTS, BITS, decide, situation   # noqa: E402

B = {n: 1 << i for i, n in enumerate(BITS)}

SITES = [
    # site, expression, the free variables, the fixed-true bits
    ("guard.py:491", "situation(UNREAD=True)", [], ["UNREAD"]),
    ("guard.py:539", "situation(CAPPED=capped0, REFUTED=acts0)",
     ["CAPPED", "REFUTED"], []),
    ("guard.py:612", "situation(REFUTED=True)", [], ["REFUTED"]),
    ("guard.py:618", "situation(REFUTED=True)", [], ["REFUTED"]),
    ("loop.py:217", "situation(BUILT=True, AMB=set_amb or sites>1, CAPPED=capped)",
     ["AMB", "CAPPED"], ["BUILT"]),
    ("loop.py:391", "situation(HIDDEN=True)", [], ["HIDDEN"]),
]

print("=" * 74)
print("THE CONSTRUCTIBLE SET — every engine byte the body can build")
print("=" * 74)
allbytes = {}
for site, expr, free, fixed in SITES:
    base = sum(B[f] for f in fixed)
    combos = []
    for on in itertools.product([False, True], repeat=len(free)):
        b = base | sum(B[n] for n, v in zip(free, on) if v)
        combos.append(b)
        allbytes.setdefault(b, []).append(site)
    print("\n%-14s %s" % (site, expr))
    for b in sorted(set(combos)):
        names = "|".join(n for n in BITS if b >> BITS.index(n) & 1) or "(none)"
        print("     0x%02x  %-24s -> %s" % (b, names, decide(b | (2 << 8))))

print("\n" + "=" * 74)
print("SUMMARY")
print("=" * 74)
print("distinct bytes constructible : %d of 256 (%.1f%%)"
      % (len(allbytes), 100.0 * len(allbytes) / 256))
print("bytes                        : %s"
      % ["0x%02x" % b for b in sorted(allbytes)])
rul = {decide(b | (2 << 8)) for b in allbytes}
print("distinct rulings reachable   : %d of 8 -> %s" % (len(rul), sorted(rul)))
print("acts NEVER reachable         : %s" % [a for a in ACTS if a not in rul])

# ---- which sites are tautologies on a literal byte -----------------------
print("\n" + "=" * 74)
print("TAUTOLOGY / DECORATION CHECK (what the comparison at each site can do)")
print("=" * 74)
CMP = {"guard.py:491": "ADD_MATERIAL", "guard.py:539": "RAISE_BUDGET",
       "guard.py:612": "HARVEST_COUNTEREXAMPLE",
       "guard.py:618": "HARVEST_COUNTEREXAMPLE",
       "loop.py:217": "(dispatch on ruling)", "loop.py:391": "(none: message only)"}
for site, expr, free, fixed in SITES:
    base = sum(B[f] for f in fixed)
    outs = set()
    for on in itertools.product([False, True], repeat=len(free)):
        b = base | sum(B[n] for n, v in zip(free, on) if v)
        outs.add(decide(b | (2 << 8)))
    tgt = CMP[site]
    if not free:
        verdict = ("TAUTOLOGY: single literal byte, ruling is always %s, "
                   "the == test can never be False" % outs.pop()) \
            if tgt.startswith(("ADD", "HARV")) else \
            "DECORATIVE: ruling is interpolated into a message, nothing branches"
    else:
        verdict = "LIVE: %d distinct rulings possible -> %s" % (len(outs),
                                                                sorted(outs))
    print("%-14s %s" % (site, verdict))

# ---- the byte the body never builds --------------------------------------
print("\n" + "=" * 74)
print("BYTES THE BODY NEEDS BUT NEVER BUILDS (precedence handled in code)")
print("=" * 74)
for b, why in [(B["UNREAD"] | B["REFUTED"],
                "guard.py: UNREAD hint set at :491, REFUTED hint at :618 is "
                "gated by `if not hint` — code precedence, law never asked"),
               (B["BUILT"] | B["REFUTED"],
                "a green plus other rejected candidates: loop never sets "
                "REFUTED alongside BUILT"),
               (B["UNREAD"] | B["CAPPED"],
                "blind localisation AND a truncated search"),
               (B["HIDDEN"] | B["BUILT"],
                "a flaky green: loop.py:391 asks with HIDDEN alone")]:
    names = "|".join(n for n in BITS if b >> BITS.index(n) & 1)
    print("0x%02x  %-22s -> law rules %-24s  (%s)"
          % (b, names, decide(b | (2 << 8)), why))
