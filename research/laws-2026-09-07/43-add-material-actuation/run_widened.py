#!/usr/bin/env python
"""Run the widening prototype on a fixture and measure it against baseline.

Usage: python run_widened.py FIXTURE_DIR [budget_seconds]
"""
import os
import sys
import time

sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fluidfix.oracle import Oracle                  # noqa: E402
from fluidfix.observers import MechanicalObserver   # noqa: E402
from fluidfix.guard import guard_once, find_candidate_files  # noqa: E402
import widen as W                                   # noqa: E402

DEFECT = "shop/discount.py"

RUNS = []
_orig = Oracle.run


def counting(self, args, cache=False, timeout=None):
    RUNS.append(" ".join(args))
    return _orig(self, args, cache=cache, timeout=timeout)


Oracle.run = counting


def main(root, budget):
    o = Oracle(root, python=sys.executable)
    t0 = time.time()
    fails, out = o.failing_output()
    n_base_out = len(RUNS)
    ev = {}
    framed = find_candidate_files(o, out, limit=3, evidence=ev)
    n_framed = len(RUNS)

    order, rep = W.material(o, out, framed, limit=6)
    n_widen = len(RUNS)

    print("FRAMED (what the body searches today):", framed)
    print("assertion carriers                   :", rep["carriers"])
    print("UNREAD measured                      :", rep["UNREAD"])
    print("engine law ruling on UNREAD          :", rep["ruling"])
    print("widened set (SIGHT tier 2)           :", rep["widened"])
    print("sight evidence                       :", rep["sight_evidence"])
    print("search order handed to guard_once    :", order)
    print("defect file rank in widened set      :",
          (rep["widened"].index(DEFECT) + 1) if DEFECT in rep["widened"] else "ABSENT")
    print("suite runs: failing_output=%d framed=%d widening=%d"
          % (n_base_out, n_framed - n_base_out, n_widen - n_framed))

    rep2 = guard_once(o, MechanicalObserver(), files=order, budget=budget,
                      escalate_budget=budget)
    dt = time.time() - t0
    print("-" * 70)
    print("status     :", rep2.status)
    print("file       :", rep2.file)
    print("hint       :", rep2.hint)
    print("summary    :", rep2.summary())
    print("TOTAL SUITE RUNS:", len(RUNS))
    print("seconds    : %.2f" % dt)
    src = open(os.path.join(root, DEFECT)).read()
    print("defect still on disk (`qty > BULK_QTY`):", "qty > BULK_QTY" in src)
    helper = open(os.path.join(root, "shop/support/expect.py")).read()
    print("helper assertions intact (`assert got >= want` present):",
          "assert got >= want" in helper)


if __name__ == "__main__":
    main(os.path.abspath(sys.argv[1]),
         int(sys.argv[2]) if len(sys.argv) > 2 else 120)
