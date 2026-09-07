"""MEASUREMENT 1 — a SECOND guard run of the SAME class on the same
unrepaired tree, with and without the harvested negatives.

usage: bench_crossrun.py N F [--memo]
  N   candidates the taught class proposes per line
  F   how many modules carry the class's signal
Without --memo this is fluidfix as shipped. With --memo the prototype in
negatives.py consults the previous run's rejections.

Everything printed is MEASURED: `check` counts oracle.check() calls (one per
candidate adjudicated), `pytest` counts real `python -m pytest` invocations.
"""
import os, re, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
sys.path.insert(0, HERE)

N = int(sys.argv[1]); F = int(sys.argv[2])
MEMO = "--memo" in sys.argv
os.environ["FLUIDFIX_CANDIDATE_CAP"] = str(N)

from fluidfix import MechanicalObserver, Oracle, guard_once      # noqa: E402
from fluidfix.acts import register                               # noqa: E402
from fluidfix.guard import write_refusal                         # noqa: E402
from negatives import Counter, Negatives, tree_fingerprint       # noqa: E402

root = tempfile.mkdtemp(prefix=f"crossrun_{'memo' if MEMO else 'base'}_",
                        dir=HERE)
files = []
for i in range(F):
    open(os.path.join(root, f"mod{i}.py"), "w").write(
        "K = 999\n\ndef f():\n    return K\n")
    files.append(f"mod{i}.py")
open(os.path.join(root, "test_all.py"), "w").write(
    "\n".join(f"import mod{i}" for i in range(F))
    + "\n\ndef test_all():\n    assert "
    + " and ".join(f"mod{i}.f() == -1" for i in range(F)) + "\n")

# a taught class (reserved slot 4) that proposes N candidates, none correct:
# the fault (-1) is outside what it can spell. Every candidate is REFUTED.
register(4, "cap-probe", "N wrong candidates", re.compile(r"K = "),
         lambda line, o: [f"K = {i}" for i in range(1, N + 1)])

oracle = Oracle(root, python=sys.executable)
cnt = Counter(oracle)
neg = Negatives(os.path.join(root, ".fluidfix", "negatives.json"))


def run(label):
    fp = tree_fingerprint(root)
    cnt.reset()
    uninstall = neg.install(fp) if MEMO else (lambda: None)
    t0 = time.time()
    try:
        rep = guard_once(oracle, MechanicalObserver(), files=files,
                         escalate=False)
    finally:
        uninstall()
    dt = time.time() - t0
    p = write_refusal(root, rep)
    import json
    kept = len(json.load(open(p))["rejected_candidates"])
    added = neg.harvest(fp, green_texts=(rep.result.greens if rep.result else ()))
    neg.save()
    print(f"[{label}] memo={MEMO} status={rep.status} seconds={dt:.1f} "
          f"check={cnt.check} pytest={cnt.pytest} "
          f"attempts={len(rep.attempts)} persisted_rejects={kept} "
          f"memo_skipped={neg.skipped} memo_size={len(neg.entries)} "
          f"(+{added} this run)")
    print(f"[{label}] hint: {rep.hint[:110]!r}")
    print(f"[{label}] summary: {rep.summary()!r}")
    return cnt.check, cnt.pytest, dt


c1, p1, d1 = run("run1")
c2, p2, d2 = run("run2")
print(f"RESULT memo={MEMO}: run2/run1 candidates adjudicated {c2}/{c1}, "
      f"pytest invocations {p2}/{p1}, seconds {d2:.1f}/{d1:.1f}")
print(f"RESULT memo={MEMO}: reduction on the second run — candidates "
      f"{100.0 * (c1 - c2) / c1:.1f}%, pytest {100.0 * (p1 - p2) / p1:.1f}%, "
      f"wall {100.0 * (d1 - d2) / d1:.1f}%")
print("root:", root)
