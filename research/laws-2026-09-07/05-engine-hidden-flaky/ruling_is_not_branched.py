"""Does loop.py act on the HIDDEN *ruling*, or on its own `fine_disagree` flag?

A fake oracle answers green on the first check of a candidate and red on the
re-check (a suite that does not hold still). `fluidfix.loop.decide` is
monkeypatched IN THIS PROCESS ONLY so that the HIDDEN situation rules "SHIP"
instead of CHANGE_GRANULARITY. If the body consulted the ruling, the candidate
would then be accepted; if it branches on `fine_disagree`, the candidate is
rejected regardless and the fake ruling merely appears in the message.
No src/ file is modified. Run: .venv/bin/python ruling_is_not_branched.py
"""
import os, tempfile
import fluidfix.loop as loop
from fluidfix.engine import decide as real_decide, situation
from fluidfix.acts import Observation

HERE = os.path.dirname(os.path.abspath(__file__))


class FakeOracle:
    """Duck-typed to what loop.repair() needs. check() alternates
    green/red PER CANDIDATE: first call green, re-check red."""
    def __init__(self, root):
        self.root, self.timeout = root, 60
        self.calls = []
        self._n = 0
    def clear_pyc(self): pass
    def green(self, timeout=None): return False          # baseline is red
    def check(self, timeout=None):
        self._n += 1
        with open(os.path.join(self.root, "calc.py")) as f:
            line = f.read().split("\n")[1].strip()
        # green on the first look at any candidate, red on every re-check
        first_look = line not in [c[0] for c in self.calls]
        self.calls.append((line, first_look))
        return (True, "") if first_look else (False, "FAILED test_x - flaky")


def run(patched):
    root = tempfile.mkdtemp(prefix="rnb_", dir=HERE)
    with open(os.path.join(root, "calc.py"), "w") as f:
        f.write("def add(a, b):\n    return a - b\n")
    orig = loop.decide
    if patched:
        loop.decide = lambda sit: ("SHIP" if sit == situation(HIDDEN=True)
                                   else real_decide(sit))
    try:
        os.environ["FLUIDFIX_CONFIRM"] = "1"
        o = FakeOracle(root)
        res = loop.repair(o, "calc.py", [Observation(lineno=2, kinds=[2, 3, 11])])
    finally:
        loop.decide = orig
        os.environ.pop("FLUIDFIX_CONFIRM", None)
    print(f"--- decide patched for HIDDEN: {patched} ---")
    print("  repaired:", res.repaired, "| refused:", res.refused, "| greens:", res.greens)
    for e in res.tried_log:
        print("  rejected:", e["tried"].strip(), "|", e["why"][:150])
    print("  oracle.check() calls:", o.calls)
    return res


a = run(patched=False)
b = run(patched=True)
print()
print("VERDICT: with the HIDDEN ruling forced to SHIP the candidate is",
      "STILL REJECTED" if b.refused and not b.repaired else "ACCEPTED",
      "-> the body branches on fine_disagree; the ruling only reaches the message.")
