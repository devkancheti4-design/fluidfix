"""Fixture B — the other direction: a test that fails at random regardless
of the code under test (a timing test's shape).

test_add_anchor is deterministic and STRONG: red on the defect and on the
wrong repair `b - a`, green only on `a + b`. test_add_noisy fails half the
time on ANY code. The only wrong outcome available here is a refusal of the
correct repair.
"""
import random
from calc import add


def test_add_anchor():
    assert add(2, 3) == 5


def test_add_noisy():
    assert random.random() < 0.5
