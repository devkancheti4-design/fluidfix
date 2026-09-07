"""31-cross-rank-sight, probe 4: the counterfactual file order, run LIVE.

guard_once(files=[...]) bypasses find_candidate_files entirely, so the
documented tie-break (specificity, then executed-line count -- no affinity)
can be measured as a real repair pass without editing src/.

Usage: python forced_order.py <fixture> <workdir> <file1,file2,...>
"""
import json, os, shutil, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
import fixtures, order_probe

name, work, order = sys.argv[1], sys.argv[2], sys.argv[3].split(",")
if os.path.isdir(work):
    shutil.rmtree(work)
os.makedirs(work)
fixtures.ALL[name](work)
order_probe.install(work)
from fluidfix import MechanicalObserver, Oracle, guard_once
o = Oracle(work, python=sys.executable)
t0 = time.time()
rep = guard_once(o, MechanicalObserver(), files=order, budget=180)
print(json.dumps({"fixture": name, "forced_file_order": order,
                  "status": rep.status, "file": rep.file,
                  "seconds": round(time.time() - t0, 2),
                  "suite_runs": sum(e["kind"] == "RUN"
                                    for e in order_probe.EVENTS),
                  "events": order_probe.EVENTS}, indent=1, default=str))
