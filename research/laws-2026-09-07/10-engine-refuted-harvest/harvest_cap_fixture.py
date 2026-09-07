"""Measure the harvest cap: a taught class that proposes N candidates, every
one rejected by the suite. Counts what the harvest keeps vs drops, and what
write_refusal() persists. Everything happens in a temp dir inside this
research directory; src/ is never touched."""
import json, os, re, sys, tempfile, time
sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
N = int(sys.argv[1]) if len(sys.argv) > 1 else 100
os.environ["FLUIDFIX_CANDIDATE_CAP"] = str(N)
from fluidfix import MechanicalObserver, Oracle, guard_once
from fluidfix.acts import register
from fluidfix.guard import write_refusal

here = os.path.dirname(os.path.abspath(__file__))
root = tempfile.mkdtemp(prefix="harvestcap_", dir=here)
src = "K = 999\n\ndef f():\n    return K\n"
open(os.path.join(root, "mod.py"), "w").write(src)
open(os.path.join(root, "test_mod.py"), "w").write(
    "from mod import f\n\ndef test_f():\n    assert f() == -1\n")
# every candidate K = 1..N is wrong: the suite must reject all N
register(4, "cap-probe", "N wrong candidates", re.compile(r"K = "),
         lambda line, o: [f"K = {i}" for i in range(1, N + 1)])
oracle = Oracle(root, python=sys.executable)
t0 = time.time()
rep = guard_once(oracle, MechanicalObserver(), escalate=False)
dt = time.time() - t0
r = rep.result if rep.result else None
print(f"N={N} status={rep.status} seconds={dt:.1f}")
print(f"attempts kept in GuardReport: {len(rep.attempts)}")
if r is not None:
    print(f"RepairResult.tried_log={len(r.tried_log)} tried_more={r.tried_more} "
          f"suite_runs={r.suite_runs} acts_tried={r.acts_tried}")
else:
    print("GuardReport.result is None (refusal path does not attach the RepairResult)")
p = write_refusal(root, rep)
j = json.load(open(p))
print(f"last_refusal.json rejected_candidates={len(j['rejected_candidates'])}")
print("first entry:", j["rejected_candidates"][0] if j["rejected_candidates"] else None)
print("distinct why values:", len({e['why'] for e in j['rejected_candidates']}))
print("hint:", j["hint"][:300])
print("mod.py untouched:", open(os.path.join(root, "mod.py")).read() == src)
