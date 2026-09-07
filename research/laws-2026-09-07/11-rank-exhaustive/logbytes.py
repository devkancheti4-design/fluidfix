#!/usr/bin/env python
"""11-rank-exhaustive: log every observation byte the BODY hands the
ranking law on three tiny Python fixtures (copied from tests/test_guard.py,
rebuilt here -- tests/ is never touched).

Run (one at a time, per BRIEF):
  nice -n 15 ./timeout.sh 300 /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python logbytes.py

Monkeypatches fluidfix.rank.rank; guard.rank_observations imports it at
call time (`from .rank import rank as _rank`), so every call is seen.
"""
import collections
import os
import shutil
import sys
import tempfile

sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
import fluidfix.rank as R                                        # noqa: E402
from fluidfix import MechanicalObserver, Oracle, guard_once     # noqa: E402
from fluidfix.rank import BITS                                   # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
SEEN: list[int] = []
ALL: list[int] = []
_orig = R.rank


def _spy(x):
    SEEN.append(x)
    ALL.append(x)
    return _orig(x)


R.rank = _spy

BUGGY = ("def count_above(xs, t):\n    n = 0\n    for x in xs:\n"
         "        if x >= t:\n            n += 1\n    return n\n")
TEST = ("from mod import count_above\n\ndef test_c():\n"
        "    assert count_above([1, 5, 5, 9], 5) == 1\n")
FIXTURES = {
    "count_above (assertion only, no frame)": (BUGGY, TEST),
    "join2 (raising fault, traceback frames mod.py)": (
        "def join2(a, b):\n    return a - b\n",
        "from mod import join2\n\ndef test_j():\n    assert join2('x', 'y') == 'xy'\n"),
    "both (novel class -> refusal)": (
        "def both(a, b):\n    return bool(a or b)\n",
        "from mod import both\n\ndef test_b():\n    assert both(True, False) is False\n"),
}


def bits(x):
    return "+".join(b for i, b in enumerate(BITS) if (x >> i) & 1) or "none"


for name, (mod, test) in FIXTURES.items():
    d = tempfile.mkdtemp(prefix="rankfix_", dir=HERE)
    try:
        open(os.path.join(d, "mod.py"), "w").write(mod)
        open(os.path.join(d, "test_mod.py"), "w").write(test)
        SEEN.clear()
        rep = guard_once(Oracle(d, python=sys.executable), MechanicalObserver())
        c = collections.Counter(SEEN)
        print(f"\n== {name}: status={rep.status} file={rep.file} "
              f"rank() calls={len(SEEN)}")
        for x, n in sorted(c.items()):
            print(f"   byte {x:3d} = {bits(x):<32} -> rank {_orig(x)}   x{n}")
    finally:
        shutil.rmtree(d, ignore_errors=True)

print("\nBits ever set across all three fixtures:",
      [b for i, b in enumerate(BITS) if any((x >> i) & 1 for x in ALL)] or "n/a")
