"""Three measurements on the harvest actuation, all on a synthetic pytest
fixture (never on src/):
  A. report wording: what GuardReport.summary() SAYS was tried vs what WAS tried
  B. memory: does a second run re-try exactly the candidates the first run
     harvested as rejected? (does anything read last_refusal.json back?)
  C. caps across FILES: F files x N wrong candidates each -> attempts kept,
     rejected_candidates persisted.
usage: harvest_cap_fixture2.py N F"""
import json, os, re, sys, tempfile, time
sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
N = int(sys.argv[1]); F = int(sys.argv[2])
os.environ["FLUIDFIX_CANDIDATE_CAP"] = str(N)
from fluidfix import MechanicalObserver, Oracle, guard_once
from fluidfix.acts import register
from fluidfix.guard import write_refusal

here = os.path.dirname(os.path.abspath(__file__))
root = tempfile.mkdtemp(prefix=f"harvestcap_{F}f_", dir=here)
files = []
for i in range(F):
    m = f"mod{i}"
    open(os.path.join(root, f"{m}.py"), "w").write("K = 999\n\ndef f():\n    return K\n")
    open(os.path.join(root, f"test_{m}.py"), "w").write(
        f"from {m} import f\n\ndef test_f():\n    assert f() == -1\n")
    files.append(f"{m}.py")
register(4, "cap-probe", "N wrong candidates", re.compile(r"K = "),
         lambda line, o: [f"K = {i}" for i in range(1, N + 1)])
oracle = Oracle(root, python=sys.executable)

def run(label):
    t0 = time.time()
    rep = guard_once(oracle, MechanicalObserver(), files=files, escalate=False)
    dt = time.time() - t0
    p = write_refusal(root, rep)
    j = json.load(open(p))
    print(f"[{label}] N={N} F={F} status={rep.status} seconds={dt:.1f} "
          f"candidates_actually_tried={N*F}")
    print(f"[{label}] GuardReport.attempts={len(rep.attempts)}  "
          f"last_refusal.json rejected_candidates={len(j['rejected_candidates'])}")
    print(f"[{label}] summary() says: ...{rep.summary().split('teach it once')[1][:120]!r}")
    return [(e['at'], e['tried']) for e in j['rejected_candidates']], rep

first, rep1 = run("run1")
second, rep2 = run("run2")
print("run2 harvested exactly the same rejected candidates as run1:", first == second)
print("run2 suite runs (from summary timing) vs run1: see seconds above")
print("per-file tally of harvested entries:",
      {f: sum(1 for a, _ in first if a.startswith(f + ":")) for f in files})
