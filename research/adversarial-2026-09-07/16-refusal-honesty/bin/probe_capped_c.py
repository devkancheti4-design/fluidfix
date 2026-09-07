"""C twin of probe_capped.py: drive coracle's PUBLIC api the way
cguard_once does (same whole-pass deadline) and print the RepairResult
fields cguard_once never reads. No fluidfix source is modified.

  usage: probe_capped_c.py ROOT REL_FILE BUILD_CMD TEST_CMD BUDGET
"""
import sys, time, json
from fluidfix.coracle import COracle, find_candidate_files_c, build_packet_c
from fluidfix.observers import MechanicalObserver
from fluidfix.loop import repair

root, rel, build_cmd, test_cmd, budget = (sys.argv[1], sys.argv[2],
                                          sys.argv[3], sys.argv[4],
                                          float(sys.argv[5]))
t0 = time.time()
o = COracle(root, build_cmd=build_cmd, test_cmd=test_cmd)
fails, out = o.failing_output()
cands = find_candidate_files_c(o, out)
packet = build_packet_c(o, rel, out)
obs = MechanicalObserver().observe([packet])[0]
res = repair(o, rel, obs, deadline=t0 + budget)         # coracle.py:760
print(json.dumps({
    "candidates_from_frames": cands,
    "repaired": res.repaired,
    "ambiguous": res.ambiguous,
    "reason_repair_produced": res.reason,
    "greens_len": len(res.greens),
    "greens": res.greens,
    "rejected": len(res.tried_log),
    "suite_runs": res.suite_runs,
    "seconds": round(res.seconds, 2),
}, indent=1))
