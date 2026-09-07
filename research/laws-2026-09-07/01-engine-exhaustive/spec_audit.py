#!/usr/bin/env python
"""01-engine-exhaustive, part 2: the DOCSTRING SPEC vs the law vs the BODY.

Three checks, all mechanical, no hand-typed numbers:

  A. The docstring's per-bit table (BITS[i] -> ACTS[i]) against the law on
     every single-bit input.
  B. The docstring's standing claim, quoted verbatim from engine.py:
        "NOTWIN, HIDDEN and SELF are not yet measured by fluidfix and are
         never set"
     against every `decide(situation(...))` call site actually present in
     src/fluidfix/*.py (parsed, not remembered).
  C. Entry conditions: for each of the 8 acts, the minimal observation bytes
     that reach it, so an unreachable lane can be named exactly.

Run: /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python spec_audit.py
"""
import pathlib
import re
import sys

ROOT = pathlib.Path("/Users/kanchetidevieswar/neo/fluidfix")
sys.path.insert(0, str(ROOT / "src"))
import fluidfix.engine as E  # noqa: E402
from fluidfix.engine import ACTS, BITS, decide, situation  # noqa: E402


def rule(x):
    return decide(situation(**{b: True for i, b in enumerate(BITS) if x >> i & 1}))


def names(x):
    return "+".join(b for i, b in enumerate(BITS) if x >> i & 1) or "(none)"


print("=== A. docstring per-bit table: BITS[i] alone -> ACTS[i]? ===")
dev = []
for i, b in enumerate(BITS):
    got = rule(1 << i)
    ok = got == ACTS[i]
    if not ok:
        dev.append((b, ACTS[i], got))
    print(f"    bit {i} {b:<8} table says {ACTS[i]:<22} law rules {got:<22} "
          f"{'OK' if ok else 'DEVIATES'}")
print(f"    per-bit table holds on {8 - len(dev)}/8 bits; deviations: {dev}")
for b, want, got in dev:
    reach = [x for x in range(256) if rule(x) == want]
    print(f"    {want} is instead reached by {len(reach)} bytes, all of which "
          f"have NOTWIN set: {all((x >> BITS.index('NOTWIN')) & 1 for x in reach)}")
    print(f"      e.g. {[names(x) for x in reach[:3]]}")

print()
print("=== B. docstring claim vs the call sites in src/fluidfix/*.py ===")
doc = E.__doc__ or ""
m = re.search(r"NOTWIN, HIDDEN and SELF[^.]*\.", doc.replace("\n", " "))
print(f"    engine.py docstring says: {re.sub(r'  +', ' ', m.group(0)) if m else 'CLAIM NOT FOUND'}")

def call_args(text, open_at):
    """Balanced-paren slice of situation(...) starting at the '(' index.
    A regex with [^)]* silently truncates `AMB=set_amb or len(sites) > 1`
    and drops the whole loop.py call site, so match parens properly."""
    depth, i = 0, open_at
    while i < len(text):
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
            if depth == 0:
                return text[open_at + 1:i]
        i += 1
    return ""


CALL = re.compile(r"decide\(\s*situation\s*\(")
set_by = {}
for path in sorted((ROOT / "src" / "fluidfix").glob("*.py")):
    if path.name == "engine.py":
        continue
    text = path.read_text(encoding="utf-8")
    for mm in CALL.finditer(text):
        ln = text[:mm.start()].count("\n") + 1
        args = call_args(text, mm.end() - 1)
        args_flat = re.sub(r"\s+", " ", args)
        for kw in re.findall(r"\b([A-Z_]+)\s*=", args_flat):
            if kw in BITS:
                val = re.search(rf"\b{kw}\s*=\s*(.+?)(?:,\s*[A-Z_]+\s*=|$)",
                                args_flat)
                set_by.setdefault(kw, []).append(
                    f"{path.name}:{ln} ({kw}={val.group(1).strip() if val else '?'})")
for b in BITS:
    sites = set_by.get(b, [])
    print(f"    {b:<8} {'SET at ' + '; '.join(sites) if sites else 'never passed to decide() anywhere in src/'}")
claimed_never = ["NOTWIN", "HIDDEN", "SELF"]
contradict = [b for b in claimed_never if set_by.get(b)]
print(f"    bits the docstring calls 'never set' that the body DOES set: {contradict}")
truly_never = [b for b in BITS if not set_by.get(b)]
print(f"    bits genuinely never passed to decide(): {truly_never}")

print()
print("=== C. entry condition for each act (minimal bytes that reach it) ===")
for i, a in enumerate(ACTS):
    xs = [x for x in range(256) if rule(x) == a]
    minpop = min(bin(x).count("1") for x in xs)
    mins = [x for x in xs if bin(x).count("1") == minpop]
    always = [b for j, b in enumerate(BITS) if all((x >> j) & 1 for x in xs)]
    print(f"    {a:<22} {len(xs):3d} bytes; smallest observation = "
          f"{minpop} bit(s): {[names(x) for x in mins]}")
    print(f"        bits required in EVERY byte that reaches it: {always or '(none)'}")

print()
print("=== D. what the never-measured bits cost, act by act ===")
never = truly_never
print(f"    never-measured bits: {never}")
for b in never:
    j = BITS.index(b)
    acts_needing = [a for a in ACTS
                    if all((x >> j) & 1 for x in range(256) if rule(x) == a)]
    lost = [x for x in range(256) if rule(x) in acts_needing]
    print(f"    {b:<8} is REQUIRED by acts {acts_needing} "
          f"({len(lost)} of 256 bytes) -> those acts are unreachable while "
          f"{b} is never measured")
reachable_bits = [b for b in BITS if set_by.get(b)]
mask = sum(1 << BITS.index(b) for b in reachable_bits)
reach_acts = sorted({rule(x) for x in range(256) if x & ~mask == 0})
print(f"    bits the body CAN set: {reachable_bits} (mask={mask})")
print(f"    acts reachable from ANY combination of those bits: {reach_acts}")
print(f"    acts unreachable no matter how those bits combine: "
      f"{[a for a in ACTS if a not in reach_acts]}")
