import sys
sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix.acts import ACTS, WORKED_EXAMPLE, act_for, candidates, Observation
from fluidfix.lanes import kind_of
print("WORKED_EXAMPLE =", WORKED_EXAMPLE, " ACTS keys =", sorted(ACTS))
for k in (-1, 0, 1, 12, 15, 16, 64):
    try:
        a = act_for(k)
        known = a in ACTS
        print(f"  act_for({k:>3}) = {a:>3}   in ACTS: {known}")
    except Exception as e:
        print(f"  act_for({k:>3}) RAISES {type(e).__name__}: {e}")
print("kind_of(0) =", kind_of(0), "-> act_for(kind_of(0)) =", act_for(kind_of(0)))
o = Observation(lineno=1, kinds=[-1])
for a in (4, act_for(-1)):
    try:
        print(f"  candidates('return a + b', act={a}) -> {candidates('return a + b', a, o)}")
    except Exception as e:
        print(f"  candidates(act={a}) RAISES {type(e).__name__}: {e}")
