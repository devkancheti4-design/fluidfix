"""MEASUREMENT 4 — what the harvest AS WRITTEN TODAY can carry forward.

The store the prototype builds comes from the candidate stream. The store the
shipped code already writes is `.fluidfix/last_refusal.json`
(`rejected_candidates`), and it is lossy in two documented ways:
  loop.py:346/407  at most 64 rejections per repair() call (`tried_more` counts
                   the rest and is never persisted at all)
  loop.py:348/409  the candidate text is truncated to 200 characters

So this runs the SAME fixture twice: run 2's memo is built ONLY from what
run 1 actually persisted. `skipped` is then the ceiling a read-back of
today's file would reach, with no other change to the code.

usage: cap_effect.py N   (N candidates from one taught class, one file)
"""
import json, os, re, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
sys.path.insert(0, HERE)
N = int(sys.argv[1])
os.environ["FLUIDFIX_CANDIDATE_CAP"] = str(N)

from fluidfix import MechanicalObserver, Oracle, guard_once      # noqa: E402
from fluidfix.acts import register                               # noqa: E402
from fluidfix.guard import write_refusal                         # noqa: E402
from negatives import Counter, Negatives, _sha, tree_fingerprint  # noqa: E402

root = tempfile.mkdtemp(prefix=f"cap_{N}_", dir=HERE)
open(os.path.join(root, "mod0.py"), "w").write(
    "K = 999\n\ndef f():\n    return K\n")
open(os.path.join(root, "test_all.py"), "w").write(
    "import mod0\n\ndef test_all():\n    assert mod0.f() == -1\n")
register(4, "cap-probe", "N wrong candidates", re.compile(r"K = "),
         lambda line, o: [f"K = {i}" for i in range(1, N + 1)])

oracle = Oracle(root, python=sys.executable)
cnt = Counter(oracle)

# ---- run 1: fluidfix exactly as shipped -----------------------------------
cnt.reset()
t0 = time.time()
rep1 = guard_once(oracle, MechanicalObserver(), files=["mod0.py"],
                  escalate=False)
d1, c1, p1 = time.time() - t0, cnt.check, cnt.pytest
path = write_refusal(root, rep1)
persisted = json.load(open(path))["rejected_candidates"]
print(f"[run1] N={N} adjudicated={c1} pytest={p1} seconds={d1:.1f} "
      f"attempts={len(rep1.attempts)} persisted={len(persisted)}")
print(f"[run1] loop.py's 64-entry cap dropped "
      f"{c1 - len(rep1.attempts)} of {c1} rejections before they were ever "
      f"persisted (RepairResult.tried_more)")

# ---- run 2: memo built ONLY from what run 1 persisted ---------------------
fp = tree_fingerprint(root)
neg = Negatives()
for e in persisted:
    neg.add(e["at"], _sha(e["tried"]), fp, e.get("why", ""))
cnt.reset()
un = neg.install(fp)
t0 = time.time()
try:
    rep2 = guard_once(oracle, MechanicalObserver(), files=["mod0.py"],
                      escalate=False)
finally:
    un()
d2, c2, p2 = time.time() - t0, cnt.check, cnt.pytest
print(f"[run2] memo-from-last_refusal.json entries={len(neg.entries)} "
      f"skipped={neg.skipped} adjudicated={c2} pytest={p2} seconds={d2:.1f}")
print(f"RESULT N={N}: read-back of the file fluidfix ALREADY writes saves "
      f"{c1 - c2} of {c1} candidate adjudications "
      f"({100.0 * (c1 - c2) / c1:.1f}%), {p1 - p2} of {p1} pytest invocations, "
      f"{d1 - d2:.1f}s of {d1:.1f}s")
print("root:", root)
