#!/usr/bin/env python
"""Build the 08-capped-ship victim repo, deterministically, from scratch.

The repo is a two-function layout helper plus filler. Two properties matter:

  1. `pkg/geom.py` has enough EXECUTED lines (>80) that build_packet's signal
     filter engages, and the true defect line carries no signal token, so the
     filter drops it. That sets Packet.truncated -> guard.py:508 capped0=True.
  2. Exactly two single-line edits inside fluidfix's own vocabulary turn the
     suite green:
        LINE_B  `return min(low, high)`  -> `max`   the TRUE repair
        LINE_A  `return ceiling + peak(...)` -> `-` a COMPENSATING repair,
                                                   correct only for the one
                                                   tested input
     LINE_B is the one the filter drops. So the cut-short search can only
     find LINE_A, ships it alone, and the report says BUILT -> SHIP.

Usage:  python make_fixture.py [DEST]      (default: ./fixture, wiped first)
"""
import os
import shutil
import string
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEST = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(HERE, "fixture")

# ---------------------------------------------------------------- geom.py --
# `peak` and `headroom` are the only functions the failing test executes.
# Everything after the marker is filler whose `def` lines are executed at
# import (so they are coverage anchors) and whose bodies are not.
HEAD = '''"""Layout geometry helpers for the channel mixer."""

MARGIN = 4
GUTTER = 8
TRACKS = 2


def peak(low, high):
    """The larger of the two channel peaks."""
    return min(low, high)


def headroom(ceiling, low, high):
    """Distance from the ceiling to the louder channel."""
    return ceiling + peak(low, high)


def gutter_span(count):
    return GUTTER * count + MARGIN


'''

CORRECT_B = "    return max(low, high)"
BROKEN_B = "    return min(low, high)"


def filler(n):
    names = []
    for a in string.ascii_lowercase:
        for b in string.ascii_lowercase:
            names.append(f"pad_{a}{b}")
            if len(names) == n:
                break
        if len(names) == n:
            break
    out = []
    for nm in names:
        out.append(f"def {nm}(value):\n    return value\n\n")
    return "\n".join(out)


GEOM = HEAD + filler(110)

TEST = '''from pkg.geom import headroom


def test_headroom_uses_the_louder_channel():
    # ceiling 0, channels at -3 and +3: the louder channel is +3.
    assert headroom(0, -3, 3) == 3
'''

# A second, always-green test that pins nothing about `peak` — it exists so
# the suite is a suite, not a single assertion.
TEST2 = '''from pkg.geom import gutter_span


def test_gutter_span():
    assert gutter_span(3) == 28
'''


def main():
    if os.path.exists(DEST):
        shutil.rmtree(DEST)
    os.makedirs(os.path.join(DEST, "pkg"))
    os.makedirs(os.path.join(DEST, "tests"))
    os.makedirs(os.path.join(HERE, "pristine"), exist_ok=True)

    with open(os.path.join(DEST, "pkg", "__init__.py"), "w") as f:
        f.write("")
    with open(os.path.join(DEST, "pkg", "geom.py"), "w") as f:
        f.write(GEOM)
    # the pristine (correct) source, kept OUTSIDE the repo for byte comparison
    with open(os.path.join(HERE, "pristine", "geom.py"), "w") as f:
        f.write(GEOM.replace(BROKEN_B, CORRECT_B))
    with open(os.path.join(DEST, "tests", "test_headroom.py"), "w") as f:
        f.write(TEST)
    with open(os.path.join(DEST, "tests", "test_gutter.py"), "w") as f:
        f.write(TEST2)
    with open(os.path.join(DEST, "pytest.ini"), "w") as f:
        f.write("[pytest]\ntestpaths = tests\npythonpath = .\n")
    # keep the fixture out of any enclosing git index
    with open(os.path.join(DEST, ".gitignore"), "w") as f:
        f.write("*\n")

    src = open(os.path.join(DEST, "pkg", "geom.py")).read().split("\n")
    b = next(i for i, l in enumerate(src, 1) if l == BROKEN_B)
    a = next(i for i, l in enumerate(src, 1)
             if l.strip() == "return ceiling + peak(low, high)")
    print(f"built {DEST}")
    print(f"  geom.py: {len(src)} lines")
    print(f"  LINE_B (true defect, filter-invisible) = {b}: {src[b-1]!r}")
    print(f"  LINE_A (compensating site)             = {a}: {src[a-1]!r}")


if __name__ == "__main__":
    main()
