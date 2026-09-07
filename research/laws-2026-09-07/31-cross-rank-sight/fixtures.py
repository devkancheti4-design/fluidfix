# Fixture builders for target 31-cross-rank-sight.
# F1/F2 are copied verbatim in shape from tests/test_guard.py (BUGGY/TEST and
# the join2 traceback fixture). F3..F5 are multi-file extensions built here,
# because every Python fixture under tests/ is single-source-file and a
# single-file project cannot exercise a FILE ordering at all.
import os

BUGGY = ("def count_above(xs, t):\n    n = 0\n    for x in xs:\n"
         "        if x >= t:\n            n += 1\n    return n\n")
TEST = ("from mod import count_above\n\ndef test_c():\n"
        "    assert count_above([1, 5, 5, 9], 5) == 1\n")

JOIN_BUG = "def join2(a, b):\n    return a - b\n"
JOIN_TEST = ("from mod import join2\n\ndef test_j():\n"
             "    assert join2('x', 'y') == 'xy'\n")

# Three innocent siblings the failing test also executes, so coverage-based
# file ranking has something to choose between.
SIB_A = ("def scale(v, k):\n    return v * k\n\n\n"
         "def offset(v, k):\n    return v + k\n")
SIB_B = ("def clamp(v, lo, hi):\n    if v < lo:\n        return lo\n"
         "    if v > hi:\n        return hi\n    return v\n")
SIB_C = ("def total(xs):\n    s = 0\n    for x in xs:\n        s += x\n"
         "    return s\n")


def _w(root, rel, text):
    p = os.path.join(root, rel)
    os.makedirs(os.path.dirname(p) or root, exist_ok=True)
    with open(p, "w") as f:
        f.write(text)


def f1_single_assert(root):
    """tests/test_guard.py::test_guard_finds_file_and_repairs...  (assertion)"""
    _w(root, "mod.py", BUGGY)
    _w(root, "test_mod.py", TEST)
    return "mod.py", 4


def f2_single_traceback(root):
    """tests/test_guard.py::test_guard_follows_traceback_frames (TypeError)"""
    _w(root, "mod.py", JOIN_BUG)
    _w(root, "test_mod.py", JOIN_TEST)
    return "mod.py", 2


def f3_multi_assert(root):
    """Same defect as F1, but four source modules all executed by the test."""
    _w(root, "mod.py", BUGGY)
    _w(root, "scaling.py", SIB_A)
    _w(root, "bounds.py", SIB_B)
    _w(root, "totals.py", SIB_C)
    _w(root, "test_mod.py",
       "from mod import count_above\nfrom scaling import scale, offset\n"
       "from bounds import clamp\nfrom totals import total\n\n"
       "def test_c():\n"
       "    assert scale(2, 3) == 6 and offset(2, 3) == 5\n"
       "    assert clamp(5, 0, 9) == 5 and total([1, 2]) == 3\n"
       "    assert count_above([1, 5, 5, 9], 5) == 1\n")
    return "mod.py", 4


def f4_multi_traceback(root):
    """Same four modules, but the fault raises so a traceback exists."""
    _w(root, "mod.py", JOIN_BUG)
    _w(root, "scaling.py", SIB_A)
    _w(root, "bounds.py", SIB_B)
    _w(root, "totals.py", SIB_C)
    _w(root, "test_mod.py",
       "from mod import join2\nfrom scaling import scale, offset\n"
       "from bounds import clamp\nfrom totals import total\n\n"
       "def test_j():\n"
       "    assert scale(2, 3) == 6 and offset(2, 3) == 5\n"
       "    assert clamp(5, 0, 9) == 5 and total([1, 2]) == 3\n"
       "    assert join2('x', 'y') == 'xy'\n")
    return "mod.py", 2


def f5_named_misdirection(root):
    """The failing test module's name matches an INNOCENT file (bounds.py),
    while the defect lives in mod.py. Assertion-only, so SIGHT is reached and
    the circumstantial NAMED lane has something wrong to say."""
    _w(root, "mod.py", BUGGY)
    _w(root, "bounds.py", SIB_B)
    _w(root, "totals.py", SIB_C)
    _w(root, "test_bounds.py",
       "from mod import count_above\nfrom bounds import clamp\n"
       "from totals import total\n\n"
       "def test_bounds_behaviour():\n"
       "    assert clamp(5, 0, 9) == 5 and total([1, 2]) == 3\n"
       "    assert count_above([1, 5, 5, 9], 5) == 1\n")
    return "mod.py", 4


ALL = {
    "F1-single-assert": f1_single_assert,
    "F2-single-traceback": f2_single_traceback,
    "F3-multi-assert": f3_multi_assert,
    "F4-multi-traceback": f4_multi_traceback,
    "F5-named-misdirection": f5_named_misdirection,
}


def f6_order_sensitive(root):
    """Built to make the two laws' ORDER matter, which none of F1..F5 does.

    The failing test MODULE is test_bounds.py, so the caller's affinity
    tie-break puts the innocent bounds.py first in FILE order.  The failing
    test FUNCTION is test_count_above, so the RANK law's NAMED bit fires on
    mod.py's defect line (enclosing def count_above shares both tokens) and
    on nothing in bounds.py.  File-outer therefore searches bounds.py first;
    line-outer would reach the defect line first."""
    _w(root, "mod.py", BUGGY)
    _w(root, "bounds.py", SIB_B)
    _w(root, "totals.py", SIB_C)
    _w(root, "test_bounds.py",
       "from mod import count_above\nfrom bounds import clamp\n"
       "from totals import total\n\n"
       "def test_count_above():\n"
       "    assert clamp(5, 0, 9) == 5 and total([1, 2]) == 3\n"
       "    assert count_above([1, 5, 5, 9], 5) == 1\n")
    return "mod.py", 4


ALL["F6-order-sensitive"] = f6_order_sensitive
