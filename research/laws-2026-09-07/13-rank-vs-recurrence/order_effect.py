#!/usr/bin/env python
"""13-rank-vs-recurrence, decisive measurement.

The history replay (scan_history.py / dedupe.py) counts the POSITION of the
maintainer's fix in the candidate stream under different class orders. That
number only becomes a saving if the loop STOPS at the first green. It does
not: loop.repair exhausts each candidate set and then walks to the next kind,
because "a lone green with the set unfinished is an UNPROVEN-unique repair"
(loop.py:287-290).

So this script measures the thing the replay cannot: does changing the class
order change the number of SUITE RUNS a completed repair costs?

  A  winner-first vs winner-last, no deadline        -> suite_runs, repaired
  B  same, with a wall-clock deadline that expires   -> repaired / reason

Two fixtures. Runs a 1-test pytest suite a few dozen times; builds nothing.
Usage: .venv/bin/python order_effect.py
"""
import os
import shutil
import sys
import tempfile
import time

sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
os.environ.setdefault("FLUIDFIX_CONFIRM", "0")   # count candidates, not re-checks

from fluidfix import Oracle, Observation, repair          # noqa: E402
from fluidfix.acts import KINDS                            # noqa: E402
from fluidfix.lanes import ADVANCE, EMIT, HALT, kind_of, mask_of  # noqa: E402

PY = "/Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python"
HERE = os.path.dirname(os.path.abspath(__file__))


def loop_order():
    mask, out = mask_of(k for k in KINDS if 0 <= k <= 15), []
    while not HALT(mask):
        out.append(kind_of(EMIT(mask)))
        mask = ADVANCE(mask)
    return out


def observed_kinds(line):
    return [k for k, (_, _, sig) in sorted(KINDS.items()) if sig.search(line)]


FIXTURES = {
    # `>=` should be `>`. kinds 0 (strictness) and 10 (flipped-comparison).
    "cmp": dict(
        mod="def f(x, t):\n    if x >= t:\n        return 1\n    return 0\n",
        test="from mod import f\ndef test():\n    assert f(5, 5) == 0\n"
             "    assert f(6, 5) == 1\n",
        lineno=2,
    ),
    # `a - b` should be `a + b` on a line that also carries a comparison and a
    # literal, so several kinds fire and the winner (3, flipped-additive) is
    # NOT the lowest kind id.
    "add": dict(
        mod="def g(a, b):\n    return a - b if a >= 0 else 1\n",
        test="from mod import g\ndef test():\n    assert g(2, 3) == 5\n"
             "    assert g(-1, 3) == 1\n",
        lineno=2,
    ),
}


def run(fx, order, deadline_after=None):
    """One repair() on a fresh copy of the fixture with `order` as the kind
    order. deadline_after: seconds from now, or None."""
    d = tempfile.mkdtemp(dir=HERE, prefix="oe_")
    try:
        open(os.path.join(d, "mod.py"), "w").write(fx["mod"])
        open(os.path.join(d, "test_mod.py"), "w").write(fx["test"])
        oracle = Oracle(d, python=PY)
        obs = [Observation(lineno=fx["lineno"], kinds=list(order))]
        dl = (time.time() + deadline_after) if deadline_after else None
        res = repair(oracle, "mod.py", obs, deadline=dl)
        return dict(repaired=res.repaired, suite_runs=res.suite_runs,
                    acts=list(res.acts_tried), new_line=res.new_line,
                    reason=(res.reason or "")[:110], seconds=round(res.seconds, 2))
    finally:
        shutil.rmtree(d, ignore_errors=True)


def main():
    print("loop kind order (lanes.EMIT over KINDS):",
          [(k, KINDS[k][0]) for k in loop_order()])
    for name, fx in FIXTURES.items():
        line = fx["mod"].split("\n")[fx["lineno"] - 1]
        ks = observed_kinds(line)
        print(f"\n================ fixture {name!r}: {line.strip()!r}")
        print("  kinds on the line:", [(k, KINDS[k][0]) for k in ks])
        if len(ks) < 2:
            print("  only one kind fires; order cannot matter here")
            continue

        # --- A: no deadline. Winner-first vs winner-last vs loop order. -----
        base = run(fx, ks)
        winner = None
        # identify the winning kind by running each kind alone
        for k in ks:
            r1 = run(fx, [k])
            if r1["repaired"]:
                winner = k
                print(f"  kind {k} ({KINDS[k][0]}) alone: repaired="
                      f"{r1['repaired']} runs={r1['suite_runs']} "
                      f"new_line={r1['new_line']!r}")
        first = [winner] + [k for k in ks if k != winner]
        last = [k for k in ks if k != winner] + [winner]
        print("  --- A: no deadline ---")
        for label, order in (("loop order   ", ks), ("winner FIRST ", first),
                             ("winner LAST  ", last), ("reversed     ",
                                                       list(reversed(ks)))):
            r = run(fx, order)
            print(f"   {label} order={order} repaired={r['repaired']} "
                  f"suite_runs={r['suite_runs']} acts={r['acts']} "
                  f"new_line={r['new_line']!r}")

        # --- B: a deadline that expires after roughly one candidate set -----
        # base["seconds"] is the cost of the WHOLE search; cut it to a
        # fraction so the loop stops between kinds.
        cut = round(base["seconds"] * 0.45, 2)
        print(f"  --- B: deadline = {cut}s "
              f"(full search took {base['seconds']}s) ---")
        for label, order in (("winner FIRST ", first), ("winner LAST  ", last)):
            r = run(fx, order, deadline_after=cut)
            print(f"   {label} order={order} repaired={r['repaired']} "
                  f"suite_runs={r['suite_runs']} reason={r['reason']!r}")


if __name__ == "__main__":
    main()
