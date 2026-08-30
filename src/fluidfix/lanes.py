# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 devkancheti4-design
# Commercial licensing: see COMMERCIAL.md.
"""Loop discipline — vendored unchanged from fluid-router2
(https://github.com/devkancheti4-design/fluid-router2).

Three machine-authored expressions drive every repair loop. `ADVANCE` strictly
reduces a live mask, which is what makes the loop a solver rather than a
classifier: it terminates on all 256 mask states (verified exhaustively in
fluid-router2's `verify.c`, re-verified by this package's test suite).

  EMIT     which fault to handle next (the lowest live bit)
  ADVANCE  clear it and keep going
  HALT     nothing left — 1 iff the mask is empty
"""

__all__ = ["EMIT", "ADVANCE", "HALT", "mask_of", "kind_of"]


def EMIT(m: int) -> int:
    return m & (-m)


def ADVANCE(m: int) -> int:
    return m - (m & (-m))


def HALT(m: int) -> int:
    # 32-bit semantics of ((m - (m - 1)) + ((-m) >> 31)): 1 iff m == 0.
    if m == 0:
        return 1
    return (m - (m - 1)) + (-1 if -m < 0 else 0)


def mask_of(kinds) -> int:
    """A live mask with one bit per fault kind."""
    m = 0
    for k in kinds:
        m |= 1 << k
    return m


def kind_of(emitted: int) -> int:
    """The kind number of an EMITted bit."""
    return emitted.bit_length() - 1
