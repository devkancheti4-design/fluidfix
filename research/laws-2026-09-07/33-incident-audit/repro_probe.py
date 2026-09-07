# Independent probe: rebuild the defect, run the real guard_once, and print
# the greens the run held and the byte the law was handed.
import os, shutil, sys, subprocess
sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix.engine import decide, situation
from fluidfix.oracle import Oracle
from fluidfix.guard import guard_once
from fluidfix.observers import MechanicalObserver

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "repro_S1_amb")
PRISTINE = "    return readings[0] > limit\n"
DEFECT   = "    return readings[1] > limit\n"

src = open(os.path.join(ROOT, "gate.py")).read().splitlines(True)
src[4] = DEFECT
open(os.path.join(ROOT, "gate.py"), "w").writelines(src)
print("reset to defect:", repr(src[4]))

o = Oracle(ROOT, python=sys.executable)
rep = guard_once(o, MechanicalObserver())
print("status   :", rep.status)
print("reason   :", getattr(rep.result, "reason", None))
print("ambiguous:", getattr(rep.result, "ambiguous", None))
print("greens   :", getattr(rep.result, "greens", None))
print("shipped  :", repr(open(os.path.join(ROOT, "gate.py")).read().splitlines(True)[4]))
print("pristine :", repr(PRISTINE))
print("shipped_equals_pristine:", open(os.path.join(ROOT,"gate.py")).read().splitlines(True)[4] == PRISTINE)

g = getattr(rep.result, "greens", []) or []
n = len(g)
print()
print("byte PASSED  : situation(BUILT=True, AMB=False) =", situation(BUILT=True), "->", decide(situation(BUILT=True)))
print("byte OWED    : situation(BUILT=True, AMB=True ) =", situation(BUILT=True, AMB=True), "->", decide(situation(BUILT=True, AMB=True)))
print("greens held at ruling time:", n, "(AMB owed True iff the two greens are different programs)")

# behavioural separation of the two greens
ns1, ns2 = {}, {}
exec("def alarm(readings, limit):\n" + PRISTINE, ns1)
exec("def alarm(readings, limit):\n    return readings[1] >= limit\n", ns2)
for args in ([9, 1], 5), ([0, 9], 5), ([7, 3], 3):
    print("  alarm(%r, %r): pristine=%s shipped=%s" % (args[0], args[1], ns1["alarm"](*args), ns2["alarm"](*args)))
