# SPDX-License-Identifier: AGPL-3.0-or-later
"""Class properties — what a taught class must be true of, checked exhaustively before the suite runs.

A fault class is taught from one worked example; the suite then judges every candidate it proposes. That
is enough to stop a candidate that breaks a test, and not enough to stop one no test happens to exercise.
The 2026-09-19 real-repo study shipped `* len(text) - 1` into rich and rich's own suite accepted it.

A class property closes that gap. It is not a statement about the repaired program — it is a statement
about the REWRITE, so it holds whatever code surrounds the line:

    class 7  len-as-last-index   the candidate must equal the original with len(x) -> (len(x) - 1),
                                 for every integer value of every free subexpression

That distinction is what makes it cheap. A function property must be written per function; a class
property is written ONCE, when the class is taught, and then gates every application of that class
forever — on code nobody has written yet, in repositories nobody has cloned yet, at zero suite runs and
zero tokens.

Three outcomes, and the middle one is the honest part:

    PROVEN     checked over the whole bounded domain, no disagreement — ship to the suite
    REFUTED    a witness exists — refuse now, before spending a suite run
    UNPROVEN   the property did not apply, or nothing could be evaluated — the suite still judges, and
               the certificate says the claim was never established

A property that everything satisfies proves nothing, so a check that evaluates zero inputs is UNPROVEN,
never PROVEN. Teaching a property should come with a control that fails it.
"""
from __future__ import annotations

PROVEN, REFUTED, UNPROVEN = "PROVEN", "REFUTED", "UNPROVEN"

# kind -> (statement, checker). checker(original_line, candidate_line) -> (ok, why, n_inputs)
#   ok is True / False / None, and True with n == 0 is demoted to UNPROVEN.
PROPERTIES: dict = {}


def teach_property(kind: int, statement: str, checker) -> None:
    """Teach the property a class's rewrites must satisfy. One line of English, one checker, taught
    beside the class itself and versioned with it."""
    if not 0 <= kind <= 15:
        raise ValueError("kind must be 0..15 — the kernel routes mod 16")
    PROPERTIES[kind] = (statement, checker)


def check(kind: int, original: str, candidate: str):
    """(verdict, why, n_inputs_checked) for one candidate of one class."""
    if kind not in PROPERTIES:
        return UNPROVEN, "no property taught for this class", 0
    statement, checker = PROPERTIES[kind]
    try:
        ok, why, n = checker(original, candidate)
    except Exception as e:                       # a broken checker must not pass a candidate
        return UNPROVEN, f"checker raised {type(e).__name__}: {e}", 0
    if ok is None:
        return UNPROVEN, why, n
    if ok is False:
        return REFUTED, why, n
    if n == 0:
        return UNPROVEN, "no input was evaluated — a check nothing can fail proves nothing", 0
    return PROVEN, statement, n


def gate(kind: int, original: str, candidates: list):
    """Split candidates into those the class property permits and those it refutes.

    Refusal here costs no suite run. That is the point: the suite is the expensive judge and the only
    one that can accept, but a class property can reject for free — and can reject candidates the suite
    would have accepted."""
    kept, refused = [], []
    for c in candidates:
        if c == original:
            continue
        verdict, why, n = check(kind, original, c)
        (refused if verdict == REFUTED else kept).append((c, verdict, why, n))
    return kept, refused
