"""Measuring instrument, not a patch: drive fluidfix's PUBLIC api the way
guard_once does, with the same first-pass deadline (budget/3), and print the
RepairResult fields guard.py never reads.  No fluidfix source is modified.

  usage: probe_capped.py ROOT REL_FILE BUDGET_SECONDS
"""
import sys, time, json
from fluidfix.oracle import Oracle
from fluidfix.localize import build_packet
from fluidfix.observers import MechanicalObserver
from fluidfix.guard import rank_observations
from fluidfix.loop import repair

root, rel, budget = sys.argv[1], sys.argv[2], float(sys.argv[3])
t0 = time.time()
oracle = Oracle(root)
fails, out = oracle.failing_output()
packet = build_packet(oracle, rel)
obs = rank_observations("\n".join(packet.src_lines),
                        MechanicalObserver().observe([packet])[0], out,
                        root=oracle.root, rel=rel)
res = repair(oracle, rel, obs, deadline=t0 + budget / 3)   # guard.py:481
print(json.dumps({
    "repaired": res.repaired,
    "ambiguous": res.ambiguous,
    "reason_repair_produced": res.reason,
    "greens_len": len(res.greens),
    "greens": res.greens,
    "rejected": len(res.tried_log),
    "suite_runs": res.suite_runs,
    "seconds": round(res.seconds, 2),
}, indent=1))
