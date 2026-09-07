#!/usr/bin/env python
"""16-sight-exhaustive — every claim in REPORT.md is produced by this script.

Run:  /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python exhaustive.py

Sections
  A  all 256 inputs of the Python port vs the sight.c specification
     (table written to table_256.txt next to this script)
  B  lane algebra: each authored lane reduces to one bit of x
  C  R1 algebraically (pointing -> mask bit 0; circumstantial -> bits >= 2)
  D  R2 algebraically (gate = POINT1 - 1 is 0 on every pointing input)
  E  UBIQUITOUS penalty on every input (all 128 lower-byte pairs)
  F  inputs the body cannot construct (FAILONLY and UBIQUITOUS share one
     measurement: specificity >= 0.9 vs specificity < 0.25)
  G  out-of-byte inputs (documentation of the domain, not a defect)
  H  which inputs the tests pin by a named assertion vs only by the loop
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix import sight as S                                  # noqa: E402
from fluidfix.sight import BITS, observe_bits, sight, situation  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
FRAMED, SCARCE, LITERAL = 1, 2, 4
FAILONLY, NAMED, TOUCHED, SMALL, UBIQ = 8, 16, 32, 64, 128


def spec_c(x: int) -> int:
    """Transcribed from docs/laws/sight.c spec()."""
    if x & 7:
        return 0
    if (x >> 3) & 1:
        return 2 + ((x >> 7) & 1)
    if (x >> 4) & 1:
        return 3 + ((x >> 7) & 1)
    if (x >> 5) & 1:
        return 4 + ((x >> 7) & 1)
    if (x >> 6) & 1:
        return 5 + ((x >> 7) & 1)
    return 6 + ((x >> 7) & 1)


def closed_form(x: int) -> int:
    """My own reduction of the authored expression (derived in section B):
    pointing -> 0; else ctz(circumstantial bits shifted down one | 64) plus
    the penalty bit."""
    if x & 7:
        return 0
    m = ((x >> 1) & 0x3C) | 64
    return (m & -m).bit_length() - 1 + ((x >> 7) & 1)


def names(x: int) -> str:
    return "+".join(b for i, b in enumerate(BITS) if (x >> i) & 1) or "-"


def ctz(m: int) -> int:
    return (m & -m).bit_length() - 1


def section(title: str) -> None:
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


# ------------------------------------------------------------------ A ----
section("A  all 256 inputs: Python port vs sight.c specification")
rows = []
wrong = []
for x in range(256):
    got, want = sight(x), spec_c(x)
    rows.append((x, names(x), got, want))
    if got != want:
        wrong.append(x)
with open(os.path.join(HERE, "table_256.txt"), "w") as fh:
    fh.write("x    bits                                                sight  spec  closed_form\n")
    for x, nm, got, want in rows:
        fh.write(f"{x:<4d} {nm:<50s} {got:<6d} {want:<5d} {closed_form(x)}\n")
print(f"mismatches vs spec_c            : {len(wrong)}  {wrong}")
print(f"mismatches vs my closed form    : "
      f"{sum(sight(x) != closed_form(x) for x in range(256))}")
print(f"outputs outside 0..7            : "
      f"{[x for x in range(256) if not 0 <= sight(x) <= 7]}")
hist = {p: sum(1 for x in range(256) if sight(x) == p) for p in range(8)}
print(f"how many inputs land on each priority: {hist}")
print("table written to table_256.txt")

# ------------------------------------------------------------------ B ----
section("B  lane algebra: each authored lane is one bit of x (all 256)")
bit = lambda x, i: (x >> i) & 1                                    # noqa: E731
checks = {
    "_POINT1(x)   == (x & 7 != 0)":     all(S._POINT1(x) == int(x & 7 != 0) for x in range(256)),
    "_FAILONLY(x) == 4  * bit3":        all(S._FAILONLY(x) == 4 * bit(x, 3) for x in range(256)),
    "_NAMED(x)    == 8  * bit4":        all(S._NAMED(x) == 8 * bit(x, 4) for x in range(256)),
    "_TOUCHED(x)  == 16 * bit5":        all(S._TOUCHED(x) == 16 * bit(x, 5) for x in range(256)),
    "_SMALL(x)    == 32 * bit6":        all(S._SMALL(x) == 32 * bit(x, 6) for x in range(256)),
    "_UBIQ(x)     == bit7":             all(S._UBIQ(x) == bit(x, 7) for x in range(256)),
    "circ sum     == (x>>1) & 0x3C (disjoint powers of two, sum == OR)":
        all(S._FAILONLY(x) + S._NAMED(x) + S._TOUCHED(x) + S._SMALL(x) == ((x >> 1) & 0x3C)
            for x in range(256)),
    "_EMIT(m)     == lowest set bit, m in 1..255":
        all(S._EMIT(m) == (m & -m) for m in range(1, 256)),
}
for k, v in checks.items():
    print(f"  {'OK ' if v else 'BAD'}  {k}")
# the POINT1 identity beyond the byte (the derivation in the docstring is
# for x = 8*high + low; check it on a wider signed range too)
wide = all(S._POINT1(x) == int(x & 7 != 0) for x in range(-(1 << 16), 1 << 16))
print(f"  {'OK ' if wide else 'BAD'}  _POINT1 identity on -65536..65535 (signed, Python port)")
mask_ok = True
for x in range(256):
    p = S._POINT1(x)
    gate = p - 1
    circ = ((x >> 1) & 0x3C)
    mask = p + (gate & circ) + 64
    expect = 65 if x & 7 else (circ | 64)
    if mask != expect:
        mask_ok = False
print(f"  {'OK ' if mask_ok else 'BAD'}  mask == 65 on pointing inputs, == circ|64 on non-pointing")
print("  therefore sight(x) == 0 (pointing) or ctz(circ|64) + bit7 (non-pointing)")

# ------------------------------------------------------------------ C ----
section("C  R1 algebraically and exhaustively")
pointing = [x for x in range(256) if x & 7]
plain = [x for x in range(256) if not x & 7]
print(f"pointing inputs: {len(pointing)}   non-pointing inputs: {len(plain)}")
print(f"max sight over pointing     : {max(sight(x) for x in pointing)}")
print(f"min sight over non-pointing : {min(sight(x) for x in plain)}")
print("  gap is the reserved priority 1: pointing -> mask bit 0 (ctz 0); "
      "non-pointing -> lowest circumstantial slot is mask bit 2 (ctz >= 2)")
r1_bad = [(a, b) for a in pointing for b in plain if not sight(a) < sight(b)]
print(f"R1 pairs checked: {len(pointing) * len(plain)}   violations: {len(r1_bad)}")

# ------------------------------------------------------------------ D ----
section("D  R2 algebraically and exhaustively")
gates_pointing = {S._POINT1(x) - 1 for x in pointing}
gates_plain = {S._POINT1(x) - 1 for x in plain}
print(f"gate values on pointing inputs    : {gates_pointing}   (0 kills circ AND penalty)")
print(f"gate values on non-pointing inputs: {gates_plain}   (-1 = all ones passes both)")
r2_bad = [x for x in pointing if sight(x) != sight(x & 0x7F)]
print(f"R2 pointing inputs checked: {len(pointing)}   violations: {len(r2_bad)}")
# and the converse: on non-pointing inputs the penalty always lands
r2_conv = [x for x in plain if not x & UBIQ and sight(x | UBIQ) != sight(x) + 1]
print(f"converse: non-pointing inputs where UBIQ does NOT add exactly 1: {r2_conv}")

# ------------------------------------------------------------------ E ----
section("E  UBIQUITOUS penalty on every input (128 lower-byte pairs)")
deltas = {}
for low in range(128):
    deltas[low] = sight(low | UBIQ) - sight(low)
from collections import Counter                                    # noqa: E402
print(f"delta histogram over the 128 pairs: {dict(Counter(deltas.values()))}")
print("the 16 non-pointing pairs (the only ones the penalty touches):")
print(f"  {'low':>4} {'bits':<34} {'w/o':>4} {'with':>4}")
for low in range(128):
    if not low & 7:
        print(f"  {low:>4} {names(low):<34} {sight(low):>4} {sight(low | UBIQ):>4}")
print()
print("cross-tier ties the penalty creates (a|UBIQ ties b, a != b, both non-pointing):")
ties = []
for a in plain:
    if a & UBIQ:
        continue
    for b in plain:
        if b & UBIQ or b == a:
            continue
        if sight(a | UBIQ) == sight(b) and sight(a) != sight(b):
            ties.append((a, b))
tie_classes = sorted({(sight(a), sight(a | UBIQ), sight(b)) for a, b in ties})
print(f"  {len(ties)} ordered pairs; distinct (prio(a), prio(a|UBIQ)==prio(b)) classes: {tie_classes}")
examples = {}
for a, b in ties:
    key = (sight(a | UBIQ))
    examples.setdefault(key, (a, b))
for key, (a, b) in sorted(examples.items()):
    print(f"    {names(a)}+UBIQUITOUS -> {sight(a | UBIQ)}  ==  {names(b)} -> {sight(b)}")
print()
print("order flips: a ahead of b without the penalty, behind it with the penalty on a:")
flips = [(a, b) for a in plain if not a & UBIQ for b in plain
         if sight(a) < sight(b) and sight(a | UBIQ) > sight(b)]
print(f"  {len(flips)} ordered pairs (a, b)  -- the penalty is exactly one tier, so a"
      " flip needs prio(b) == prio(a)+1 ... : {}".format(
          sorted({(sight(a), sight(b)) for a, b in flips})))

# ------------------------------------------------------------------ F ----
section("F  inputs the body's caller cannot construct (guard.py file_priority2)")
print("  failonly   = specificity >= 0.9")
print("  ubiquitous = specificity < 0.25       -- same variable, so both set is impossible")
contra = [x for x in range(256) if x & FAILONLY and x & UBIQ]
contra_pointing = [x for x in contra if x & 7]
contra_plain = [x for x in contra if not x & 7]
print(f"inputs with FAILONLY and UBIQUITOUS both set : {len(contra)} of 256")
print(f"  of which pointing (rule 0 regardless)      : {len(contra_pointing)}")
print(f"  of which non-pointing                      : {len(contra_plain)}  "
      f"-> rulings {sorted({sight(x) for x in contra_plain})}")
print(f"  the non-pointing eight: {[(x, names(x), sight(x)) for x in contra_plain]}")
print(f"inputs constructible w.r.t. this constraint  : {256 - len(contra)}")
# what priority-3 means with and without the constraint
p3_all = [x for x in range(256) if sight(x) == 3]
p3_reach = [x for x in p3_all if x not in contra]
print(f"priority 3 is emitted for {len(p3_all)} inputs; body-constructible: {len(p3_reach)}")
print(f"  constructible priority-3 inputs: {[(x, names(x)) for x in p3_reach]}")
# same for every priority
for p in range(8):
    allp = [x for x in range(256) if sight(x) == p]
    reach = [x for x in allp if x not in contra]
    print(f"  priority {p}: {len(allp):3d} inputs, {len(reach):3d} body-constructible")

# ------------------------------------------------------------------ G ----
section("G  out-of-byte inputs (domain note; situation()/observe_bits() cannot produce them)")
for x in (256, 384, 512, 1024, -1, -128):
    print(f"  sight({x:>5}) = {sight(x):>4}   (x>>7 = {x >> 7})")
print(f"  max packable by situation(): {situation(**{b: True for b in BITS})}")
print(f"  observe_bits(all True)     : {observe_bits(**{k: True for k in ('framed','scarce','literal','failonly','named','touched','small','ubiquitous')})}")

# ------------------------------------------------------------------ H ----
section("H  inputs pinned by a NAMED assertion in tests/test_sight_law.py")
named_pins = {
    LITERAL: "incident 1: sight(LITERAL) == 0",
    SCARCE | UBIQ: "incident 2: sight(SCARCE|UBIQ) == 0 and < sight(NAMED)",
    NAMED: "incident 2 / r2-demote: sight(NAMED) reference",
    NAMED | SMALL | TOUCHED: "incident 2: shell_completion_py situation",
    0: "incident 3: sight(0) == 6; r2-demote: sight(0|UBIQ) > sight(0)",
    UBIQ: "r2-demote: sight(0|UBIQ) > sight(0)",
    NAMED | UBIQ: "r2-demote: sight(NAMED|UBIQ) > sight(NAMED)",
    FRAMED: "equal-rank: sight(FRAMED) == 0",
    SCARCE: "equal-rank: sight(SCARCE) == 0",
}
for x, why in sorted(named_pins.items()):
    print(f"  {x:>3} {names(x):<30} -> {sight(x)}   {why}")
print(f"  {len(named_pins)} inputs pinned by name; the other {256 - len(named_pins)} only by the"
      " exhaustive loop test_matches_specification_on_all_256_situations (which pins all 256)")

print()
print("DONE")
