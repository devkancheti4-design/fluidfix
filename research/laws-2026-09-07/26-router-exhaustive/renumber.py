"""26-router-exhaustive: does the renumbering claim hold INSIDE fluidfix?

router.py's docstring: "the action vocabulary can be renumbered by any
translation without touching code. A lookup table frozen at one numbering is
wrong on 15 of the 16 renumberings; this is wrong on none."

Test it against fluidfix's own act table: for each of the 16 translations t,
renumber every act code in ACTS by +t (mod 16), set the worked example's
A1 to (5+t) mod 16, and check that every registered kind still lands on its
ORIGINAL applier function. Then do the same against a frozen lookup table.

Nothing in src/ is modified: ACTS is rebound in this process only.
Run: ./run.sh 120 /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python renumber.py
"""
import sys

sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")

from fluidfix import acts as A  # noqa: E402
from fluidfix.router import route  # noqa: E402

ORIG_ACTS = dict(A.ACTS)
KINDS = sorted(A.KINDS)
TRUTH = {k: ORIG_ACTS[route(0, 5, k)] for k in KINDS}   # kind -> applier fn

# The frozen lookup table an implementation without a router would ship:
FROZEN = {k: route(0, 5, k) for k in KINDS}

print(f"registered kinds: {KINDS}")
print(f"shipped act codes: {sorted(ORIG_ACTS)}")
print()
print(f"{'t':>3} {'router right':>13} {'frozen table right':>20}")
router_ok = frozen_ok = 0
for t in range(16):
    table = {(code + t) % 16: fn for code, fn in ORIG_ACTS.items()}
    a1 = (5 + t) % 16                      # the worked example, renumbered too
    r = sum(table.get(route(0, a1, k)) is TRUTH[k] for k in KINDS)
    f = sum(table.get(FROZEN[k]) is TRUTH[k] for k in KINDS)
    router_ok += r == len(KINDS)
    frozen_ok += f == len(KINDS)
    print(f"{t:>3} {r:>9}/{len(KINDS)} {f:>16}/{len(KINDS)}")
print()
print(f"renumberings on which the ROUTER is fully right: {router_ok}/16")
print(f"renumberings on which a FROZEN TABLE is fully right: {frozen_ok}/16")
print()
print("NOTE: the router needs A1 in acts.py:53 WORKED_EXAMPLE moved with the "
      "vocabulary; router.py itself is untouched. With A1 left at 5 the "
      "router is right on:")
stuck = sum(
    all({(c + t) % 16: fn for c, fn in ORIG_ACTS.items()}
        .get(route(0, 5, k)) is TRUTH[k] for k in KINDS)
    for t in range(16))
print(f"  {stuck}/16 renumberings -- i.e. it degenerates to the frozen table.")
