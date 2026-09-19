# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 devkancheti4-design
"""THE PLACEMENT LAW, and the measurement that feeds it.

Where does an inserted token go in an existing expression? Every applier that adds one — ` - 1`, ` + 1`,
a negation, a clamp — has been answering that by accident of where its regex matched. Measured
consequence: the taught class `len-as-last-index` is right on `last = len(x)`, right on `off + len(x)`
by associativity, right inside `min(99, len(x))`, and **wrong on `k * len(x)`** — 0 of 12 — because
`k * len(x) - 1` is `(k·len) − 1` and not `k·(len−1)`. It shipped exactly that into rich, and rich's own
suite accepted it.

THE BODY MEASURES, THE LAW RULES. The body's whole job is to turn the syntactic context into an integer:
the precedence class of the operator ADJACENT to the call on each side, within its own bracket scope.

    x = (L << 3) | R          six bits, 49 reachable values

The law never sees a string, an operator, or which token is being inserted. Authored by search, two lanes
because x is two independent 3-bit fields and posing it whole asked the search to bridge both at once:

    L_LEFT   (x + 24) >> 6                adds 3 to the left field, reads the carry OUT of it
    L_RIGHT  ((x + 3) >> 3) - (x >> 3)    adds 3 to the right field, reads the carry INTO the left
                                          field, then subtracts that field back out

Verified exhaustively on all 49 reachable words and total on 0..63.
"""
from __future__ import annotations

import re

__all__ = ["TRAIL", "WRAP", "place", "situation", "measure", "insert_token"]

TRAIL, WRAP = 0, 1

# precedence classes: 0 nothing in scope · 1 comparison · 2 | ^ & · 3 << >> · 4 + - · 5 * / // % @ · 6 ** unary
_CLASS = [
    (6, ("**",)),
    (5, ("//", "@", "*", "/", "%")),
    (4, ("+", "-")),
    (3, ("<<", ">>")),
    (1, ("<=", ">=", "==", "!=", "<", ">")),
    (2, ("|", "^", "&")),
]
_WORD_OPS = {"in": 1, "is": 1, "and": 1, "or": 1, "not": 6, "if": 0, "else": 0, "return": 0}
_OPEN, _CLOSE = "([{", ")]}"


def place(x: int) -> int:
    """0 = TRAIL (append after the call), 1 = WRAP (parenthesise the call)."""
    return ((x + 24) >> 6) | ((((x + 3) >> 3) - (x >> 3)))


def situation(L: int, R: int) -> int:
    return (L << 3) | R


def _class_of(tok: str) -> int:
    for pri, ops in _CLASS:
        if tok in ops:
            return pri
    return _WORD_OPS.get(tok, 0)


def _left_class(line: str, start: int) -> int:
    """The operator immediately left of `start`, skipping balanced brackets. 0 when the scope opens."""
    i, depth = start - 1, 0
    while i >= 0:
        c = line[i]
        if c.isspace():
            i -= 1; continue
        if c in _CLOSE:
            depth += 1; i -= 1; continue
        if c in _OPEN:
            if depth == 0:
                return 0                       # the scope opens here: nothing binds this call
            depth -= 1; i -= 1; continue
        if depth:
            i -= 1; continue
        if c == ",":
            return 0                           # a separator, not an operator
        if c.isalnum() or c == "_":            # a bare name or number: read the word, it may be `not`
            j = i
            while j >= 0 and (line[j].isalnum() or line[j] == "_"):
                j -= 1
            return _WORD_OPS.get(line[j+1:i+1], 0)
        two = line[i-1:i+1]
        if len(two) == 2 and _class_of(two):
            return _class_of(two)
        return _class_of(c)
    return 0


def _right_class(line: str, end: int) -> int:
    """The operator immediately right of `end`, skipping balanced brackets. 0 when the scope closes."""
    i, depth = end, 0
    while i < len(line):
        c = line[i]
        if c.isspace():
            i += 1; continue
        if c in _OPEN:
            depth += 1; i += 1; continue
        if c in _CLOSE:
            if depth == 0:
                return 0                       # the scope closes here
            depth -= 1; i += 1; continue
        if depth:
            i += 1; continue
        if c in ",:":
            return 0
        if c.isalnum() or c == "_":
            j = i
            while j < len(line) and (line[j].isalnum() or line[j] == "_"):
                j += 1
            return _WORD_OPS.get(line[i:j], 0)
        two = line[i:i+2]
        if len(two) == 2 and _class_of(two):
            return _class_of(two)
        return _class_of(c)
    return 0


def measure(line: str, start: int, end: int) -> int:
    """The situation word for a call occupying line[start:end]."""
    return situation(_left_class(line, start), _right_class(line, end))


def insert_token(line: str, start: int, end: int, token: str = " - 1") -> str:
    """Insert `token` after the call at [start:end), where the LAW says it belongs."""
    call = line[start:end]
    if place(measure(line, start, end)) == WRAP:
        return line[:start] + "(" + call + token + ")" + line[end:]
    return line[:start] + call + token + line[end:]
