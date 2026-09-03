# SPDX-License-Identifier: AGPL-3.0-or-later
"""A suite that does not RUN must never be judged as a failing suite.

Found on SQLAlchemy 2.1 (2026-09-02): its pytest plugin collects 1,466 tests
with `-p no:cacheprovider` and ZERO with the cache provider on. fluidfix's
fail-fast gate enables the cache so `--lf` works, so the suite silently
collected nothing, every candidate scored red, and a 21-minute guard run
ended in "REFUSED: fault is outside the taught vocabulary" — when the truth
was that the harness never ran a single test.
"""
import sys

import pytest

from fluidfix import Oracle
from fluidfix.oracle import HarnessError


def test_no_tests_collected_raises_harness_error_not_red(tmp_path):
    (tmp_path / "mod.py").write_text("def f():\n    return 1\n")   # no tests
    oracle = Oracle(str(tmp_path), python=sys.executable)
    with pytest.raises(HarnessError) as e:
        oracle.failing_output()
    assert "NO TESTS" in str(e.value)
    assert "nothing can be judged" in str(e.value)


def test_green_raises_but_check_rejects(tmp_path):
    # green()/failing_output() judge the PROJECT's own tree: a dead harness
    # there is unjudgeable and must raise. check() always has a CANDIDATE
    # applied, so the same symptom is the candidate's fault — reject it and
    # keep searching rather than aborting the run.
    (tmp_path / "mod.py").write_text("def f():\n    return 1\n")
    oracle = Oracle(str(tmp_path), python=sys.executable)
    with pytest.raises(HarnessError):
        oracle.green()
    ok, why = oracle.check()
    assert ok is False and "candidate applied" in why


def test_candidate_caused_harness_failure_rejects_not_aborts(tmp_path):
    # A candidate in the tree owns whatever pytest chokes on. Measured on
    # SQLAlchemy 2026-09-02: a candidate triggered pytest exit 3 and the
    # whole run aborted, when the honest outcome is "this candidate is bad".
    (tmp_path / "mod.py").write_text("def f():\n    return 1\n")
    (tmp_path / "test_mod.py").write_text(
        "from mod import f\n\ndef test_f():\n    assert f() == 2\n")
    oracle = Oracle(str(tmp_path), python=sys.executable)
    oracle.failing_output()                     # baseline is legitimately red
    # now make the FULL run fail as a usage error, as a bad candidate would
    oracle.extra_args = ["--not-a-real-flag"]
    oracle._fastgate_ok = False
    ok, why = oracle.check()
    assert ok is False and "candidate applied" in why   # rejected, not raised


def test_a_real_failing_suite_is_still_just_red(tmp_path):
    # exit 1 must stay a normal red suite — this fix must not over-trigger
    (tmp_path / "mod.py").write_text("def f():\n    return 1\n")
    (tmp_path / "test_mod.py").write_text(
        "from mod import f\n\ndef test_f():\n    assert f() == 2\n")
    oracle = Oracle(str(tmp_path), python=sys.executable)
    fails, out = oracle.failing_output()
    assert fails
    ok, why = oracle.check()
    assert not ok and "test_f" in why


def test_budget_refusal_does_not_blame_the_vocabulary():
    """A refusal must name the right cause.

    Measured on click 2026-09-02: a taught constant-drift class had just
    repaired two instances of that class, and the third was reported as
    "fault is outside the taught vocabulary" — when the truth was that the
    defect file was never opened before the clock ran out. That message
    sends the user to write a rule they already have.
    """
    from fluidfix.guard import GuardReport

    # The termui incident had POINTING evidence: the asserted literal 95
    # occurred in exactly one file. That is what makes it a SEARCH limit
    # rather than an evidence gap — with nothing pointing, a bigger budget
    # re-searches the same arbitrary order (see test_refusal_diagnosis.py).
    starved = GuardReport(
        status="refused", candidates=["a.py", "b.py"], attempts=[{"x": 1}],
        evidence={"pointed": ["src/click/termui.py"]},
        hint="escalation budget exhausted (600s) with CAPPED still ruling "
             "RAISE_BUDGET — raise --escalate-budget")
    s = starved.summary()
    assert "SEARCH limit" in s
    assert "not a gap in the taught vocabulary" in s
    assert "outside the taught vocabulary" not in s.split("hint:")[0]

    genuine = GuardReport(status="refused", candidates=["a.py"],
                          hint="every generated candidate was rejected")
    assert "outside the taught vocabulary" in genuine.summary()
