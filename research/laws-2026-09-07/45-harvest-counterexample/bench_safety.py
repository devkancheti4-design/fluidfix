"""MEASUREMENT 3 — is the memo SOUND?

A rejection is a fact about the TREE it was measured against, not about the
candidate. Change the tree and the same candidate can become the repair. This
script builds exactly that: run 1 rejects `LIMIT = 9`; the tree then changes
(the test's expected value moves) and `LIMIT = 9` becomes green.

  naive  memo keyed on (site, candidate) only        -> the repair is LOST
  fp     memo keyed on (site, candidate, tree hash)  -> the repair still lands

usage: bench_safety.py naive|fp
"""
import os, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
sys.path.insert(0, HERE)
MODE = sys.argv[1] if len(sys.argv) > 1 else "fp"

from fluidfix import MechanicalObserver, Oracle, guard_once      # noqa: E402
from negatives import Counter, Negatives, tree_fingerprint       # noqa: E402

root = tempfile.mkdtemp(prefix=f"safety_{MODE}_", dir=HERE)
open(os.path.join(root, "mod.py"), "w").write(
    "LIMIT = 10\n\n\ndef f():\n    return LIMIT\n")


def set_expected(v: int) -> None:
    open(os.path.join(root, "test_mod.py"), "w").write(
        f"import mod\n\ndef test_f():\n    assert mod.f() == {v}\n")


oracle = Oracle(root, python=sys.executable)
cnt = Counter(oracle)
neg = Negatives(os.path.join(root, ".fluidfix", "negatives.json"))


def run(label, expected):
    set_expected(expected)
    fp = "NAIVE-no-tree-check" if MODE == "naive" else tree_fingerprint(root)
    cnt.reset()
    un = neg.install(fp)
    t0 = time.time()
    try:
        rep = guard_once(oracle, MechanicalObserver(), files=["mod.py"],
                         escalate=False)
    finally:
        un()
    neg.harvest(fp, green_texts=(rep.result.greens if rep.result else ()))
    neg.save()
    print(f"[{label}] mode={MODE} expected={expected} fp={fp[:12]} "
          f"status={rep.status} check={cnt.check} skipped={neg.skipped} "
          f"memo={len(neg.entries)} seconds={time.time() - t0:.1f} "
          f"new_line={rep.result.new_line.strip() if rep.result and rep.result.new_line else None!r}")
    return rep.status


s1 = run("run1", 7)     # LIMIT = 9 is rejected here
s2 = run("run2", 9)     # ... and is the correct repair here
print(f"VERDICT mode={MODE}: run1={s1} run2={s2} — "
      f"{'REPAIR LOST to a stale negative' if s2 != 'repaired' else 'repair still lands'}")
print("root:", root)
