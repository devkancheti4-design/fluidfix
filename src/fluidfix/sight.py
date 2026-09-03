# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 devkancheti4-design
# Commercial licensing: see COMMERCIAL.md.
"""The SIGHT law — fluidfix's fifth machine-authored kernel.

Decides, for ONE candidate source file, how soon it should be opened when
the suite has gone red. Reads the SITUATION of the evidence, never the
content of the code.

    input   one byte of observations, all measurable before any candidate
            is tried
    output  priority 0..7, lower is opened first

    bit  observation                                        tier
      0  FRAMED      the failing traceback names this file   POINTING
      1  SCARCE      the class signal matches <= 2 files      POINTING
      2  LITERAL     an asserted literal occurs in <= 2 files POINTING
      3  FAILONLY    specificity >= 0.9                      circumstantial
      4  NAMED       filename shares a token with the test   circumstantial
      5  TOUCHED     modified in the last 40 commits         circumstantial
      6  SMALL       0 < executed lines < 80                 circumstantial
      7  UBIQUITOUS  specificity < 0.25                      penalty

WHY R1 AND R2 HOLD STRUCTURALLY (the author's derivation, verified here)

    POINT1(x) reduces to (x & 7) != 0: writing x = 8*high + low, the term
    -(x >> 3) is -high and (x + 7) >> 3 is high + (low != 0), so `high`
    cancels exactly and the pointing indicator is what remains.

    POINTING owns mask bit 0 and every circumstantial slot owns a bit >= 2,
    so ctz of any mask carrying pointing evidence is 0 while ctz of any mask
    without it is at least 2 — no quantity of circumstantial evidence can
    close that gap.  That is R1.  For R2, both the circumstantial sum and
    the demotion term are ANDed with gate = POINT1 - 1, identically zero
    whenever a pointing bit is set: the penalty is unreachable on a
    pointed-at file by the algebra of the expression, not by a test that
    could be written the wrong way round.

WHY THIS EXISTS. The ranking law (rank.py) ordered LINES; file order was
still decided by a hand-written blend in which a filename-token overlap
(NAMED) could outrank direct evidence, and in which the ubiquity penalty
could demote the defect file itself.

    Measured 2026-09-03 on click 8.5.1: a taught class was injected at
    src/click/types.py:499. The failing tests live in
    tests/test_shell_completion.py and click HAS a src/click/
    shell_completion.py, so NAMED fired for the WRONG file. The defect file
    had no frame, no name overlap, no discriminating literal, and was
    UBIQUITOUS (every test executes it) — an active penalty. Search order
    came out _utils, shell_completion, __init__, globals, parser, types(6th),
    exceptions, core: 209 candidates tried, budget exhausted, REFUSED.

    The evidence to find it existed and nothing read it: the taught class's
    own signal regex matches lines in only a handful of files repo-wide.
    That is the SCARCE lane, and it is what this law adds.

Two deliberate properties of the authored law, recorded so callers do not
mistake them for bugs:

  * the three POINTING bits all land on priority 0 — they are equal rank.
    When they point at different files the CALLER breaks the tie (this
    module's callers use specificity, then executed-line count).
  * priority 1 is never emitted; the spec steps 0 -> 2. The slot is
    reserved.

Vendored VERBATIM from the authored sight.c; re-verified exhaustively by
`fluidfix selfcheck` and tests/test_sight_law.py — all 256 situations
against the specification, R1, R2, R3, and the three incidents.
"""
from __future__ import annotations

__all__ = ["BITS", "sight", "situation", "observe_bits"]

BITS = ["FRAMED", "SCARCE", "LITERAL", "FAILONLY",
        "NAMED", "TOUCHED", "SMALL", "UBIQUITOUS"]

POINTING = frozenset(("FRAMED", "SCARCE", "LITERAL"))


def _s32(v: int) -> int:
    v &= 0xFFFFFFFF
    return v - 0x100000000 if v & 0x80000000 else v


# ------------------------------------------------------------- THE LAW ----
# Authored, verbatim. Lane comments give the mask bit each lane lands on.
def _POINT1(x): return _s32((0 - (x >> 3)) + ((x + 7) >> 3))   # any pointing
def _FAILONLY(x): return _s32((2 & (x >> 2)) + (2 & (x >> 2)))  # -> mask bit 2
def _NAMED(x): return _s32(8 & (x >> 1))                        # -> mask bit 3
def _TOUCHED(x): return _s32((8 & (x >> 2)) + (8 & (x >> 2)))   # -> mask bit 4
def _SMALL(x): return _s32((63 & (x >> 1)) - (31 & (x >> 1)))   # -> mask bit 5
def _UBIQ(x): return _s32(x >> 7)


def _EMIT(m: int) -> int:
    """authored for 'which token do I write next', unchanged since"""
    return _s32(m & (-m))


_FLOOR = 64                       # no evidence at all -> mask bit 6


def sight(observations: int) -> int:
    """Priority 0..7 for one candidate FILE; lower is opened first."""
    x = _s32(observations)
    p = _POINT1(x)
    gate = p - 1                  # 0 when pointing, all-ones when not
    circ = _FAILONLY(x) + _NAMED(x) + _TOUCHED(x) + _SMALL(x)
    mask = p + (gate & circ) + _FLOOR
    low = _EMIT(mask)
    ctz = 0
    while low >> 1:
        low >>= 1
        ctz += 1
    return ctz + (gate & _UBIQ(x))


def situation(**obs) -> int:
    """Pack observations into the law's input. Observations only, never
    opinions — an invented label is what made an earlier law abstain."""
    return sum(1 << BITS.index(k) for k, on in obs.items() if on)


def observe_bits(*, framed=False, scarce=False, literal=False, failonly=False,
                 named=False, touched=False, small=False,
                 ubiquitous=False) -> int:
    """Convenience wrapper with every lane named, so a caller cannot pass a
    bit it never measured by accident."""
    return situation(FRAMED=framed, SCARCE=scarce, LITERAL=literal,
                     FAILONLY=failonly, NAMED=named, TOUCHED=touched,
                     SMALL=small, UBIQUITOUS=ubiquitous)
