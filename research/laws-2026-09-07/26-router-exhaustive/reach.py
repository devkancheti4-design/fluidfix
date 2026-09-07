"""26-router-exhaustive: which route() inputs the BODY can construct.

Traces the two production paths that reach the router and shows what each
does with a fault kind outside 0..15.

  loop.py:283  mask = mask_of(k for k in obs.kinds if 0 <= k <= 15)
  loop.py:297  kind = kind_of(EMIT(mask));  loop.py:299  act = act_for(kind)
  guard.py:401 n = sum(len(candidates(body, act_for(k), obs))
                       for k in (obs.kinds or [])[:2])      <-- NOT filtered

Run: ./run.sh 120 /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python reach.py
"""
import sys

sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")

from fluidfix.acts import ACTS, KINDS, Observation, act_for, candidates  # noqa: E402
from fluidfix.lanes import ADVANCE, EMIT, HALT, kind_of, mask_of  # noqa: E402


def hdr(t):
    print("\n== " + t)


def loop_kinds(reported):
    """Exactly loop.py's mask_of/EMIT/ADVANCE/HALT walk over obs.kinds."""
    mask = mask_of(k for k in reported if 0 <= k <= 15)
    out = []
    while not HALT(mask):
        out.append(kind_of(EMIT(mask)))
        mask = ADVANCE(mask)
    return out


hdr("B1  every kind the MECHANICAL observer can report")
print(f"observers.py:37 draws from sorted(KINDS) = {sorted(KINDS)}")
print(f"-> acts the loop can therefore reach: "
      f"{sorted({act_for(k) for k in KINDS})}")

hdr("B2  the loop's filter drops out-of-range kinds; the ranker's does not")
for reported in ([0, 3], [99], [-1, 1], [16], [3, 99]):
    lk = loop_kinds(reported)
    ranked = [(k, act_for(k)) for k in (reported or [])[:2]]
    print(f"  obs.kinds={reported!r:<12} loop tries kinds {lk!r:<10} "
          f"(acts {[act_for(k) for k in lk]!r:<12})   "
          f"guard priority() calls act_for on {ranked!r}")

hdr("B3  a kind the loop DROPS still buys a candidate count in the ranker")
obs = Observation(lineno=1, kinds=[99])
body = "    total = a + b"
n = sum(len(candidates(body.strip(), act_for(k), obs))
        for k in (obs.kinds or [])[:2])        # guard.py:401, verbatim
print(f"  line          = {body!r}")
print(f"  obs.kinds     = {obs.kinds}   (99 & 15 == {99 & 15} -> "
      f"kind {99 & 15} = {KINDS[99 & 15][0]!r})")
print(f"  act_for(99)   = {act_for(99)}  -> applier "
      f"{getattr(ACTS.get(act_for(99)), '__name__', 'NONE')}")
print(f"  guard CHEAP n = {n}  -> cheap = {0 < n < 8}")
print(f"  loop kinds    = {loop_kinds(obs.kinds)}  <- the loop tries NOTHING")
print(f"  guard SIGNALED bit = bool(obs.kinds) = {bool(obs.kinds)}  "
      f"<- claims a signal the loop cannot act on")

hdr("B4  no two distinct fault classes can share an applier")
print("  route(0,5,.) is a bijection on 0..15 (exhaustive.py R4), so "
      "act_for is injective:")
print(f"  len({{act_for(k) for k in range(16)}}) = "
      f"{len({act_for(k) for k in range(16)})} / 16")

hdr("B5  free kind slots vs the reserved range the docstring names")
free = [k for k in range(16) if k not in KINDS]
print(f"  kinds with no registered class: {free}")
print(f"  acts.py:89 comment reserves 4..7; slots 13,14,15 are ALSO free")
print(f"  their act codes: {[(k, act_for(k)) for k in free]}")
print(f"  act codes with no applier: "
      f"{sorted(set(range(16)) - set(ACTS))}")

hdr("B6  what an unrouted act does downstream (no suite run)")
for a in sorted(set(range(16)) - set(ACTS)):
    out = candidates(body, a, Observation(lineno=1, kinds=[]))
    print(f"  candidates(line, act={a}) -> {out!r}  "
          f"== [line]: {out == [body]}  -> NOPROGRESS, ADVANCE, 0 suite runs")
    break
print("  (identical for every act code with no applier: "
      "acts.py:399-400 `if fn is None: return [line]`)")
