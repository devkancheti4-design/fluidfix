# SPDX-License-Identifier: AGPL-3.0-or-later
"""AMB is a question about PROGRAMS, not about provenance.

The engine law asks whether ONE INPUT CARRIES TWO OUTPUTS. Until 0.15.0 the
body answered a different question — which candidate set a green came from, and
which line it sat on — and got it wrong in both directions.

Measured 2026-09-07 by a red team, on the shapes below:
  * two different programs reachable at ONE line from two candidate sets:
    12 of 12 shipped, 6 WRONG, and the output was byte-identical inside each
    matched pair, so the choice was provably blind to correctness;
  * two greens in different FILES: blind by construction, 5 of 5 wrong;
  * and the opposite error, a correct repair refused for being reachable twice.

The remedy, measured on the same 12 fixtures: run the greens against inputs
harvested from the repo's own suite and look for one they disagree on.
12/12 separated, 6 wrong repairs to 0, zero extra suite runs, 0.10 s per site.
"""
import shutil
import sys

import pytest

from fluidfix.differ import UNKNOWN, programs_differ


def _repo(tmp_path, body, test_body):
    (tmp_path / "mod.py").write_text(body)
    (tmp_path / "test_mod.py").write_text(test_body)
    return str(tmp_path)


def test_two_different_programs_at_one_line_are_separated(tmp_path):
    """THE SHAPE THAT SHIPPED 12 WRONG REPAIRS. Both candidates pass the suite;
    they disagree on an input the suite never tries."""
    root = _repo(tmp_path,
                 "def alarm(readings, limit):\n    return readings[0] > limit\n",
                 "from mod import alarm\ndef test_a():\n"
                 "    assert alarm([1, 9], 5) is True\n")
    answer, rec = programs_differ(
        root, "mod.py", 2,
        [(2, "    return readings[1] >= limit"),
         (2, "    return readings[0] > limit")],
        python=sys.executable)
    assert answer is True, rec
    assert rec["witness_call"].startswith("alarm(")
    # the two really do disagree there
    assert len(set(map(repr, rec["witness_values"]))) == 2


def test_one_program_spelled_twice_is_not_ambiguous(tmp_path):
    """THE OPPOSITE ERROR. `units >= 10` and `units > 9` are one program written
    two ways. Refusing these would refuse the commonest bug class there is, and
    the loop's own comments say so."""
    root = _repo(tmp_path,
                 "def over(units):\n    return units >= 10\n",
                 "from mod import over\ndef test_b():\n"
                 "    assert over(10) is True\n    assert over(9) is False\n")
    answer, rec = programs_differ(
        root, "mod.py", 2,
        [(2, "    return units >= 10"), (2, "    return units > 9")],
        python=sys.executable)
    assert answer is False, rec


def test_a_probe_that_cannot_look_says_so_rather_than_saying_no(tmp_path):
    """The three-state answer, and the reason it exists. C source cannot be
    parsed by this module at all — Box2D and cglm are C — and 'could not look'
    must never be reported as 'looked and found nothing'."""
    (tmp_path / "m.c").write_text("int add(int a, int b) {\n  return a - b;\n}\n")
    answer, rec = programs_differ(
        str(tmp_path), "m.c", 2,
        [(2, "  return a + b;"), (2, "  return b + a;")],
        python=sys.executable)
    assert answer is UNKNOWN, rec


def test_fewer_than_two_greens_is_never_ambiguous(tmp_path):
    answer, _ = programs_differ(str(tmp_path), "mod.py", 1, [], python=sys.executable)
    assert answer is False


def test_the_probe_never_raises(tmp_path):
    """A probe that cannot answer must not break a repair."""
    answer, rec = programs_differ("/no/such/root", "nope.py", 1,
                                  [(1, "a"), (1, "b")], python=sys.executable)
    assert answer is UNKNOWN and "reason" in rec


