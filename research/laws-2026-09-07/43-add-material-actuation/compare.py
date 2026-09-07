#!/usr/bin/env python
"""Baseline vs ADD_MATERIAL-widened, on one fixture, on fresh copies.

Usage: python compare.py SRC_FIXTURE DEFECT_REL LABEL [budget]
Prints one block per arm: candidate set, defect-file rank, status, suite runs,
and whether the file that was EDITED is the defect file.
"""
import os
import shutil
import sys
import time

sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fluidfix.oracle import Oracle                  # noqa: E402
from fluidfix.observers import MechanicalObserver   # noqa: E402
from fluidfix.guard import guard_once, find_candidate_files  # noqa: E402
import widen as W                                   # noqa: E402

RUNS = []
_orig = Oracle.run


def counting(self, args, cache=False, timeout=None):
    RUNS.append(" ".join(args))
    return _orig(self, args, cache=cache, timeout=timeout)


Oracle.run = counting


def fresh(src, suffix):
    dst = src + suffix
    if os.path.isdir(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    return dst


def arm(root, widened, defect, budget):
    RUNS.clear()
    o = Oracle(root, python=sys.executable)
    t0 = time.time()
    files = None
    info = {}
    if widened:
        _f, out = o.failing_output()
        framed = find_candidate_files(o, out, limit=3)
        files, info = W.material(o, out, framed, limit=6)
    rep = guard_once(o, MechanicalObserver(), files=files, budget=budget,
                     escalate_budget=budget)
    dt = time.time() - t0
    searched = files or rep.candidates
    return {
        "arm": "WIDENED" if widened else "baseline",
        "searched": searched,
        "defect_rank": (searched.index(defect) + 1) if defect in searched else None,
        "status": rep.status,
        "edited": rep.file if rep.status == "repaired" else None,
        "correct_file": (rep.file == defect) if rep.status == "repaired" else None,
        "hint": (rep.hint or rep.summary())[:200],
        "runs": len(RUNS),
        "secs": round(dt, 2),
        "carriers": info.get("carriers"),
        "UNREAD": info.get("UNREAD"),
        "ruling": info.get("ruling"),
    }


def main(src, defect, label, budget):
    print("=" * 72)
    print("FIXTURE", label, " defect file:", defect)
    for widened in (False, True):
        root = fresh(src, "_run_w" if widened else "_run_b")
        r = arm(root, widened, defect, budget)
        for k in ("arm", "carriers", "UNREAD", "ruling", "searched",
                  "defect_rank", "status", "edited", "correct_file",
                  "runs", "secs", "hint"):
            if r.get(k) is not None or k in ("status", "arm"):
                print("  %-12s %s" % (k, r[k]))
        print("  " + "-" * 60)


if __name__ == "__main__":
    main(os.path.abspath(sys.argv[1]), sys.argv[2], sys.argv[3],
         int(sys.argv[4]) if len(sys.argv) > 4 else 120)
