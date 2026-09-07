"""Prove that the candidate fluidfix's own generator produces for kind 3 at
include/cglm/bezier.h:53 leaves the suite GREEN. No fluidfix source is
modified; this uses its public generators and its own oracle."""
import sys
sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix.acts import Observation, act_for, candidates
from fluidfix.coracle import COracle

root, rel, lineno = sys.argv[1], sys.argv[2], int(sys.argv[3])
path = f"{root}/{rel}"
src = open(path, encoding="utf-8", newline="").read()
raw = src.split("\n")
body = raw[lineno - 1].rstrip("\r")
obs = Observation(lineno=lineno, kinds=[1, 3])
obs.file, obs.root, obs.all_lines = rel, root, [l.rstrip("\r") for l in raw]
print("line", lineno, "=", repr(body))
for kind in (1, 3):
    act = act_for(kind)
    cands = [c for c in candidates(body, act, obs) if c != body]
    print(f"  kind {kind} -> act {act}: {cands}")

o = COracle(root)
act3 = act_for(3)
cands3 = [c for c in candidates(body, act3, obs) if c != body]
try:
    for c in cands3:
        new = raw[:]
        new[lineno - 1] = c + raw[lineno - 1][len(body):]
        open(path, "w", encoding="utf-8", newline="").write("\n".join(new))
        ok, why = o.check()
        print(f"  CANDIDATE {c!r} -> oracle.check() ok={ok} why={why!r}")
finally:
    open(path, "w", encoding="utf-8", newline="").write(src)
    print("restored; sha equal:", open(path, encoding='utf-8', newline='').read() == src)