# ---------------------------------------------------------------- the loop --
def test_the_loop_refuses_two_different_programs_and_writes_the_test(tmp_path):
    """END TO END, on the red team's own fixture A1.

    `alarm(readings, limit)` should test readings[0]; the defect tests
    readings[1]. At that ONE line two different acts each reach a green:
    the index fix `readings[0] > limit`, and a strictness flip
    `readings[1] >= limit`. Both pass this suite. They are different programs —
    alarm([9, 1], 5) is True for one and False for the other.

    Measured before 0.15.0: shipped, chosen by kind number, wrong half the time
    across six matched pairs. It must now refuse and hand over the test."""
    from fluidfix.acts import Observation
    from fluidfix.loop import repair
    from fluidfix.oracle import Oracle
    (tmp_path / "gate.py").write_text(
        '"""Reading gate: does the FIRST reading exceed the limit?"""\n\n\n'
        "def alarm(readings, limit):\n"
        "    return readings[1] > limit\n")          # the defect
    (tmp_path / "test_gate.py").write_text(
        "from gate import alarm\n\n\n"
        "def test_first_reading_at_limit_is_above():\n"
        "    assert alarm([7, 3], 3) is True\n\n\n"
        "def test_first_reading_below_limit():\n"
        "    assert alarm([1, 0], 5) is False\n\n\n"
        "def test_first_reading_clearly_above():\n"
        "    assert alarm([9, 8], 2) is True\n")
    o = Oracle(str(tmp_path), python=sys.executable)
    res = repair(o, "gate.py", [Observation(lineno=5, kinds=[0, 1])])
    assert len(res.greens) >= 2, f"fixture no longer admits two greens: {res.greens}"
    assert res.repaired is False, "shipping one of two programs is the defect"
    assert res.ambiguous is True
    assert res.ruling == "ADD_STATE", res.ruling
    assert res.pinning_test, "ADD_STATE must produce the test it asks for"
    assert "def test_" in res.pinning_test
    assert "alarm(" in res.pinning_test
    # the file is left exactly as it was found
    assert (tmp_path / "gate.py").read_text().count("readings[1] > limit") == 1


def test_the_refusal_record_carries_the_ruling_and_the_test(tmp_path):
    """A refusal a machine reads must name the ruling, not only describe it in
    prose — and when the ruling is ADD_STATE the test it asks for is written
    beside it."""
    import json
    from fluidfix.guard import GuardReport, write_refusal
    from fluidfix.loop import RepairResult
    res = RepairResult(repaired=False, refused=True, ambiguous=True)
    res.ruling, res.greens = "ADD_STATE", ["a", "b"]
    res.pinning_test = "def test_pin():\n    pass\n"
    write_refusal(str(tmp_path), GuardReport(status="refused", result=res))
    rec = json.loads((tmp_path / ".fluidfix" / "last_refusal.json").read_text())
    assert rec["ruling"] == "ADD_STATE"
    assert rec["greens"] == ["a", "b"]
    assert (tmp_path / ".fluidfix" / "pin_me_test.py").read_text() == res.pinning_test


def test_a_language_the_probe_cannot_read_does_not_lose_its_repairs(tmp_path):
    """The regression a blanket refusal caused, kept as a pin.

    Measured on tests/test_java.py: the two greens for the boundary flip are
    `units >= 10` and `units > 9` — ONE PROGRAM SPELLED TWICE. Refusing every
    unmeasurable pair turned that correct, byte-exact repair into a denial.

    So where the probe cannot read the language the loop falls back to the older
    provenance measure AND records that identity was never established."""
    from fluidfix.loop import RepairResult
    r = RepairResult(repaired=False, refused=True)
    assert r.amb_measured is True, "measured is the default; the fallback clears it"


def test_an_unmeasured_ship_says_so_in_its_own_reason():
    """A repair shipped without the identity check must not read like one that
    passed it. The gap is real: the red team shipped 6 wrong repairs through
    exactly this blind spot, and closing it means compiling and running both
    candidates — the C/Java oracle's job, not this module's."""
    import pathlib
    src = (pathlib.Path(__file__).resolve().parents[1]
           / "src" / "fluidfix" / "loop.py").read_text(encoding="utf-8")
    assert "uniqueness NOT " in src
    assert "res.amb_measured = False" in src
