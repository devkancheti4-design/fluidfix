#!/usr/bin/env python
"""What EMIT's 'lowest live bit' costs, measured on real source.

EMIT is exact: it returns the lowest live bit, always. The question this
script answers is what the BODY has encoded into that ruling. loop.py:297
tries fault classes in EMIT order, i.e. ascending kind id, i.e. the order
in which acts.KINDS happens to be numbered. Each class tried before the
true one is a candidate set, and every candidate in it is a suite run.

Measured here, read-only, over Box2D's sources and fluidfix's own:
  - for every signalled line, the mask and its EMIT drain order
  - for each kind, its mean 0-based position in that order
    (= how many other classes the loop tries first when this kind is right)
"""
import os
import sys

sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix.acts import KINDS  # noqa: E402
from fluidfix.lanes import ADVANCE, EMIT, HALT, kind_of, mask_of  # noqa: E402


def drain(m):
    out, w = [], m
    while not HALT(w):
        out.append(kind_of(EMIT(w)))
        w = ADVANCE(w)
    return out


def scan(root, exts, label):
    pos = {k: [] for k in KINDS}
    pops = []
    nf = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames
                       if d not in (".git", ".venv", "__pycache__", "build",
                                    "dist", "node_modules")]
        for fn in filenames:
            if not fn.endswith(exts):
                continue
            try:
                with open(os.path.join(dirpath, fn), "r", encoding="utf-8",
                          errors="replace") as fh:
                    src = fh.read()
            except OSError:
                continue
            nf += 1
            for line in src.split("\n"):
                line = line.rstrip("\r")
                ks = [k for k, (_, _, sig) in sorted(KINDS.items())
                      if sig.search(line)]
                if not ks:
                    continue
                order = drain(mask_of(ks))
                pops.append(len(order))
                for i, k in enumerate(order):
                    pos[k].append(i)
    n = len(pops)
    print(f"\n== {label}: {nf} files, {n} signalled lines")
    print(f"   mean classes live per signalled line (popcount): "
          f"{sum(pops) / max(n, 1):.2f}   max {max(pops) if pops else 0}")
    print(f"   {'kind':>4} {'name':<28} {'lines':>7} {'mean EMIT position':>19}"
          f" {'%lines preceded':>16} {'worst':>6}")
    for k in sorted(KINDS):
        v = pos[k]
        if not v:
            print(f"   {k:>4} {KINDS[k][0]:<28} {0:>7} "
                  f"{'never signalled':>19} {'-':>16} {'-':>6}")
            continue
        # 'preceded' = at least one other class is tried before this one on
        # that line, i.e. this kind's position in the drain order is > 0
        print(f"   {k:>4} {KINDS[k][0]:<28} {len(v):>7} "
              f"{sum(v) / len(v):>19.2f} "
              f"{100.0 * sum(1 for i in v if i > 0) / len(v):>15.1f}% "
              f"{max(v):>6}")
    return pos


here = "/Users/kanchetidevieswar/neo/fluidfix"
scan(os.path.join(here, "src"), (".py",), "fluidfix src/*.py")
box = ("/private/tmp/claude-501/-Users-kanchetidevieswar-neo/"
       "a9bf7d26-7aef-4c1e-a919-68bc40ac2e97/scratchpad/box2d")
if os.path.isdir(box):
    scan(box, (".c", ".h", ".cpp"), "Box2D (shared clone, READ-ONLY)")
else:
    print(f"\nBox2D clone not present at {box} -- unmeasured")

cglm = ("/private/tmp/claude-501/-Users-kanchetidevieswar-neo/"
        "a9bf7d26-7aef-4c1e-a919-68bc40ac2e97/scratchpad/cglm")
if os.path.isdir(cglm):
    scan(cglm, (".c", ".h"), "cglm (shared clone, READ-ONLY)")
else:
    print(f"\ncglm clone not present at {cglm} -- unmeasured")
