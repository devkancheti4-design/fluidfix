#!/usr/bin/env python
"""Exhaustive analysis of the PAIR law over all 256 observation bytes.

Run:  nice -n 15 timeout 300 /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python \
        research/laws-2026-09-07/21-pair-exhaustive/exhaustive.py

Three independent models are compared on every input:
  A  the shipped kernel          fluidfix.pair.pair_law
  B  the authored case table     transcribed from docs/laws/pair.c's spec()
  C  an algebraic re-derivation  each lane replaced by the closed form this
     script FIRST verifies over all 256 inputs, then ctz of the assembled mask
Plus R1-R5, the five prompt incidents, and a pin-coverage census of
tests/test_pair_law.py.
"""
import sys

sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")

from fluidfix.pair import ACTS, BITS, pair_law           # noqa: E402
import fluidfix.pair as P                                # noqa: E402

EXH, PAR, DIS, COU, CHE, TAU, CAN, CAP = (1 << i for i in range(8))
PARTITION, PAIR, WIDEN, TEACH, BUDGET, CAPPED_A, SINGLE, REFUSE = range(8)
R = range(256)


def bits(x):
    on = [BITS[i] for i in range(8) if x >> i & 1]
    return "|".join(on) if on else "-none-"


# ---------------------------------------------------------------- model B --
def spec_table(x):
    """Transcribed VERBATIM from docs/laws/pair.c's spec()."""
    if x & CAN:
        return 7
    if not (x & CAP):
        if x & EXH:
            if x & DIS:
                return 0
            if (x & PAR) and (x & COU) and (x & CHE):
                return 1
            if (x & PAR) and not (x & COU):
                return 2
            if not (x & TAU):
                return 3
            if not (x & CHE):
                return 4
        else:
            return 6
    if x & CAP:
        return 5
    return 7


# ---------------------------------------------------------------- model C --
# Closed forms claimed for each authored lane; every one is CHECKED over all
# 256 inputs below before model C is allowed to use them.
CLOSED = {
    "READY":     (P._READY,     lambda x: 1 if x & EXH else 0),
    "CANCEL":    (P._CANCEL,    lambda x: 1 if x & CAN else 0),
    "BLOCK":     (P._BLOCK,     lambda x: 1 if (x & CAN or x & CAP) else 0),
    "PARTITION": (P._PARTITION, lambda x: 1 if x & DIS else 0),
    "PARTIAL":   (P._PARTIAL,   lambda x: 1 if x & PAR else 0),
    "COUPLED":   (P._COUPLED,   lambda x: 1 if x & COU else 0),
    "CHEAP2":    (P._CHEAP2,    lambda x: 2 if x & CHE else 0),
    "NOTCOUP":   (P._NOTCOUP,   lambda x: 0 if x & COU else 4),
    "TEACH":     (P._TEACH,     lambda x: 0 if x & TAU else 8),
    "BUDGET":    (P._BUDGET,    lambda x: 0 if x & CHE else 16),
    "CAPPED_L":  (P._CAPPED_L,  lambda x: 32 if x & CAP else 0),
    "SINGLE":    (P._SINGLE,    lambda x: 0 if x & EXH else 64),
}


def model_c(x):
    """Re-derivation: mask bits are ORed lane weights, priority = ctz."""
    mask = 128                                   # the floor, always present
    if not (x & CAN) and not (x & CAP):          # gb: neither
        if not (x & EXH):
            mask += 64                           # SINGLE
        else:                                    # gr: EXHAUSTED gates all
            if x & DIS:
                mask += 1                        # PARTITION
            if (x & PAR) and (x & COU) and (x & CHE):
                mask += 2                        # PAIR
            if (x & PAR) and not (x & COU):
                mask += 4                        # WIDEN
            if not (x & TAU):
                mask += 8                        # TEACH
            if not (x & CHE):
                mask += 16                       # BUDGET
    if not (x & CAN) and (x & CAP):
        mask += 32                               # CAPPED
    return (mask & -mask).bit_length() - 1


def mask_of(x):
    """The kernel's mask, recomputed exactly as pair_law assembles it."""
    s = P._s32
    gr, gc = s(0 - P._READY(x)), s(P._CANCEL(x) - 1)
    gb, gp, gcp = s(P._BLOCK(x) - 1), s(0 - P._PARTIAL(x)), s(0 - P._COUPLED(x))
    pair = s(gp & gcp & P._CHEAP2(x))
    widen = s(gp & P._NOTCOUP(x))
    act = s(gr & (P._PARTITION(x) + pair + widen + P._TEACH(x) + P._BUDGET(x)))
    return s((gb & (act + P._SINGLE(x))) + (gc & P._CAPPED_L(x)) + 128)


