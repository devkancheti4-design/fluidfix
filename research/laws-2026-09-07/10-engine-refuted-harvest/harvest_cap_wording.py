"""The harvest cap and what the refusal SAYS about it.

loop.py:346/407 keeps at most 64 rejections per RepairResult and counts the
rest in RepairResult.tried_more.  guard.py sums tried_log into
GuardReport.attempts and NEVER reads tried_more; summary() (guard.py:104)
reports len(self.attempts); write_refusal (guard.py:719) truncates to 200.

This measures, on one file with N wrong candidates, all four numbers:
  candidates actually tried (oracle.check calls) / tried_log / tried_more /
  what summary() tells the user / what the json persists.

usage: harvest_cap_wording.py N
"""
import json, os, re, sys, tempfile, time

sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
N = int(sys.argv[1]) if len(sys.argv) > 1 else 100
os.environ["FLUIDFIX_CANDIDATE_CAP"] = str(N)
from fluidfix import MechanicalObserver, Oracle, guard_once
from fluidfix.acts import register
from fluidfix.guard import write_refusal

here = os.path.dirname(os.path.abspath(__file__))
root = tempfile.mkdtemp(prefix="capword_", dir=here)
open(os.path.join(root, "mod.py"), "w").write("K = 999\n\ndef f():\n    return K\n")
open(os.path.join(root, "test_mod.py"), "w").write(
    "import mod\n\ndef test_f():\n    assert mod.f() == -1\n")
register(4, "cap-probe", "N wrong candidates", re.compile(r"K = "),
         lambda line, o: [f"K = {i}" for i in range(1, N + 1)])

oracle = Oracle(root, python=sys.executable)
calls = {"n": 0}
_orig = oracle.check
def counted(timeout=None):
    calls["n"] += 1
    return _orig(timeout=timeout)
oracle.check = counted

t0 = time.time()
rep = guard_once(oracle, MechanicalObserver(), files=["mod.py"], escalate=False)
dt = time.time() - t0
p = write_refusal(root, rep)
j = json.load(open(p))
tm = rep.result.tried_more if rep.result is not None else "unavailable (refusal path attaches no RepairResult)"
print(f"N={N} status={rep.status} seconds={dt:.1f}")
print(f"candidates ACTUALLY tried (oracle.check calls): {calls['n']}")
print(f"GuardReport.attempts (harvest kept):            {len(rep.attempts)}")
print(f"RepairResult.tried_more (rejections dropped):   {tm}")
print(f"last_refusal.json rejected_candidates:          {len(j['rejected_candidates'])}")
print("\nsummary() tail:")
print("  ..." + rep.summary().split("fluidfix kinds)")[-1].strip())
print("\nis 'tried_more' mentioned anywhere the user can see it?")
print("  in summary():", "tried_more" in rep.summary() or "more" in rep.summary().split("rejected")[-1][:60])
print("  in last_refusal.json keys:", sorted(j.keys()))
print("\nfixture root:", root)
