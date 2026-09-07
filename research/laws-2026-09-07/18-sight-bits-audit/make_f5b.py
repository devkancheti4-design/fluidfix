#!/usr/bin/env python
"""f5b = f5 with the decoy renamed pkg/decoder.py -> pkg/dcodr.py.

Nothing else changes: same defect, same coverage shape, same ballast. The
ONLY difference is that the decoy's basename no longer collides with the
stdlib json/decoder.py that the traceback names. Any difference in file
order or suite-run count is therefore attributable to the FRAMED
measurement at guard.py:281 and to nothing else.

Usage:  .venv/bin/python make_f5b.py    (run make_f5.py first)
"""
import os
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "fixtures", "f5_framed_coincidence")
DST = os.path.join(HERE, "fixtures", "f5b_no_collision")


def main():
    if os.path.isdir(DST):
        shutil.rmtree(DST)
    shutil.copytree(SRC, DST, ignore=shutil.ignore_patterns(
        ".pytest_cache", "__pycache__", ".fluidfix"))
    os.rename(os.path.join(DST, "pkg/decoder.py"),
              os.path.join(DST, "pkg/dcodr.py"))
    for rel in ("pkg/__init__.py", "tests/test_deep.py"):
        p = os.path.join(DST, rel)
        t = open(p, encoding="utf-8").read().replace("decoder", "dcodr")
        open(p, "w", encoding="utf-8").write(t)
    print("built", DST)


if __name__ == "__main__":
    main()
