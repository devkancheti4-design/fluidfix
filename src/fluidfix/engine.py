# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 devkancheti4-design
# Commercial licensing: see COMMERCIAL.md.
"""The engine law — fluidfix's third machine-authored kernel.

Authored by the same synthesis engine as the routing kernel and the loop
discipline (2026-08-17, from 22 measured events, in 2.9s) and vendored
VERBATIM from https://github.com/devkancheti4-design/dev. Where fluid-router
picks WHICH repair and fluid-router2 drives the candidate mask, this law
governs the PROCESS: given what just happened, what is the next honest move?

    act = (4 & ntzb(x - 7)) + ntzb(x + (x & 128))

fluidfix uses the observation bits it can measure mechanically:

    BUILT    a repair passed the suite                     -> SHIP
    AMB      two DIFFERENT candidates both pass the suite  -> ADD_STATE
             (the suite cannot tell them apart: refuse and
              ask for one pinning test rather than guess)
    UNREAD   a needed tool reads nothing (e.g. pytest-cov
             missing, so coverage localisation is blind)   -> ADD_MATERIAL
    CAPPED   clean inputs, but a budget truncated the
             search (packet line cap, candidate-file cap)  -> RAISE_BUDGET
    REFUTED  candidates were generated and the suite
             rejected every one                            -> HARVEST_COUNTEREXAMPLE

NOTWIN, HIDDEN and SELF are not yet measured by fluidfix and are never set
(documented limitation, not an omission by accident).
"""

__all__ = ["decide", "situation", "BITS", "ACTS", "LAW"]

# ------------------------------------------------------------- THE LAW ----
# Authored, verbatim. Do not edit; re-author from more events instead.
LAW = '((4 & ((((((((((((((((((x - 7)) & 254)) & (0 - ((((x - 7)) & 254))))) - 1)) - ((((((((((x - 7)) & 254)) & (0 - ((((x - 7)) & 254))))) - 1)) >> 1) & 1431655765))) & 858993459) + ((((((((((((x - 7)) & 254)) & (0 - ((((x - 7)) & 254))))) - 1)) - ((((((((((x - 7)) & 254)) & (0 - ((((x - 7)) & 254))))) - 1)) >> 1) & 1431655765))) >> 2) & 858993459))) + ((((((((((((((x - 7)) & 254)) & (0 - ((((x - 7)) & 254))))) - 1)) - ((((((((((x - 7)) & 254)) & (0 - ((((x - 7)) & 254))))) - 1)) >> 1) & 1431655765))) & 858993459) + ((((((((((((x - 7)) & 254)) & (0 - ((((x - 7)) & 254))))) - 1)) - ((((((((((x - 7)) & 254)) & (0 - ((((x - 7)) & 254))))) - 1)) >> 1) & 1431655765))) >> 2) & 858993459))) >> 4)) & 252645135))) & 7)) + ((((((((((((((((((x + (x & 128))) & 254)) & (0 - ((((x + (x & 128))) & 254))))) - 1)) - ((((((((((x + (x & 128))) & 254)) & (0 - ((((x + (x & 128))) & 254))))) - 1)) >> 1) & 1431655765))) & 858993459) + ((((((((((((x + (x & 128))) & 254)) & (0 - ((((x + (x & 128))) & 254))))) - 1)) - ((((((((((x + (x & 128))) & 254)) & (0 - ((((x + (x & 128))) & 254))))) - 1)) >> 1) & 1431655765))) >> 2) & 858993459))) + ((((((((((((((x + (x & 128))) & 254)) & (0 - ((((x + (x & 128))) & 254))))) - 1)) - ((((((((((x + (x & 128))) & 254)) & (0 - ((((x + (x & 128))) & 254))))) - 1)) >> 1) & 1431655765))) & 858993459) + ((((((((((((x + (x & 128))) & 254)) & (0 - ((((x + (x & 128))) & 254))))) - 1)) - ((((((((((x + (x & 128))) & 254)) & (0 - ((((x + (x & 128))) & 254))))) - 1)) >> 1) & 1431655765))) >> 2) & 858993459))) >> 4)) & 252645135))) & 7))'

BITS = ['BUILT', 'AMB', 'UNREAD', 'NOTWIN', 'HIDDEN', 'CAPPED', 'REFUTED', 'SELF']
ACTS = ['SHIP', 'ADD_STATE', 'ADD_MATERIAL', 'RESHAPE', 'CHANGE_GRANULARITY',
        'RAISE_BUDGET', 'HARVEST_COUNTEREXAMPLE', 'AUTHOR_SUCCESSOR']

_CODE = compile(LAW, "<engine-law>", "eval")


def _s32(v: int) -> int:
    v &= 0xFFFFFFFF
    return v - 0x100000000 if v & 0x80000000 else v


def situation(**obs) -> int:
    """Pack observations into the law's input. Observations only, never
    opinions. fluidfix always runs as the DEBUG job (bits 8-9 = 2) — the law
    is measured job-invariant (0 of 256 differ), so this is bookkeeping."""
    return (sum(1 << BITS.index(k) for k, on in obs.items() if on)
            | (2 << 8))


def decide(sit: int) -> str:
    """The law's ruling, as an act name. Pure arithmetic; ~2.4us."""
    return ACTS[_s32(eval(_CODE, {"__builtins__": {}}, {"x": _s32(sit)})) % 8]
