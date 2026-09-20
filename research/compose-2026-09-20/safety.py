#!/usr/bin/env python3
"""Descent relaxes the intermediate gate, so it must not relax what gets ACCEPTED.

The adversarial case is the rich incident reproduced inside a composition: a multi-fault bug where one
fault sits at a multiplicative position, and the suite is WEAK there — it only ever exercises k = 1, where
`k * len(x) - 1` and `k * (len(x) - 1)` agree. A suite like that accepts the wrong placement. rich's did.

Three arms, same bug, same tests."""
import os, sys
from pathlib import Path
R = Path.cwd()
sys.path.insert(0, str(R / "src")); sys.path.insert(0, str(R / "research/life-fluidfix-2026-09-18"))
sys.path.insert(0, str(R / "research/compose-2026-09-20"))
from life_fluidfix import load_dictionary, KINDS, ACTS
from descend import descend

CODE = ("def scale_last(items, k):\n    return k * len(items)\n\n"
        "def label(item, fallback):\n    return item and fallback\n")
TESTS = ['assert scale_last([1,2,3], 1) == 2',          # k = 1: the blind spot
         'assert label("", "-") == "-"',
         'assert label("hi", "-") == "hi"']
TRUTH = 'assert scale_last([1,2,3], 2) == 4'            # k = 2: what the weak suite never asks

def arm(tag, dictionary, use_property):
    for k in list(KINDS): KINDS.pop(k, None)
    for a in list(ACTS): ACTS.pop(a, None)
    import importlib, fluidfix.acts as A; importlib.reload(A)
    from life_fluidfix import load_dictionary as ld
    ld(str(R / dictionary))
    r = descend(CODE, TESTS, use_property=use_property, depth=2)
    if not r or r.get("refused"):
        print(f"{tag:46} refused            {r['blocked_by_property'] if r else 0} blocked by property")
        return
    ns = {}
    exec(r["code"], ns)
    try:
        exec(TRUTH, ns); verdict = "and it is CORRECT"
    except AssertionError:
        verdict = "but it is WRONG  <-- scale_last([1,2,3],2) != 4"
    fix = next((s["after"] for s in r["steps"] if s["kind"] == 7), "?")
    print(f"{tag:46} green, {verdict}")
    print(f"{'':46}   {fix}    ({r['blocked_by_property']} blocked by property)")

arm("naive class 7, property gate OFF", "examples/taught-2026-09-16/rules_session.py", False)
arm("naive class 7, property gate ON", "examples/taught-2026-09-16/rules_session.py", True)
arm("placement law, property gate ON", "examples/taught-2026-09-19/corpus.py", True)
