#!/usr/bin/env python3
"""One arm of the safety test, in its own process so the class registry is clean.
   usage: arm.py <dictionary> <on|off>"""
import sys
from pathlib import Path
R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / "src")); sys.path.insert(0, str(R / "research/life-fluidfix-2026-09-18"))
sys.path.insert(0, str(R / "research/compose-2026-09-20"))
from life_fluidfix import load_dictionary
from descend import descend

CODE = ("def scale_last(items, k):\n    return k * len(items)\n\n"
        "def label(item, fallback):\n    return item and fallback\n")
TESTS = ['assert scale_last([1,2,3], 1) == 2',
         'assert label("", "-") == "-"',
         'assert label("hi", "-") == "hi"']
TRUTH = 'assert scale_last([1,2,3], 2) == 4'

load_dictionary(str(R / sys.argv[1]))
if sys.argv[2] == "on":
    load_dictionary(str(R / "examples/taught-2026-09-19/props.py"))   # <- the properties are a SEPARATE file
from fluidfix.props import PROPERTIES
print(f"   properties loaded: {sorted(PROPERTIES)}", file=sys.stderr)
r = descend(CODE, TESTS, use_property=(sys.argv[2] == "on"), depth=2)
if not r or r.get("refused"):
    print(f"refused | {r['blocked_by_property'] if r else 0} blocked | steps={len(r['steps']) if r else 0}")
else:
    ns = {}; exec(r["code"], ns)
    try:
        exec(TRUTH, ns); v = "CORRECT"
    except AssertionError:
        v = "WRONG"
    fix = next((s["after"] for s in r["steps"] if s["kind"] == 7), "(class 7 never fired)")
    print(f"green -> {v} | {r['blocked_by_property']} blocked | {fix}")
