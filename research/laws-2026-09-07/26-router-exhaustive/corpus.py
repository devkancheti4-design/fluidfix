"""26-router-exhaustive: routing value over a real corpus of lines.

For every line of every .py file under fluidfix's own src/ and tests/ (read
only), compare the distinct candidate set produced by
  ALL   every applier in ACTS                (a body with no routing law)
  MECH  act_for(k) for the mechanical observer's kinds on that line
  TRUE  act_for(one kind)                    (a precise observer)
Distinct candidates are what the loop actually runs: loop.py:332 dedups on
(lineno, candidate) and loop.py:355 pays one suite run each.

Run: ./run.sh 300 /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python corpus.py
"""
import os
import sys

sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")

from fluidfix.acts import ACTS, KINDS, Observation, act_for, candidates  # noqa: E402

ROOTS = ["/Users/kanchetidevieswar/neo/fluidfix/src",
         "/Users/kanchetidevieswar/neo/fluidfix/tests"]


def cset(line, acts, obs):
    out = set()
    for a in acts:
        for c in candidates(line, a, obs):
            if isinstance(c, str) and c != line:
                out.add(c)
    return out


files = lines_seen = signalled = 0
tot_all = tot_mech = tot_true = 0
mech_lt_all = 0        # lines where routing from the mechanical observer prunes
for root in ROOTS:
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        for fn in sorted(filenames):
            if not fn.endswith(".py"):
                continue
            files += 1
            with open(os.path.join(dirpath, fn), encoding="utf-8",
                      errors="replace") as f:
                for line in f.read().split("\n"):
                    lines_seen += 1
                    ks = [k for k, (_, _, sig) in sorted(KINDS.items())
                          if sig.search(line)]
                    if not ks:
                        continue
                    signalled += 1
                    obs = Observation(lineno=1, kinds=ks)
                    a = cset(line, sorted(ACTS), obs)
                    m = cset(line, [act_for(k) for k in ks], obs)
                    t = cset(line, [act_for(ks[0])], obs)   # "most specific first"
                    tot_all += len(a); tot_mech += len(m); tot_true += len(t)
                    if len(m) < len(a):
                        mech_lt_all += 1
print(f"files scanned                              {files}")
print(f"lines scanned                              {lines_seen}")
print(f"lines the mechanical observer signals      {signalled}")
print(f"lines where MECH prunes anything vs ALL    {mech_lt_all}")
print()
print(f"candidates ALL  (no routing law)           {tot_all}")
print(f"candidates MECH (routed, mech observer)    {tot_mech}")
print(f"candidates TRUE (routed, one-kind observer){tot_true}")
print()
print(f"routing saves vs ALL, mechanical observer: "
      f"{tot_all - tot_mech} / {tot_all} = {(tot_all - tot_mech) / tot_all:.4%}")
print(f"routing saves vs ALL, one-kind observer:   "
      f"{tot_all - tot_true} / {tot_all} = {(tot_all - tot_true) / tot_all:.4%}")
