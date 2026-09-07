"""26-router-exhaustive: re-derive route(F1,A1,Fq) on all 16^3 inputs.

Nothing here imports a reference from fluidfix except the law itself; the
reference is written from the docstring by hand.
Run: ./run.sh 120 /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python exhaustive.py
"""
import sys

sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")

from fluidfix.router import pack, route, route_packed  # noqa: E402


def reference(F1, A1, Fq):
    """The docstring spec, verbatim: route(F1, A1, Fq) == (Fq + A1 - F1) mod 16."""
    return (Fq + A1 - F1) % 16


def hdr(t):
    print("\n== " + t)


# --- 1. all 4096 in-domain inputs -------------------------------------------
hdr("R1  all 16^3 inputs vs the docstring reference")
bad = []
for F1 in range(16):
    for A1 in range(16):
        for Fq in range(16):
            g, w = route(F1, A1, Fq), reference(F1, A1, Fq)
            if g != w:
                bad.append((F1, A1, Fq, g, w))
print(f"agree {4096 - len(bad)}/4096; disagreements: {bad[:5]}")

# --- 2. range of the output -------------------------------------------------
hdr("R2  output is always in 0..15")
outs = {route(a, b, c) for a in range(16) for b in range(16) for c in range(16)}
print(f"distinct outputs = {sorted(outs)}  (min={min(outs)} max={max(outs)})")

# --- 3. identity ------------------------------------------------------------
hdr("R3  identity: route(F1, A1, F1) == A1")
n = sum(route(F1, A1, F1) != A1 for F1 in range(16) for A1 in range(16))
print(f"holds on {256 - n}/256")

# --- 4. bijection in each argument -----------------------------------------
hdr("R4  bijection: fixing two arguments, the third permutes 0..15")
b1 = all(len({route(f, A1, Fq) for f in range(16)}) == 16
         for A1 in range(16) for Fq in range(16))
b2 = all(len({route(F1, a, Fq) for a in range(16)}) == 16
         for F1 in range(16) for Fq in range(16))
b3 = all(len({route(F1, A1, q) for q in range(16)}) == 16
         for F1 in range(16) for A1 in range(16))
print(f"vary F1: {b1}   vary A1: {b2}   vary Fq: {b3}  (all 256 slices each)")

# --- 5. translation invariance (the renumbering claim) ----------------------
hdr("R5  renumbering: adding t to BOTH A1 and the answer, or to F1 and Fq")
t_act = all(route(F1, (A1 + t) % 16, Fq) == (route(F1, A1, Fq) + t) % 16
            for F1 in range(16) for A1 in range(16)
            for Fq in range(16) for t in range(16))
t_kind = all(route((F1 + t) % 16, A1, (Fq + t) % 16) == route(F1, A1, Fq)
             for F1 in range(16) for A1 in range(16)
             for Fq in range(16) for t in range(16))
print(f"act renumbering (65536 cases): {t_act}")
print(f"kind renumbering (65536 cases): {t_kind}")

# --- 6. composition ---------------------------------------------------------
hdr("R6  composition: route(0,o2,route(0,o1,q)) == (q+o1+o2) mod 16")
c = sum(route(0, o2, route(0, o1, q)) != (q + o1 + o2) % 16
        for o1 in range(16) for o2 in range(16) for q in range(16))
print(f"holds on {4096 - c}/4096")

# --- 7. high bits: EXHAUSTIVE over the 12-bit payload x 20-bit-position probe
hdr("R7  'Bits 12-31 cannot influence the result' -- exhaustive over payload")
viol = []
for low in range(4096):
    base = route_packed(low)
    for bit in range(12, 32):
        if route_packed(low | (1 << bit)) != base:
            viol.append((low, bit))
        # and with the sign bit set as well (negative int32 input)
        if route_packed(low | (1 << bit) | (1 << 31) | (-1 << 32)) != base:
            viol.append((low, bit, "neg"))
print(f"4096 payloads x 20 high bits (both int32-positive and sign-extended "
      f"negative): violations = {len(viol)}; first = {viol[:3]}")

hdr("R7b random int32 probe, 200000 draws")
import random  # noqa: E402
rng = random.Random(20260907)
v2 = sum(route_packed(x) != route_packed(x & 0xFFF)
         for x in (rng.randrange(-2**31, 2**31) for _ in range(200000)))
print(f"route_packed(x) != route_packed(x & 0xFFF) on {v2}/200000 draws")

# --- 8. pack() wraps rather than rejects out-of-range arguments -------------
hdr("R8  out-of-domain arguments: pack masks each field to 4 bits")
rows = []
for F1, A1, Fq in [(0, 5, 16), (0, 5, 99), (0, 5, -1), (0, 5, -16),
                   (16, 5, 3), (0, 21, 3), (0, 5, 2**40 + 3)]:
    rows.append((F1, A1, Fq, route(F1, A1, Fq),
                 reference(F1 & 15, A1 & 15, Fq & 15)))
for r in rows:
    print(f"  route({r[0]}, {r[1]}, {r[2]}) = {r[3]}   "
          f"== reference of masked args {r[4]}: {r[3] == r[4]}")

# --- 9. what the BODY can actually ask -------------------------------------
hdr("R9  the body's only worked example, and the act table it lands in")
from fluidfix.acts import ACTS, KINDS, WORKED_EXAMPLE, act_for  # noqa: E402
print(f"WORKED_EXAMPLE = {WORKED_EXAMPLE}  -> the body only ever calls "
      f"route({WORKED_EXAMPLE[0]}, {WORKED_EXAMPLE[1]}, kind)")
print(f"{'kind':>4} {'name':<28} {'act=route(0,5,kind)':>20}  applier")
for k in range(16):
    name = KINDS[k][0] if k in KINDS else "-- not registered --"
    a = act_for(k)
    fn = ACTS.get(a)
    print(f"{k:>4} {name:<28} {a:>20}  "
          f"{getattr(fn, '__name__', 'NONE -- candidates() no-ops')}")

hdr("R10 coverage of the 4096-input domain by the shipped body")
print(f"inputs the body can construct with the shipped WORKED_EXAMPLE: "
      f"16 of 4096 ({16 / 4096:.4%}) -- F1 and A1 are frozen constants")
print(f"of those 16, kinds with a registered fault class: "
      f"{sorted(KINDS)}  ({len(KINDS)}/16)")
print(f"of those, kinds whose act has an applier: "
      f"{sorted(k for k in KINDS if act_for(k) in ACTS)}")
print(f"acts reachable from a shipped kind: "
      f"{sorted(act_for(k) for k in KINDS)}")
print(f"act codes in ACTS that NO shipped kind routes to: "
      f"{sorted(set(ACTS) - {act_for(k) for k in KINDS})}")
print(f"act codes no kind 0..15 can reach at all: "
      f"{sorted(set(range(16)) - {act_for(k) for k in range(16)})}")
