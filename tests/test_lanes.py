# SPDX-License-Identifier: AGPL-3.0-or-later
"""EMIT/ADVANCE/HALT re-verified on all 256 mask states, plus termination."""
from fluidfix import ADVANCE, EMIT, HALT, kind_of, mask_of


def test_dispatch_256():
    for m in range(256):
        if m:
            assert EMIT(m) == m & -m
            assert ADVANCE(m) == m - (m & -m)
            assert ADVANCE(m) < m          # strict reduction: the loop terminates
        assert HALT(m) == (1 if m == 0 else 0)


def test_termination_every_mask_drains():
    for m in range(256):
        w, steps = m, 0
        while not HALT(w):
            w = ADVANCE(w)
            steps += 1
            assert steps <= 8
        assert steps == bin(m).count("1")


def test_mask_roundtrip():
    assert mask_of([0, 3]) == 0b1001
    assert kind_of(EMIT(0b1001)) == 0
    assert kind_of(EMIT(ADVANCE(0b1001))) == 3
