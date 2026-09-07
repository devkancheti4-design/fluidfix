#!/usr/bin/env python
"""Does class order change the suite-run COUNT of a completed search?
Fixture: `if x >= t:` where `if x > t:` is intended. Two shipped kinds match
the line: 0 strictness (candidate `x > t`, the fix) and 10 flipped-comparison
(candidate `x <= t`). If the loop stopped at the first green, kind order
would decide 2 vs 3 runs; if it is exhaustive, the count is order-free.
Runs a 1-test pytest suite a handful of times. Builds nothing."""
import os, shutil, sys, tempfile
sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix import Oracle, Observation, repair
from fluidfix.acts import KINDS
os.environ.setdefault("FLUIDFIX_CONFIRM", "0")      # no re-check runs: count candidates only
PY = "/Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python"
d = tempfile.mkdtemp(dir=os.path.dirname(os.path.abspath(__file__)), prefix="fx_")
try:
    open(os.path.join(d, "mod.py"), "w").write("def f(x, t):\n    if x >= t:\n        return 1\n    return 0\n")
    open(os.path.join(d, "test_mod.py"), "w").write("from mod import f\ndef test():\n    assert f(5, 5) == 0\n    assert f(6, 5) == 1\n")
    oracle = Oracle(d, python=PY)
    line = "    if x >= t:"
    kinds = [k for k, (_, _, sig) in sorted(KINDS.items()) if sig.search(line)]
    print("kinds on the defect line (MechanicalObserver order):", [(k, KINDS[k][0]) for k in kinds])
    for order in (kinds, list(reversed(kinds))):
        res = repair(oracle, "mod.py", [Observation(lineno=2, kinds=order)])
        print(f"kinds given as {order}: repaired={res.repaired} suite_runs={res.suite_runs} "
              f"acts_tried={res.acts_tried} tried_log={[t['tried'].strip() for t in res.tried_log]} "
              f"greens={res.greens} new_line={res.new_line!r}")
        # restore the defect for the second pass
        open(os.path.join(d, "mod.py"), "w").write("def f(x, t):\n    if x >= t:\n        return 1\n    return 0\n")
finally:
    shutil.rmtree(d, ignore_errors=True)
