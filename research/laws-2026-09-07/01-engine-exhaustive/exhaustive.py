#!/usr/bin/env python
"""01-engine-exhaustive: re-derive all 256 engine-law rulings.

Three independent sources are compared:
  (1) the readable formula in engine.py's docstring,
          act = (4 & ntzb(x - 7)) + ntzb(x + (x & 128))
      re-implemented here with a plain ntzb;
  (2) the vendored branchless LAW string evaluated raw (before ACTS[...%8]);
  (3) fluidfix.engine.decide (what the body actually consults).
Then every input is checked against the docstring spec and against every
ruling a test pins, and the unpinned inputs are listed.

Run:  /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python exhaustive.py
Writes table.md (all 256 rows) next to itself; prints the summary.
"""
import hashlib
import pathlib
import re
import sys

ROOT = pathlib.Path("/Users/kanchetidevieswar/neo/fluidfix")
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
from fluidfix.engine import ACTS, BITS, LAW, _CODE, _s32, decide, situation  # noqa: E402


def ntzb(y: int) -> int:
    """Trailing-zero count of the byte with bit 0 masked off; 0 when bits
    1..7 are all clear. This is exactly what the branchless LAW computes:
    popcount(((y & 254) & -(y & 254)) - 1) restricted to the low byte, & 7
    (for t == 0 the popcount of the low byte of -1 is 8, and 8 & 7 == 0)."""
    t = y & 254
    return 0 if t == 0 else (t & -t).bit_length() - 1


def formula(x: int) -> int:
    return (4 & ntzb(x - 7)) + ntzb(x + (x & 128))


def raw_law(x: int) -> int:
    return _s32(eval(_CODE, {"__builtins__": {}}, {"x": _s32(x)}))


def bits_of(x: int) -> str:
    return "+".join(b for i, b in enumerate(BITS) if (x >> i) & 1) or "(none)"


def byte_of(names) -> int:
    return sum(1 << BITS.index(n) for n in names)


out = []
P = out.append

# ---- 0. fingerprint ---------------------------------------------------------
fp = hashlib.sha256(LAW.encode()).hexdigest()
P(f"LAW length={len(LAW)} sha256[:16]={fp[:16]}  "
  f"({'matches the 1555/48bf50bff36a2cc9 claim' if len(LAW) == 1555 and fp.startswith('48bf50bff36a2cc9') else 'DRIFTED'})")

# ---- 1. formula vs raw LAW vs decide, all 256, all 4 job values -----------
mismatch_formula_raw = []
mismatch_job = []
table = []
for x in range(256):
    f = formula(x)
    r = raw_law(x | (2 << 8))          # the DEBUG job, as situation() packs it
    if f != r:
        mismatch_formula_raw.append((x, f, r))
    names = {decide(x | (job << 8)) for job in range(4)}
    if len(names) != 1:
        mismatch_job.append((x, names))
    act = decide(situation(**{b: True for i, b in enumerate(BITS) if (x >> i) & 1}))
    assert act == ACTS[r % 8]
    table.append((x, bits_of(x), r, r % 8, act))
P(f"formula (docstring) vs raw LAW, 256 inputs: {256 - len(mismatch_formula_raw)}/256 agree"
  + (f"  MISMATCH {mismatch_formula_raw[:5]}" if mismatch_formula_raw else ""))
P(f"job-invariance (bits 8-9 in 0..3), 256 inputs: {256 - len(mismatch_job)}/256 invariant"
  + (f"  DIFFER {mismatch_job[:5]}" if mismatch_job else ""))

# ---- 2. the raw value range and the %8 wrap ---------------------------------
raws = sorted({r for _, _, r, _, _ in table})
wrapped = [(x, b, r, a) for x, b, r, _, a in table if r >= 8 or r < 0]
P(f"raw LAW values seen: {raws}; inputs where raw >= 8 (ACTS[...%8] wraps): {len(wrapped)}")
for x, b, r, a in wrapped:
    P(f"    x={x:3d} {b:<45} raw={r} -> ACTS[{r % 8}]={a}")

