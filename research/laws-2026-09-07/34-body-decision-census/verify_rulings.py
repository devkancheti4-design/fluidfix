import sys
sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix.engine import decide, situation, BITS, ACTS

print("=== A. The three constant-byte decide() calls in guard.py ===")
for label, kw in [("guard.py:491  UNREAD=True", dict(UNREAD=True)),
                  ("guard.py:612  REFUTED=True", dict(REFUTED=True)),
                  ("guard.py:618  REFUTED=True", dict(REFUTED=True))]:
    print(f"  {label:34} -> {decide(situation(**kw))}   (byte is a literal: branch is a tautology)")

print("\n=== B. loop.py:221/230 -- is `set_amb or len(sites)>1` the same test as `ruling==ADD_STATE`? ===")
print("  BUILT is always True at loop.py:217. Enumerate AMB x CAPPED:")
mism = []
for amb in (False, True):
    for capped in (False, True):
        r = decide(situation(BUILT=True, AMB=amb, CAPPED=capped))
        body_says = "AMBIGUOUS wording" if amb else "CAPPED wording"
        law_says  = {"SHIP":"ship","ADD_STATE":"AMBIGUOUS wording","RAISE_BUDGET":"CAPPED wording"}.get(r, f"?? {r}")
        agree = "OK " if (r=="SHIP" or body_says==law_says) else "MISMATCH"
        if agree=="MISMATCH": mism.append((amb,capped,r,body_says))
        print(f"    AMB={int(amb)} CAPPED={int(capped)} -> law={r:22} body branch at :230 -> {body_says:18} {agree}")
print("  mismatches:", mism or "none")

print("\n=== C. guard.py:539 -- what the law rules for every (CAPPED,REFUTED) the body can pass ===")
for c in (False, True):
    for r in (False, True):
        print(f"    CAPPED={int(c)} REFUTED={int(r)} -> {decide(situation(CAPPED=c, REFUTED=r))}")

print("\n=== D. the engine law's full 8-act reach vs what the body's 6 decide() calls can construct ===")
constructible = set()
constructible.add(situation(BUILT=True))            # loop.py:217 lanes
for amb in (0,1):
    for cap in (0,1):
        constructible.add(situation(BUILT=True, AMB=bool(amb), CAPPED=bool(cap)))
constructible.add(situation(HIDDEN=True))           # loop.py:391
constructible.add(situation(UNREAD=True))           # guard.py:491
for c in (0,1):
    for r in (0,1):
        constructible.add(situation(CAPPED=bool(c), REFUTED=bool(r)))
constructible.add(situation(REFUTED=True))          # guard.py:612/618
acts_reached = sorted({decide(s) for s in constructible})
print("  situations the body can construct:", len(constructible), "of 256")
print("  acts reached:", acts_reached)
print("  acts NEVER reached:", sorted(set(ACTS) - set(acts_reached)))
