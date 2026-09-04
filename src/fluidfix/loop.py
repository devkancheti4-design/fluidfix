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

import json

import os
import subprocess
import time
from dataclasses import dataclass, field

from .acts import Observation, SpanEdit, act_for, candidates
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
    # the engine law's HARVEST_COUNTEREXAMPLE act, actuated: every rejected
    # candidate is kept WITH the failing test that rejected it
    tried_log: list = field(default_factory=list)
    tried_more: int = 0               # rejections beyond the 64-entry cap
    # provenance: the repair equals the git-HEAD content at that line (the
    # defect was an uncommitted edit); None when git/HEAD is unavailable
    restored_original: bool | None = None

    def summary(self) -> str:
        if self.repaired:
            return (f"repaired line {self.lineno} in {self.suite_runs} suite runs "
                    f"({self.seconds:.1f}s):\n  - {self.old_line.strip()}\n"
                    f"  + {self.new_line.strip()}")
        return f"refused: {self.reason} ({self.seconds:.1f}s)"


def _write(path: str, content: str) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(content)


# ---------------------------------------------------------- crash safety --
# ROLLBACK MUST SURVIVE THE PROCESS DYING. Candidates are applied to the real
# file and rolled back from memory, which is byte-exact and correct — right up
# until the process is killed while a candidate is applied. Then the mutation
# stays on disk and nothing records what was there before.
#
# Measured 2026-09-04 on Box2D: a literal-off-by-one candidate turned an
# atomic increment into `+ 0` inside a worker spin loop. The test binary hung,
# every core went to 100% (load average 30), the guard was killed, and
# src/parallel_for.c was left holding fluidfix's mutation. Unattended on a
# studio's CI that is corrupted source with no audit trail.
#
# So the original bytes are journalled to .fluidfix/inflight.json before the
# first mutation and cleared after the final restore. A later run — or the
# same one restarting — puts the file back.
def _journal_path(root: str) -> str:
    return os.path.join(root, ".fluidfix", "inflight.json")


def begin_inflight(root: str, rel: str, original: str) -> None:
    try:
        os.makedirs(os.path.join(root, ".fluidfix"), exist_ok=True)
        with open(_journal_path(root), "w", encoding="utf-8") as fh:
            json.dump({"file": rel, "original": original,
                       "started": time.time()}, fh)
    except OSError:
        pass                      # journalling is best-effort, never fatal


def end_inflight(root: str) -> None:
    try:
        os.remove(_journal_path(root))
    except OSError:
        pass


def recover_inflight(root: str) -> str | None:
    """Restore a file a killed run left mutated. Returns the path restored,
    or None. Safe to call on every start."""
    jp = _journal_path(root)
    if not os.path.exists(jp):
        return None
    try:
        with open(jp, encoding="utf-8") as fh:
            rec = json.load(fh)
        target = os.path.join(root, rec["file"])
        with open(target, "w", encoding="utf-8", newline="") as fh:
            fh.write(rec["original"])
    except (OSError, KeyError, ValueError):
        return None
    end_inflight(root)
    return rec.get("file")


def _restored_original(root: str, rel: str, lineno: int, new_line: str) -> bool | None:
    """Does the shipped repair equal the committed (HEAD) content at that
    line? None when git or the HEAD version is unavailable."""
    try:
        p = subprocess.run(["git", "-C", root, "show",
                            f"HEAD:{rel.replace(os.sep, '/')}"],
                           capture_output=True, text=True, timeout=30)
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None
    if p.returncode != 0:
        return None
    new = new_line.split("\n")
    return p.stdout.split("\n")[lineno - 1:lineno - 1 + len(new)] == new


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

    # Journal the original bytes for the WHOLE call, not per observation.
    # First attempt scoped this to the first mutation window and discharged
    # it inside the per-kind loop; `wrote` stays True across iterations, so
    # every later mutation ran UNJOURNALLED — measured 2026-09-04, a hung
    # candidate in Box2D's parallel_for.c was left on disk with no journal.
    begin_inflight(oracle.root, defect_file, src)
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
                # each green: (new_repr, full_file_content, old_repr, lineno)
                greens: list[tuple[str, str, str, int]] = []
                for cand in candidates(body, act, obs):
                    if isinstance(cand, SpanEdit):
                        # the engine law's CHANGE_GRANULARITY act, actuated:
                        # one candidate replaces lines start..end atomically.
                        # Bounds AND anchor safety — a span may only edit
                        # code its own observation points into.
                        s_, e_ = cand.start, cand.end
                        if not (1 <= s_ <= e_ <= len(raw)) \
                                or not (s_ <= obs.lineno <= e_):
                            continue
                        old_repr = "\n".join(l.rstrip("\r")
                                             for l in raw[s_ - 1:e_])
                        if cand.text == old_repr:            # NOPROGRESS
                            continue
                        key = (s_, e_, cand.text)
                        cend = raw[e_ - 1][len(raw[e_ - 1].rstrip("\r")):]
                        new = raw[:s_ - 1] + [cand.text + cend] + raw[e_:]
                        crepr, at = cand.text, s_
                        at_str = f"{defect_file}:{s_}-{e_}"
                    else:
                        if cand == body:                     # NOPROGRESS
                            continue
                        key = (i, cand)
                        new = raw[:]
                        new[i] = cand + ending
                        crepr, old_repr, at = cand, body, obs.lineno
                        at_str = f"{defect_file}:{obs.lineno}"
                    if key in tried:
                        continue
                    tried.add(key)
                    if not counted:
                        res.acts_tried.append(act)           # a real candidate set
                        counted = True
                    content = "\n".join(new)
                    # a candidate that cannot even compile is rejected for
                    # free: never written, no suite run paid (.py only —
                    # jguard's Java candidates are the JVM's to judge)
                    if defect_file.endswith(".py"):
                        try:
                            compile(content, path, "exec")
                        except SyntaxError as e:
                            if len(res.tried_log) < 64:
                                res.tried_log.append(
                                    {"at": at_str, "tried": crepr[:200],
                                     "why": f"does not compile: {e}"[:400]})
                            else:
                                res.tried_more += 1
                            continue
                    _write(path, content)
                    wrote = True
                    res.suite_runs += 1
                    ok, why = oracle.check(timeout=cand_t)
                    if ok:
                        greens.append((crepr, content, old_repr, at))
                        if len(greens) >= 2:                 # AMB proven — stop
                            _write(path, "\n".join(raw))
                            break
                    elif len(res.tried_log) < 64:
                        res.tried_log.append({"at": at_str,
                                              "tried": crepr[:200],
                                              "why": why})
                    else:
                        res.tried_more += 1
                    _write(path, "\n".join(raw))             # roll back, keep testing
                _write(path, src)                        # byte-exact restore
                if greens:
                    # the engine law rules on what happened: one green is
                    # BUILT -> SHIP; two DISTINCT greens is BUILT+AMB ->
                    # ADD_STATE (the suite cannot tell the candidates apart —
                    # refuse and ask for a pinning test, never guess)
                    ruling = decide(situation(BUILT=True, AMB=len(greens) > 1))
                    res.greens = [g[0] for g in greens]
                    if ruling == "SHIP":
                        crepr, content, old_repr, at = greens[0]
                        _write(path, content)
                        res.repaired, res.refused = True, False
                        res.lineno, res.old_line, res.new_line = at, old_repr, crepr
                        res.restored_original = _restored_original(
                            oracle.root, defect_file, at, crepr)
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
        # The file is now either its original bytes or an ACCEPTED repair —
        # both intentional, neither something a later run should undo.
        end_inflight(oracle.root)
        res.seconds = time.time() - t0
