#!/usr/bin/env python
"""BASELINE: run the real guard_once() on the misdirection fixture.
Counts every Oracle.run() (= suite run) and prints the report + hint.

Usage: python run_baseline.py FIXTURE_DIR [budget_seconds]
"""
import os
import sys
import time

sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")

from fluidfix.oracle import Oracle              # noqa: E402
from fluidfix.observers import MechanicalObserver  # noqa: E402
from fluidfix.guard import guard_once           # noqa: E402

RUNS = []
_orig = Oracle.run


def counting(self, args, cache=False, timeout=None):
    RUNS.append(" ".join(args))
    return _orig(self, args, cache=cache, timeout=timeout)


Oracle.run = counting


def main(root, budget):
    o = Oracle(root, python=sys.executable)
    t0 = time.time()
    rep = guard_once(o, MechanicalObserver(), budget=budget,
                     escalate_budget=budget)
    dt = time.time() - t0
    print("status      :", rep.status)
    print("file        :", rep.file)
    print("candidates  :", rep.candidates)
    print("evidence    :", rep.evidence)
    print("hint        :", rep.hint)
    print("summary     :", rep.summary())
    print("attempts    :", len(rep.attempts))
    print("SUITE RUNS  :", len(RUNS))
    print("seconds     : %.2f" % dt)
    for i, r in enumerate(RUNS, 1):
        print("   run %2d: pytest %s" % (i, r))
    # was the defect actually fixed?
    src = open(os.path.join(root, "shop/discount.py")).read()
    print("discount.py still has the defect (`qty > BULK_QTY`):",
          "qty > BULK_QTY" in src)


if __name__ == "__main__":
    main(os.path.abspath(sys.argv[1]),
         int(sys.argv[2]) if len(sys.argv) > 2 else 120)
