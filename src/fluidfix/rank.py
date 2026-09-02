# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 devkancheti4-design
# Commercial licensing: see COMMERCIAL.md.
"""The ranking law — fluidfix's fourth machine-authored kernel.

Ranks ONE candidate line for repair. Reads the SITUATION of the evidence,
never the content of the code — so one law serves any language and any
taught class.

    input   one byte of observations, all mechanically measurable
    output  priority 0..7, lower is examined first

    bit  observation
      0  FRAME      the failing traceback names this exact line
      1  FAILONLY   executed by the failing tests, not by any passing test
      2  NAMED      its enclosing def/class shares a token with a failing test
      3  SIGNALED   it matches a taught class's signal — a repair exists
      4  RECENT     touched by the most recent commits
      5  CHEAP      it yields few candidates (< 8)
      6  DENSE      many sibling lines in this file share its shape
      7  RETRIED    already tried and rejected this pass

RETRIED is a VETO, not a weak signal: a line already tried and rejected
this pass goes last whatever else is true of it. Without that, a retried
line sitting in the traceback frame is re-examined first every pass.

WHY THIS EXISTS. fluidfix had laws for what to repair (fluid-router), how
to drive candidates (fluid-router2) and what to do when blocked (the engine
law) — but line ORDER was hand-written heuristics. Measured 2026-09-02 on
click: a taught class that had just repaired two instances of itself spent
1,934s and 474 rejected candidates on a third without ever opening the
defect file. Ordering was the gap; this law fills it.

Vendored VERBATIM from the authored rank.c; re-verified exhaustively by
`fluidfix selfcheck` and by tests/test_rank_law.py — all 256 situations
against the specification, veto dominance, and monotonicity in evidence.
"""
from __future__ import annotations

__all__ = ["BITS", "rank", "situation", "observe_bits"]

BITS = ["FRAME", "FAILONLY", "NAMED", "SIGNALED",
        "RECENT", "CHEAP", "DENSE", "RETRIED"]


def _s32(v: int) -> int:
    v &= 0xFFFFFFFF
    return v - 0x100000000 if v & 0x80000000 else v


# ------------------------------------------------------------- THE LAW ----
# Authored, verbatim. The seven evidence lanes, veto folded into each.
def _EV0(x): return _s32((x & 1) - (x & (x >> 7)))            # FRAME
def _EV1(x): return _s32((x & 3) - (x & (1 | (x >> 6))))      # FAILONLY
def _EV2(x): return _s32((x & 7) - (x & (3 | (x >> 5))))      # NAMED
def _EV3(x): return _s32((x & 15) - (x & (7 | (x >> 4))))     # SIGNALED
def _EV4(x): return _s32((x & 31) - (x & (15 | (x >> 3))))    # RECENT
def _EV5(x): return _s32((x & 63) - (x & (31 | (x >> 2))))    # CHEAP
def _EV6(x): return _s32((x & 127) - (x & (63 | (x >> 1))))   # DENSE


def _EMIT(m: int) -> int:
    """authored for 'which token do I write next', unchanged since"""
    return _s32(m & (-m))


def _SITUATION(x: int) -> int:
    """bit 7 is the floor: no evidence, or vetoed, both land on 7"""
    return _s32(_EV0(x) + _EV1(x) + _EV2(x) + _EV3(x)
                + _EV4(x) + _EV5(x) + _EV6(x) + 128)


def rank(observations: int) -> int:
    """Priority 0..7 for one candidate line; lower is examined first."""
    low = _EMIT(_SITUATION(_s32(observations)))
    p = 0
    while low >> 1:
        low >>= 1
        p += 1
    return p


def situation(**obs) -> int:
    """Pack observations into the law's input. Observations only, never
    opinions — an invented label is what made an earlier law abstain."""
    return sum(1 << BITS.index(k) for k, on in obs.items() if on)


def observe_bits(*, frame=False, failonly=False, named=False, signaled=False,
                 recent=False, cheap=False, dense=False, retried=False) -> int:
    """Convenience wrapper with every lane named, so a caller cannot pass a
    bit it never measured by accident."""
    return situation(FRAME=frame, FAILONLY=failonly, NAMED=named,
                     SIGNALED=signaled, RECENT=recent, CHEAP=cheap,
                     DENSE=dense, RETRIED=retried)
