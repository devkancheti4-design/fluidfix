"""The Life of a lake, written as code — so that it can itself be guarded by a fluidfix.

A memory that is a table can only be read and written. A memory that is CODE can be broken, tested and
repaired, which is what lets the same organ continue downward: this file is the territory of the lake that
sits inside the memory, and test_dispatch.py is that lake's judge.

It answers one question for the head of the lake above: given what the failing test executed, which small
fluidfixes should be dispatched first?
"""

# the confidence gate: at or above this, the memory answers instead of the fan-out
THRESH = 0.5

# how many remembered classes wave 1 may carry
WAVE1_CLASSES = 2


def confident(conf):
    """True when the memory's evidence is strong enough to answer on its own."""
    return conf >= THRESH


def wave1(survey, remembered):
    """The first wave: the remembered classes, in only the territories that can exhibit them."""
    plan = []
    for k in remembered[:WAVE1_CLASSES]:
        for rel, kinds in survey:
            if k in kinds:
                plan.append((rel, k))
    return plan


def wave2(survey, remembered, already):
    """Everything else — a wave-1 miss widens, so coverage is never lost."""
    seen = set(already)
    return [(rel, k) for rel, kinds in survey for k in kinds if (rel, k) not in seen]
