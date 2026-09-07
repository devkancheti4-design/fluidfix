"""26-router-exhaustive: the observer's kind ORDER never reaches the router.

observers.py:54 asks the observer for "fault kinds that apply to that line,
from this closed vocabulary, MOST SPECIFIC FIRST". loop.py:283 turns that
ordered list into a BITMASK (mask_of), and lanes.py EMIT (m & -m) then walks
it low-bit-first, i.e. in ascending kind number. The order is destroyed
before act_for/route is called.

It is outcome-relevant: loop.py:222 ships greens[0], and greens are appended
in walk order.

Fixture: `if n > 10:` where the intended predicate is "n >= 10".
  kind 0  -> act 5  _flip_strictness  -> `if n >= 10:`   GREEN
  kind 1  -> act 6  _reduce_literal   -> `if n > 9:`     GREEN
  kind 10 -> act 15 _flip_comparison  -> `if n < 10:`    red

Run: ./run.sh 300 /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python order.py
"""
import os
import shutil
import sys

sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")

from fluidfix import Observation, Oracle, repair  # noqa: E402
from fluidfix.acts import act_for  # noqa: E402
from fluidfix.lanes import ADVANCE, EMIT, HALT, kind_of, mask_of  # noqa: E402

MOD = ("def gate(n):\n"
       "    if n > 10:\n"
       "        return 1\n"
       "    return 0\n")
TEST = ("from mod import gate\n\n"
        "def test_it():\n"
        "    assert gate(10) == 1\n"
        "    assert gate(9) == 0\n")

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(HERE, "fixtures_order")
shutil.rmtree(WORK, ignore_errors=True)

print("the loop's walk order is the bitmask's, not the list's:")
for order in ([0, 1, 10], [1, 0, 10], [10, 1, 0]):
    m = mask_of(k for k in order if 0 <= k <= 15)
    walk = []
    while not HALT(m):
        walk.append(kind_of(EMIT(m)))
        m = ADVANCE(m)
    print(f"  obs.kinds={order!r:<12} mask={mask_of(order):#07x}  "
          f"loop walks {walk!r} -> acts {[act_for(k) for k in walk]!r}")

print("\nand the shipped repair follows the walk, not the list:")
for i, order in enumerate(([0, 1, 10], [1, 0, 10], [10, 1, 0])):
    d = os.path.join(WORK, f"case{i}")
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "mod.py"), "w").write(MOD)
    open(os.path.join(d, "test_mod.py"), "w").write(TEST)
    oracle = Oracle(d, python=sys.executable)
    res = repair(oracle, "mod.py",
                 [Observation(lineno=2, kinds=list(order))])
    print(f"  obs.kinds={order!r:<12} repaired={res.repaired}  "
          f"greens={res.greens!r}  shipped={res.new_line.strip()!r}"
          if res.repaired else
          f"  obs.kinds={order!r:<12} repaired=False  "
          f"reason={res.reason[:70]!r}")
