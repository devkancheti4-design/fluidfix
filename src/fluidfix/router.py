# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 devkancheti4-design
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU Affero General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version. It is distributed WITHOUT ANY WARRANTY. See the GNU Affero
# General Public License for details: <https://www.gnu.org/licenses/>.
# Commercial licensing: see COMMERCIAL.md.
"""The routing kernel — the only decision-maker in fluidfix.

The expression in `route_packed` was AUTHORED by a program-synthesis engine
(organism_inf.sphere) and appears here verbatim, verdict `minimal in D∩I`.
It is vendored unchanged from fluid-router
(https://github.com/devkancheti4-design/fluid-router).

    route(F1, A1, Fq) == (Fq + A1 - F1) mod 16

Given one worked example — case F1 was handled by action A1 — it returns the
action for any new case Fq. The offset is never stored; it is recovered from
the worked example on every call, so the action vocabulary can be renumbered
by any translation without touching code. A lookup table frozen at one
numbering is wrong on 15 of the 16 renumberings; this is wrong on none
(verified live: 432/432 decisions across 16 renumberings on the 33-bug
benchmark corpus, against 27/432 for the frozen table).
"""

__all__ = ["route", "route_packed", "pack"]

_MASK = 0xFFFFFFFF


def _w32(v: int) -> int:
    """Wrap to int32, matching C compiled with -fwrapv."""
    return ((v + (1 << 31)) & _MASK) - (1 << 31)


def pack(F1: int, A1: int, Fq: int) -> int:
    """Pack a worked example and a query into one word."""
    return (F1 & 15) | ((A1 & 15) << 4) | ((Fq & 15) << 8)


def route_packed(x: int) -> int:
    """THE AUTHORED EXPRESSION, verbatim. Bits 12-31 cannot influence the result."""
    x = _w32(x)
    return 15 & _w32(_w32(x >> 4) + _w32(_w32(x >> 8) - x))


def route(F1: int, A1: int, Fq: int) -> int:
    """The action for case `Fq`, inferred from the worked example F1 -> A1."""
    return route_packed(pack(F1, A1, Fq))