# ---- 3. ruling census --------------------------------------------------------
P("ruling census over 256 inputs:")
for i, a in enumerate(ACTS):
    xs = [x for x, _, _, _, act in table if act == a]
    P(f"    {a:<22} {len(xs):3d} inputs")

# ---- 4. docstring spec: single bits, and the index alignment BITS[i]<->ACTS[i]
P("single-bit rulings (BITS[i] alone) vs ACTS[i]:")
for i, b in enumerate(BITS):
    a = decide(situation(**{b: True}))
    P(f"    {b:<8} -> {a:<22} {'== ACTS[%d]' % i if a == ACTS[i] else '!= ACTS[%d]=%s' % (i, ACTS[i])}")
P(f"no bits set (x=0) -> {decide(situation())}")

# spec lines the docstring states in words
SPEC = [(("BUILT",), "SHIP"),
        (("BUILT", "AMB"), "ADD_STATE"),   # docstring: 'two DIFFERENT candidates both pass'
        (("AMB",), "ADD_STATE"),           # AMB read literally, without BUILT
        (("UNREAD",), "ADD_MATERIAL"),
        (("CAPPED",), "RAISE_BUDGET"),
        (("REFUTED",), "HARVEST_COUNTEREXAMPLE"),
        (("HIDDEN",), "CHANGE_GRANULARITY"),  # from tests/test_c_adapter.py + loop.py
        ]
P("docstring spec lines vs law:")
for names, want in SPEC:
    got = decide(situation(**{n: True for n in names}))
    P(f"    {'+'.join(names):<14} spec={want:<22} law={got:<22} {'OK' if got == want else 'DIFFERS'}")

# ---- 5. what the tests pin --------------------------------------------------
PIN_RE = re.compile(r'decide\(\s*(?:situation|esit)\(\s*([^)]*)\)\s*\)\s*==\s*"([A-Z_]+)"')
INC_RE = re.compile(r'dict\(([^)]*)\),\s*"([A-Z_]+)"')
CITE_RE = re.compile(r"engine law:\s*([A-Z_+ ]+?)\s*->\s*([A-Z_]+)")


def parse_kw(s: str):
    return [k for k, v in re.findall(r"([A-Z_]+)\s*=\s*(True|1)", s)]


pins = {}      # byte -> list of (source, act)


def add_pin(byte, src, act):
    pins.setdefault(byte, []).append((src, act))


for path in sorted((ROOT / "tests").glob("*.py")):
    text = path.read_text(encoding="utf-8")
    for m in PIN_RE.finditer(text):
        ln = text[:m.start()].count("\n") + 1
        add_pin(byte_of(parse_kw(m.group(1))), f"{path.name}:{ln}", m.group(2))
    if path.name == "test_law_never_ruled_wrong.py":
        for m in INC_RE.finditer(text):
            ln = text[:m.start()].count("\n") + 1
            add_pin(byte_of(parse_kw(m.group(1))), f"{path.name}:{ln} (INCIDENTS)", m.group(2))
# cli selfcheck's rulings dict
cli = (ROOT / "src/fluidfix/cli.py").read_text(encoding="utf-8")
m = re.search(r'rulings = \{([^}]*)\}', cli)
for k, v in re.findall(r'"([A-Z_]+)":\s*"([A-Z_]+)"', m.group(1)):
    add_pin(byte_of([k]), "cli.py selfcheck", v)
# fusion-integrity citations (the test re-derives each from the law)
cites = []
for path in sorted((ROOT / "src/fluidfix").glob("*.py")):
    text = path.read_text(encoding="utf-8")
    for m in CITE_RE.finditer(text):
        bits = [b for b in re.split(r"[+ ]+", m.group(1).strip()) if b]
        if bits and all(b in BITS for b in bits):
            ln = text[:m.start()].count("\n") + 1
            cites.append((f"{path.name}:{ln}", bits, m.group(2)))
            add_pin(byte_of(bits), f"{path.name}:{ln} (citation, checked by test_every_cited_ruling...)", m.group(2))

P("citations the fusion-integrity test re-derives (engine law: X -> Y in src):")
for src, bits, act in cites:
    P(f"    {src:<16} {'+'.join(bits):<14} -> {act}")

