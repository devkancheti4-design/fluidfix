#!/usr/bin/env python
"""Confirm the ONE body call site the pytest sweep never exercised:
guard.py:491, the UNREAD lane (x=4 -> ADD_MATERIAL).

The site's guard is:
    if not candidates and not _has_pytest_cov(oracle):
        if decide(situation(UNREAD=True)) == "ADD_MATERIAL": ...

so reaching it needs BOTH conjuncts true at once:
  * `not candidates` — the failing output names no project source file AND
    coverage localisation ranks nothing (find_candidate_files -> []).
  * `not _has_pytest_cov(oracle)` — `oracle.python -c "import pytest_cov"`
    exits non-zero. We use a REAL interpreter that genuinely lacks it
    (/usr/bin/python3; the project venv has pytest_cov 7.1.0), so this is the
    situation the bit describes, not a mock of it.

guard_once() is driven with a stub oracle duck-typed to what it uses:
root, python, failing_output(), run(). No suite is executed.

Run:  ./run.sh 300 <venv>/bin/python reach_unread.py
"""
import os
import sys
import tempfile

sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
import fluidfix.engine as engine  # noqa: E402
import fluidfix.guard as guard  # noqa: E402
from fluidfix.engine import BITS  # noqa: E402

asked = []
_real = engine.decide


def logged(sit):
    act = _real(sit)
    asked.append((sit & 0xFF, act))
    return act


engine.decide = logged
# guard_once does `from .engine import decide, situation` INSIDE the function,
# so patching the module attribute is enough (loop.py binds at import time and
# is patched separately in reach_dynamic.py).


def bits(x):
    return "+".join(b for i, b in enumerate(BITS) if x >> i & 1) or "<empty>"


NO_COV_PYTHON = "/usr/bin/python3"          # genuinely lacks pytest_cov
VENV_PYTHON = "/Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python"


class StubOracle:
    """Minimal duck type for guard_once's first 60 lines."""
    timeout = 5

    def __init__(self, root, python, out):
        self.root, self.python, self.out = root, python, out
        self.runs = 0

    def failing_output(self):
        return True, self.out              # a real failure, no .py frames

    def run(self, args, cache=False):
        self.runs += 1                     # writes no cov json -> no ranking
        return 1, ""

    def green(self):
        return False

    def check(self, timeout=None):
        return False, "stub: red"

    def clear_pyc(self):
        pass


def scenario(label, python, out):
    d = tempfile.mkdtemp(prefix="unread-")
    o = StubOracle(d, python, out)
    asked.clear()
    ev = {}
    cands = guard.find_candidate_files(o, out, evidence=ev)
    has_cov = guard._has_pytest_cov(o)
    rep = guard.guard_once(o, observer=None, escalate=True)
    print(f"\n--- {label}")
    print(f"  interpreter                : {python}")
    print(f"  find_candidate_files       : {cands}  (empty => `not candidates` True)")
    print(f"  _has_pytest_cov(oracle)    : {has_cov}")
    print(f"  law asked                  : {[(x, bits(x), a) for x, a in asked]}")
    print(f"  guard status               : {rep.status}")
    print(f"  hint                       : {rep.hint[:150]!r}")
    return asked.copy(), rep


print("=== UNREAD lane (guard.py:491) — both conjuncts true ===")
# a pure assertion failure: no project .py frame in the text
OUT = ("FAILED tests/test_x.py::test_thing - assert 1 == 2\n"
       "1 failed in 0.01s\n")
a1, r1 = scenario("pytest-cov ABSENT  (expected: UNREAD asked)", NO_COV_PYTHON, OUT)

print("\n=== control: same repo, an interpreter that HAS pytest-cov ===")
a2, r2 = scenario("pytest-cov PRESENT (expected: UNREAD not asked)", VENV_PYTHON, OUT)

print("\n=== verdict ===")
hit1 = any(x == 4 for x, _ in a1)
hit2 = any(x == 4 for x, _ in a2)
print(f"  x=4 UNREAD asked with pytest-cov absent : {hit1}")
print(f"  x=4 UNREAD asked with pytest-cov present: {hit2}")
print(f"  lane guard.py:491 is REACHABLE and gated by the measurement: "
      f"{hit1 and not hit2}")
print(f"  law rules on x=4: {_real(4 | 512)}")
print(f"  hint mentions the ruling: "
      f"{'ADD_MATERIAL' in (r1.hint or '')}")
