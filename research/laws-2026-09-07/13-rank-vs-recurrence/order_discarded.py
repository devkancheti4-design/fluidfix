#!/usr/bin/env python
"""Why class order cannot matter: loop.repair converts obs.kinds to a BITMASK.

    loop.py:283   mask = mask_of(k for k in obs.kinds if 0 <= k <= 15)
    lanes.py:35   mask_of ORs 1<<k          -- a SET; order is gone
    loop.py:297   kind = kind_of(EMIT(mask)) -- EMIT = lowest live bit

So every permutation of obs.kinds runs the same kinds in ASCENDING KIND ID
order. acts.Observation documents `kinds` as "most specific first"
(acts.py:60); the search never reads that order.

Part 1  all 720 permutations of a 6-kind line -> is acts_tried identical?
Part 2  the deadline case from order_effect.py, repeated, to show the
        winner-first/winner-last difference there is wall-clock jitter and
        not an order effect.

Usage: .venv/bin/python order_discarded.py
"""
import itertools
import os
import shutil
import sys
import tempfile
import time

sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
os.environ.setdefault("FLUIDFIX_CONFIRM", "0")

from fluidfix import Oracle, Observation, repair          # noqa: E402
from fluidfix.acts import KINDS                            # noqa: E402
from fluidfix.lanes import mask_of                         # noqa: E402

PY = "/Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python"
HERE = os.path.dirname(os.path.abspath(__file__))

MOD = "def g(a, b):\n    return a - b if a >= 0 else 1\n"
TEST = ("from mod import g\ndef test():\n    assert g(2, 3) == 5\n"
        "    assert g(-1, 3) == 1\n")
LINE = "    return a - b if a >= 0 else 1"
KS = [k for k, (_, _, sig) in sorted(KINDS.items()) if sig.search(LINE)]


def run(order, deadline_after=None):
    d = tempfile.mkdtemp(dir=HERE, prefix="od_")
    try:
        open(os.path.join(d, "mod.py"), "w").write(MOD)
        open(os.path.join(d, "test_mod.py"), "w").write(TEST)
        oracle = Oracle(d, python=PY)
        dl = (time.time() + deadline_after) if deadline_after else None
        res = repair(oracle, "mod.py",
                     [Observation(lineno=2, kinds=list(order))], deadline=dl)
        return res
    finally:
        shutil.rmtree(d, ignore_errors=True)


def main():
    print("kinds on the line:", [(k, KINDS[k][0]) for k in KS])

    # ---- Part 0: the bitmask itself, no suite runs at all ------------------
    masks = {mask_of(p) for p in itertools.permutations(KS)}
    print(f"\nPart 0  mask_of over all {len(list(itertools.permutations(KS)))} "
          f"permutations of {KS}: {len(masks)} distinct mask(s) -> {masks}")
    print("        (one mask => the order in obs.kinds is not representable)")

    # ---- Part 1: a sample of permutations, end to end ----------------------
    perms = list(itertools.permutations(KS))
    sample = [perms[0], perms[len(perms) // 3], perms[2 * len(perms) // 3],
              perms[-1], tuple(reversed(KS))]
    print(f"\nPart 1  acts_tried per permutation (of {len(perms)} possible, "
          f"{len(sample)} run end to end)")
    seen = set()
    for p in sample:
        r = run(p)
        key = (tuple(r.acts_tried), r.suite_runs, r.repaired, r.new_line)
        seen.add(key)
        print(f"   kinds={list(p)} -> acts_tried={list(r.acts_tried)} "
              f"suite_runs={r.suite_runs} repaired={r.repaired}")
    print(f"   distinct (acts_tried, suite_runs, repaired, new_line) "
          f"outcomes: {len(seen)}")

    # ---- Part 2: the deadline case, repeated ------------------------------
    win = 3                                   # flipped-additive, verified above
    first = [win] + [k for k in KS if k != win]
    last = [k for k in KS if k != win] + [win]
    full = run(KS)
    cut = round(full.seconds * 0.45, 2)
    print(f"\nPart 2  deadline={cut}s (full search {round(full.seconds,2)}s), "
          f"5 repeats per order")
    for label, order in (("winner FIRST", first), ("winner LAST ", last)):
        outs = []
        for _ in range(5):
            r = run(order, deadline_after=cut)
            outs.append((r.repaired, r.suite_runs))
        print(f"   {label} order={order}")
        print(f"      (repaired, suite_runs) x5 = {outs}")


if __name__ == "__main__":
    main()
