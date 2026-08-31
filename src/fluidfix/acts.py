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
    # repo context, populated by the repair loop before appliers run — lets a
    # taught transform search for values that live in the repo rather than on
    # the broken line (enumerate candidates; the suite picks; refusal if none)
    file: str | None = None          # defect file, relative to root
    root: str | None = None          # project root (absolute)
    all_lines: list | None = None    # full defect-file lines, sans endings


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


def _flip_strictness(line: str, obs: Observation) -> list:
    """Every strictness flip on the line, as a candidate set. The legacy
    first-match candidate stays FIRST (apply() back-compat); the seeded
    large-repo benchmark showed the mutated operator is usually NOT the
    line's first, so the loop tries every occurrence — suite judges."""
    out, seen = [], set()
    for a, b in ((">=", ">"), ("<=", "<"), (">", ">="), ("<", "<=")):
        start = 0
        while True:
            i = line.find(a, start)
            if i < 0:
                break
            # don't rewrite the strict op inside its own relaxed form
            if a in (">", "<") and line[i:i + 2] in (">=", "<="):
                start = i + 2
                continue
            cand = line[:i] + b + line[i + len(a):]
            if cand not in seen:
                seen.add(cand)
                out.append(cand)
            start = i + len(a)
    return out or [line]


def _dec_at(line: str, m) -> str:
    lit = m.group()
    val = int(lit) - 1
    new_lit = str(val)
    # A zero-padded literal keeps its width ("034" -> "033", not "33"):
    # inside string escapes the padding is meaning, and byte-exact
    # restoration is the product's whole claim (measured: click termui
    # \033 -> \034 replay shipped "\33" without this).
    if val >= 0 and len(lit) > 1 and lit.startswith("0"):
        new_lit = new_lit.zfill(len(lit))
    out = line[:m.start()] + new_lit + line[m.end():]
    # Simplify `x + 1` -> decrement -> `x + 0` -> `x`, but ONLY at the
    # decrement site, and only when the zero stands alone: a global
    # unanchored sub was measured to eat an unrelated `-0.5` elsewhere on
    # the line while the suite still passed.
    if new_lit == "0" and not re.match(r"[0-9.eEjJxXbBoO_]", line[m.end():m.end() + 1] or " "):
        pre = re.search(r"\s*[+-]\s*$", line[:m.start()])
        if pre:
            out = line[:pre.start()] + line[m.end():]
    return out


def _reduce_literal(line: str, obs: Observation) -> list:
    """Decrement candidates for EVERY literal on the line, observer-pointed
    literal first, then left-to-right (legacy first-match order preserved)."""
    hits = list(re.finditer(r"\d+", line))
    if not hits:
        return [line]
    ordered = []
    if obs.literal_value:
        want = [h for h in hits if h.group() == str(obs.literal_value)]
        occ = max(1, obs.literal_occurrence or 1)
        if len(want) >= occ:
            ordered.append(want[occ - 1])
    ordered += [h for h in hits if h not in ordered]
    out, seen = [], set()
    for m in ordered:
        cand = _dec_at(line, m)
        if cand not in seen:
            seen.add(cand)
            out.append(cand)
    return out


def _swap_return_operands(line: str, obs: Observation) -> str:
    m = re.match(r"^(\s*return\s+)(.*?)(\s(?://|[-+*])\s)(.*)$", line)
    return line if not m else f"{m.group(1)}{m.group(4)}{m.group(3)}{m.group(2)}"


def _flip_additive(line: str, obs: Observation) -> list:
    """Flip candidates for EVERY binary +/- on the line. Order: the
    observer's op_occurrence pointer first, else legacy first-`+` heuristic,
    then the remaining occurrences left-to-right — suite judges each."""
    ops = list(re.finditer(r"\s([+-])\s", line))
    if not ops:
        return [line]
    ordered = []
    if obs.op_occurrence and 1 <= obs.op_occurrence <= len(ops):
        ordered.append(ops[obs.op_occurrence - 1])
    else:
        ordered.append(next((o for o in ops if o.group(1) == "+"), ops[0]))
    ordered += [o for o in ops if o not in ordered]
    out, seen = [], set()
    for m in ordered:
        flipped = "-" if m.group(1) == "+" else "+"
        cand = line[:m.start(1)] + flipped + line[m.end(1):]
        if cand not in seen:
            seen.add(cand)
            out.append(cand)
    return out


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


def register(kind: int, name: str, description: str, signal,
             applier) -> int:
    """Teach fluidfix a new fault class. One entry, one transform — the router
    is untouched: it infers this kind's act code from the same single worked
    example, so a new class costs exactly one registration, once, and every
    future member of the class is decided for free.

    kind: 0-15 (the kernel's domain — one dictionary holds 16 classes).
    signal: compiled regex a line must match for the mechanical observer to
        report this kind (LLM observers receive `description` verbatim).
    applier(line, observation) -> candidate line.
    Returns the act code the router assigned.
    """
    if not 0 <= kind <= 15:
        raise ValueError("kind must be 0..15 — the kernel routes mod 16")
    code = act_for(kind)
    KINDS[kind] = (name, description, signal)
    ACTS[code] = applier
    return code


def load_dictionary(path: str) -> int:
    """Load a repo's fault-class dictionary: a Python file whose top level
    calls register(). Version it next to the code it maintains — one worked
    example per class, taught once, decided free forever. Returns how many
    classes the file registered."""
    import re as _re
    before = set(KINDS)
    ns = {"register": register, "re": _re}
    with open(path, encoding="utf-8") as f:
        code = compile(f.read(), path, "exec")
    exec(code, ns)
    return len(set(KINDS) - before)


def candidates(line: str, act: int, obs: Observation) -> list:
    """All candidate lines an act proposes (possibly several).

    A shipped or taught applier may return either a single string (the common
    case: the fix is a pure rule over the line) or a list of strings — a
    candidate set searched in order, for classes whose correct value lives
    elsewhere in the repo (`obs.file`/`obs.root`/`obs.all_lines` carry the
    context). The suite adjudicates every candidate; none passing means
    refusal, so the no-wrong-repairs contract is unchanged. Unknown acts are
    a no-op (NOPROGRESS upstream). Candidate sets are capped at 32.
    """
    fn = ACTS.get(act)
    if fn is None:
        return [line]
    out = fn(line, obs)
    if isinstance(out, str):
        return [out]
    return [c for c in out if isinstance(c, str)][:32]   # bounded search


def apply(line: str, act: int, obs: Observation) -> str:
    """Apply an act to a line — the first candidate (back-compat single-fix API)."""
    out = candidates(line, act, obs)
    return out[0] if out else line