fusion_only = {}
text = (ROOT / "tests/test_engine_fusion.py").read_text(encoding="utf-8")
for m in PIN_RE.finditer(text):
    fusion_only.setdefault(byte_of(parse_kw(m.group(1))), []).append(m.group(2))

P(f"bytes pinned by a direct decide() assertion in tests/test_engine_fusion.py: {len(fusion_only)}")
for b in sorted(fusion_only):
    P(f"    x={b:3d} {bits_of(b):<20} pinned={fusion_only[b]} law={decide(situation(**{n: True for i, n in enumerate(BITS) if b >> i & 1}))}")
P(f"bytes pinned anywhere (tests/*.py direct asserts + INCIDENTS + selfcheck + src citations): {len(pins)}")
bad_pins = []
for b in sorted(pins):
    law = decide(situation(**{n: True for i, n in enumerate(BITS) if b >> i & 1}))
    srcs = "; ".join(f"{s}={a}" for s, a in pins[b])
    ok = all(a == law for _, a in pins[b])
    if not ok:
        bad_pins.append(b)
    P(f"    x={b:3d} {bits_of(b):<20} law={law:<22} {'OK ' if ok else 'PIN DISAGREES '} {srcs}")
P(f"pins that disagree with the law: {len(bad_pins)}")

# ---- 6. what the body can construct (call sites, read 2026-09-07) ----------
BODY = {
    "loop.py:217  BUILT=True, AMB=set_amb or sites>1, CAPPED=capped": [
        byte_of(["BUILT"]), byte_of(["BUILT", "AMB"]), byte_of(["BUILT", "CAPPED"]),
        byte_of(["BUILT", "AMB", "CAPPED"])],
    "loop.py:391  HIDDEN=True": [byte_of(["HIDDEN"])],
    "guard.py:491 UNREAD=True": [byte_of(["UNREAD"])],
    "guard.py:539 CAPPED=capped0, REFUTED=acts0": [
        0, byte_of(["CAPPED"]), byte_of(["REFUTED"]), byte_of(["CAPPED", "REFUTED"])],
    "guard.py:612,618 REFUTED=True": [byte_of(["REFUTED"])],
}
constructible = sorted({b for bs in BODY.values() for b in bs})
P(f"bytes the body's call sites can construct: {len(constructible)} -> {constructible}")
for site, bs in BODY.items():
    for b in bs:
        law = decide(situation(**{n: True for i, n in enumerate(BITS) if b >> i & 1}))
        P(f"    {site:<60} x={b:3d} {bits_of(b):<20} -> {law:<22} {'PINNED' if b in pins else 'UNPINNED'}")

# ---- 7. the unpinned inputs -------------------------------------------------
unpinned = [x for x in range(256) if x not in pins]
P(f"inputs no test pins: {len(unpinned)}/256")
P("unpinned inputs grouped by ruling:")
for a in ACTS:
    xs = [x for x in unpinned if table[x][4] == a]
    P(f"    {a:<22} {len(xs):3d}: " + " ".join(str(x) for x in xs))
unp_constructible = [b for b in constructible if b not in pins]
P(f"unpinned AND body-constructible: {unp_constructible} -> "
  + ", ".join(f"{bits_of(b)}={table[b][4]}" for b in unp_constructible))

# ---- 8. write the full table ------------------------------------------------
with open(HERE / "table.md", "w", encoding="utf-8") as f:
    f.write("# Engine law: all 256 rulings\n\n")
    f.write("x = observation byte (bit i = BITS[i]); raw = the LAW's integer before "
            "ACTS[raw % 8]; formula = (4 & ntzb(x-7)) + ntzb(x + (x&128)) re-derived "
            "independently. pinned = a test asserts this ruling (source list in "
            "exhaustive.out). body = one of the call sites in loop.py/guard.py can "
            "build this byte today.\n\n")
    f.write("| x | bits | formula | raw | raw%8 | ruling | pinned | body |\n|---|---|---|---|---|---|---|---|\n")
    for x, b, r, r8, a in table:
        f.write(f"| {x} | {b} | {formula(x)} | {r} | {r8} | {a} | "
                f"{'yes' if x in pins else ''} | {'yes' if x in constructible else ''} |\n")

print("\n".join(out))
