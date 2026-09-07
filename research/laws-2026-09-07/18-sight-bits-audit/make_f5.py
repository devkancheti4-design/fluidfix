#!/usr/bin/env python
"""Build fixture f5_framed_coincidence.

Purpose: show what the body's FRAMED measurement (guard.py:281) actually
reads. The law's spec is "the failing traceback names this file"; the body
measures "some .py path anywhere in the failing output has the same
BASENAME as this candidate".

The fixture is a package whose failing test raises json.JSONDecodeError, so
the traceback names the STDLIB files json/__init__.py and json/decoder.py.
Both are outside oracle.root, so guard.py:136 drops them from `ordered` and
the SIGHT law path is taken (that is the only path where the law is
consulted at all). But `framed_files` (guard.py:218) keeps their BASENAMES,
and the package deliberately contains pkg/decoder.py -- a large file that
every test executes (UBIQUITOUS) and that contains no defect.

Every module carries the same nine-signal ballast so that each KINDS signal
matches all six modules; SCARCE (<=2 files) therefore cannot fire for
anybody, and the failure is not an assert so LITERAL cannot fire. The only
POINTING bit available in the whole fixture is FRAMED, and it lands on the
wrong file.

Usage:  .venv/bin/python make_f5.py
"""
import os
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "fixtures", "f5_framed_coincidence")

# Nine-signal ballast: makes every acts.KINDS signal regex match EVERY
# module, so no signal matches <=2 files and SCARCE stays empty everywhere.
BALLAST = '''
_BAL = 10


def _b_cmp(a, b):
    return a <= b


def _b_add(a, b):
    return a + b


def _b_sub(a, b):
    return a - b


def _b_mm(a, b):
    return min(a, b)


def _b_aug(a):
    a += 1
    return a


def _b_lt(a, b):
    return a < b


_BAL_OK = True
'''


def w(rel, text):
    p = os.path.join(ROOT, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(text)


def main():
    if os.path.isdir(ROOT):
        shutil.rmtree(ROOT)
    os.makedirs(ROOT)

    w("pytest.ini", "[pytest]\ntestpaths = tests\n")

    # every module is imported by the package, so every module lands in the
    # failing test's coverage and is therefore a SIGHT candidate
    w("pkg/__init__.py", '"""package"""\n'
      "from . import decoder, geom, fmtx, poolx, tablex  # noqa: F401\n"
      + BALLAST)

    # THE TRUE DEFECT. Only the failing test executes it -> specificity 1.0
    # -> FAILONLY; few executed lines -> SMALL. No pointing bit at all.
    w("pkg/geom.py", '"""the defect lives here"""\n'
      "\n"
      "def wrap(s):\n"
      '    return "[" + s + "]"\n'
      "\n"
      "\n"
      "def emit(n):\n"
      '    return ",".join(str(i) for i in range(n))\n'
      "\n"
      "\n"
      "def build():\n"
      "    return wrap(emit(3))[1:]\n"      # DEFECT: should be [0:]
      + BALLAST)

    # THE DECOY. Basename collides with the stdlib json/decoder.py that the
    # JSONDecodeError traceback names. Huge body executed only by the
    # passing test -> specificity well under 0.25 -> UBIQUITOUS.
    deep = "\n".join(f"    v{i} = v{i - 1} + 1" for i in range(1, 61))
    w("pkg/decoder.py", '"""not the defect; just shares a name with json/decoder.py"""\n'
      "\n"
      "def deep():\n"
      "    v0 = 0\n"
      + deep + "\n"
      "    return v60\n"
      + BALLAST)

    for name in ("fmtx", "poolx", "tablex"):
        w(f"pkg/{name}.py", f'"""filler module {name}"""\n' + BALLAST)

    w("tests/__init__.py", "")
    # failing test: build() returns malformed JSON, stdlib json raises, so
    # the traceback names ONLY the test file and two stdlib files.
    w("tests/test_shape.py",
      "import json\n"
      "from pkg.geom import build\n"
      "\n"
      "\n"
      "def test_shape():\n"
      "    assert json.loads(build()) == [0, 1, 2]\n")
    # passing test: drives decoder.deep() so the full suite executes far
    # more of pkg/decoder.py than the failing test does -> UBIQUITOUS.
    w("tests/test_deep.py",
      "from pkg.decoder import deep\n"
      "\n"
      "\n"
      "def test_deep():\n"
      "    assert deep() == 60\n")

    print("built", ROOT)


if __name__ == "__main__":
    main()
