#!/usr/bin/env python
"""07-engine-precedence: exhaustive precedence analysis of the engine law.

Read-only. Imports the vendored law, never edits it. Run with
    /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python precedence.py
"""
import itertools
import re
import sys
from pathlib import Path

sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix.engine import ACTS, BITS, LAW, _CODE, _s32, decide, situation  # noqa: E402

B = {name: i for i, name in enumerate(BITS)}
SRC = Path("/Users/kanchetidevieswar/neo/fluidfix/src/fluidfix")


def names(byte: int) -> str:
    return "+".join(b for b in BITS if byte >> B[b] & 1) or "(none)"


def sit(byte: int) -> int:
    return situation(**{b: True for b in BITS if byte >> B[b] & 1})


def raw_decide(x: int) -> str:
    """decide() on an arbitrary x (lets us vary the job bits 8-9)."""
    return ACTS[_s32(eval(_CODE, {"__builtins__": {}}, {"x": _s32(x)})) % 8]


def ntz_1to7(v: int) -> int:
    """The law's ntzb as the formula actually computes it: over (v & 254)
    only, 0 when that is zero (popcount(0xFFFFFFFF)=32, &7 -> 0)."""
    v &= 254
    if v == 0:
        return 0
    return (v & -v).bit_length() - 1


# --------------------------------------------------------------- part 1 ----
print("=" * 72)
print("PART 1  all 256 rulings from decide(situation(...))")
print("=" * 72)
table = {byte: decide(sit(byte)) for byte in range(256)}
hist = {a: sum(1 for v in table.values() if v == a) for a in ACTS}
for a in ACTS:
    print(f"  {a:23s} {hist[a]:3d}/256")

# --------------------------------------------------------------- part 2 ----
print()
print("=" * 72)
print("PART 2  algebraic model  act = (T1 + T2) mod 8")
print("        T2 = ntz over bits AMB..REFUTED (SELF cleared by x+(x&128)); 0 if none")
print("        T1 = 4 iff borrow of x-7 lands the lowest set bit at index >= 4:")
print("             (BUILT=AMB=UNREAD=0 and NOTWIN=1 and any of HIDDEN/CAPPED/REFUTED/SELF)")
print("          or (BUILT=AMB=UNREAD=1 and NOTWIN=0 and any of HIDDEN/CAPPED/REFUTED/SELF)")
print("=" * 72)


def model(byte: int) -> str:
    low3 = byte & 7
    notwin = byte >> 3 & 1
    high4 = byte >> 4 & 15
    t2 = ntz_1to7(byte & 0x7E)           # bits 1..6
    t1 = 4 if high4 and ((low3 == 0 and notwin) or (low3 == 7 and not notwin)) else 0
    return ACTS[(t1 + t2) % 8]


def model_terms(byte: int):
    """The two terms exactly as the formula computes them (for display)."""
    x = sit(byte)
    return 4 & ntz_1to7(x - 7), ntz_1to7(x + (x & 128))


mism = [b for b in range(256) if model(b) != table[b]]
print(f"  model == decide on {256 - len(mism)}/256 bytes; mismatches: {mism}")
# and the two-term reading of the formula itself
term_mism = [b for b in range(256)
             if ACTS[sum(model_terms(b)) % 8] != table[b]]
print(f"  (4 & ntz(x-7)) + ntz(x+(x&128)) mod 8 == decide on "
      f"{256 - len(term_mism)}/256; mismatches: {term_mism}")

jobs = {}
for job in range(4):
    jobs[job] = [raw_decide(byte | (job << 8)) for byte in range(256)]
job_diff = sum(1 for byte in range(256)
               if len({jobs[j][byte] for j in range(4)}) > 1)
print(f"  job-invariance (bits 8-9 = 0..3): {job_diff}/256 bytes differ")

# --------------------------------------------------------------- part 3 ----
print()
print("=" * 72)
print("PART 3  precedence ladder: lowest set bit among AMB<UNREAD<NOTWIN<HIDDEN<CAPPED<REFUTED wins")
print("        BUILT and SELF never win when any of those six is set")
print("=" * 72)
LADDER = ["AMB", "UNREAD", "NOTWIN", "HIDDEN", "CAPPED", "REFUTED"]
single = {b: decide(situation(**{b: True})) for b in BITS}
print("  single-bit rulings:")
for b in BITS:
    print(f"    {b:8s} -> {single[b]}")
print(f"    (none)   -> {decide(situation())}")


def ladder_predict(byte: int) -> str:
    for b in LADDER:
        if byte >> B[b] & 1:
            return single[b]
    return "SHIP"


exc = [b for b in range(256) if ladder_predict(b) != table[b]]
print(f"  ladder predicts decide on {256 - len(exc)}/256; exceptions: {len(exc)}")
famA = [b for b in exc if (b & 7) == 0 and b >> 3 & 1]
famB = [b for b in exc if (b & 7) == 7 and not (b >> 3 & 1)]
other = [b for b in exc if b not in famA and b not in famB]
print(f"  family A (no BUILT/AMB/UNREAD, NOTWIN + any of HIDDEN/CAPPED/REFUTED/SELF): {len(famA)}")
for b in famA:
    print(f"    {names(b):45s} ladder={ladder_predict(b):10s} law={table[b]}")
print(f"  family B (BUILT+AMB+UNREAD, no NOTWIN, + any of HIDDEN/CAPPED/REFUTED/SELF): {len(famB)}")
for b in famB:
    print(f"    {names(b):45s} ladder={ladder_predict(b):10s} law={table[b]}")
print(f"  exceptions outside A/B: {other}")

