"""Progress-rate curve on ONE cglm defect (C path, cguard_once).

Defect: include/cglm/vec3.h:944 glm_vec3_clamp, off-by-one array index
        v[2] = glm_clamp(v[2], ...)  ->  v[2] = glm_clamp(v[1], ...)
Suite goes 1128/1131 (3 failures). Injected by inject_cglm.sh.

usage: run_cglm.py ROOT OUTDIR BUDGET
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
import probe
probe.install()
from fluidfix import MechanicalObserver
from fluidfix.coracle import COracle, cguard_once

root, out, budget = sys.argv[1], sys.argv[2], int(sys.argv[3])
oracle = COracle(root, jobs=8, timeout=120)
print("test_cmd:", oracle.test_cmd, flush=True)
rep = cguard_once(oracle, MechanicalObserver(), budget=budget)
print("STATUS", rep.status, "seconds", round(rep.seconds, 2),
      "file", rep.file, flush=True)
print("HINT", (rep.hint or "")[:400], flush=True)
print("CANDIDATE FILES", (rep.candidates or [])[:20], flush=True)
probe.dump(os.path.join(out, "cglm_budget%d.json" % budget))
json.dump({"status": rep.status, "seconds": rep.seconds, "file": rep.file,
           "candidates": rep.candidates, "hint": rep.hint,
           "attempts": (rep.attempts or [])[:64]},
          open(os.path.join(out, "cglm_budget%d_summary.json" % budget), "w"),
          indent=1)
print("DONE", flush=True)
