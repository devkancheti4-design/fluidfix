#!/usr/bin/env python
"""Mechanical census of hardcoded constants in the fluidfix BODY.

Body = the modules that MEASURE and ACTUATE (never decide): loop.py,
guard.py, acts.py, oracle.py, coracle.py, localize.py, observers.py,
hotspots.py, javaoracle.py, cli.py.  The six LAW modules (engine, rank,
sight, pair, router, lanes) are excluded -- their constants are the
authored kernel and are not the body's to own.

Emits, for every numeric literal and every hardcoded string tuple/set/list
that is compared against, the file, line, and source text.
"""
import ast
import os
import sys

SRC = "/Users/kanchetidevieswar/neo/fluidfix/src/fluidfix"
BODY = ["loop.py", "guard.py", "acts.py", "oracle.py", "coracle.py",
        "localize.py", "observers.py", "hotspots.py", "javaoracle.py",
        "cli.py"]
LAWS = ["engine.py", "rank.py", "sight.py", "pair.py", "router.py",
        "lanes.py"]


def scan(fn, mode):
    path = os.path.join(SRC, fn)
    src = open(path, encoding="utf-8").read()
    lines = src.split("\n")
    tree = ast.parse(src)
    nums, strs = [], []
    for node in ast.walk(tree):
        if mode in ("num", "all") and isinstance(node, ast.Constant) \
                and isinstance(node.value, (int, float)) \
                and not isinstance(node.value, bool):
            nums.append((node.lineno, node.value))
        if mode in ("str", "all") and isinstance(node, (ast.Tuple, ast.List,
                                                        ast.Set)):
            vals = [e.value for e in node.elts
                    if isinstance(e, ast.Constant) and isinstance(e.value, str)]
            if len(vals) >= 2 and len(vals) == len(node.elts):
                strs.append((node.lineno, vals))
    return lines, nums, strs


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "num"
    files = BODY if len(sys.argv) < 3 else [sys.argv[2]]
    for fn in files:
        lines, nums, strs = scan(fn, which)
        seen = set()
        for ln, val in sorted(nums):
            if (ln, val) in seen:
                continue
            seen.add((ln, val))
            print(f"{fn}:{ln}: {val!r:>12}  | {lines[ln-1].strip()[:100]}")
        for ln, vals in sorted(strs):
            print(f"{fn}:{ln}: NAMELIST({len(vals)}) {vals} "
                  f"| {lines[ln-1].strip()[:80]}")


if __name__ == "__main__":
    main()
