# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 devkancheti4-design
# Commercial licensing: see COMMERCIAL.md.
"""The PAIR law — fluidfix's sixth machine-authored kernel.

When a single-edit search has failed, decides whether to attempt MORE THAN
ONE simultaneous edit, and in what form.

    input   one byte of observations, measurable after a completed
            single-edit search
    output  priority 0..7, lower is attempted first

    bit  observation
      0  EXHAUSTED  every single-edit candidate tried and rejected
      1  PARTIAL    some single edit strictly REDUCED the failing count
      2  DISJOINT   the failing tests partition into disjoint sites
      3  COUPLED    every failing test touches the same site
      4  CHEAP      the candidate space is affordable
      5  TAUGHT     the classes were taught from worked examples
      6  CANCELING  a pair is green JOINTLY while each member alone leaves
                    the suite red AND reduces nothing
      7  CAPPED     clean inputs, budget already spent

    act  meaning
      0  PARTITION  repair the disjoint groups separately (linear)
      1  PAIR       attempt two simultaneous edits (quadratic)
      2  WIDEN      the fault is not coupled to one site; widen the search
      3  TEACH      the classes are not taught; teach one first
      4  BUDGET     affordable evidence is exhausted; raise the budget
      5  CAPPED     the budget is already spent
      6  SINGLE     a single edit has not been exhausted; keep going
      7  REFUSE     nothing warrants a multi-edit attempt

WHY A PAIR SEARCH IS DANGEROUS, AND WHY THIS LAW IS SO CONSERVATIVE.

Measured 2026-09-04 on Unity-shaped gameplay logic: a sign flip in
ProjectOnPlane admitted TWO passing repairs — restoring the sign (line 32),
and breaking Vec3's operator+ so the two faults CANCEL (line 11). Both pass
the suite; the second corrupts vector addition everywhere else in the
program. Single-edit search only avoided shipping it because the engine
law's AMB lane refuses when candidates at two different sites both pass.

A pair search INVERTS that protection: it goes looking for combinations that
are green only jointly, which is the exact shape of two bugs that cancel.
Naively implemented it is not merely at risk of compensating repairs, it is
a machine for finding them. Hence CANCELING as a veto, and hence the
measured result that only 2 of 256 situations reach a PAIR at all.

COST is the second constraint. Measured on Box2D's contact_solver.c: a
single-edit search tried 1,063 candidates at ~3.5s each before refusing.
The naive pair search over the same space is 564,453 combinations — about
23 days of continuous building. So DISJOINT dominates: when the failing
tests partition into independent groups the situation is N separate
single-bug repairs, linear rather than quadratic, and a law that reached for
pairs while a partition existed would have chosen the expensive answer to
the wrong question.

WHY R1, R2 AND R3 HOLD STRUCTURALLY (the author's derivation, verified here)

    R1  Every action slot is ANDed with gr = 0 - READY, identically zero
        until EXHAUSTED is set. The multi-edit lanes are not unlikely to
        fire while a single edit remains untried — they are algebraically
        absent from the word.
    R2  PARTITION owns mask bit 0 and PAIR owns bit 1, so ctz returns the
        partition whenever one exists. The quadratic answer cannot outrank
        the linear one by position, never by comparison.
    R3  On CANCELING both gb and gc are zero, so every lane vanishes and
        only the floor at bit 7 survives. A compensating pair reaches last
        place because nothing else is left in the mask, not because a rule
        demoted it.

THIS LAW DOES NOT DECIDE WHETHER A REPAIR SHIPS. That remains the engine
law (BUILT / AMB / CAPPED). A pair that is found and accepted faces exactly
the same ambiguity test as any single candidate — which, after the Unity
incident, is the property that matters most.

Vendored VERBATIM from the authored pair.c (docs/laws/pair.c); re-verified
exhaustively by `fluidfix selfcheck` and tests/test_pair_law.py — all 256
situations against the specification, R1-R5, and the five incidents.
"""
from __future__ import annotations

__all__ = ["BITS", "ACTS", "pair_law", "situation", "observe_bits"]

BITS = ["EXHAUSTED", "PARTIAL", "DISJOINT", "COUPLED",
        "CHEAP", "TAUGHT", "CANCELING", "CAPPED"]

ACTS = ["PARTITION", "PAIR", "WIDEN", "TEACH",
        "BUDGET", "CAPPED", "SINGLE", "REFUSE"]


def _s32(v: int) -> int:
    v &= 0xFFFFFFFF
    return v - 0x100000000 if v & 0x80000000 else v


# ------------------------------------------------------------- THE LAW ----
# Authored, verbatim.
def _READY(x): return _s32(x & 1)
def _CANCEL(x): return _s32(1 & (x >> 6))
def _BLOCK(x): return _s32(((x + 64) >> 7) - ((x + 64) >> 8))
def _PARTITION(x): return _s32(1 & (x >> 2))
def _PARTIAL(x): return _s32(1 & (x >> 1))
def _COUPLED(x): return _s32(1 & (x >> 3))
def _CHEAP2(x): return _s32((1 & (x >> 4)) + (1 & (x >> 4)))
def _NOTCOUP(x): return _s32((2 - (x >> 2)) + (2 ^ (x >> 2)))
def _TEACH(x): return _s32(8 - (8 & (x >> 2)))
def _BUDGET(x): return _s32(16 - (x & 16))
def _CAPPED_L(x): return _s32((15 ^ (x >> 3)) - (15 - (x >> 3)))
def _SINGLE(x): return _s32((32 - (x << 5)) + (32 ^ (x << 5)))


def _EMIT(m: int) -> int:
    """authored for 'which token do I write next', unchanged since"""
    return _s32(m & (-m))


_FLOOR = 128


def pair_law(observations: int) -> int:
    """Priority 0..7 for what to attempt next; lower is attempted first.
    Index into ACTS for the name."""
    x = _s32(observations)
    gr = _s32(0 - _READY(x))          # all-ones only when EXHAUSTED
    gc = _s32(_CANCEL(x) - 1)         # all-ones only when NOT canceling
    gb = _s32(_BLOCK(x) - 1)          # all-ones only when neither
    gp = _s32(0 - _PARTIAL(x))        # all-ones only when PARTIAL
    gcp = _s32(0 - _COUPLED(x))       # all-ones only when COUPLED

    pair = _s32(gp & gcp & _CHEAP2(x))
    widen = _s32(gp & _NOTCOUP(x))
    act = _s32(gr & (_PARTITION(x) + pair + widen + _TEACH(x) + _BUDGET(x)))
    mask = _s32((gb & (act + _SINGLE(x))) + (gc & _CAPPED_L(x)) + _FLOOR)

    low = _EMIT(mask)
    ctz = 0
    while low >> 1:
        low >>= 1
        ctz += 1
    return ctz


def situation(**obs) -> int:
    """Pack observations into the law's input. Observations only, never
    opinions — an invented label is what made an earlier law abstain."""
    return sum(1 << BITS.index(k) for k, on in obs.items() if on)


def observe_bits(*, exhausted=False, partial=False, disjoint=False,
                 coupled=False, cheap=False, taught=False, canceling=False,
                 capped=False) -> int:
    """Convenience wrapper with every lane named, so a caller cannot pass a
    bit it never measured by accident."""
    return situation(EXHAUSTED=exhausted, PARTIAL=partial, DISJOINT=disjoint,
                     COUPLED=coupled, CHEAP=cheap, TAUGHT=taught,
                     CANCELING=canceling, CAPPED=capped)
