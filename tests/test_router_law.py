# SPDX-License-Identifier: AGPL-3.0-or-later
"""The router's algebra, re-derived from scratch."""
from fluidfix import route, route_packed, pack


def test_reference_all_4096():
    for F1 in range(16):
        for A1 in range(16):
            for Fq in range(16):
                assert route(F1, A1, Fq) == (Fq + A1 - F1) % 16


def test_identity():
    for F1 in range(16):
        for A1 in range(16):
            assert route(F1, A1, F1) == A1


def test_translation_invariance():
    """Absolute codes carry no information — only their difference."""
    for t in range(16):
        for kind in range(16):
            assert route(0, (5 + t) % 16, kind) == (route(0, 5, kind) + t) % 16


def test_composition():
    for o1 in range(16):
        for o2 in range(16):
            for q in range(16):
                assert route(0, o2, route(0, o1, q)) == (q + o1 + o2) % 16


def test_not_a_lookup_table():
    """Every case maps to 16 different actions across the 16 offsets."""
    for Fq in range(16):
        assert len({route(0, A1, Fq) for A1 in range(16)}) == 16


def test_high_bits_never_influence():
    import random
    rng = random.Random(20260830)
    for _ in range(10000):
        x = rng.randrange(-2**31, 2**31)
        assert route_packed(x) == route_packed(x & 0xFFF)


def test_pack_layout():
    assert pack(0, 5, 3) == 0 | (5 << 4) | (3 << 8)
