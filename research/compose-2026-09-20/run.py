#!/usr/bin/env python3
"""The same four cases, now by descent instead of one-shot."""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1] / "src"))
sys.path.insert(0, str(HERE.parents[1] / "research/life-fluidfix-2026-09-18"))
from life_fluidfix import load_dictionary
from descend import descend, DICT
load_dictionary(DICT)

CASES = [
 ("C  one fault, class 7 alone",
  "def last_word(words):\n    i = len(words)\n    return words[i]\n",
  ['assert last_word(["a","b","c"]) == "c"', 'assert last_word(["x"]) == "x"']),
 ("C2 one fault, class 4 alone",
  "def label(item, fallback):\n    return item and fallback\n",
  ['assert label("", "-") == "-"', 'assert label("hi", "-") == "hi"']),
 ("A  two faults, classes 7 + 4, two lines",
  "def last_word(words):\n    i = len(words)\n    return words[i]\n\n"
  "def label(item, fallback):\n    return item and fallback\n",
  ['assert last_word(["a","b","c"]) == "c"', 'assert label("", "-") == "-"',
   'assert label("hi", "-") == "hi"']),
 ("B  two faults, classes 7 + 4, ONE line",
  "def tail_or(words, fallback):\n    return words[len(words)] and fallback\n",
  ['assert tail_or(["a","b",""], "-") == "-"', 'assert tail_or(["a","b","z"], "-") == "z"']),
 ("D  THREE faults, classes 7 + 4 + 6, three lines",
  "def last_word(words):\n    i = len(words)\n    return words[i]\n\n"
  "def label(item, fallback):\n    return item and fallback\n\n"
  "def guard(value):\n    if value:\n        return 'empty'\n    return 'full'\n",
  ['assert last_word(["a","b","c"]) == "c"', 'assert label("", "-") == "-"',
   'assert label("hi", "-") == "hi"', 'assert guard([]) == "empty"', 'assert guard([1]) == "full"']),
]

DEPTH = int(__import__("os").environ.get("DEPTH", "1"))
print(f"--- per-line composition depth {DEPTH}\n")
for name, code, tests in CASES:
    r = descend(code, tests, depth=DEPTH)
    if r is None:
        print(f"{name:46} NOT RED"); continue
    ok = not r.get("refused")
    print(f"{name:46} {'REPAIRED' if ok else 'refused':>9}  "
          f"{r['runs']:>3} runs  {r['blocked_by_property']:>2} blocked by property")
    for s in r["steps"]:
        print(f"{'':46}   kind {s['kind']}  {s['before']}  ->  {s['after']}   failing {s['failing']}")
    print()
