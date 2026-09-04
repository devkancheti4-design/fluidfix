# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 devkancheti4-design
# Commercial licensing: see COMMERCIAL.md.
"""The oracle: the target project's own test suite, run safely.

Every flag here is a scar from a measured harness defect (see BENCHMARK.md in
fluid-router, plus two found while building this package):

  -B / PYTHONDONTWRITEBYTECODE + __pycache__ clearing
      Python validates .pyc on whole-second mtime + size; same-size rewrites
      made milliseconds apart re-import stale bytecode and score correct
      candidates as failures.
  -p no:benchmark
      pytest-benchmark collides with suites that define their own `benchmark`
      fixture; every run returns non-zero and an entire library scores zero.
  no -x on coverage runs
      pytest 9.1 + pytest-cov 7.1 silently write no JSON report when the
      session ends via exit-first.
  full-suite oracle, never a failing-node fast path
      parametrized node ids containing spaces truncate in -q output; the
      mangled id is a usage error that scores every candidate as a failure.
  per-candidate timeout
      an act that decrements a loop bound can make a candidate
      non-terminating; a candidate that will not terminate is a failed
      candidate, not a hung harness.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys

__all__ = ["Oracle", "HarnessError"]


class HarnessError(RuntimeError):
    """The suite did not RUN — so nothing can be judged.

    pytest distinguishes "tests failed" (exit 1) from "no tests collected"
    (5), "usage error" (4), "internal error" (3) and "interrupted" (2).
    Treating those as a red suite is unsafe: every candidate scores red, no
    repair can ever be accepted, and the guard reports "outside the taught
    vocabulary" when the truth is that the harness is misconfigured.

    Measured on SQLAlchemy 2.1 (2026-09-02): its pytest plugin collects
    1,466 tests with `-p no:cacheprovider` and ZERO with the cache provider
    enabled — so the coverage/--lf paths silently collected nothing and the
    guard searched for 21 minutes against a suite that never ran."""


# Exit 1 (tests failed) and exit 2 (interrupted — which is how a collection
# error from a broken module under test surfaces) are REAL red suites: an
# import-breaking regression must stay repairable. Only these mean the
# harness itself never produced a verdict.
_EXIT_MEANING = {
    3: "pytest hit an internal error",
    4: "pytest usage/configuration error",
    5: "pytest collected NO TESTS",
}


# `python -m pytest` with pytest absent exits 1 — indistinguishable, by exit
# code alone, from a genuine red suite. Measured 2026-09-03: `fluidfix
# estimate` on this very repo, run by the pipx interpreter, reported a
# confident 0.03s estimate and blamed the user's suite for being red. The
# suite had never run. Installing fluidfix and having the project's pytest
# on the SAME interpreter is the exception, not the rule.
_NO_PYTEST = "No module named pytest"


def _check_harness(rc: int, args: list, out: str, root: str,
                   python: str = "") -> None:
    if rc != 0 and _NO_PYTEST in out:
        raise HarnessError(
            "the interpreter running your suite has no pytest, so no test "
            "has been judged.\n"
            f"  interpreter: {python or '(the one fluidfix runs on)'}\n"
            "  fix: point fluidfix at your project's interpreter --\n"
            "       fluidfix ... --python /path/to/venv/bin/python\n"
            "  (or install pytest into the interpreter above)")
    if rc not in _EXIT_MEANING:
        return
    hint = ""
    if rc == 5:
        hint = (" — the suite collected nothing, so nothing can be judged. "
                "Common causes: wrong --python (project deps missing), a "
                "testpaths/plugin interaction (SQLAlchemy collects 0 unless "
                "`-p no:cacheprovider` is passed), or no tests in this root.")
    raise HarnessError(
        f"{_EXIT_MEANING[rc]} (exit {rc}) while running pytest in {root} "
        f"with {' '.join(args) or 'no extra args'}{hint}\n"
        f"--- last output ---\n{out.strip()[-600:]}")


# A GREEN EXIT CODE IS NOT ENOUGH. Measured on the C adapter 2026-09-04:
# given a test runner it was allowed to edit, the guard changed the harness's
# failing `return 1` to `return 0`, left the defect untouched, and declared
# success — while the output still read `test failed`. Any repair tool that
# can reach its own oracle will find that edit, because it is the cheapest
# path to green. Python is less exposed (`_is_test_path` keeps test files out
# of the candidate set) but the exposure is structural, not language-specific:
# a project may keep tests somewhere fluidfix does not recognise. So the exit
# code is cross-examined against what the run actually SAID.
_SUMMARY_FAIL = re.compile(r"\b(\d+) (failed|error(?:s|ed)?)\b")


def _still_reports_failures(out: str) -> str:
    """Non-empty when a run that exited 0 nonetheless reports failures."""
    for line in reversed(out.strip().splitlines()[-25:]):
        m = _SUMMARY_FAIL.search(line)
        if m and m.group(1) != "0":
            return m.group(0)
    return ""


class Oracle:
    def __init__(self, root: str, python: str | None = None,
                 timeout: int = 300, per_test_timeout: int = 60,
                 extra_args: list[str] | None = None):
        self.root = os.path.abspath(root)
        self.python = python or sys.executable
        self.timeout = timeout
        self.per_test_timeout = per_test_timeout
        self.extra_args = list(extra_args or [])
        self._fastgate_ok = True      # cleared if the harness cannot do --lf
        # probe the TARGET interpreter for pytest-timeout once
        try:
            self._has_timeout = subprocess.run(
                [self.python, "-c", "import pytest_timeout"],
                capture_output=True, timeout=30).returncode == 0
        except Exception:
            self._has_timeout = False

    def clear_pyc(self) -> None:
        for dp, dn, _ in os.walk(self.root):
            for d in list(dn):
                if d == "__pycache__":
                    shutil.rmtree(os.path.join(dp, d), ignore_errors=True)

    def run(self, args: list[str], cache: bool = False,
            timeout: int | None = None) -> tuple[int, str]:
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        cmd = [self.python, "-m", "pytest", "-q", "--no-header", "-p", "no:benchmark"]
        if not cache:
            cmd += ["-p", "no:cacheprovider"]
        if self._has_timeout:
            cmd += [f"--timeout={self.per_test_timeout}"]
        cmd += self.extra_args + args
        # pytest-cov drops its .coverage data file in root; a coverage-bearing
        # run must not leave a stray one behind in the guarded repo
        cov_data = os.path.join(self.root, ".coverage")
        stray = (any(a.startswith("--cov") for a in cmd)
                 and not os.path.exists(cov_data))
        try:
            p = subprocess.run(cmd, cwd=self.root, capture_output=True, text=True,
                               timeout=timeout or self.timeout, env=env)
            return p.returncode, p.stdout + p.stderr
        except subprocess.TimeoutExpired:
            return 1, "TIMEOUT"
        finally:
            if stray and os.path.exists(cov_data):
                try:
                    os.remove(cov_data)
                except OSError:
                    pass

    def green(self, timeout: int | None = None) -> bool:
        self.clear_pyc()
        rc, out = self.run(["--tb=no"], timeout=timeout)
        _check_harness(rc, self.extra_args, out, self.root, self.python)
        return rc == 0

    def _cov_installed(self) -> bool:
        if not hasattr(self, "_cov_probe"):
            try:
                self._cov_probe = subprocess.run(
                    [self.python, "-c", "import pytest_cov"],
                    capture_output=True, timeout=30).returncode == 0
            except Exception:
                self._cov_probe = False
        return self._cov_probe

    def check(self, timeout: int | None = None) -> tuple[bool, str]:
        """Candidate adjudication with WHY: (ok, first-failure line).

        FAIL-FAST, FULL-CONFIRM: the candidate first faces only the
        last-failed tests (--lf, ~10x cheaper) — a candidate that cannot
        even fix those is rejected on the spot, with the failing test
        harvested (engine law: REFUTED -> HARVEST_COUNTEREXAMPLE). Only a
        candidate that clears the fast gate runs the FULL suite, which
        remains the ONLY acceptance gate — soundness is untouched, the
        v0.7 span bench measured rejection cost dominating (32-candidate
        span sets x full 1,990-test runs busting every honest budget).
        A coverage fail-under gate is neutralized on the fast run only
        (subset coverage is meaningless); the full run keeps the repo's
        own configuration."""
        self.clear_pyc()
        fast = ["--lf", "--tb=no"]
        if self._cov_installed():
            fast.append("--cov-fail-under=0")
        if self._fastgate_ok:
            rc, out = self.run(fast, cache=True, timeout=timeout)
            if rc in _EXIT_MEANING:
                # The fast gate is an OPTIMIZATION, never a verdict. When a
                # project cannot support it, disable it and judge on the
                # full suite alone rather than failing the run over a
                # speedup. Measured on SQLAlchemy 2.1: its pytest plugin
                # collects 1,466 tests with `-p no:cacheprovider` and ZERO
                # with the cache provider that --lf requires.
                self._fastgate_ok = False
            elif rc != 0:
                why = next((l.strip() for l in out.splitlines()
                            if l.startswith(("FAILED", "ERROR"))), "")
                if not why:
                    tail = [l for l in out.strip().splitlines() if l.strip()]
                    why = tail[-1] if tail else "suite run produced no output"
                return False, why[:400]
        rc, out = self.run(["--tb=no"], timeout=timeout)
        if rc in _EXIT_MEANING:
            # A CANDIDATE is in the tree: whatever pytest just choked on is
            # attributable to the candidate, not the harness. Reject it and
            # keep searching — only baseline judgments (green/failing_output,
            # where the tree is the project's own) raise HarnessError.
            return False, f"{_EXIT_MEANING[rc]} with this candidate applied"
        if rc == 0:
            liars = _still_reports_failures(out)
            if liars:
                return False, (
                    f"suite exited 0 but still reports failures ({liars}) — "
                    f"refusing to accept a candidate that silences the oracle "
                    f"instead of repairing the fault")
            return True, ""
        why = next((l.strip() for l in out.splitlines()
                    if l.startswith(("FAILED", "ERROR"))), "")
        if not why:
            tail = [l for l in out.strip().splitlines() if l.strip()]
            why = tail[-1] if tail else "suite run produced no output"
        return False, why[:400]

    def failing_output(self) -> tuple[bool, str]:
        """(suite_fails, first-failure output). Uses -x and keeps the cache so
        a later --lf coverage run re-runs exactly the recorded failing test."""
        self.clear_pyc()
        rc, out = self.run(["-x", "--tb=long"], cache=True)
        _check_harness(rc, self.extra_args, out, self.root, self.python)
        return rc != 0, out
