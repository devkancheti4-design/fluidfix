#!/usr/bin/env python
"""Build the fixtures the SIGHT-bits audit probes. Writes ONLY under
research/laws-2026-09-07/18-sight-bits-audit/fixtures/. Git repos created
here are fresh nested repos inside this directory; the fluidfix repo's own
git state is never touched.

    f1_canonical   tests/test_guard.py's BUGGY fixture (mod.py + test_mod.py),
                   no git                      -> the body's canonical no-frame case
    f1_git         same, git-initialised, 1 commit -> TOUCHED reachable
    f2_multi       6-module package, 41 commits touching only fmt.py, a
                   failing assertion carrying the literal 40 that occurs in
                   exactly one source file          -> every bit except FRAMED
    f3_framed      the failing test calls json.loads() on a string a defective
                   pkg/render.py produced; the traceback names ONLY stdlib
                   json/__init__.py and json/decoder.py, and the package has
                   its own __init__.py and decoder.py  -> FRAMED on the law path
    f4_tiebreak    two files both at priority 0 (SCARCE); one has specificity
                   1.0 and no name overlap, the other 0.25 and NAMED
"""
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FX = os.path.join(HERE, "fixtures")

BUGGY = ("def count_above(xs, t):\n    n = 0\n    for x in xs:\n"
         "        if x >= t:\n            n += 1\n    return n\n")
TEST = ("from mod import count_above\n\ndef test_c():\n"
        "    assert count_above([1, 5, 5, 9], 5) == 1\n")


def w(root, rel, text):
    p = os.path.join(root, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f:
        f.write(text)


def git(root, *args):
    subprocess.run(["git", "-C", root, *args], check=True,
                   capture_output=True, text=True)


def git_init(root):
    git(root, "init", "-q")
    git(root, "config", "user.email", "audit@test")
    git(root, "config", "user.name", "audit")
    git(root, "config", "commit.gpgsign", "false")


def f1(root, with_git):
    w(root, "mod.py", BUGGY)
    w(root, "test_mod.py", TEST)
    if with_git:
        git_init(root)
        git(root, "add", "-A")
        git(root, "commit", "-qm", "seed (bug included)")


def f2(root):
    # pkg/__init__.py — executed by every test (imports everything)
    w(root, "pkg/__init__.py",
      "from .core import compute\nfrom .util import clamp\n"
      "from .fmt import label\nfrom .big import table\n"
      "from .consts import A0\nfrom .mid import M0, walk\n")
    # core.py — the defect file. Literal 40 occurs ONLY here. Uses min( so the
    # minmax-swap signal (\b(?:min|max)\() matches here and in util.py only.
    w(root, "pkg/core.py",
      "def compute(xs):\n    total = sum(xs)\n    return min(total, 40) + 1\n")
    # util.py — NAMED by the test module name (test_util_core.py); its body is
    # executed only by a passing test, so specificity < 0.9 here.
    w(root, "pkg/util.py",
      "def clamp(x, lo, hi):\n    y = max(lo, x)\n    z = min(y, hi)\n    return z\n")
    # fmt.py — the only file the last 40 commits touch (TOUCHED)
    w(root, "pkg/fmt.py",
      "def label(name):\n    text = str(name)\n    return text.upper()\n")
    # big.py — UBIQUITOUS: the failing test executes only its def line, the
    # passing tests execute the whole body
    body = "\n".join(f"    v{i} = n * {i}" for i in range(24))
    w(root, "pkg/big.py",
      f"def table(n):\n{body}\n    return [v0, v23]\n")
    # consts.py — 120 module-level statements: executed on import by the
    # failing test, so n_fail >= 80 and SMALL is OFF; specificity 1.0
    w(root, "pkg/consts.py",
      "\n".join(f"A{i} = {i}" for i in range(120)) + "\n")
    # mid.py — 100 module-level lines + a 100-line function executed only by
    # passing tests: specificity ~0.5, n_fail >= 80, no name overlap -> the
    # evidence-free class the law lands on priority 6
    head = "\n".join(f"M{i} = {i}" for i in range(100))
    walk = "\n".join(f"    acc = acc * 1 + M{i}" for i in range(100))
    w(root, "pkg/mid.py",
      f"{head}\n\n\ndef walk():\n    acc = 0\n{walk}\n    return acc\n")
    w(root, "tests/__init__.py", "")
    w(root, "tests/test_util_core.py",
      "from pkg import compute, clamp\n\n"
      "def test_compute():\n    assert compute([10, 20]) == 40\n\n"
      "def test_clamp():\n    assert clamp(5, 0, 3) == 3\n")
    w(root, "tests/test_others.py",
      "from pkg import table, label, walk\n\n"
      "def test_table():\n    assert table(2)[0] == 0\n\n"
      "def test_table2():\n    assert table(3)[1] == 69\n\n"
      "def test_label():\n    assert label('a') == 'A'\n\n"
      "def test_walk():\n    assert walk() == 4950\n")
    git_init(root)
    git(root, "add", "-A")
    git(root, "commit", "-qm", "seed")
    # 41 commits touching only fmt.py, so `git log -40 --name-only` lists
    # fmt.py alone and every other file falls outside the TOUCHED window
    for i in range(41):
        w(root, "pkg/fmt.py",
          f"def label(name):\n    text = str(name)  # rev {i}\n"
          "    return text.upper()\n")
        git(root, "add", "-A")
        git(root, "commit", "-qm", f"touch fmt {i}")


def f3(root):
    w(root, "pkg/__init__.py", "from .render import render\nfrom .decoder import parse\n")
    # defect: [1:] should be [0:] (shipped class 1, literal-off-by-one)
    w(root, "pkg/render.py",
      "def render(n):\n    s = '[' + ','.join(str(i) for i in range(n)) + ']'\n"
      "    return s[1:]\n")
    w(root, "pkg/decoder.py",
      "def parse(text):\n    return text.split(',')\n")
    w(root, "tests/__init__.py", "")
    w(root, "tests/test_render.py",
      "import json\nfrom pkg import render, parse\n\n"
      "def test_render_roundtrip():\n"
      "    assert json.loads(render(3)) == [0, 1, 2]\n\n"
      "def test_parse():\n    assert parse('a,b') == ['a', 'b']\n")


def f4(root):
    # alpha.py: executed entirely by the failing test, specificity 1.0, no
    # token shared with the test module name
    w(root, "alpha.py", "def f(x):\n    return x >= 1\n")
    # widget.py: only its def line runs under the failing test; the passing
    # test runs the body -> specificity 0.25; NAMED via test_widget.py
    w(root, "widget.py",
      "def g(x):\n    a = x + 1\n    b = a * 2\n    return b\n")
    w(root, "test_widget.py",
      "from alpha import f\nfrom widget import g\n\n"
      "def test_fail():\n    assert f(0) is True\n\n"
      "def test_pass():\n    assert g(1) == 4\n")


def main():
    if os.path.isdir(FX):
        shutil.rmtree(FX)
    for name, fn in (("f1_canonical", lambda r: f1(r, False)),
                     ("f1_git", lambda r: f1(r, True)),
                     ("f2_multi", f2), ("f3_framed", f3), ("f4_tiebreak", f4)):
        root = os.path.join(FX, name)
        os.makedirs(root)
        fn(root)
        print("built", root)


if __name__ == "__main__":
    main()
