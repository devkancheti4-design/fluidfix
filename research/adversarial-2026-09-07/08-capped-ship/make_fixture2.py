#!/usr/bin/env python
"""Variant 2: the OTHER route to Packet.truncated -- the SPREAD SAMPLE.

Variant 1 (make_fixture.py) trips `filtered`: the true defect line carries no
signal token so build_packet's filter drops it. Variant 2 trips the other
branch: every anchor carries a signal token, but there are more than
max_lines of them, so the stride sample at localize.py:178-179 keeps only 110
of them and the true defect line is one of the ones it steps over.

Same consequence: Packet.truncated=True (guard.py:508 latches CAPPED) and the
line that carries the real repair is never observed.

Usage:  python make_fixture2.py [PAD] [DEST]
"""
import os
import shutil
import string
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PAD = int(sys.argv[1]) if len(sys.argv) > 1 else 60
DEST = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 \
    else os.path.join(HERE, "fixture2")

BROKEN_B = "    return min(low * SCALE, high * SCALE)"
CORRECT_B = "    return max(low * SCALE, high * SCALE)"


def consts(n, prefix):
    names = [f"{prefix}_{a}{b}" for a in string.ascii_lowercase
             for b in string.ascii_lowercase][:n]
    return "".join(f"{nm} = 4\n" for nm in names)


def geom(pad):
    return (
        '"""Layout geometry helpers for the channel mixer."""\n\n'
        "SCALE = 1\nGUTTER = 8\nMARGIN = 4\n\n"
        + consts(pad, "lo") +
        "\n\ndef peak(low, high):\n"
        '    """The larger of the two channel peaks."""\n'
        + BROKEN_B + "\n\n\n"
        "def headroom(ceiling, low, high):\n"
        '    """Distance from the ceiling to the louder channel."""\n'
        "    return ceiling + peak(low, high)\n\n\n"
        "def gutter_span(count):\n"
        "    return GUTTER * count + MARGIN\n\n\n"
        + consts(140 - pad, "hi")
    )


TEST = '''from pkg.geom import headroom


def test_headroom_uses_the_louder_channel():
    assert headroom(0, -3, 3) == 3
'''
TEST2 = '''from pkg.geom import gutter_span


def test_gutter_span():
    assert gutter_span(3) == 28
'''


def main(pad=PAD, dest=DEST):
    if os.path.exists(dest):
        shutil.rmtree(dest)
    os.makedirs(os.path.join(dest, "pkg"))
    os.makedirs(os.path.join(dest, "tests"))
    src = geom(pad)
    open(os.path.join(dest, "pkg", "__init__.py"), "w").write("")
    open(os.path.join(dest, "pkg", "geom.py"), "w").write(src)
    open(os.path.join(dest, "tests", "test_headroom.py"), "w").write(TEST)
    open(os.path.join(dest, "tests", "test_gutter.py"), "w").write(TEST2)
    open(os.path.join(dest, "pytest.ini"), "w").write(
        "[pytest]\ntestpaths = tests\npythonpath = .\n")
    open(os.path.join(dest, ".gitignore"), "w").write("*\n")
    raw = src.split("\n")
    return (raw.index(BROKEN_B) + 1,
            raw.index("    return ceiling + peak(low, high)") + 1)


if __name__ == "__main__":
    b, a = main()
    print(f"built {DEST} pad={PAD}  LINE_B={b}  LINE_A={a}")
