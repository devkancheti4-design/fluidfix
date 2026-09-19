#!/usr/bin/env python3
"""Print the three accepted repairs, the suite's verdict, and the exhaustive verdict side by side."""
import json, sys, itertools
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "src"))
sys.path.insert(0, str(HERE.parent / "life-fluidfix-2026-09-18"))
from life_fluidfix import shapes_repair
sys.path.insert(0, str(HERE))
from gate import prop_insert_sorted

BUGS = HERE.parent / "model-bugs-2026-09-18"
DIC = str(HERE.parents[1] / "examples/taught-2026-09-16/rules_session.py")

for f in sorted(BUGS.glob("written_*.json")):
    d = json.load(open(f))
    if "haiku" in d["author"]: continue
    for r in d["rows"]:
        if r["passed"] or r["name"] != "insert_sorted": continue
        got = shapes_repair(r["code"], "\n".join(r["tests"]), DIC)
        if not got: continue
        before = r["code"].splitlines()
        after  = got["code"].splitlines()
        diff = [(b, a) for b, a in zip(before, after) if b != a]
        ok, why, n = prop_insert_sorted(__import__("types").FunctionType.__call__ and
                                        (lambda c: (exec(c, (ns := {})), ns["insert_sorted"])[1])(got["code"]))
        print(f"--- {d['author']}")
        for b, a in diff:
            print(f"      was  {b.strip()}")
            print(f"      now  {a.strip()}")
        print(f"      the suite : accepted  ({len(r['tests'])} test lines, all green)")
        print(f"      exhaustive: {'PASS over %d inputs' % n if ok else 'FAIL — ' + why}")
        print()

# ---- the control: does the property reject a KNOWN-GOOD implementation? It must not.
import bisect
def reference(items, v):
    items.insert(bisect.bisect_left(items, v), v); return items
ok, why, n = prop_insert_sorted(reference)
print(f"control, bisect reference : {'PASS over %d inputs' % n if ok else 'FAIL — ' + why}")
def always_empty(items, v): return []
ok, why, n = prop_insert_sorted(always_empty)
print(f"control, returns []       : {'PASS' if ok else 'FAIL — ' + why}  (must fail — a property that")
print(f"                             anything satisfies proves nothing)")
