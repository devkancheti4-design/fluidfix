#!/usr/bin/env python
"""Does the gcov tier's own directory enter the candidate FILE set?

_c_sources(root, build_dir) skips only the FAST build dir. _Coverage's
instrumented tree is hardcoded to `covbuild` (coracle.py:333) and is not in
the skip set, so once the gcov tier has run, its contents are walked as
production source. Measured here on the Box2D copy.
"""
import os, sys
sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix.coracle import _c_sources
R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "box2d_copy")
s = _c_sources(R)
leak = {b: r for b, r in s.items() if r.startswith("covbuild/")}
print(f"total basenames in the candidate-file set : {len(s)}")
print(f"...resolved into covbuild/                : {len(leak)}")
tops = {}
for r in leak.values():
    tops[r.split("/")[1]] = tops.get(r.split("/")[1], 0) + 1
print(f"...by covbuild subdirectory               : {tops}")
print("sample leaked paths:")
for b, r in sorted(leak.items())[:8]:
    print(f"   {b:34s} -> {r}")
# basename shadowing: a real src/ file whose basename resolved to covbuild
real = set()
for dp, dn, fns in os.walk(os.path.join(R, "src")):
    for f in fns:
        if f.endswith((".c", ".h")):
            real.add(f)
shadow = sorted(b for b in leak if b in real)
print(f"real src/ basenames SHADOWED by a covbuild path: {len(shadow)} {shadow}")

# The recorded contact_solver.c shape: no frame, no name affinity -> the
# no-evidence fallback ranks by SIZE and takes the first 5.
print()
print("no-evidence fallback (coracle.py:560) = 5 biggest sources, "
      "as it is on a SECOND pass, once covbuild/ exists:")
def size(r): return os.path.getsize(os.path.join(R, r))
for r in sorted(set(s.values()), key=lambda r: (-size(r), r))[:5]:
    print(f"   {size(r):9d}  {r}")
clean = {b: r for b, r in s.items() if not r.startswith("covbuild/")}
print("the same fallback on a FIRST pass (no covbuild/ yet):")
for r in sorted(set(clean.values()), key=lambda r: (-size(r), r))[:5]:
    print(f"   {size(r):9d}  {r}")
