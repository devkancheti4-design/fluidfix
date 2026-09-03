# SPDX-License-Identifier: AGPL-3.0-or-later
"""A refusal must name the RIGHT cause. There are three, and they need
opposite advice:

    vocabulary gap  files were searched, candidates generated, all rejected
                    -> teach the class
    search limit    a POINTING lane named a file, the clock ran out
                    -> a bigger budget genuinely helps
    evidence gap    nothing pointed anywhere; ranking was circumstantial
                    -> a bigger budget searches the same arbitrary order

Measured 2026-09-03 on click: a defect at types.py:499 hit the third case
and was reported as the second, sending the user to raise a budget that
could not have helped.
"""
from fluidfix.guard import GuardReport


def _refusal(hint="", evidence=None, candidates=("a.py", "b.py")):
    return GuardReport(status="refused", candidates=list(candidates),
                       hint=hint, evidence=evidence or {}).summary()


def test_vocabulary_gap_says_teach_it():
    s = _refusal(hint="every generated candidate was rejected by the suite")
    assert "outside the taught vocabulary" in s
    assert "teach it once" in s


def test_search_limit_when_something_pointed():
    s = _refusal(hint="escalation budget exhausted (600s)",
                 evidence={"pointed": ["src/pkg/mod.py"]})
    assert "SEARCH limit" in s
    assert "src/pkg/mod.py" in s
    assert "more clock genuinely helps" in s


def test_evidence_gap_does_not_blame_the_budget():
    """The types.py incident. A bigger budget cannot help, so the refusal
    must not ask for one."""
    s = _refusal(hint="escalation budget exhausted (600s)", evidence={})
    assert "nothing in the failure pointed at a file" in s
    assert "SEARCH limit" not in s
    assert "outside the taught vocabulary" not in s
    # and it must offer what actually helps
    assert "--file" in s


def test_evidence_gap_and_search_limit_are_mutually_exclusive():
    with_ev = _refusal(hint="budget exhausted", evidence={"pointed": ["x.py"]})
    without = _refusal(hint="budget exhausted", evidence={"pointed": []})
    assert ("SEARCH limit" in with_ev) != ("SEARCH limit" in without)


def test_attempts_are_still_reported_in_every_cause():
    for ev in ({}, {"pointed": ["x.py"]}):
        r = GuardReport(status="refused", candidates=["a.py"],
                        hint="budget exhausted", evidence=ev,
                        attempts=[{"line": 1}, {"line": 2}])
        assert "2 candidate(s) were tried" in r.summary()


def test_green_and_repaired_are_untouched():
    assert "nothing to do" in GuardReport(status="green").summary()
