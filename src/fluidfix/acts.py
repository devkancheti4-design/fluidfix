# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 devkancheti4-design
# Commercial licensing: see COMMERCIAL.md.
"""The act vocabulary: fault kinds, repairs, and the observation contract.

One structure defines each kind's meaning; the mechanical observer's regexes,
the LLM observer's prompt, and the appliers all derive from it. The router
never sees any of this — it maps kind -> act code from one worked example.

Observations may carry "clear data" pointers that sharpen the applier without
touching the router:

  literal_value/-occurrence  which numeric literal is wrong (kind 1). On the
      benchmark corpus this alone took in-vocabulary exact repairs from 17/27
      (first-literal heuristic) to 26/27.
  op_occurrence  which additive operator is flipped (kind 3), counting binary
      " + "/" - " left to right, 1-based. Closes the remaining measured miss:
      a line carrying both a `+` and the faulty `-`.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

__all__ = ["Observation", "KINDS", "ACTS", "WORKED_EXAMPLE", "apply", "act_for"]

from .router import route

# The single mapping supplied to the router; every other act is inferred.
WORKED_EXAMPLE = (0, 5)


@dataclass
class Observation:
    """What an observer reports. Never a fix, never an act code."""
    lineno: int                      # 1-based line in the defect file
    kinds: list[int] = field(default_factory=list)   # most specific first; [] = refuse
    literal_value: str | None = None
    literal_occurrence: int | None = None
    op_occurrence: int | None = None
    note: str = ""


# kind -> (name, description used verbatim in observer prompts, line-signal regex)
KINDS = {
    0: ("strictness",
        'a token containing < or > has one "=" too many or too few '
        '(a ">=" that should be ">", a "<" that should be "<=", an "->" '
        'corrupted to "->=", including inside strings)',
        re.compile(r"[<>]=?")),
    1: ("literal-off-by-one",
        "a numeric literal on the line is exactly one greater than correct "
        "(3601 for 3600, [2:] for [1:], group(2) for group(1))",
        re.compile(r"\d")),
    2: ("swapped-return-operands",
        'a "return a OP b" whose two operands are in the wrong order',
        re.compile(r"^\s*return\s+.*\s(?://|[-+*])\s")),
    3: ("flipped-additive",
        'a binary " + " that should be " - ", or a " - " that should be '
        '" + " (spaces around the operator)',
        re.compile(r"\s[-+]\s")),
}


def _flip_strictness(line: str, obs: Observation) -> str:
    for a, b in ((">=", ">"), ("<=", "<")):
        if a in line:
            return line.replace(a, b, 1)
    for a, b in ((">", ">="), ("<", "<=")):
        if a in line:
            return line.replace(a, b, 1)
    return line


def _reduce_literal(line: str, obs: Observation) -> str:
    m = None
    if obs.literal_value:
        hits = [h for h in re.finditer(r"\d+", line) if h.group() == str(obs.literal_value)]
        occ = max(1, obs.literal_occurrence or 1)
        if len(hits) >= occ:
            m = hits[occ - 1]
    if m is None:
        m = re.search(r"\d+", line)
    if not m:
        return line
    out = line[:m.start()] + str(int(m.group()) - 1) + line[m.end():]
    return re.sub(r"\s*[+-]\s*0(?![0-9])", "", out)


def _swap_return_operands(line: str, obs: Observation) -> str:
    m = re.match(r"^(\s*return\s+)(.*?)(\s(?://|[-+*])\s)(.*)$", line)
    return line if not m else f"{m.group(1)}{m.group(4)}{m.group(3)}{m.group(2)}"


def _flip_additive(line: str, obs: Observation) -> str:
    ops = list(re.finditer(r"\s([+-])\s", line))
    if not ops:
        return line
    if obs.op_occurrence and 1 <= obs.op_occurrence <= len(ops):
        m = ops[obs.op_occurrence - 1]
    else:
        # legacy first-match heuristic, kept for observers with no pointer
        m = next((o for o in ops if o.group(1) == "+"), ops[0])
    flipped = "-" if m.group(1) == "+" else "+"
    return line[:m.start(1)] + flipped + line[m.end(1):]


# act code -> applier; codes are one translation of the vocabulary. Renumber
# them freely — the router recovers the offset from WORKED_EXAMPLE each call.
ACTS = {
    5: _flip_strictness,
    6: _reduce_literal,
    7: _swap_return_operands,
    8: _flip_additive,
}


def act_for(kind: int) -> int:
    """The router's decision: kind -> act code, from the one worked example."""
    return route(WORKED_EXAMPLE[0], WORKED_EXAMPLE[1], kind)


def apply(line: str, act: int, obs: Observation) -> str:
    """Apply an act to a line. Unknown acts are a no-op (NOPROGRESS upstream)."""
    fn = ACTS.get(act)
    return line if fn is None else fn(line, obs)
