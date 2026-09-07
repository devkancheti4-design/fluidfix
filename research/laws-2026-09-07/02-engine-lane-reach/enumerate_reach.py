#!/usr/bin/env python
"""02-engine-lane-reach: which of the 256 engine-law situations can the body
construct, and what does the law rule on each?

Static enumeration. Every decide(situation(...)) call site in the body was
found with:
    grep -n "decide(situation" src/fluidfix/*.py
and the free bits at each site were read off the source. This script packs
every combination those sites can produce, rules on each, and prints the
reach table plus the lanes (bits / acts) the body never reaches.

Run:  .venv/bin/python enumerate_reach.py
"""
import itertools
import sys

sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix.engine import ACTS, BITS, decide, situation  # noqa: E402

# ---- call sites, transcribed from source (file:line -> free bits) ---------
# Each entry: (site, fixed bits, free bits). The body constructs every
# combination of the free bits; fixed bits are always on at that site.
SITES = [
    ("loop.py:217  _rule()",            {"BUILT"},   ["AMB", "CAPPED"]),
    ("loop.py:391  HIDDEN re-check",    {"HIDDEN"},  []),
    ("guard.py:491 UNREAD pytest-cov",  {"UNREAD"},  []),
    ("guard.py:539 escalation gate",    set(),       ["CAPPED", "REFUTED"]),
    ("guard.py:612 REFUTED (escalated)", {"REFUTED"}, []),
    ("guard.py:618 REFUTED (pass 0)",   {"REFUTED"}, []),
]

# Combinations the source can PACK but control flow can never REACH, with
# the reason (verified by reading loop.py; see REPORT.md finding 3).
UNREACHABLE_COMBOS = {
    ("loop.py:217  _rule()", frozenset({"BUILT", "AMB", "CAPPED"})):
        "AMB proven -> amb_proven -> break -> _rule(capped=False); the "
        "deadline checks (capped=True) sit at loop heads never revisited "
        "after AMB is proven, and before it sites<=1 so AMB=False",
}


def pack(bits):
    return situation(**{b: True for b in bits})


def main():
    print("=== every situation the body's call sites can PACK ===")
    packed = {}
    for site, fixed, free in SITES:
        for n in range(len(free) + 1):
            for combo in itertools.combinations(free, n):
                bits = frozenset(fixed | set(combo))
                x = pack(bits) & 0xFF
                reach = "UNREACHABLE" if (site, bits) in UNREACHABLE_COMBOS else "reachable"
                packed.setdefault(x, []).append((site, bits, reach))
                print(f"  x={x:3d} {sorted(bits, key=BITS.index) or ['<empty>']!s:40} "
                      f"-> {decide(pack(bits)):22} @ {site}  [{reach}]")
    reachable = {x for x, lst in packed.items()
                 if any(r == "reachable" for _, _, r in lst)}
    print(f"\ndistinct situations packed:    {len(packed)}/256")
    print(f"distinct situations reachable: {len(reachable)}/256 -> "
          f"{sorted(reachable)}")

    print("\n=== bits the body can set ===")
    settable = set()
    for site, fixed, free in SITES:
        settable |= fixed | set(free)
    for b in BITS:
        print(f"  {b:8} {'SET by body' if b in settable else 'NEVER SET'}")

    print("\n=== acts the law rules on reachable situations ===")
    ruled = {decide(x | 512) for x in reachable}
    for a in ACTS:
        print(f"  {a:22} {'ruled on a reachable situation' if a in ruled else 'NEVER RULED for the body'}")

    print("\n=== full 256 table: which act each situation rules, and how many "
          "of each act's situations the body can reach ===")
    per_act = {a: [] for a in ACTS}
    for x in range(256):
        per_act[decide(x | 512)].append(x)
    for a in ACTS:
        xs = per_act[a]
        r = sorted(set(xs) & reachable)
        print(f"  {a:22} rules {len(xs):3d}/256 situations; body reaches {len(r)} of them: {r}")

    print("\n=== single-bit rulings (the docstring's spec) ===")
    for i, b in enumerate(BITS):
        print(f"  {b:8} (x={1 << i:3d}) -> {decide(pack({b}))}")

    print("\n=== reachable situations, per-site verdict the body branches on ===")
    # what the body compares the ruling against at each site
    branch = {
        "loop.py:217  _rule()": '== "SHIP" (else refuse; message keyed on AMB/CAPPED)',
        "loop.py:391  HIDDEN re-check": "not branched on: ok=False regardless; ruling interpolated into `why`",
        "guard.py:491 UNREAD pytest-cov": '== "ADD_MATERIAL" (hint text only)',
        "guard.py:539 escalation gate": '== "RAISE_BUDGET" (gates depth-first escalation)',
        "guard.py:612 REFUTED (escalated)": '== "HARVEST_COUNTEREXAMPLE" (hint text only)',
        "guard.py:618 REFUTED (pass 0)": '== "HARVEST_COUNTEREXAMPLE" (hint text only)',
    }
    for site, fixed, free in SITES:
        print(f"  {site}: {branch[site]}")


if __name__ == "__main__":
    main()
