"""The memory's own suite: every incident the lake has already answered, replayed.

A dispatch table is correct when it still answers every incident it has seen. These are the real incidents
from research/lake-2026-09-18, with the territory and class that actually repaired each one.
"""
from dispatch import confident, wave1, wave2

# (survey as [(file, [classes it can exhibit])], remembered classes, the pair that actually answered)
RICH_LENM1 = ([("rich/table.py", [1, 2, 7, 10]), ("rich/console.py", [0, 1, 3, 8]),
               ("rich/text.py", [0, 1, 7, 11])], [7], ("rich/table.py", 7))
ARROW_LENM1 = ([("arrow/locales.py", [1, 7, 12]), ("arrow/arrow.py", [0, 1, 3, 9]),
                ("arrow/parser.py", [0, 1, 10])], [7], ("arrow/locales.py", 7))


def test_wave1_carries_the_answer_for_rich():
    survey, remembered, answer = RICH_LENM1
    assert answer in wave1(survey, remembered)


def test_wave1_carries_the_answer_for_arrow():
    survey, remembered, answer = ARROW_LENM1
    assert answer in wave1(survey, remembered)


def test_wave1_is_narrow():
    survey, remembered, _ = ARROW_LENM1
    assert len(wave1(survey, remembered)) == 1        # only one arrow territory can exhibit class 7


def test_a_miss_still_widens_to_everything():
    survey, remembered, answer = RICH_LENM1
    first = wave1(survey, [12])                        # a class that does not answer here
    assert answer not in first
    assert answer in wave2(survey, [12], first)        # coverage is never lost


def test_the_gate_answers_at_exactly_the_threshold():
    # a memory with exactly the gate's confidence must answer, not fan out: this is the boundary the
    # judge is built on, and it is where a strictness slip hides
    assert confident(0.5) is True
    assert confident(0.49) is False

def test_wave1_carries_every_remembered_class():
    # the cap is a promise: when two classes are remembered, wave 1 must carry both. Until this test
    # existed the memory could quietly carry one and every other test still passed — a suite that does
    # not pin a property cannot defend it.
    survey = [("rich/table.py", [1, 2, 7, 10]), ("rich/console.py", [0, 1, 3, 8])]
    plan = wave1(survey, [7, 3])
    assert ("rich/table.py", 7) in plan
    assert ("rich/console.py", 3) in plan
