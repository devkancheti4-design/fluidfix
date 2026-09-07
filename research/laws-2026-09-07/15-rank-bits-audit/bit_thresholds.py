#!/usr/bin/env python
"""Measure the body's DENSE and RECENT measurements on real files, using the
body's own functions (guard._shape, guard._recent_lines) — no src edits.

  nice -n 15 timeout 300 /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python bit_thresholds.py

DENSE  : fraction of non-blank lines whose shape recurs >= 8 times in the
         file (the body's threshold), over fluidfix's own src and tests.
RECENT : fraction of lines git-blamed to the last 40 commits (the body's
         depth) on the shared Box2D / cglm clones. Read-only git.
"""
from __future__ import annotations

import collections
import glob
import os
import sys

sys.dont_write_bytecode = True
import fluidfix.guard as G  # noqa: E402

FF = "/Users/kanchetidevieswar/neo/fluidfix"
SCRATCH = ("/private/tmp/claude-501/-Users-kanchetidevieswar-neo/"
           "a9bf7d26-7aef-4c1e-a919-68bc40ac2e97/scratchpad")

print("== DENSE (shape count >= 8) over fluidfix src + tests")
tot = dense = 0
top = collections.Counter()
for path in sorted(glob.glob(f"{FF}/src/fluidfix/*.py") + glob.glob(f"{FF}/tests/*.py")):
    lines = open(path).read().split("\n")
    shapes = collections.Counter(G._shape(l) for l in lines if l.strip())
    n = sum(1 for l in lines if l.strip())
    d = sum(1 for l in lines if l.strip() and shapes[G._shape(l)] >= 8)
    tot += n
    dense += d
    for s, c in shapes.items():
        if c >= 8:
            top[s] += c
    print(f"  {os.path.relpath(path, FF):40s} dense {d:4d}/{n:4d} = {d / n:5.1%}")
print(f"  TOTAL dense {dense}/{tot} = {dense / tot:.1%}")
print("  most common DENSE shapes:")
for s, c in top.most_common(12):
    print(f"    {c:5d}  {s!r}")

print("\n== RECENT (blamed to last 40 commits) on the shared clones, body's _recent_lines")
for repo, files in (("box2d", ["src/contact_solver.c", "src/body.c", "src/math_functions.c",
                               "src/shape.c"]),
                    ("cglm", ["include/cglm/vec3.h", "include/cglm/mat4.h",
                              "include/cglm/frustum.h", "include/cglm/euler.h"])):
    root = f"{SCRATCH}/{repo}"
    for rel in files:
        p = os.path.join(root, rel)
        if not os.path.exists(p):
            print(f"  {repo}/{rel}: (missing)")
            continue
        n = len(open(p, errors="replace").read().split("\n"))
        hit = G._recent_lines(root, rel)
        print(f"  {repo:6s} {rel:32s} recent {len(hit):5d}/{n:5d} = {len(hit) / n:5.1%}")
