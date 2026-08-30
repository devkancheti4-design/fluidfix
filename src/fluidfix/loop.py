# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 devkancheti4-design
# Commercial licensing: see COMMERCIAL.md.
"""The repair loop: observations in, byte-exact repair or honest refusal out.

    for each observation:
        mask <- one bit per reported kind
        while not HALT(mask):
            kind <- EMIT(mask)              # fluid-router2, verbatim
            act  <- route(0, 5, kind)       # fluid-router, verbatim
            candidate <- apply(act, line, observation)
            unchanged?          -> NOPROGRESS: ADVANCE
            suite green?        -> repaired, stop
            else restore        -> ADVANCE

The output space is exactly {repair the suite accepts, refusal}. There is no
"plausible fix" branch: an empty mask halts, a kindless observation refuses,
and a green suite refuses before anything runs — searching without a failing
test has been measured to corrupt working code while reporting success.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass, field

from .acts import Observation, act_for, apply
from .lanes import ADVANCE, EMIT, HALT, kind_of, mask_of
from .oracle import Oracle

__all__ = ["RepairResult", "repair"]


@dataclass
class RepairResult:
    repaired: bool
    refused: bool
    lineno: int | None = None
    old_line: str | None = None
    new_line: str | None = None
    acts_tried: list[int] = field(default_factory=list)
    suite_runs: int = 0
    seconds: float = 0.0
    reason: str = ""

    def summary(self) -> str:
        if self.repaired:
            return (f"repaired line {self.lineno} in {self.suite_runs} suite runs "
                    f"({self.seconds:.1f}s):\n  - {self.old_line.strip()}\n"
                    f"  + {self.new_line.strip()}")
        return f"refused: {self.reason} ({self.seconds:.1f}s)"


def repair(oracle: Oracle, defect_file: str,
           observations: list[Observation],
           candidate_timeout: int = 120) -> RepairResult:
    t0 = time.time()
    res = RepairResult(repaired=False, refused=True)
    path = os.path.join(oracle.root, defect_file)

    # PRECONDITION: a failing test. Without one the first candidate that leaves
    # the suite green is accepted — on a green suite that is the first
    # candidate tried, on whatever line it lands.
    if oracle.green():
        res.reason = "no failing test — nothing to repair"
        res.suite_runs = 1
        res.seconds = time.time() - t0
        return res
    res.suite_runs += 1

    src = open(path, encoding="utf-8").read()
    lines = src.splitlines()
    trailing_nl = "\n" if src.endswith("\n") else ""
    tried: set[tuple[int, str]] = set()

    try:
        for obs in observations:
            i = obs.lineno - 1
            if not (0 <= i < len(lines)):
                continue
            line = lines[i]
            mask = mask_of(k for k in obs.kinds if 0 <= k <= 15)
            while not HALT(mask):
                kind = kind_of(EMIT(mask))
                mask = ADVANCE(mask)
                act = act_for(kind)
                cand = apply(line, act, obs)
                res.acts_tried.append(act)
                if cand == line or (i, cand) in tried:   # NOPROGRESS
                    continue
                tried.add((i, cand))
                new = lines[:]
                new[i] = cand
                open(path, "w", encoding="utf-8").write("\n".join(new) + trailing_nl)
                res.suite_runs += 1
                if oracle.green(timeout=candidate_timeout):
                    res.repaired, res.refused = True, False
                    res.lineno, res.old_line, res.new_line = obs.lineno, line, cand
                    res.reason = f"kind {kind} -> act {act}"
                    return res
                open(path, "w", encoding="utf-8").write("\n".join(lines) + trailing_nl)
        res.reason = ("no observation named a kind this vocabulary can repair"
                      if not res.acts_tried else
                      "every candidate left the suite red — fault is outside "
                      "this vocabulary or the observations are wrong")
        return res
    finally:
        if not res.repaired:
            open(path, "w", encoding="utf-8").write(src)
            oracle.clear_pyc()
        res.seconds = time.time() - t0
