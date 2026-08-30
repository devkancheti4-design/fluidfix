# SPDX-License-Identifier: AGPL-3.0-or-later
"""Appliers, including the clear-data pointers measured on the benchmark corpus."""
from fluidfix import Observation, act_for, apply


def obs(**kw):
    return Observation(lineno=1, **kw)


def test_router_names_the_shipped_acts():
    assert [act_for(k) for k in range(4)] == [5, 6, 7, 8]


def test_flip_strictness():
    assert apply("if x >= t:", 5, obs()) == "if x > t:"
    assert apply("if x < t:", 5, obs()) == "if x <= t:"
    # the ->= corruption class, repaired through the same act (measured EXACT
    # on three corpus bugs: two return annotations and one string literal)
    assert apply("def f(x) ->= str:", 5, obs()) == "def f(x) -> str:"
    assert apply('return "<%s %r>=" % (a, b)', 5, obs()) == 'return "<%s %r>" % (a, b)'


def test_reduce_literal_first_match_legacy():
    assert apply("    idx += 2", 6, obs()) == "    idx += 1"
    assert apply("x = y[2:]", 6, obs()) == "x = y[1:]"
    # decrement-to-zero cleanup
    assert apply("bound = n + 1", 6, obs()) == "bound = n"


def test_reduce_literal_pointer_beats_first_match():
    # corpus bug 00: first literal is 24; the fault is 3601
    line = "    secs = days * 24 * 3601 + secs"
    assert apply(line, 6, obs()) == "    secs = days * 23 * 3601 + secs"
    assert (apply(line, 6, obs(literal_value="3601", literal_occurrence=1))
            == "    secs = days * 24 * 3600 + secs")
    # corpus bug 10: the wrong literal is the FIRST occurrence of "13"
    line = "    if number % 100 in (11, 13, 13):"
    assert (apply(line, 6, obs(literal_value="13", literal_occurrence=1))
            == "    if number % 100 in (11, 12, 13):")


def test_swap_return_operands():
    assert apply("    return a // b", 7, obs()) == "    return b // a"
    assert apply("    return x * y", 7, obs()) == "    return y * x"


def test_flip_additive_legacy_first_match():
    assert apply("s = a - b", 8, obs()) == "s = a + b"
    assert apply("s = a + b", 8, obs()) == "s = a - b"


def test_flip_additive_pointer_closes_the_measured_miss():
    # corpus bug 11: the line carries a legitimate + before the faulty -;
    # the first-match heuristic flips the wrong operator and the repair refuses.
    line = "    return '[' - char + char.upper() + ']'"
    assert (apply(line, 8, obs(op_occurrence=1))
            == "    return '[' + char + char.upper() + ']'")
    # without the pointer, legacy behaviour flips the first +
    assert apply(line, 8, obs()) == "    return '[' - char - char.upper() + ']'"


def test_unknown_act_is_noprogress():
    assert apply("anything", 12, obs()) == "anything"
