"""Drive loop.repair() into the BUILT+CAPPED / RAISE_BUDGET lane, then
evaluate guard.py's own expressions (lines 508, 519, 538, 539, 617) on the
RepairResult it returns, verbatim. Shows what guard_once would have reported.
"""
import os, sys, time
sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "fixture_refuted")
sys.path.insert(0, ROOT)

from fluidfix.acts import Observation
from fluidfix.engine import decide, situation
from fluidfix.loop import repair
from fluidfix.oracle import Oracle

orig = open(os.path.join(ROOT, "prog.py"), encoding="utf-8").read()
o = Oracle(ROOT, python=sys.executable, timeout=120, extra_args=["-p","no:randomly"])
print("baseline suite green?", o.green())

# obs1: line 2 `return a - b`, kind 3 (flipped-additive) -> `return a + b` = green
# obs2: line 6, same kind. The deadline is checked BETWEEN observations
# (loop.py:269), so obs1 completes and obs2 trips it.
obs = [Observation(lineno=2, kinds=[3]), Observation(lineno=6, kinds=[3])]

t0 = time.time()
res = repair(o, "prog.py", obs, candidate_timeout=60, deadline=t0 + 3.0)
print(f"\nelapsed {time.time()-t0:.1f}s")
print("  repaired :", res.repaired)
print("  ambiguous:", res.ambiguous)
print("  greens   :", res.greens)
print("  acts_tried:", res.acts_tried)
print("  reason   :", res.reason)
open(os.path.join(ROOT, "prog.py"), "w").write(orig)   # restore fixture

print("\n--- now guard_once's own expressions, verbatim, on this result ---")
capped0 = False            # guard.py:508  packet.truncated (a 6-line file: False)
acts0   = False
acts0 = acts0 or bool(res.acts_tried)                  # guard.py:519  VERBATIM
print(f"  guard.py:519  acts0 = acts0 or bool(result.acts_tried)  -> {acts0}")
print(f"                but a candidate PASSED the suite: res.greens = {res.greens}")
print("                engine.py:24 defines REFUTED as 'candidates were generated")
print("                AND the suite rejected every one'. Not every one was.")
all_files, candidates = ["prog.py"], ["prog.py"]
capped0 = capped0 or len(all_files) > len(candidates)  # guard.py:538  VERBATIM
print(f"\n  guard.py:538  capped0 -> {capped0}   (the DEADLINE cap that repair()")
print("                just ruled RAISE_BUDGET on is never propagated here)")
r539 = decide(situation(CAPPED=capped0, REFUTED=acts0))
print(f"  guard.py:539  decide(situation(CAPPED={capped0}, REFUTED={acts0})) = {r539}")
print(f"                == 'RAISE_BUDGET'? {r539 == 'RAISE_BUDGET'}  -> escalation SKIPPED")
r617 = decide(situation(REFUTED=True))
print(f"  guard.py:617  acts0 and decide(situation(REFUTED=True))=='HARVEST_COUNTEREXAMPLE' -> {acts0 and r617=='HARVEST_COUNTEREXAMPLE'}")
print("\n  => guard would return status='refused' with hint:")
print('     "every generated candidate was rejected by the suite')
print('      (engine law: REFUTED -> HARVEST_COUNTEREXAMPLE)"')
print(f"\n  TRUTH: {len(res.greens)} candidate(s) passed; the engine law had already ruled")
print(f"         {decide(situation(BUILT=True, CAPPED=True))} inside repair(). GuardReport carries no `greens`")
print("         field and result=None on that return path (guard.py:622), so the")
print("         passing candidate never reaches the user at all.")
