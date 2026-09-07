"""26-router-exhaustive: does routing prune anything the appliers do not?

The mechanical observer (observers.py:37) reports EVERY kind whose signal
regex matches the line -- and each applier is itself a no-op on lines outside
its shape. So `kind -> act` may be redundant with the appliers' own guards.
Measure it three ways on the same line:

  all-acts   candidates from every applier in ACTS  (a body with no router)
  mechanical candidates from act_for(k) for the mechanical observer's kinds
  true-kind  candidates from act_for(true kind) only (a precise observer)

Also does it on a deliberately signal-dense line.
Run: ./run.sh 300 /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python precision.py
"""
import os
import sys

sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")

from fluidfix.acts import ACTS, KINDS, Observation, act_for, candidates  # noqa: E402


def mech_kinds(line):
    return [k for k, (_, _, sig) in sorted(KINDS.items()) if sig.search(line)]


def n(line, acts, obs):
    seen = set()
    for a in acts:
        for c in candidates(line, a, obs):
            if isinstance(c, str) and c != line:
                seen.add(c)
    return len(seen)


LINES = [
    # (line, the true fault kind)
    ("        if x >= t:", 0),
    ("    return days * 3601", 1),
    ("    return a // b", 2),
    ("    return a + b", 3),
    ("    return min(a, b)", 8),
    ("        n += 1", 9),
    ("    if a < b:", 10),
    ("    d = a - b", 11),
    ("DEBUG = True", 12),
    # signal-dense: matches many vocabularies at once
    ("    return max(hi - 1, lo) if a >= b else min(hi + 1, lo)", 8),
    ("    idx = end - start + 1", 1),
    ("    ok = True if n >= 10 else False", 0),
]
print(f"{'line':<56} {'mech kinds':<20} {'all':>4} {'mech':>5} {'true':>5}")
ta = tm = tt = 0
for line, true_k in LINES:
    obs = Observation(lineno=1, kinds=mech_kinds(line))
    a = n(line, sorted(ACTS), obs)
    m = n(line, [act_for(k) for k in obs.kinds], obs)
    t = n(line, [act_for(true_k)], obs)
    ta += a; tm += m; tt += t
    print(f"{line.strip()[:54]:<56} {str(obs.kinds):<20} {a:>4} {m:>5} {t:>5}")
print(f"{'TOTAL (distinct candidates = suite runs)':<56} {'':<20} "
      f"{ta:>4} {tm:>5} {tt:>5}")
print(f"\nrouting from the MECHANICAL observer saves {ta - tm} of {ta} "
      f"candidates ({(ta - tm) / ta:.1%})")
print(f"routing from a PRECISE (one-kind) observer saves {ta - tt} of {ta} "
      f"candidates ({(ta - tt) / ta:.1%})")
