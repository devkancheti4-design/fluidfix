"""Shared fixtures for 47-reshape-actuation.

Five git scenarios, all built under ./work/ (this agent's own directory).
Nothing outside this directory is written; no git command touches the
fluidfix repo itself.
"""
import os
import shutil
import subprocess
import sys
import textwrap

sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")

from fluidfix import Oracle                     # noqa: E402
from fluidfix.acts import Observation           # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(HERE, "work")
PY = "/Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python"

# ---------------------------------------------------------------- sources --
# NOTE ON CANDIDATE DIRECTION (measured, see candidate_probe.out): the
# literal-off-by-one act emits exactly ONE candidate and it DECREMENTS. So a
# defect whose repair is "10" must be spelled "11" in the working tree.
def _gate(pred):
    return textwrap.dedent(f"""\
        def gate(n):
            if {pred}:
                return "open"
            return "shut"
    """)


GATE_TEST = textwrap.dedent("""\
    from mod import gate

    def test_open():
        assert gate(10) == "open"

    def test_shut():
        assert gate(9) == "shut"
""")
# "n > 9" and "n >= 10" are THE SAME PROGRAM SPELLED TWICE — loop.py:212-215
# says in as many words that this is not ambiguity.
GATE_HEAD_GT9 = _gate("n > 9")            # correct, spelling A
GATE_HEAD_GE10 = _gate("n >= 10")         # correct, spelling B
GATE_BUG_GT10 = _gate("n > 10")           # defect: strictness + literal both signal
GATE_BUG_GE11 = _gate("n >= 11")          # defect repaired ONLY by decrementing

DELTA_FIXED = textwrap.dedent("""\
    def apply_delta(base, delta):
        return base + delta
""")
DELTA_BUG = DELTA_FIXED.replace("base + delta", "base - delta")
# WEAK suite: 0 - 5 != 5, so it is red; but delta - base ALSO greens it.
DELTA_TEST = textwrap.dedent("""\
    from mod import apply_delta

    def test_apply():
        assert apply_delta(0, 5) == 5
""")

# Pins are NOT part of the oracle's suite. They judge the shipped program
# after the fact, the way a reviewer would.
PINS = {
    "gate": ("def _pin(m):\n"
             "    return (m.gate(10) == 'open' and m.gate(9) == 'shut'\n"
             "            and m.gate(11) == 'open' and m.gate(0) == 'shut')\n"),
    "delta": ("def _pin(m):\n"
              "    return m.apply_delta(3, 4) == 7 and m.apply_delta(10, 1) == 11\n"),
}


def _git(root, *args):
    return subprocess.run(["git", "-C", root, *args],
                          capture_output=True, text=True)


def make_repo(name, head_src, work_src, test_src, git=True):
    """HEAD gets head_src; the working tree gets work_src."""
    root = os.path.join(WORK, name)
    shutil.rmtree(root, ignore_errors=True)
    os.makedirs(root)
    open(os.path.join(root, "mod.py"), "w").write(head_src)
    open(os.path.join(root, "test_mod.py"), "w").write(test_src)
    if git:
        _git(root, "init", "-q")
        _git(root, "config", "user.email", "r47@local")
        _git(root, "config", "user.name", "r47")
        _git(root, "add", "-A")
        _git(root, "commit", "-qm", "seed")
    open(os.path.join(root, "mod.py"), "w").write(work_src)
    return root, Oracle(root, python=PY)


def pin_ok(root, which):
    """Run the reviewer's pin against whatever mod.py now holds."""
    src = open(os.path.join(root, "mod.py")).read() + "\n" + PINS[which]
    ns = {}
    try:
        exec(compile(src, "mod.py", "exec"), ns)
        return bool(ns["_pin"](type("M", (), ns)))
    except Exception as e:                                   # noqa: BLE001
        return f"pin raised {type(e).__name__}: {e}"


def head_line(root, lineno):
    p = _git(root, "show", "HEAD:mod.py")
    if p.returncode != 0:
        return None
    return p.stdout.split("\n")[lineno - 1]


# name -> (head_src, work_src, test_src, lineno, kinds, pin, blurb)
SCENARIOS = {
    "G1_bug_committed": (
        GATE_BUG_GT10, GATE_BUG_GT10, GATE_TEST, 2, [0, 1], "gate",
        "the ordinary case: the defect is IN HEAD (fluidfix's whole purpose)"),
    "G2_uncommitted_exact": (
        GATE_HEAD_GE10, GATE_BUG_GE11, GATE_TEST, 2, [1], "gate",
        "provenance case: defect never committed, repair reproduces HEAD"),
    "G3_uncommitted_respelled": (
        GATE_HEAD_GT9, GATE_BUG_GT10, GATE_TEST, 2, [0, 1], "gate",
        "defect never committed; first green is the SAME PROGRAM SPELLED "
        "DIFFERENTLY from HEAD"),
    "G4_no_git": (
        GATE_HEAD_GT9, GATE_BUG_GT10, GATE_TEST, 2, [0, 1], "gate",
        "no git repository at all"),
    "G5_wrong_program": (
        DELTA_FIXED, DELTA_BUG, DELTA_TEST, 2, [2, 3], "delta",
        "weak suite: first green is a DIFFERENT PROGRAM at the same site"),
}


def build(name):
    head, work, test, lineno, kinds, pin, blurb = SCENARIOS[name]
    root, oracle = make_repo(name, head, work, test, git=(name != "G4_no_git"))
    return root, oracle, [Observation(lineno=lineno, kinds=list(kinds))], pin, blurb
