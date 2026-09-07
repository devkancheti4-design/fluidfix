#!/usr/bin/env python
"""What the BODY sees today on the misdirection fixture.

Prints: the failing output, what find_candidate_files() returns at limit=3
and limit=999 (the escalation call), whether the defect file is in either,
and the number of Oracle.run() suite runs each cost.

Usage: python measure_candidates.py FIXTURE_DIR
"""
import os
import sys

sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")

from fluidfix.oracle import Oracle          # noqa: E402
from fluidfix import guard                  # noqa: E402

DEFECT = "shop/discount.py"
HELPER = "shop/support/expect.py"

RUNS = []
_orig_run = Oracle.run


def counting_run(self, args, cache=False, timeout=None):
    RUNS.append(list(args))
    return _orig_run(self, args, cache=cache, timeout=timeout)


Oracle.run = counting_run


def main(root):
    o = Oracle(root, python=sys.executable)
    fails, out = o.failing_output()
    print("suite fails:", fails)
    print("--- failing output (verbatim) " + "-" * 40)
    print(out)
    print("-" * 70)

    for limit in (3, 999):
        RUNS.clear()
        ev = {}
        c = guard.find_candidate_files(o, out, limit=limit, evidence=ev)
        print(f"find_candidate_files(limit={limit}) -> {c}")
        print(f"   evidence={ev}")
        print(f"   defect file {DEFECT!r} present: {DEFECT in c}")
        print(f"   suite runs consumed by this call: {len(RUNS)} {RUNS}")


if __name__ == "__main__":
    main(os.path.abspath(sys.argv[1]))
