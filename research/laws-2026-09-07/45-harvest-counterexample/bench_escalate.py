"""MEASUREMENT 2 — the ESCALATION pass inside ONE guard run.

Shape (the shape guard.py:539-598 actually produces): the defect file is long
enough that pass 0's packet is TRUNCATED (localize.build_packet max_lines=110),
so `capped0` is true, the engine law rules RAISE_BUDGET, and escalation
re-builds the packet with max_lines=990 — a SUPERSET of pass 0's stride
sample. Every candidate pass 0 rejected is proposed again, and the file is not
in `full_sight`, so nothing skips it.

The true defect sits on a line the stride sample DROPS, so pass 0 must refuse
and escalation must repair. That is what makes this a clean speed measurement:
the repair still has to land, and it has to land on the same line with the
same bytes, with and without the memo.

The decoy lines are INERT by construction (`_scratch` is never read), so no
candidate on them can accidentally cancel the fault — that would be the AMB
lane, a different experiment.

usage: bench_escalate.py [--memo]
"""
import os, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
sys.path.insert(0, HERE)
MEMO = "--memo" in sys.argv
PASS0 = "--pass0" in sys.argv   # pass 0 alone, to size the re-tried set

from fluidfix import MechanicalObserver, Oracle, guard_once      # noqa: E402
from fluidfix.localize import build_packet                       # noqa: E402
from fluidfix.guard import write_refusal                         # noqa: E402
from negatives import Counter, Negatives, tree_fingerprint       # noqa: E402

NFILL = 170                     # executed filler lines -> packet truncation
root = tempfile.mkdtemp(prefix=f"esc_{'memo' if MEMO else 'base'}_", dir=HERE)
MOD = os.path.join(root, "acc.py")


def write_module(defect_at: int, decoys: set[int]) -> None:
    """Body line i (1-based inside run()) is filler, a decoy, or THE defect."""
    out = ["one = len(\"x\")", "", "def run():",
           "    t = len(\"\")", "    _scratch = len(\"\")"]
    for i in range(1, NFILL + 1):
        if i == defect_at:
            out.append("    t = t + 2")          # WRONG: should be + 1
        elif i in decoys:
            out.append("    _scratch = _scratch + 7")   # inert, always red
        else:
            out.append("    t = t * one")
    out += ["    return t", ""]
    open(MOD, "w").write("\n".join(out))


def body_line(i: int) -> int:
    """file line number of body line i"""
    return 5 + i


open(os.path.join(root, "test_acc.py"), "w").write(
    "import acc\n\ndef test_run():\n    assert acc.run() == 1\n")

oracle = Oracle(root, python=sys.executable)
cnt = Counter(oracle)

# --- placement probe: which body lines survive pass 0's stride sample? ------
write_module(defect_at=1, decoys=set())
p110 = build_packet(oracle, "acc.py")
p990 = build_packet(oracle, "acc.py", max_lines=990)
kept, full = set(p110.lines), set(p990.lines)
dropped = sorted(full - kept)
print(f"probe: pass0 packet truncated={p110.truncated} lines={len(kept)}; "
      f"escalation packet truncated={p990.truncated} lines={len(full)}; "
      f"lines pass 0 never sees={len(dropped)}")
assert p110.truncated and dropped, "fixture did not truncate"

DECOYS = {i for i in range(1, NFILL + 1) if body_line(i) in kept}
DECOYS = set(sorted(DECOYS)[:8])                     # 8 wrong-line candidates
DEFECT = next(i for i in range(NFILL, 0, -1)
              if body_line(i) in dropped and i not in DECOYS)
write_module(defect_at=DEFECT, decoys=DECOYS)
print(f"probe: defect at body line {DEFECT} (file line {body_line(DEFECT)}), "
      f"in pass-0 packet: {body_line(DEFECT) in kept}; "
      f"decoy file lines: {sorted(body_line(i) for i in DECOYS)}")

# --- the measured run -------------------------------------------------------
neg = Negatives(os.path.join(root, ".fluidfix", "negatives.json"))
fp = tree_fingerprint(root)
t_fp = time.time()
tree_fingerprint(root)
print(f"tree_fingerprint cost on this fixture: {time.time() - t_fp:.4f}s")

cnt.reset()
uninstall = neg.install(fp) if MEMO else (lambda: None)
t0 = time.time()
try:
    rep = guard_once(oracle, MechanicalObserver(), files=["acc.py"],
                     escalate=not PASS0, escalate_budget=240)
finally:
    uninstall()
dt = time.time() - t0
line = open(MOD).read().split("\n")[body_line(DEFECT) - 1] if rep.status == "repaired" else ""
print(f"RESULT pass0_only={PASS0} memo={MEMO} status={rep.status} file={rep.file} "
      f"lineno={rep.result.lineno if rep.result else None} "
      f"new_line={rep.result.new_line.strip() if rep.result and rep.result.new_line else None!r}")
print(f"RESULT memo={MEMO} candidates adjudicated (oracle.check)={cnt.check} "
      f"pytest invocations={cnt.pytest} seconds={dt:.1f} "
      f"suite_runs(RepairResult)={rep.result.suite_runs if rep.result else None} "
      f"memo_skipped={neg.skipped}")
print(f"RESULT memo={MEMO} on-disk line now: {line.strip()!r}")
if not MEMO:
    write_refusal(root, rep)
print("root:", root)