out = []
p = out.append

p("=" * 74)
p("1. LANE CLOSED FORMS — each authored expression vs a claimed closed form")
p("=" * 74)
lane_bad = 0
for name, (fn, closed) in CLOSED.items():
    bad = [x for x in R if fn(x) != closed(x)]
    lane_bad += len(bad)
    rng = sorted({fn(x) for x in R})
    p(f"  {name:<10} disagreements over 256 inputs: {len(bad):<3} range={rng}")
p(f"  TOTAL lane disagreements: {lane_bad}")

p("")
p("=" * 74)
p("2. THREE MODELS OVER ALL 256 INPUTS")
p("=" * 74)
ab = [x for x in R if pair_law(x) != spec_table(x)]
ac = [x for x in R if pair_law(x) != model_c(x)]
bc = [x for x in R if spec_table(x) != model_c(x)]
p(f"  A kernel vs B authored case table : {len(ab)} disagreements {ab}")
p(f"  A kernel vs C algebraic re-deriv. : {len(ac)} disagreements {ac}")
p(f"  B case table vs C re-derivation   : {len(bc)} disagreements {bc}")
masks = {x: mask_of(x) for x in R}
p(f"  mask is never zero (ctz terminates): min mask = {min(masks.values())}")
p(f"  mask is never negative             : min = {min(masks.values())}, "
  f"max = {max(masks.values())}")
p(f"  every output is a legal act index  : "
  f"{all(0 <= pair_law(x) < 8 for x in R)}")

p("")
p("=" * 74)
p("3. R1-R5 (the prompt's structural requirements)")
p("=" * 74)
r1 = [x for x in R if not (x & EXH) and pair_law(x) <= BUDGET]
r2 = [x for x in R if (x & DIS) and (x & EXH) and not (x & CAN)
      and not (x & CAP) and pair_law(x) != PARTITION]
r2_strict = [x for x in R if (x & DIS) and pair_law(x) != PARTITION]
r3 = [x for x in R if (x & CAN) and pair_law(x) != REFUSE]
r4 = [x for x in R if pair_law(x) == PAIR and not (x & PAR)]
r5 = [x for x in R if pair_law(x) == PAIR and not (x & CHE)]
p(f"  R1 no multi-edit lane (0..4) before EXHAUSTED : {len(r1)} violations")
p(f"  R2 DISJOINT->PARTITION (as tested, !CAN !CAP) : {len(r2)} violations")
p(f"  R2 DISJOINT->PARTITION 'whatever else is true': "
  f"{len(r2_strict)} counterexamples")
p(f"     counterexample bytes: {r2_strict[:8]}{' ...' if len(r2_strict) > 8 else ''}")
for x in r2_strict[:4]:
    p(f"       x={x:3d} {bits(x):<45} -> {ACTS[pair_law(x)]}")
p(f"  R3 CANCELING always REFUSE                    : {len(r3)} violations")
p(f"  R4 PAIR requires PARTIAL                      : {len(r4)} violations")
p(f"  R5 PAIR requires CHEAP                        : {len(r5)} violations")
p(f"  R6 determinism: pair_law is pure; 256 inputs re-evaluated twice equal: "
  f"{[pair_law(x) for x in R] == [pair_law(x) for x in R]}")

p("")
p("=" * 74)
p("4. THE FIVE INCIDENTS from docs/PAIR_LAW_PROMPT.md")
p("=" * 74)
incidents = [
    ("1 Unity ProjectOnPlane (compensating pair)",
     PAR | COU | CHE | TAU | CAN, REFUSE, "never a pair; CANCELING last"),
    ("2 Box2D contact_solver.c (1,063 cands)",
     EXH | TAU, BUDGET, "refuse to start; say the budget is why"),
    ("3 genuine two-bug program",
     EXH | PAR | DIS | TAU | CHE, PARTITION, "partition first"),
    ("4 two coupled taught faults, cheap space",
     EXH | PAR | COU | CHE | TAU, PAIR, "the only shape that earns a pair"),
    ("5 nothing observed at all", 0, SINGLE, "invent no reason to search"),
]
inc_bad = 0
for label, x, want, why in incidents:
    got = pair_law(x)
    ok = got == want
    inc_bad += not ok
    p(f"  {label}")
    p(f"     byte {x:3d} = {bits(x)}")
    p(f"     ruled {ACTS[got]:<9} required {ACTS[want]:<9} "
      f"{'OK' if ok else 'MISMATCH'}   ({why})")
