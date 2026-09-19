#!/usr/bin/env python3
"""Teach properties for the taught classes, then test them: controls first, then the gate.

No repository is checked out and no test suite runs. Everything here is algebra over the rewrite."""
from __future__ import annotations
import re, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))
from fluidfix.acts import load_dictionary
from fluidfix.props import PROPERTIES, check, gate, PROVEN, REFUTED, UNPROVEN

load_dictionary(str(ROOT / "examples/taught-2026-09-19/props.py"))


def capture(path):
    got, ns = {}, {"re": re, "register": lambda k, n, d, s, a: got.__setitem__(k, (n, s, a)),
                   "teach_property": lambda *a: None, "propcheck": None}
    sys.path.insert(0, str(ROOT / "src"))
    exec(compile(open(ROOT / path).read(), path, "exec"), ns)
    return got


# ============================================================ 1. controls: each property must REFUTE these
print("=" * 98)
print("1. CONTROLS — a property nothing can fail proves nothing. Each of these must be REFUTED.\n")
CONTROLS = [
    (7, "last = len(words)",      "last = len(words) + 1",        "adds one instead of subtracting"),
    (7, "n = k * len(words)",     "n = k * len(words) - 1",       "the rich incident, verbatim"),
    (4, "ok = a and b",           "ok = a or c",                  "flips the operator and an operand"),
    (6, "if value:",              "if value is None:",            "not the negation — both false at 0"),
    (5, 'v = cfg.get("name")',    'v = cfg.get("other", "")',     "reads a different key"),
]
bad_control = 0
for kind, o, c, why in CONTROLS:
    verdict, detail, n = check(kind, o, c)
    ok = verdict == REFUTED
    bad_control += not ok
    print(f"  class {kind}  {c:34} {verdict:9} {'ok' if ok else '<-- PROPERTY IS VACUOUS'}")
    print(f"           {why:34} {detail[:70]}")
print(f"\n  {len(CONTROLS) - bad_control}/{len(CONTROLS)} controls correctly refuted"
      f"{'' if not bad_control else '   <-- ' + str(bad_control) + ' PROPERTY IS TOO WEAK'}")

# ============================================================ 2. the gate on real candidates
LINES = {
    7: ["last = len(words)", "off = base + len(words)", "n = min(99, len(words))", "n = k * len(words)",
        "pos = int((cut / cell) * len(text))", "n = k - len(words)", "x = -len(words)",
        "n = 2 ** len(words)", "ok = len(words) > k", "n = abs(k - len(words))"],
    4: ["ok = a and b", "ok = a or b", "ok = a and b or c", "ok = a or b and c", "ok = a and b or c and d",
        "ok = a or b or c", "ok = a and b and c"],   # <- flattened chains: the UNPROVEN path
    6: ["if value:", "while items:", "elif flag:"],
    5: ['v = cfg.get("name")', 'v = opts.get("width")'],
}

for path, title in ((("examples/taught-2026-09-16/rules_session.py"), "the vocabulary AS TAUGHT (2026-09-16)"),
                    (("examples/taught-2026-09-19/corpus.py"), "the same vocabulary, class 7 ruled by the LAW")):
    got = capture(path)
    print("\n" + "=" * 98)
    print(f"2. THE GATE — {title}\n")
    tally = {PROVEN: 0, REFUTED: 0, UNPROVEN: 0}
    for kind in sorted(LINES):
        if kind not in got:
            continue
        name, signal, applier = got[kind]
        for line in LINES[kind]:
            if not signal.search(line):
                continue
            kept, refused = gate(kind, line, applier(line, None))
            for c, v, why, n in refused:
                tally[REFUTED] += 1
                print(f"  class {kind}  REFUSED   {c.strip():40} {why[:46]}")
            for c, v, why, n in kept:
                tally[v] += 1
                if v == UNPROVEN:
                    print(f"  class {kind}  unproven  {c.strip():40} {why[:46]}")
    print(f"\n  PROVEN {tally[PROVEN]}   REFUTED {tally[REFUTED]}   UNPROVEN {tally[UNPROVEN]}")
    print(f"  suite runs saved by refusing before the judge: {tally[REFUTED]}")
