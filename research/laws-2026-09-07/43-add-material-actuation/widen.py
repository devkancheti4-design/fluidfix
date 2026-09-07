#!/usr/bin/env python
"""PROTOTYPE (report-only, no src/ edits): measure UNREAD, actuate ADD_MATERIAL.

Today ADD_MATERIAL is wording only: guard.py:491 gates a hint string, and the
hint tells the user to install pytest-cov.  It is reachable only when
`candidates` is EMPTY.  When the candidate list is non-empty but made
entirely of files the failure runs THROUGH rather than files the failure is
ABOUT (assertion helpers, harness code), UNREAD is never packed and the law
never gets to rule.

This module supplies the missing OBSERVATION and the missing ACTUATION:

  observation  assertion_carriers(out) -> the FRAMED files whose traceback
               frame is a bare `assert` statement.  A file the failure only
               asserts *in* is the instrument, not the suspect.
               UNREAD := candidates and set(candidates) <= carriers
               Cost: 0 suite runs (pure text over output already in hand).

  actuation    widen(oracle, out, carriers) -> re-runs the body's OWN
               find_candidate_files() with the carrier mentions scrubbed from
               the traceback, which forces the SIGHT tier-2 (coverage
               specificity) path that guard.py:146 `if ordered: return`
               otherwise makes unreachable.
               Cost: the two coverage suite runs tier 2 already costs.

Nothing in src/fluidfix is edited or monkeypatched: guard_once() already
accepts `files=`, so the widened list is simply handed to it.
"""
from __future__ import annotations

import re
import sys

sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")

from fluidfix.engine import decide, situation      # noqa: E402
from fluidfix.guard import find_candidate_files, _ANSI, _is_test_path  # noqa: E402

# A pytest long traceback marks the raising line with '>' and the file/line
# with 'path.py:NN:' on the following separator line.
_FRAME = re.compile(r"^(?P<path>[\w./\\-]+\.py):(?P<line>\d+):", re.M)


def assertion_carriers(failing_output: str) -> set[str]:
    """Non-test files whose traceback frame raised on a bare `assert`.

    Reads the long traceback pytest already printed: within each frame, the
    line beginning '>' is the statement that raised.  If that statement is an
    `assert`, the file is carrying somebody else's assertion.
    """
    clean = _ANSI.sub("", failing_output)
    lines = clean.splitlines()
    carriers: set[str] = set()
    pending_assert = False
    for ln in lines:
        s = ln.strip()
        if s.startswith(">"):
            body = s[1:].strip()
            pending_assert = bool(re.match(r"assert\b", body))
        m = _FRAME.match(ln)
        if m:
            path = m.group("path").replace("\\", "/")
            if pending_assert and not _is_test_path(path):
                carriers.add(path)
            pending_assert = False
    return carriers


def unread(candidates: list[str], carriers: set[str]) -> bool:
    """The material in hand is insufficient: every candidate is an instrument."""
    return bool(candidates) and set(candidates) <= carriers


def _scrub(failing_output: str, carriers: set[str]) -> str:
    """Remove carrier-file mentions so the body's FRAMED tier finds nothing
    and its SIGHT tier-2 coverage ranking runs.  FAILED/ERROR summary lines
    are left untouched — tier 2 mines them for its affinity tokens."""
    out = []
    for ln in failing_output.splitlines():
        if ln.lstrip().startswith(("FAILED", "ERROR")):
            out.append(ln)
            continue
        for c in carriers:
            ln = ln.replace(c, "").replace(c.split("/")[-1], "")
        out.append(ln)
    return "\n".join(out)


def widen(oracle, failing_output: str, carriers: set[str], limit: int = 6,
          evidence: dict | None = None) -> list[str]:
    """ADD_MATERIAL, actuated: the SIGHT tier-2 file set."""
    return find_candidate_files(oracle, _scrub(failing_output, carriers),
                                limit=limit, evidence=evidence)


def material(oracle, failing_output: str, candidates: list[str],
             limit: int = 6) -> tuple[list[str], dict]:
    """Full prototype step.  Returns (file list to search, report dict)."""
    carriers = assertion_carriers(failing_output)
    u = unread(candidates, carriers)
    rep = {"carriers": sorted(carriers), "framed": list(candidates),
           "UNREAD": u, "ruling": decide(situation(UNREAD=u)) if u else None,
           "widened": [], "sight_evidence": {}}
    if not u:
        return list(candidates), rep
    ev: dict = {}
    wide = widen(oracle, failing_output, carriers, limit=limit, evidence=ev)
    rep["widened"] = wide
    rep["sight_evidence"] = ev
    # instruments go LAST: a file the failure only asserts in is not the
    # failure pointing at a fault, so it must not outrank real material.
    order = wide + [c for c in candidates if c not in wide]
    return order, rep