ship_bytes = [b for b in range(256) if table[b] == "SHIP"]
print(f"  bytes ruling SHIP: {[names(b) for b in ship_bytes]}")
built_not_ship = [b for b in range(256) if b & 1 and table[b] != "SHIP"]
print(f"  BUILT set but ruling != SHIP: {len(built_not_ship)}/128 "
      f"(every one has some bit of AMB..REFUTED set: "
      f"{all(b & 0x7E for b in built_not_ship)})")

# --------------------------------------------------------------- part 4 ----
print()
print("=" * 72)
print("PART 4  every pair of bits: ruling, and which single-bit ruling it equals")
print("=" * 72)
for i, j in itertools.combinations(range(8), 2):
    byte = (1 << i) | (1 << j)
    r = table[byte]
    who = [b for b in (BITS[i], BITS[j]) if single[b] == r]
    winner = "/".join(who) if who else "NEITHER"
    print(f"  {names(byte):18s} -> {r:23s} wins: {winner}")

# --------------------------------------------------------------- part 5 ----
print()
print("=" * 72)
print("PART 5  every triple containing BUILT (the target's named cases first)")
print("=" * 72)
named = [("BUILT", "AMB", "CAPPED"), ("BUILT", "HIDDEN", "AMB")]
rest = [t for t in itertools.combinations(BITS, 3)
        if "BUILT" in t and tuple(sorted(t)) not in {tuple(sorted(n)) for n in named}]
for t in named + rest:
    byte = sum(1 << B[b] for b in t)
    r = table[byte]
    who = [b for b in t if single[b] == r]
    print(f"  {names(byte):28s} -> {r:23s} wins: {'/'.join(who) or 'NEITHER'}")

# --------------------------------------------------------------- part 6 ----
print()
print("=" * 72)
print("PART 6  situations the body can construct today (from the six call sites)")
print("=" * 72)
sites = [
    ("loop.py:217 _rule()", ["BUILT"], ["AMB", "CAPPED"]),
    ("loop.py:391 re-check", ["HIDDEN"], []),
    ("guard.py:491 no candidates, no pytest-cov", ["UNREAD"], []),
    ("guard.py:539 escalation gate", [], ["CAPPED", "REFUTED"]),
    ("guard.py:612/618 refusal hint", ["REFUTED"], []),
]
reach = {}
for where, fixed, var in sites:
    for k in range(len(var) + 1):
        for combo in itertools.combinations(var, k):
            byte = sum(1 << B[b] for b in fixed + list(combo))
            reach.setdefault(byte, []).append(where)
print(f"  distinct constructible bytes: {len(reach)}/256")
for byte in sorted(reach):
    print(f"    {names(byte):22s} -> {table[byte]:23s} via {reach[byte][0]}"
          + (f" (+{len(reach[byte]) - 1} more site)" if len(reach[byte]) > 1 else ""))
multi = [b for b in reach if bin(b).count('1') >= 2]
print(f"  multi-bit constructible bytes (precedence actually exercised): "
      f"{[names(b) for b in multi]}")

# --------------------------------------------------------------- part 7 ----
print()
print("=" * 72)
print("PART 7  intended rulings stated in docstrings/tests/CHANGELOG vs the law")
print("=" * 72)
intended = [
    ("BUILT", "SHIP", "engine.py docstring"),
    ("BUILT+AMB", "ADD_STATE", "engine.py docstring; test_rulings_fluidfix_depends_on; CHANGELOG 0.6.0"),
    ("BUILT+CAPPED", "RAISE_BUDGET", "loop.py _rule docstring; CHANGELOG 2026-09-04"),
    ("BUILT+AMB+CAPPED", "ADD_STATE", "loop.py:236 message cites BUILT+AMB -> ruling on this 3-bit byte"),
    ("CAPPED+REFUTED", "RAISE_BUDGET", "test_rulings_fluidfix_depends_on"),
    ("HIDDEN", "CHANGE_GRANULARITY", "loop.py:355 comment; CHANGELOG 0.13.0"),
    ("UNREAD", "ADD_MATERIAL", "engine.py docstring; guard.py:491"),
    ("REFUTED", "HARVEST_COUNTEREXAMPLE", "engine.py docstring; guard.py:612"),
    ("CAPPED", "RAISE_BUDGET", "engine.py docstring; guard.py:539"),
]
ok = 0
for spec, want, src in intended:
    got = decide(situation(**{b: True for b in spec.split("+")}))
    ok += got == want
    print(f"  {spec:18s} intended {want:23s} law {got:23s} {'OK' if got == want else 'DIFFERS'}   [{src}]")
print(f"  {ok}/{len(intended)} intended rulings match the law")

# --------------------------------------------------------------- part 8 ----
print()
print("=" * 72)
print("PART 8  which multi-bit citations the fusion-integrity regex actually audits")
print("        (tests/test_engine_fusion.py::test_every_cited_ruling_in_the_source_is_a_real_ruling)")
print("=" * 72)
pat = re.compile(r"engine law:\s*([A-Z_+ ]+?)\s*->\s*([A-Z_]+)")
loose = re.compile(r"engine law:\s*([A-Z_+ ]+?)\s*->\s*(\{?[A-Za-z_]+\}?)")
for path in sorted(SRC.glob("*.py")):
    text = path.read_text(encoding="utf-8")
    for m in loose.finditer(text):
        raw_bits, act = m.group(1).strip(), m.group(2)
        audited = bool(pat.match(m.group(0)))
        bits = [b for b in re.split(r"[+ ]+", raw_bits) if b]
        if not all(b in BITS for b in bits):
            continue
        real = decide(situation(**{b: True for b in bits}))
        line = text[:m.start()].count("\n") + 1
        print(f"  {path.name}:{line:<4d} '{raw_bits} -> {act}'  law={real:23s} "
              f"{'AUDITED' if audited else 'NOT audited (f-string placeholder)'}")
