#!/usr/bin/env python
"""Drive loop.repair() with a scripted stub oracle (no real suite) to CONFIRM
three static claims about which engine-law situations the body constructs:

  A. BUILT+CAPPED (x=33) is reachable: a green found, then the wall-clock
     deadline expires before the next kind -> _rule(capped=True).
  B. HIDDEN (x=16) is reachable: one-run green, re-check red.
  C. BUILT+AMB+CAPPED (x=35) is NOT constructed even when the deadline has
     already expired at the moment AMB is proven: the body asks x=3.

The stub oracle is duck-typed to what loop.repair() needs (root, timeout,
green(), check(), clear_pyc()). decide() is wrapped to log what the body asks.
Run:  .venv/bin/python reach_dynamic.py
"""
import os
import re
import sys
import tempfile
import time

sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
import fluidfix.engine as engine  # noqa: E402
import fluidfix.loop as loop  # noqa: E402
from fluidfix.acts import Observation, register  # noqa: E402
from fluidfix.engine import BITS  # noqa: E402

asked = []
_real = engine.decide


def logged(sit):
    act = _real(sit)
    asked.append((sit & 0xFF, act))
    return act


engine.decide = loop.decide = logged


def bits(x):
    return "+".join(b for i, b in enumerate(BITS) if x >> i & 1) or "<empty>"


class StubOracle:
    """check() returns the scripted verdicts in order; sleeps `delay` each."""
    timeout = 5

    def __init__(self, root, verdicts, delay=0.0):
        self.root, self.verdicts, self.delay = root, list(verdicts), delay
        self.calls = 0

    def green(self):
        return False                       # precondition: a failing test

    def check(self, timeout=None):
        self.calls += 1
        time.sleep(self.delay)
        ok = self.verdicts.pop(0) if self.verdicts else False
        return ok, "" if ok else "stub: red"

    def clear_pyc(self):
        pass


def fresh(src):
    d = tempfile.mkdtemp(prefix="reach-")
    with open(os.path.join(d, "mod.py"), "w") as f:
        f.write(src)
    return d


# kind 4: two candidates at one site (the fusion test's amb-demo class)
register(4, "amb-demo", "two suite-passing candidates", re.compile(r"K = "),
         lambda line, o: ["K = 1", "K = 2"])
# kind 5: one candidate per line, distinct lines (for A: greens across kinds)
register(5, "one-shot", "single candidate", re.compile(r"J = "),
         lambda line, o: ["J = 9"])

print("=== A. BUILT+CAPPED via deadline between kinds ===")
os.environ["FLUIDFIX_CONFIRM"] = "0"
d = fresh("K = 0\nJ = 0\n")
# obs 1 (line 1) has kinds [5? no: 'J' only on line 2]. Use two observations:
# line 2 kind 5 (one candidate, green), then line 1 kind 4 (never reached).
obs = [Observation(lineno=2, kinds=[5]), Observation(lineno=1, kinds=[4])]
o = StubOracle(d, verdicts=[True], delay=0.6)
asked.clear()
res = loop.repair(o, "mod.py", obs, deadline=time.time() + 0.3)
print(f"  repaired={res.repaired} reason={res.reason[:90]!r}")
print(f"  law asked: {[(x, bits(x), a) for x, a in asked]}")
untouched = open(os.path.join(d, 'mod.py')).read() == "K = 0\nJ = 0\n"
print(f"  file untouched after refusal: {untouched}")

print("\n=== B. HIDDEN via one-run green, re-check red ===")
os.environ["FLUIDFIX_CONFIRM"] = "1"
d = fresh("J = 0\n")
obs = [Observation(lineno=1, kinds=[5])]
o = StubOracle(d, verdicts=[True, False])   # coarse green, fine red
asked.clear()
res = loop.repair(o, "mod.py", obs)
print(f"  repaired={res.repaired} reason={res.reason[:80]!r}")
print(f"  law asked: {[(x, bits(x), a) for x, a in asked]}")
print(f"  tried_log why: {res.tried_log[0]['why'][:120] if res.tried_log else None!r}")
print(f"  file untouched after refusal: {open(os.path.join(d, 'mod.py')).read() == 'J = 0\n'}")

print("\n=== C. AMB proven AFTER the deadline expired: is x=35 ever asked? ===")
os.environ["FLUIDFIX_CONFIRM"] = "0"
d = fresh("K = 0\n")
obs = [Observation(lineno=1, kinds=[4])]
o = StubOracle(d, verdicts=[True, True], delay=0.4)   # both candidates green
asked.clear()
# deadline expires during the first candidate's check; the set completes,
# AMB is proven inside it, and the body rules with capped=False
res = loop.repair(o, "mod.py", obs, deadline=time.time() + 0.1)
print(f"  repaired={res.repaired} ambiguous={res.ambiguous}")
print(f"  law asked: {[(x, bits(x), a) for x, a in asked]}")
print(f"  file untouched after refusal: {open(os.path.join(d, 'mod.py')).read() == 'K = 0\n'}")
print(f"  x=35 asked: {any(x == 35 for x, _ in asked)}   "
      f"(law on x=35 would rule {_real(35 | 512)}, on x=3 rules {_real(3 | 512)})")
