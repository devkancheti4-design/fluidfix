#!/usr/bin/env python3
"""Check every taught class against its property, exhaustively, on lines that vary the SYNTACTIC POSITION
of the fault — the axis the 2026-09-16 measurements never varied.

No test suite runs. No repository is checked out. The property is algebra over the rewrite."""
from __future__ import annotations
import re, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "src"))
sys.path.insert(0, str(HERE))
from classprop import PROPS

ROOT = HERE.parents[1]


def load(path):
    """exec a dictionary file with a capturing register — no global slots touched, no clobber warnings."""
    got = {}
    ns = {"re": re, "register": lambda k, n, d, s, a: got.__setitem__(k, (n, s, a))}
    sys.path.insert(0, str(ROOT / "src"))
    exec(compile(open(ROOT / path).read(), str(path), "exec"), ns)
    return got


LINES = {
    7: ["last = len(words)",                          # <- the one shape it was taught on
        "off = base + len(words)",
        "n = min(99, len(words))",
        "n = k * len(words)",
        "pos = int((cut / cell) * len(text))",        # <- the line that shipped wrong into rich
        "n = len(words) // 2",
        "n = 2 ** len(words)",
        "n = len(words) % m",
        "ok = len(words) > k",
        "n = (len(words) + k) * 2",
        "n = k - len(words)",
        "x = -len(words)",
        "n = j - len(a) + len(b)",
        "n = len(words) - k",
        "n = (k - len(words)) * 2",
        "n = abs(k - len(words))"],
    4: ["ok = a and b", "ok = a or b", "ok = a and b or c", "ok = a or b and c",
        "ok = a and b or c and d", "ok = a or b or c", "ok = a and b and c"],
    6: ["if value:", "while items:", "elif flag:"],
    5: ['v = cfg.get("name")', 'v = opts.get("width")'],
}


def run(dictpath, kinds, title):
    got = load(dictpath)
    print(f"\n=== {title}")
    print(f"    {dictpath}\n")
    tot = bad = skip = 0
    for kind in kinds:
        if kind not in got or kind not in PROPS:
            continue
        name, signal, applier = got[kind]
        pname, checker = PROPS[kind]
        print(f"  class {kind}  {name}")
        print(f"     property: {pname}")
        for line in LINES.get(kind, []):
            if not signal.search(line):
                print(f"       {line:42}  (signal does not match — not this class's business)")
                continue
            for cand in applier(line, None):
                if cand == line:
                    continue
                ok, why, n = checker(line, cand)
                tot += 1
                if ok is None:
                    skip += 1; mark = f"skipped — {why}"
                elif ok:
                    mark = f"HOLDS over {n} inputs"
                else:
                    bad += 1; mark = f"VIOLATED — {why}"
                print(f"       {cand.strip():42}  {mark}")
        print()
    return tot, bad, skip


a = run("examples/taught-2026-09-16/rules_session.py", [4, 5, 6, 7],
        "the vocabulary as it was taught on 2026-09-16")
b = run("examples/taught-2026-09-19/rules_placed.py", [7],
        "class 7 re-authored so the PLACEMENT LAW decides")

print("=" * 96)
print(f"as taught      : {a[0]} candidates checked, {a[1]} violate their class property, {a[2]} not applicable")
print(f"with the law   : {b[0]} candidates checked, {b[1]} violate their class property, {b[2]} not applicable")
