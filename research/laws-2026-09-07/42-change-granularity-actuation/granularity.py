"""PROTOTYPE (report-only, src/ untouched): the CHANGE_GRANULARITY ladder.

The engine law rules CHANGE_GRANULARITY on HIDDEN ("fine records disagree,
coarse records agree").  loop.py:391 computes that ruling and puts it in a
STRING; the body then rejects the candidate.  Rejecting is not changing the
granularity, and re-running the whole suite N more times (FLUIDFIX_CONFIRM)
is not either -- it is more SAMPLES at the same granularity.

This file actuates the ruling by moving the RECORD granularity down one rung:

  rung 0  "suite"      one full-suite run; the verdict is ONE bit.
                       (= today's body with FLUIDFIX_CONFIRM=0)
  rung 1  "resample"   1+n full-suite runs, ANDed; still one bit per run.
                       (= today's body with FLUIDFIX_CONFIRM=n)
  rung 2  "test"       one full-suite run, but the verdict is the per-TEST
                       record set compared against a baseline profile.
                       A test whose baseline records disagree with each other
                       is HIDDEN: it carries no verdict about the candidate.
  rung 3  "test+k"     rung 2, and every test that actually carries the
                       verdict is re-run ALONE k times -- k fine records at
                       test granularity instead of k coarse records at suite
                       granularity.

Everything is driven through a subclass of the shipped Oracle, so the shipped
loop.repair() runs unmodified with FLUIDFIX_CONFIRM=0.
"""
from __future__ import annotations

import re
import sys

SRC = "/Users/kanchetidevieswar/neo/fluidfix/src"
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from fluidfix.oracle import Oracle           # noqa: E402

_FAILED = re.compile(r"^(?:FAILED|ERROR)\s+(\S+)")


def _failing_set(out: str) -> set:
    return {m.group(1) for m in
            (_FAILED.match(l) for l in out.splitlines()) if m}


class Profile:
    """The baseline flake profile: B full-suite runs on the PRISTINE tree,
    kept at test granularity.  This is the observation the body never makes."""

    def __init__(self, oracle: "LadderOracle", runs: int = 5):
        self.runs = runs
        fails = []
        for _ in range(runs):
            rc, out = oracle.run(["--tb=no"])
            fails.append(_failing_set(out))
        seen = set().union(*fails) if fails else set()
        self.always_fail = {t for t in seen if all(t in f for f in fails)}
        self.mixed = {t for t in seen if t not in self.always_fail}
        self.fail_rate = {t: sum(t in f for f in fails) / runs for t in seen}
        # a test that failed in no baseline run is a GUARD: it must not start
        # failing because of a candidate
        self.ever_failed = seen

    @property
    def hidden(self) -> bool:
        """HIDDEN as the law means it: fine records of the SAME thing
        disagree while the coarse record ('the suite is red') agrees."""
        return bool(self.mixed)

    def targets(self) -> set:
        """The tests that carry the verdict.  Deterministic failures if there
        are any; otherwise the flaky failures are all the evidence there is."""
        return self.always_fail or self.mixed


class LadderOracle(Oracle):
    def __init__(self, *a, rung: int = 0, k: int = 4,
                 profile: Profile | None = None, **kw):
        super().__init__(*a, **kw)
        self.rung, self.k, self.profile = rung, k, profile
        self.invocations = 0
        self.full_runs = 0
        self.node_runs = 0
        self.hidden_seen = 0

    # ---- cost accounting -------------------------------------------------
    def run(self, args, cache=False, timeout=None):
        self.invocations += 1
        if any(a for a in args if "::" in a):
            self.node_runs += 1
        else:
            self.full_runs += 1
        return super().run(args, cache=cache, timeout=timeout)

    def _node(self, nodeid: str, timeout=None) -> bool:
        self.clear_pyc()
        rc, out = self.run(["--tb=no", nodeid], timeout=timeout)
        return rc == 0

    # ---- the ladder ------------------------------------------------------
    def green(self, timeout=None):
        """The PRECONDITION ("is there a failing test?") is a record too.
        At rungs 0/1 it is one bit from one run -- on a flaky suite that bit
        aborts ~q of all searches with "no failing test -- nothing to
        repair".  At rungs 2/3 the same question is answered from the
        baseline profile, which is already at test granularity."""
        if self.rung >= 2 and self.profile is not None:
            return not self.profile.ever_failed
        return super().green(timeout=timeout)

    def check(self, timeout=None):
        self.clear_pyc()
        rc, out = self.run(["--tb=no"], timeout=timeout)
        F = _failing_set(out)
        if self.rung <= 1:
            # rung 0/1: ONE BIT.  (rung 1's extra samples are taken by the
            # shipped body through FLUIDFIX_CONFIRM, not here.)
            if rc == 0:
                return True, ""
            return False, (sorted(F)[0] if F else "suite red")[:400]

        p = self.profile
        assert p is not None, "rungs 2-3 need a baseline profile"
        targets = p.targets()
        guards = F - p.ever_failed

        # 1. every test that carries the verdict must now pass
        for t in sorted(targets):
            if self.rung >= 3:
                # k FINE records, at test granularity
                for _ in range(self.k):
                    if not self._node(t, timeout=timeout):
                        self.hidden_seen += 1
                        return False, (f"{t} still fails under a fine "
                                       f"(test-granularity) record")
            elif t in F:
                return False, f"{t} still fails"

        # 2. a regression on a test that never failed at baseline: confirm it
        #    at test granularity before believing it (rung 3), else believe it
        for g in sorted(guards):
            if self.rung >= 3:
                if all(not self._node(g, timeout=timeout)
                       for _ in range(self.k)):
                    return False, f"regression: {g} now fails"
            else:
                return False, f"regression: {g} now fails"

        # 3. tests the profile marks HIDDEN and that are not the verdict
        #    carry NO information about this candidate -- they are ignored.
        return True, ""
