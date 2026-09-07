#!/usr/bin/env python
"""Which mask values can the BODY actually hand EMIT/ADVANCE/HALT?

The only production call site is loop.py:283-298:

    mask = mask_of(k for k in obs.kinds if 0 <= k <= 15)
    while not HALT(mask):
        kind = kind_of(EMIT(mask)); mask = ADVANCE(mask)

so the reachable set is exactly the set of subsets of the observed kinds.
This script measures three things, read-only:

  (A) the lattice reachable from the SHIPPED dictionary (acts.KINDS)
  (B) the masks MechanicalObserver actually produces over real source
      (fluidfix's own src+tests, and the shared read-only Box2D clone)
  (C) how many of those masks lie outside the 0..255 window that
      lanes.py's docstring, tests/test_lanes.py and `fluidfix selfcheck`
      verify.

Nothing is written outside this directory; every file is opened read-only.
"""
import os
import sys
from itertools import combinations

sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix.acts import KINDS  # noqa: E402
from fluidfix.lanes import ADVANCE, EMIT, HALT, kind_of, mask_of  # noqa: E402

SHIPPED = sorted(KINDS)
print(f"shipped kind ids: {SHIPPED}")
print(f"reserved user-dictionary slots: 4..7 (acts.USER_KINDS)")

# ---- (A) the lattice reachable from the shipped dictionary --------------
full = mask_of(SHIPPED)
lattice = set()
for r in range(len(SHIPPED) + 1):
    for c in combinations(SHIPPED, r):
        lattice.add(mask_of(c))
print(f"\n(A) full shipped mask = {full} = {bin(full)}")
print(f"    reachable masks with the shipped dictionary: {len(lattice)} "
      f"of 65536 ({100.0 * len(lattice) / 65536:.2f}%)")
print(f"    of those, > 255 (outside the verified window): "
      f"{sum(1 for m in lattice if m > 255)}")
print(f"    with all 16 slots filled (user dictionary): 65536")

# ---- (B) what MechanicalObserver produces over real source -------------
def scan(root, exts, label, cap_files=4000):
    from fluidfix.observers import MechanicalObserver  # noqa: F401
    seen = {}
    nfiles = nlines = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames
                       if d not in (".git", ".venv", "__pycache__", "build",
                                    "dist", "node_modules")]
        for fn in filenames:
            if not fn.endswith(exts):
                continue
            if nfiles >= cap_files:
                break
            p = os.path.join(dirpath, fn)
            try:
                with open(p, "r", encoding="utf-8", errors="replace") as fh:
                    src = fh.read()
            except OSError:
                continue
            nfiles += 1
            for line in src.split("\n"):
                line = line.rstrip("\r")
                kinds = [k for k, (_, _, sig) in sorted(KINDS.items())
                         if sig.search(line)]
                if not kinds:
                    continue
                nlines += 1
                m = mask_of(k for k in kinds if 0 <= k <= 15)
                seen[m] = seen.get(m, 0) + 1
    tot = sum(seen.values())
    big = {m: c for m, c in seen.items() if m > 255}
    print(f"\n(B) {label}: {nfiles} files, {nlines} signalled lines")
    print(f"    distinct masks produced: {len(seen)}")
    print(f"    masks > 255 (outside the verified 0..255 window): "
          f"{len(big)} distinct, {sum(big.values())} of {tot} signalled "
          f"lines ({100.0 * sum(big.values()) / max(tot, 1):.1f}%)")
    top = sorted(seen.items(), key=lambda kv: -kv[1])[:12]
    print(f"    most common masks (mask, bin, count, kinds, EMIT-order):")
    for m, c in top:
        order, w = [], m
        while not HALT(w):
            order.append(kind_of(EMIT(w)))
            w = ADVANCE(w)
        print(f"      {m:6d} {bin(m):>18} n={c:<7d} kinds={order}"
              f"{'   <== >255' if m > 255 else ''}")
    return seen


here = "/Users/kanchetidevieswar/neo/fluidfix"
scan(os.path.join(here, "src"), (".py",), "fluidfix src/*.py")
scan(os.path.join(here, "tests"), (".py",), "fluidfix tests/*.py")
box = ("/private/tmp/claude-501/-Users-kanchetidevieswar-neo/"
       "a9bf7d26-7aef-4c1e-a919-68bc40ac2e97/scratchpad/box2d")
if os.path.isdir(box):
    scan(box, (".c", ".h", ".cpp"), "Box2D (shared clone, READ-ONLY)")
else:
    print(f"\n(B) Box2D clone not present at {box} -- unmeasured")

# ---- (C) ordering: what EMIT does to the observer's ordering ------------
print("\n(C) the observer reports kinds 'most specific first' "
      "(acts.Observation, observers.observer_prompt step 2).")
for kinds in ([3, 1], [1, 3], [12, 0], [0, 12], [10, 0, 3]):
    m = mask_of(kinds)
    order, w = [], m
    while not HALT(w):
        order.append(kind_of(EMIT(w)))
        w = ADVANCE(w)
    print(f"    observer said {str(kinds):>12} -> mask {m:5d} -> "
          f"loop tries {order}")
print("    mask_of is a SET union and EMIT is 'lowest live bit', so the "
      "observer's ordering is not representable in the value the body\n"
      "    hands the law. guard.py:402 uses obs.kinds[:2] (observer order) "
      "for the CHEAP bit; loop.py:297 uses ascending kind id.")
