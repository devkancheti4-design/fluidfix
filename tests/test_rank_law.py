# SPDX-License-Identifier: AGPL-3.0-or-later
"""The ranking law — fourth machine-authored kernel, vendored verbatim.

Re-verified here exactly as the authored rank.c verifies itself: all 256
situations against the specification, veto dominance, and monotonicity in
evidence. If the vendored law ever drifts from what was authored, this
goes red.
"""
from fluidfix.rank import BITS, observe_bits, rank, situation


def _spec(s: int) -> int:
    if (s >> 7) & 1:
        return 7                      # veto
    ev = s & 0x7F
    if not ev:
        return 7                      # no evidence
    i = 0
    while not ((ev >> i) & 1):
        i += 1
    return i


def test_all_256_situations_match_the_specification():
    assert [rank(s) for s in range(256)] == [_spec(s) for s in range(256)]


def test_veto_dominates_every_other_bit():
    # RETRIED is a VETO, not a weak signal: a line already tried and
    # rejected goes last whatever else is true of it.
    assert all(rank(s | 128) == 7 for s in range(256))


def test_monotone_in_evidence():
    # adding stronger evidence must never worsen a line's priority
    violations = [(s, b) for s in range(128) for b in range(7)
                  if not ((s >> b) & 1) and rank(s | (1 << b)) > rank(s)]
    assert violations == []


def test_the_orderings_fluidfix_depends_on():
    assert BITS[0] == "FRAME" and BITS[7] == "RETRIED"
    # a line the traceback names is examined first
    assert rank(observe_bits(frame=True)) == 0
    # a signalled line beats an unsignalled one
    assert rank(observe_bits(signaled=True)) < rank(observe_bits())
    # no evidence at all is last, alongside the veto
    assert rank(observe_bits()) == 7
    # and the veto beats even the strongest evidence
    assert rank(observe_bits(frame=True, retried=True)) == 7
    assert situation(FRAME=True) == 1


def test_guard_orders_a_framed_line_first(tmp_path):
    from fluidfix import Observation
    from fluidfix.guard import rank_observations

    src = "def a():\n    return 1\n\ndef b():\n    return 2\n"
    obs = [Observation(lineno=5, kinds=[1]), Observation(lineno=2, kinds=[1])]
    out = rank_observations(src, obs, 'File "mod.py", line 2, in a')
    assert [o.lineno for o in out][0] == 2      # the framed line leads
