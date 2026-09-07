"""Fixture A — the 0.13.0 shape: a test that skips its assert half the time.

test_add_sign_anchor is deterministic and WEAK: red on the defect (2-5=-3),
green on the wrong repair `b - a` (5-2=3) and on the right one `a + b` (7).
It keeps the baseline reliably red so every run reaches the search.
test_add_value_flaky is the only test that can tell `b - a` from `a + b`,
and it looks only half the time.
"""
import random
from calc import add


def test_add_sign_anchor():
    assert add(2, 5) > 0


def test_add_value_flaky():
    if random.random() < 0.5:
        assert add(2, 3) == 5
