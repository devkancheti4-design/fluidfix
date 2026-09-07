#!/usr/bin/env python
"""The actuation map for target 03-engine-actuation-map.

For each of the engine law's 8 ACTS, find mechanically:
  (a) every decide() call site in the body whose ruling can BE that act;
  (b) every place the act NAME is compared (`== "ACT"`) -- the only way a
      ruling can change control flow;
  (c) every place the act name is only interpolated into a string.

Classification:
  BEHAVIOURAL  some `== "ACT"` comparison gates a branch that changes what
               the body DOES (writes a file, retries, stops).
  WORDING      the ruling is computed and reaches the user only as text;
               removing the comparison would change no repair outcome.
  NONE         the act name appears nowhere outside engine.py's ACTS list.

Run: /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python actuation_map.py
"""
import os
import re
import sys

SRC = "/Users/kanchetidevieswar/neo/fluidfix/src"
sys.path.insert(0, SRC)
from fluidfix.engine import ACTS, BITS, decide, situation  # noqa: E402

BODY = ["fluidfix/loop.py", "fluidfix/guard.py", "fluidfix/acts.py",
        "fluidfix/oracle.py", "fluidfix/coracle.py", "fluidfix/cli.py",
        "fluidfix/localize.py", "fluidfix/observers.py",
        "fluidfix/hotspots.py", "fluidfix/javaoracle.py"]

lines = {}
for rel in BODY:
    with open(os.path.join(SRC, rel), encoding="utf-8") as f:
        lines[rel] = f.read().splitlines()

# ---------------------------------------------------------------- part 1 --
# every decide() call site in the body, and the acts it can return.
print("== 1. decide() call sites in the body, and every act each can return ==")
CALLSITES = {
    # (file, line) -> (description, [situation kwargs the body can build])
    ("fluidfix/loop.py", 217): (
        "_rule(): BUILT always true; AMB = set_amb or len(sites)>1; CAPPED arg",
        [dict(BUILT=True, AMB=a, CAPPED=c)
         for a in (False, True) for c in (False, True)]),
    ("fluidfix/loop.py", 391): (
        "confirm re-runs disagree with the first green",
        [dict(HIDDEN=True)]),
    ("fluidfix/guard.py", 491): (
        "no candidate files and pytest-cov absent",
        [dict(UNREAD=True)]),
    ("fluidfix/guard.py", 539): (
        "escalation gate; CAPPED=capped0, REFUTED=acts0",
        [dict(CAPPED=c, REFUTED=r) for c in (False, True) for r in (False, True)]),
    ("fluidfix/guard.py", 612): (
        "post-escalation refusal wording", [dict(REFUTED=True)]),
    ("fluidfix/guard.py", 618): (
        "first-pass refusal wording", [dict(REFUTED=True)]),
    ("fluidfix/cli.py", 474): (
        "selfcheck: five single-bit rulings it pins",
        [dict(BUILT=True), dict(AMB=True), dict(UNREAD=True),
         dict(CAPPED=True), dict(REFUTED=True)]),
}
producible = {}          # act -> [(file, line)]
for (rel, ln), (desc, sits) in sorted(CALLSITES.items()):
    got = sorted({decide(situation(**s)) for s in sits})
    print(f"  {rel}:{ln}  {desc}")
    print(f"      source: {lines[rel][ln - 1].strip()[:96]}")
    print(f"      can return: {', '.join(got)}")
    for a in got:
        producible.setdefault(a, []).append(f"{rel}:{ln}")

