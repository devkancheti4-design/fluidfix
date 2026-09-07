import sys, os
sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix.oracle import Oracle
from fluidfix.observers import MechanicalObserver
from fluidfix.guard import guard_once
o = Oracle(os.path.abspath(sys.argv[1]), python=sys.executable)
r = guard_once(o, MechanicalObserver(), budget=120, escalate_budget=120)
for a in r.attempts:
    print(repr(a))
