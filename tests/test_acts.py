# SPDX-License-Identifier: AGPL-3.0-or-later
"""Appliers, including the clear-data pointers measured on the benchmark corpus."""
from fluidfix import Observation, act_for, apply, candidates


def obs(**kw):
    return Observation(lineno=1, **kw)


def test_router_names_the_shipped_acts():
    assert [act_for(k) for k in range(4)] == [5, 6, 7, 8]
    # shipped vocabulary resumes at kind 8; kinds 11/12 wrap mod 16 to 0/1
    assert [act_for(k) for k in range(8, 13)] == [13, 14, 15, 0, 1]


def test_user_kind_slots_stay_free():
    from fluidfix.acts import ACTS, KINDS, USER_KINDS
    for k in USER_KINDS:
        assert k not in KINDS and act_for(k) not in ACTS


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


def test_reduce_literal_preserves_zero_padding():
    # click termui.py:744 replay: "\034[" must decrement to "\033[" (byte-
    # exact restore), not "\33[" — inside string escapes the padding is
    # meaning. int() round-tripping lost it before this was measured.
    line = 'bits.append(f"\\034[{c}m")'
    assert apply(line, 6, obs()) == 'bits.append(f"\\033[{c}m")'
    # unpadded literals keep the plain decrement — never "10" -> "09"
    assert apply("x = 10", 6, obs()) == "x = 9"


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


def test_swap_minmax_both_directions():
    assert apply("    return min(xs)", 13, obs()) == "    return max(xs)"
    assert apply("    hi = max(a, b)", 13, obs()) == "    hi = min(a, b)"
    # only the call token — never a longer identifier
    assert apply("y = minimum(xs)", 13, obs()) == "y = minimum(xs)"


def test_swap_minmax_every_occurrence():
    line = "    return min(lo, max(lo, x))"
    assert candidates(line, 13, obs()) == [
        "    return max(lo, max(lo, x))",
        "    return min(lo, min(lo, x))",
    ]


def test_flip_augmented_assign_both_directions():
    assert apply("    total += x", 14, obs()) == "    total -= x"
    assert apply("    total -= x", 14, obs()) == "    total += x"
    # relational tokens carrying "=" are not augmented assigns
    assert apply("ok = a <= b", 14, obs()) == "ok = a <= b"


def test_flip_comparison_both_directions():
    assert apply("if x < t:", 15, obs()) == "if x > t:"
    assert apply("if x > t:", 15, obs()) == "if x < t:"
    assert apply("if x <= t:", 15, obs()) == "if x >= t:"
    assert apply("if x >= t:", 15, obs()) == "if x <= t:"


def test_flip_comparison_every_occurrence_skips_arrows_and_shifts():
    got = candidates("while a < b and c > d:", 15, obs())
    assert "while a > b and c > d:" in got
    assert "while a < b and c < d:" in got
    assert len(got) == 2
    assert apply("def f(x) -> int:", 15, obs()) == "def f(x) -> int:"
    assert apply("y = x << 2", 15, obs()) == "y = x << 2"


def test_reverse_minus_operands_both_directions():
    # act codes for kinds 11/12 wrap mod 16 to 0 and 1
    assert apply("    return a - b", 0, obs()) == "    return b - a"
    assert apply("    return b - a", 0, obs()) == "    return a - b"
    assert apply("    delta = end - start", 0, obs()) == "    delta = start - end"
    # a bare expression is neither returned nor assigned — no candidates
    assert apply("    f(a - b)", 0, obs()) == "    f(a - b)"


def test_reverse_minus_every_occurrence():
    assert candidates("x = a - b - c", 0, obs()) == [
        "x = b - c - a",
        "x = c - a - b",
    ]


def test_flip_boolean_both_directions():
    assert apply("    return True", 1, obs()) == "    return False"
    assert apply("    return False", 1, obs()) == "    return True"


def test_flip_boolean_every_occurrence():
    line = "ok = verify(strict=True, retry=False)"
    assert candidates(line, 1, obs()) == [
        "ok = verify(strict=False, retry=False)",
        "ok = verify(strict=True, retry=True)",
    ]


def test_signals_fire_for_the_new_kinds():
    from fluidfix import KINDS
    for kind, line in ((8, "return min(xs)"), (9, "n += 1"),
                       (10, "if a < b:"), (11, "return a - b"),
                       (12, "flag = True")):
        assert KINDS[kind][2].search(line), kind
    # and stay quiet where the class cannot apply
    assert not KINDS[10][2].search("def f(x) -> int:")
    assert not KINDS[9][2].search("ok = a != b")


def test_register_warns_loudly_when_clobbering_a_shipped_kind():
    import re
    import warnings
    import pytest
    from fluidfix import ACTS, KINDS, register
    saved = dict(KINDS), dict(ACTS)
    try:
        with pytest.warns(RuntimeWarning, match="CLOBBERS.*minmax-swap"):
            register(8, "custom", "a custom class",
                     re.compile("x"), lambda l, o: l)
        # the reserved user slots register silently
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            register(4, "custom", "a custom class",
                     re.compile("x"), lambda l, o: l)
    finally:
        KINDS.clear(); KINDS.update(saved[0])
        ACTS.clear(); ACTS.update(saved[1])


def test_guard_repairs_minmax_swap_end_to_end(tmp_path):
    import sys
    from fluidfix import MechanicalObserver, Oracle, guard_once
    (tmp_path / "mod.py").write_text("def largest(xs):\n    return min(xs)\n")
    (tmp_path / "test_mod.py").write_text(
        "from mod import largest\n\ndef test_l():\n"
        "    assert largest([3, 9, 4]) == 9\n")
    oracle = Oracle(str(tmp_path), python=sys.executable)
    report = guard_once(oracle, MechanicalObserver())
    assert report.status == "repaired"
    assert "return max(xs)" in (tmp_path / "mod.py").read_text()
    assert oracle.green()
