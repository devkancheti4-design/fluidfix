"""Measure: does CHANGING the record granularity beat RE-CONFIRMING at the
same granularity, on both flake shapes?

Runs the SHIPPED loop.repair() unmodified.  The only thing that varies is the
Oracle handed to it (granularity.LadderOracle) and FLUIDFIX_CONFIRM.

usage: run_experiment.py SHAPE CONFIG TRIALS [K]
  SHAPE   A (flake correlated with the code under test) | B (independent)
  CONFIG  g0 | g1c1 | g1c2 | g1c4 | g2 | g3
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = "/Users/kanchetidevieswar/neo/fluidfix/src"
sys.path.insert(0, SRC)
sys.path.insert(0, HERE)

from fluidfix.acts import KINDS, Observation          # noqa: E402
from fluidfix.localize import Packet                  # noqa: E402
from fluidfix.observers import MechanicalObserver     # noqa: E402
from fluidfix import loop                             # noqa: E402
from granularity import LadderOracle, Profile         # noqa: E402

CORRECT = "    return a + b"
DEFECT = "    return a - b"

CONFIGS = {
    "g0":   dict(rung=0, confirm=0),
    "g1c1": dict(rung=1, confirm=1),      # the shipped default
    "g1c2": dict(rung=1, confirm=2),
    "g1c4": dict(rung=1, confirm=4),
    "g2":   dict(rung=2, confirm=0),
    "g3":   dict(rung=3, confirm=0),
}


def observations(root):
    """The REAL MechanicalObserver, on a packet naming the defect line."""
    with open(os.path.join(root, "src.py"), encoding="utf-8") as f:
        src_lines = f.read().split("\n")
    pkt = Packet(defect_file="src.py", failure="(elided)", lines=[2],
                 src_lines=src_lines, mode="frames")
    return MechanicalObserver().observe([pkt])[0]


def one_trial(shape, cfg, k, timeout):
    fixture = os.path.join(HERE, "fixtures", f"shape{shape}")
    work = tempfile.mkdtemp(prefix=f"gran{shape}", dir=HERE + "/work")
    root = os.path.join(work, "repo")
    shutil.copytree(fixture, root)
    os.environ["FLUIDFIX_CONFIRM"] = str(cfg["confirm"])
    t0 = time.time()
    orc = LadderOracle(root, python=sys.executable, timeout=timeout,
                       rung=cfg["rung"], k=k)
    prof = None
    if cfg["rung"] >= 2:
        prof = Profile(orc, runs=5)
        orc.profile = prof
    obs = observations(root)
    try:
        res = loop.repair(orc, "src.py", obs, candidate_timeout=timeout)
    except Exception as e:                          # harness blow-up, logged
        shutil.rmtree(work, ignore_errors=True)
        return dict(outcome="HARNESS_ERROR", why=repr(e)[:200],
                    invocations=orc.invocations, seconds=time.time() - t0)
    if res.repaired:
        outcome = "CORRECT" if res.new_line == CORRECT else "FALSE_ACCEPT"
    elif "no failing test" in res.reason:
        outcome = "NO_FAILING_TEST"
    else:
        outcome = "REFUSED"
    rec = dict(outcome=outcome, new_line=res.new_line, why=res.reason[:160],
               invocations=orc.invocations, full_runs=orc.full_runs,
               node_runs=orc.node_runs, seconds=round(time.time() - t0, 2),
               kinds=[o.kinds for o in obs])
    if prof is not None:
        rec["profile"] = dict(always_fail=sorted(prof.always_fail),
                              mixed=sorted(prof.mixed),
                              hidden=prof.hidden)
    shutil.rmtree(work, ignore_errors=True)
    return rec


def main():
    shape, config, trials = sys.argv[1], sys.argv[2], int(sys.argv[3])
    k = int(sys.argv[4]) if len(sys.argv) > 4 else 4
    os.makedirs(HERE + "/work", exist_ok=True)
    cfg = CONFIGS[config]
    recs = [one_trial(shape, cfg, k, 60) for _ in range(trials)]
    counts = {}
    for r in recs:
        counts[r["outcome"]] = counts.get(r["outcome"], 0) + 1
    out = dict(shape=shape, config=config, cfg=cfg, k=k, trials=trials,
               counts=counts,
               mean_invocations=round(
                   sum(r["invocations"] for r in recs) / len(recs), 2),
               mean_full_runs=round(
                   sum(r.get("full_runs", 0) for r in recs) / len(recs), 2),
               mean_node_runs=round(
                   sum(r.get("node_runs", 0) for r in recs) / len(recs), 2),
               mean_seconds=round(sum(r["seconds"] for r in recs) / len(recs), 2),
               records=recs)
    path = os.path.join(HERE, "results", f"shape{shape}_{config}.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(out, f, indent=1)
    print(json.dumps({kk: out[kk] for kk in
                      ("shape", "config", "k", "trials", "counts",
                       "mean_invocations", "mean_full_runs", "mean_node_runs",
                       "mean_seconds")}))


if __name__ == "__main__":
    main()
