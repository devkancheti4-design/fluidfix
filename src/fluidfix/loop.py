# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 devkancheti4-design
# Commercial licensing: see COMMERCIAL.md.
"""The repair loop: observations in, suite-accepted repair or honest refusal out.
(Byte-exactness is a measured property of the acts — 26/26 accepted repairs on
the benchmark corpus — not an enforced invariant; the suite is the judge.)

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

File handling is byte-preserving: the source is split on "\\n" only (CRLF
lines keep their "\\r" as line content, form feeds stay inside lines so line
numbers match the tokenizer's), candidates re-attach the line's own ending,
and nothing is written back unless a candidate was actually tried.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass, field

from .acts import Observation, act_for, candidates
from .engine import decide, situation
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
    ambiguous: bool = False
    greens: list[str] = field(default_factory=list)   # all suite-passing candidates

    def summary(self) -> str:
        if self.repaired:
            return (f"repaired line {self.lineno} in {self.suite_runs} suite runs "
                    f"({self.seconds:.1f}s):\n  - {self.old_line.strip()}\n"
                    f"  + {self.new_line.strip()}")
        return f"refused: {self.reason} ({self.seconds:.1f}s)"


def _write(path: str, content: str) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(content)


def repair(oracle: Oracle, defect_file: str,
           observations: list[Observation],
           candidate_timeout: int | None = None,
           deadline: float | None = None) -> RepairResult:
    t0 = time.time()
    res = RepairResult(repaired=False, refused=True)
    path = os.path.join(oracle.root, defect_file)
    cand_t = candidate_timeout or oracle.timeout

    # PRECONDITION: a failing test. Without one the first candidate that leaves
    # the suite green is accepted — on a green suite that is the first
    # candidate tried, on whatever line it lands.
    if oracle.green():
        res.reason = "no failing test — nothing to repair"
        res.suite_runs = 1
        res.seconds = time.time() - t0
        return res
    res.suite_runs += 1

    with open(path, encoding="utf-8", newline="") as f:
        src = f.read()
    raw = src.split("\n")            # "\n".join(raw) == src, byte for byte
    tried: set[tuple[int, str]] = set()
    wrote = False

    try:
        for obs in observations:
            if deadline is not None and time.time() > deadline:
                # tree is byte-identical to src here (every candidate is
                # rolled back before the next observation) — an honest stop
                res.reason = ("wall-clock deadline reached mid-search — "
                              "remaining observations untried")
                return res
            i = obs.lineno - 1
            if not (0 <= i < len(raw)):
                continue
            body = raw[i].rstrip("\r")
            ending = raw[i][len(body):]          # "" or "\r"
            mask = mask_of(k for k in obs.kinds if 0 <= k <= 15)
            while not HALT(mask):
                if deadline is not None and time.time() > deadline:
                    # between kinds the tree is byte-identical to src.
                    # NEVER inside a candidate set: a lone green with the
                    # set unfinished is an UNPROVEN-unique repair — shipping
                    # it would be a guess (adversarial review, 2026-08-31).
                    # Overshoot is bounded: one candidate set, <= 32 runs.
                    res.reason = ("wall-clock deadline reached mid-search — "
                                  "remaining kinds untried")
                    return res
                kind = kind_of(EMIT(mask))
                mask = ADVANCE(mask)
                act = act_for(kind)
                obs.file, obs.root = defect_file, oracle.root
                obs.all_lines = [l.rstrip("\r") for l in raw]
                counted = False
                greens: list[str] = []
                for cand in candidates(body, act, obs):
                    if cand == body or (i, cand) in tried:   # NOPROGRESS
                        continue
                    tried.add((i, cand))
                    if not counted:
                        res.acts_tried.append(act)           # a real candidate set
                        counted = True
                    new = raw[:]
                    new[i] = cand + ending
                    _write(path, "\n".join(new))
                    wrote = True
                    res.suite_runs += 1
                    if oracle.green(timeout=cand_t):
                        greens.append(cand)
                        if len(greens) >= 2:                 # AMB proven — stop
                            _write(path, "\n".join(raw))
                            break
                    _write(path, "\n".join(raw))             # roll back, keep testing
                _write(path, src)                        # byte-exact restore
                if greens:
                    # the engine law rules on what happened: one green is
                    # BUILT -> SHIP; two DISTINCT greens is BUILT+AMB ->
                    # ADD_STATE (the suite cannot tell the candidates apart —
                    # refuse and ask for a pinning test, never guess)
                    ruling = decide(situation(BUILT=True, AMB=len(greens) > 1))
                    res.greens = greens
                    if ruling == "SHIP":
                        new = raw[:]
                        new[i] = greens[0] + ending
                        _write(path, "\n".join(new))
                        res.repaired, res.refused = True, False
                        res.lineno, res.old_line, res.new_line = obs.lineno, body, greens[0]
                        res.reason = f"kind {kind} -> act {act}"
                        return res
                    res.ambiguous = True
                    res.reason = (f"AMBIGUOUS: {len(greens)} different candidates all "
                                  f"pass the suite at line {obs.lineno} — the tests "
                                  "cannot tell them apart; add one pinning test "
                                  "(engine law: ADD_STATE, never guess)")
                    return res
        res.reason = ("no observation named a kind this vocabulary can repair"
                      if not res.acts_tried else
                      "every candidate left the suite red — fault is outside "
                      "this vocabulary or the observations are wrong")
        return res
    finally:
        if wrote and not res.repaired:
            _write(path, src)
            oracle.clear_pyc()
        res.seconds = time.time() - t0
