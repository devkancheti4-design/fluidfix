"""Corrected multi-file measurement. ONE failing test executes all F modules
(so every module gets a coverage packet), oracle.check is wrapped with a
counter so 'tried' is MEASURED, and the guard runs twice to see whether the
harvest is ever read back. usage: harvest_cap_fixture3.py N F"""
import json, os, re, sys, tempfile, time
sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
N = int(sys.argv[1]); F = int(sys.argv[2])
os.environ["FLUIDFIX_CANDIDATE_CAP"] = str(N)
from fluidfix import MechanicalObserver, Oracle, guard_once
from fluidfix.acts import register
from fluidfix.guard import write_refusal

here = os.path.dirname(os.path.abspath(__file__))
root = tempfile.mkdtemp(prefix=f"harvestcap3_{F}f_", dir=here)
files = []
for i in range(F):
    open(os.path.join(root, f"mod{i}.py"), "w").write("K = 999\n\ndef f():\n    return K\n")
    files.append(f"mod{i}.py")
imports = "\n".join(f"import mod{i}" for i in range(F))
conds = " and ".join(f"mod{i}.f() == -1" for i in range(F))
open(os.path.join(root, "test_all.py"), "w").write(
    f"{imports}\n\ndef test_all():\n    assert {conds}\n")
register(4, "cap-probe", "N wrong candidates", re.compile(r"K = "),
         lambda line, o: [f"K = {i}" for i in range(1, N + 1)])
oracle = Oracle(root, python=sys.executable)
calls = {"check": 0}
_orig = oracle.check
def counted(timeout=None):
    calls["check"] += 1
    return _orig(timeout=timeout)
oracle.check = counted

def run(label):
    calls["check"] = 0
    t0 = time.time()
    rep = guard_once(oracle, MechanicalObserver(), files=files, escalate=False)
    dt = time.time() - t0
    p = write_refusal(root, rep)
    j = json.load(open(p))
    print(f"[{label}] N={N} F={F} status={rep.status} seconds={dt:.1f} "
          f"MEASURED candidates tried (oracle.check calls)={calls['check']}")
    print(f"[{label}] GuardReport.attempts={len(rep.attempts)}  "
          f"last_refusal.json rejected_candidates={len(j['rejected_candidates'])}")
    tail = rep.summary().split("fluidfix kinds)")[-1][:90]
    print(f"[{label}] summary() says: {tail!r}")
    return [(e['at'], e['tried']) for e in j['rejected_candidates']], calls["check"]

first, c1 = run("run1")
second, c2 = run("run2")
print("run2 re-tried the same number of candidates as run1:", c1 == c2, f"({c1} vs {c2})")
print("run2 persisted exactly the same rejected list as run1:", first == second)
print("per-file tally of PERSISTED entries:",
      {f: sum(1 for a, _ in first if a.startswith(f + ":")) for f in files})
