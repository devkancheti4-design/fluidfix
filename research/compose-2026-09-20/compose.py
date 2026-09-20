#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Two taught classes were never taught together. Does the net connect them?

Every class in the vocabulary was taught from its own worked example, in isolation. Nothing has ever
handed it a bug that needs TWO of them at once. Three shapes of that question:

    A  two faults, two classes, two lines   the ordinary case: a commit that broke two things
    B  two faults, two classes, ONE line    composition proper
    C  one fault, for control               must still repair, or the harness is broken
"""
from __future__ import annotations
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "research/life-fluidfix-2026-09-18"))
from life_fluidfix import shapes_repair

DICT = str(ROOT / "examples/taught-2026-09-19/corpus.py")

CASES = []

# ---- C: control, ONE fault (class 7). Must repair.
CASES.append(("C  one fault, class 7 alone", '''
def last_word(words):
    i = len(words)
    return words[i]
''', '''
assert last_word(["a", "b", "c"]) == "c"
assert last_word(["x"]) == "x"
'''))

# ---- C2: control, ONE fault (class 4). Must repair.
CASES.append(("C2 one fault, class 4 alone", '''
def label(item, fallback):
    return item and fallback
''', '''
assert label("", "-") == "-"
assert label("hi", "-") == "hi"
'''))

# ---- A: TWO faults, TWO classes, TWO lines.
CASES.append(("A  two faults, classes 7 + 4, two lines", '''
def last_word(words):
    i = len(words)
    return words[i]

def label(item, fallback):
    return item and fallback
''', '''
assert last_word(["a", "b", "c"]) == "c"
assert label("", "-") == "-"
assert label("hi", "-") == "hi"
'''))

# ---- B: TWO faults, TWO classes, ONE line.
CASES.append(("B  two faults, classes 7 + 4, ONE line", '''
def tail_or(words, fallback):
    return words[len(words)] and fallback
''', '''
assert tail_or(["a", "b", ""], "-") == "-"
assert tail_or(["a", "b", "z"], "-") == "-"
'''))

print(f"{'case':44} {'repaired':>9}  {'runs':>5}  what it did")
print("-" * 104)
for name, code, test in CASES:
    got = shapes_repair(code, test, DICT)
    if got:
        print(f"{name:44} {'YES':>9}  {got['tests_run']:>5}  kind {got['kind']}: "
              f"{got['before']}  ->  {got['after']}")
    else:
        print(f"{name:44} {'no':>9}  {'':>5}  refused — no single line edit turns the suite green")
