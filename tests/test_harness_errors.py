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


def test_green_and_check_also_refuse_to_judge_a_dead_harness(tmp_path):
    (tmp_path / "mod.py").write_text("def f():\n    return 1\n")
    oracle = Oracle(str(tmp_path), python=sys.executable)
    with pytest.raises(HarnessError):
        oracle.green()
    with pytest.raises(HarnessError):
        oracle.check()


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
