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
import shutil
import subprocess
import sys

__all__ = ["Oracle"]


class Oracle:
    def __init__(self, root: str, python: str | None = None,
                 timeout: int = 300, per_test_timeout: int = 60,
                 extra_args: list[str] | None = None):
        self.root = os.path.abspath(root)
        self.python = python or sys.executable
        self.timeout = timeout
        self.per_test_timeout = per_test_timeout
        self.extra_args = list(extra_args or [])
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
        try:
            p = subprocess.run(cmd, cwd=self.root, capture_output=True, text=True,
                               timeout=timeout or self.timeout, env=env)
            return p.returncode, p.stdout + p.stderr
        except subprocess.TimeoutExpired:
            return 1, "TIMEOUT"

    def green(self, timeout: int | None = None) -> bool:
        self.clear_pyc()
        rc, _ = self.run(["--tb=no"], timeout=timeout)
        return rc == 0

    def check(self, timeout: int | None = None) -> tuple[bool, str]:
        """green() plus WHY: (ok, first-failure line). The rejection
        evidence the repair loop harvests per candidate (engine law:
        REFUTED -> HARVEST_COUNTEREXAMPLE) — same suite run, no extra cost."""
        self.clear_pyc()
        rc, out = self.run(["--tb=no"], timeout=timeout)
        if rc == 0:
            return True, ""
        why = next((l.strip() for l in out.splitlines()
                    if l.startswith(("FAILED", "ERROR"))), "")
        if not why:
            tail = [l for l in out.strip().splitlines() if l.strip()]
            why = tail[-1] if tail else "suite run produced no output"
        return False, why[:200]

    def failing_output(self) -> tuple[bool, str]:
        """(suite_fails, first-failure output). Uses -x and keeps the cache so
        a later --lf coverage run re-runs exactly the recorded failing test."""
        self.clear_pyc()
        rc, out = self.run(["-x", "--tb=long"], cache=True)
        return rc != 0, out
