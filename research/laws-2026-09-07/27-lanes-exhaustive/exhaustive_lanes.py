#!/usr/bin/env python
"""Exhaustive enumeration of every input of lanes.py EMIT / ADVANCE / HALT.

Run:  ./tmo 300 /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python exhaustive_lanes.py

Three domains are enumerated, because three different documents claim three
different domains for this law:

  D8   m in 0..255      -- what lanes.py's docstring, tests/test_lanes.py and
                           `fluidfix selfcheck` verify ("all 256 mask states")
  D16  m in 0..65535    -- what loop.py:283 can actually construct
                           (mask_of(k for k in obs.kinds if 0 <= k <= 15))
  OOD  hand-picked out-of-domain values (negative, 2**31, 2**32, bool, huge)

For each m the reference is the docstring spec:
  EMIT(m)    == lowest set bit of m           == m & -m
  ADVANCE(m) == m with that bit cleared       == m & (m - 1)
  HALT(m)    == 1 iff m == 0 else 0
plus the loop-discipline properties the docstring rests on:
  strict reduction   ADVANCE(m) < m for m != 0
  drain length       #ADVANCE steps to HALT == popcount(m)
  round trip         kind_of(EMIT(m)) == index of lowest set bit
"""
import sys

sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix.lanes import ADVANCE, EMIT, HALT, kind_of, mask_of  # noqa: E402


def check_domain(name, values):
    bad = {"EMIT": [], "ADVANCE": [], "HALT": [], "STRICT": [],
           "DRAIN": [], "KIND_OF": []}
    n = 0
    for m in values:
        n += 1
        if m:
            if EMIT(m) != (m & -m):
                bad["EMIT"].append(m)
            if ADVANCE(m) != (m & (m - 1)):
                bad["ADVANCE"].append(m)
            if ADVANCE(m) >= m:
                bad["STRICT"].append(m)
            if kind_of(EMIT(m)) != (m & -m).bit_length() - 1:
                bad["KIND_OF"].append(m)
        if HALT(m) != (1 if m == 0 else 0):
            bad["HALT"].append(m)
        # drain: bounded so a non-terminating mask cannot hang the run
        w, steps = m, 0
        while not HALT(w):
            w = ADVANCE(w)
            steps += 1
            if steps > 64:
                bad["DRAIN"].append(("no-halt", m))
                break
        else:
            if steps != bin(m).count("1") if m >= 0 else True:
                if m >= 0 and steps != bin(m).count("1"):
                    bad["DRAIN"].append((m, steps, bin(m).count("1")))
    print(f"--- domain {name}: {n} inputs")
    for k, v in bad.items():
        print(f"    {k:8s} wrong: {len(v)}" + (f"  e.g. {v[:6]}" if v else ""))
    return bad


print("== D8: m in 0..255 (what the docstring/tests/selfcheck verify) ==")
check_domain("D8", range(256))

print()
print("== D16: m in 0..65535 (what loop.py:283 can construct) ==")
check_domain("D16", range(65536))

print()
print("== EMIT/ADVANCE/HALT truth table, first 17 masks ==")
print(f"{'m':>6} {'bin':>18} {'EMIT':>6} {'ADVANCE':>8} {'HALT':>5} {'kind':>5}")
for m in list(range(17)):
    print(f"{m:6d} {bin(m):>18} {EMIT(m):6d} {ADVANCE(m):8d} {HALT(m):5d} "
          f"{kind_of(EMIT(m)) if m else '-':>5}")

print()
print("== OOD: values outside 0..65535 that a caller could hand the law ==")
ood = [-1, -2, -8, -255, -256, 2 ** 16, 2 ** 31 - 1, 2 ** 31, -(2 ** 31),
       2 ** 32, 2 ** 63, True, False]
for m in ood:
    try:
        e, a, h = EMIT(m), ADVANCE(m), HALT(m)
    except Exception as exc:                                  # noqa: BLE001
        print(f"  m={m!r:>14}  RAISES {type(exc).__name__}: {exc}")
        continue
    want_h = 1 if m == 0 else 0
    flag = "" if h == want_h else "   <== HALT DISAGREES WITH SPEC"
    strict = "" if (m == 0 or a < m) else "   <== ADVANCE NOT A REDUCTION"
    print(f"  m={m!r:>14}  EMIT={e:<14} ADVANCE={a:<16} HALT={h} "
          f"(spec {want_h}){flag}{strict}")

print()
print("== the C expression this Python is a port of ==")
print("   docstring: 32-bit semantics of ((m - (m - 1)) + ((-m) >> 31))")


def halt_c32(m):
    """Literal C int32_t evaluation of the authored expression."""
    def w(x):
        x &= 0xFFFFFFFF
        return x - (1 << 32) if x >= (1 << 31) else x
    a = w(m - w(m - 1))
    b = w(-m) >> 31          # arithmetic shift, C semantics for int32_t
    return w(a + b)


div = [m for m in list(range(-1024, 1024)) + [2 ** 31 - 1, -(2 ** 31)]
       if halt_c32(m) != HALT(m)]
print(f"   python HALT vs literal C-int32 evaluation, m in -1024..1023 plus "
      f"INT32 extremes: {len(div)} divergences" +
      (f" -> {div[:8]}" if div else ""))
for m in div[:8]:
    print(f"     m={m}: python HALT={HALT(m)}  C-int32 HALT={halt_c32(m)}")

print()
print("== mask_of / kind_of domain ==")
for ks in ([0, 3], [12], [0, 1, 2, 3, 8, 9, 10, 11, 12], [15], [1, 1, 1],
           [3, 1], [1, 3]):
    print(f"  mask_of({ks}) = {mask_of(ks)} = {bin(mask_of(ks))}")
for ks in ([-1], [16], [64], [True]):
    try:
        print(f"  mask_of({ks}) = {mask_of(ks)}")
    except Exception as exc:                                  # noqa: BLE001
        print(f"  mask_of({ks}) RAISES {type(exc).__name__}: {exc}")
try:
    print(f"  kind_of(0) = {kind_of(0)}   <== EMIT of an empty mask")
except Exception as exc:                                      # noqa: BLE001
    print(f"  kind_of(0) RAISES {type(exc).__name__}: {exc}")