p(f"  incident violations: {inc_bad}")

p("")
p("=" * 74)
p("5. ACT DISTRIBUTION AND REACHABILITY OVER 256 INPUTS")
p("=" * 74)
for a, name in enumerate(ACTS):
    xs = [x for x in R if pair_law(x) == a]
    p(f"  {a} {name:<10} {len(xs):>3}/256")
    if len(xs) <= 4:
        for x in xs:
            p(f"        x={x:3d} {bits(x)}")
p("")
p("  REFUSE (7) has two disjoint causes:")
veto = [x for x in R if pair_law(x) == REFUSE and (x & CAN)]
dry = [x for x in R if pair_law(x) == REFUSE and not (x & CAN)]
p(f"     CANCELING veto        : {len(veto)} inputs")
p(f"     exhausted, no evidence: {len(dry)} inputs -> {dry}")
for x in dry:
    p(f"        x={x:3d} {bits(x)}")

p("")
p("  Incident-5 wording check — 'every evidence-free input lands in the same")
p("  low-priority class'. Inputs with EXHAUSTED clear:")
for a in range(8):
    xs = [x for x in R if not (x & EXH) and pair_law(x) == a]
    if xs:
        p(f"     {ACTS[a]:<10} {len(xs):>3} inputs")

p("")
p("=" * 74)
p("6. PIN CENSUS — what tests/test_pair_law.py actually fixes per input")
p("=" * 74)
# Assertions in tests/test_pair_law.py that fix an EXACT act for an input
# WITHOUT consulting the transcribed spec table.
exact = {}


def pin(x, src):
    exact.setdefault(x, []).append(src)


for x in R:                                   # test_r2_...
    if (x & DIS) and (x & EXH) and not (x & CAN) and not (x & CAP):
        pin(x, "R2(->PARTITION)")
for x in R:                                   # test_r3_...
    if x & CAN:
        pin(x, "R3(->REFUSE)")
for label, x, want, _ in incidents:           # the five incident tests
    pin(x, f"incident {label.split()[0]}(->{ACTS[want]})")
for x in R:                                   # test_a_pair_is_reachable...
    if pair_law(x) == PAIR:
        pin(x, "reach-2(->PAIR)")
unpinned = [x for x in R if x not in exact]
p(f"  inputs with an EXACT act pinned independently of the spec table: "
  f"{len(exact)}/256")
p(f"  inputs pinned ONLY by the transcribed spec table                : "
  f"{len(unpinned)}/256")
p("")
p("  Weak (non-exact) constraints those unpinned inputs still carry:")
weak_r1 = [x for x in unpinned if not (x & EXH)]
p(f"     R1 bound 'act > BUDGET' covers {len(weak_r1)} of them")
p(f"     act-range 0<=g<8 covers all {len(unpinned)}")
p("")
p("  The unpinned inputs, grouped by the act the kernel gives them:")
for a in range(8):
    xs = [x for x in unpinned if pair_law(x) == a]
    if xs:
        p(f"     {ACTS[a]:<10} {len(xs):>3}: {xs}")
p("")
p("  Acts NOT pinned to any single input by a spec-table-independent")
p("  assertion:")
covered_acts = sorted({pair_law(x) for x in exact})
p(f"     pinned acts   : {[ACTS[a] for a in covered_acts]}")
p(f"     unpinned acts : "
  f"{[ACTS[a] for a in range(8) if a not in covered_acts]}")

p("")
p("=" * 74)
p("7. FULL 256-ROW TABLE (kernel / table / re-derivation / mask)")
p("=" * 74)
p(f"  {'x':>3} {'mask':>5} {'kernel':<10} {'table':<10} {'rederiv':<10} bits")
for x in R:
    p(f"  {x:>3} {masks[x]:>5} {ACTS[pair_law(x)]:<10} "
      f"{ACTS[spec_table(x)]:<10} {ACTS[model_c(x)]:<10} {bits(x)}")

text = "\n".join(out)
print(text)
with open("/Users/kanchetidevieswar/neo/fluidfix/research/laws-2026-09-07/"
          "21-pair-exhaustive/exhaustive_output.txt", "w") as fh:
    fh.write(text + "\n")
