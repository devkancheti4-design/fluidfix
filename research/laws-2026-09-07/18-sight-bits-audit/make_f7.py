#!/usr/bin/env python
"""f7_realframe: the failure DOES name a project source file.

This is the case the SIGHT law's FRAMED bit was specified for ("the failing
traceback names this file"). guard.py:146-150 returns the frame list before
reaching the law, so the expected result is `sight() calls: 0` -- the law is
never consulted on exactly the observation its first bit describes.

Usage:  .venv/bin/python make_f7.py && .venv/bin/python sight_probe.py \
            fixtures/f7_realframe 4
"""
import os
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "fixtures", "f7_realframe")


def w(rel, text):
    p = os.path.join(ROOT, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w", encoding="utf-8").write(text)


if __name__ == "__main__":
    if os.path.isdir(ROOT):
        shutil.rmtree(ROOT)
    os.makedirs(ROOT)
    w("pytest.ini", "[pytest]\ntestpaths = tests\n")
    w("pkg/__init__.py", "from . import geom  # noqa: F401\n")
    w("pkg/geom.py",
      "def ratio(xs):\n"
      "    return sum(xs) / (len(xs) - 1)\n")     # defect: raises on len 1
    w("tests/__init__.py", "")
    w("tests/test_ratio.py",
      "from pkg.geom import ratio\n"
      "\n"
      "\n"
      "def test_ratio():\n"
      "    assert ratio([4]) == 4\n")
    print("built", ROOT)