# ---------------------------------------------------------------- part 2 --
# every textual occurrence of each act name in the body, split into
# comparisons (control flow) and string interpolation (wording).
print()
print("== 2. every occurrence of each act name in the body ==")
CMP = re.compile(r'==\s*["\'](%s)["\']')
occ = {a: {"cmp": [], "str": [], "comment": []} for a in ACTS}
for rel in BODY:
    for i, line in enumerate(lines[rel], 1):
        for a in ACTS:
            # avoid SHIPPED_KINDS / SHIPPED matching SHIP
            if not re.search(rf"\b{a}\b", line):
                continue
            if a == "SHIP" and re.search(r"\bSHIPPED", line):
                continue
            if CMP.sub("", line) != line and re.search(
                    rf'==\s*["\']{a}["\']', line):
                occ[a]["cmp"].append((rel, i, line.strip()))
            elif line.lstrip().startswith("#"):
                occ[a]["comment"].append((rel, i, line.strip()))
            else:
                occ[a]["str"].append((rel, i, line.strip()))

for a in ACTS:
    print(f"  --- {a}")
    for tag in ("cmp", "str", "comment"):
        for rel, i, s in occ[a][tag]:
            print(f"      [{tag:7}] {rel}:{i}  {s[:92]}")
    if not any(occ[a].values()):
        print("      (no occurrence anywhere in the body)")

# ---------------------------------------------------------------- part 3 --
print()
print("== 3. THE TABLE: act -> actuation status ==")
# Hand-classified from part 2; each row cites the line that justifies it.
TABLE = {
    "SHIP": ("BEHAVIOURAL",
             "loop.py:221 `if ruling == \"SHIP\"` gates _write(path,content) "
             "at loop.py:223 -- the only place a repair is committed"),
    "ADD_STATE": ("WORDING",
                  "never compared. loop.py:230 `if set_amb or len(sites)>1` is "
                  "the CODE re-testing the same facts it fed the law; the "
                  "ruling only fills the message at loop.py:237"),
    "ADD_MATERIAL": ("WORDING",
                     "guard.py:491 comparison gates ONLY `hint = ...` "
                     "(guard.py:492-496). No material is ever added"),
    "RESHAPE": ("NONE", "appears only in engine.py:38's ACTS list"),
    "CHANGE_GRANULARITY": ("WORDING",
                           "loop.py:391 computes it; loop.py:392 `ok = False` "
                           "is UNCONDITIONAL; the ruling only fills `why` at "
                           "loop.py:396. loop.py:307's SpanEdit comment claims "
                           "the act but consults no ruling"),
    "RAISE_BUDGET": ("BEHAVIOURAL",
                     "guard.py:539 `if escalate and decide(...)==\"RAISE_BUDGET\"` "
                     "gates the whole depth-first escalation pass "
                     "(guard.py:540-616). loop.py:242 is wording only"),
    "HARVEST_COUNTEREXAMPLE": ("WORDING",
                               "guard.py:612 and 618 gate ONLY `hint`. The "
                               "harvest itself (loop.py:407-410 tried_log) is "
                               "unconditional and never consults a ruling"),
    "AUTHOR_SUCCESSOR": ("NONE", "appears only in engine.py:39's ACTS list"),
}
print(f"  {'ACT':<23}{'STATUS':<14}{'PRODUCIBLE AT':<34}JUSTIFICATION")
for a in ACTS:
    st, why = TABLE[a]
    prod = ", ".join(producible.get(a, [])) or "-- no call site can return it --"
    print(f"  {a:<23}{st:<14}{prod[:32]:<34}{why}")

# ---------------------------------------------------------------- part 4 --
print()
print("== 4. cross-check: acts.py, named in engine.py's docstring as "
      "'the actuation table' ==")
acts_src = "\n".join(lines["fluidfix/acts.py"])
hits = [a for a in ACTS if re.search(rf"\b{a}\b", acts_src)
        and not (a == "SHIP" and not re.search(r"\bSHIP\b(?!PED)", acts_src))]
print(f"  engine ACTS names occurring in acts.py: {hits or 'NONE'}")
print(f"  acts.py defines its own ACTS dict of {len(__import__('fluidfix.acts', fromlist=['ACTS']).ACTS)} "
      f"kind->applier entries, keyed by ROUTER act codes 0..15 -- a different "
      f"namespace from the engine law's 8 process acts.")
print("  => acts.py actuates ZERO of the engine law's 8 acts.")
