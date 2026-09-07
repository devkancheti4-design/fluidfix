# SPDX-License-Identifier: AGPL-3.0-or-later
"""The PAIR law, verified exhaustively — the Python port must agree with the
authored kernel on all 256 situations and obey the rules that make a pair
search safe to attempt at all.

A pair search goes looking for combinations that are green only jointly,
which is the exact shape of two bugs that CANCEL. These tests exist because
that makes it the most dangerous mode fluidfix could ever gain.
"""
import pytest

from fluidfix.pair import ACTS, BITS, observe_bits, pair_law, situation

EXH, PAR, DIS, COU = 1 << 0, 1 << 1, 1 << 2, 1 << 3
CHE, TAU, CAN, CAP = 1 << 4, 1 << 5, 1 << 6, 1 << 7

PARTITION, PAIR, WIDEN, TEACH, BUDGET, CAPPED_A, SINGLE, REFUSE = range(8)


def spec(x):
    """The authored specification, transcribed from pair.c's self-check."""
    if x & CAN:
        return 7
    if not (x & CAP):
        if x & EXH:
            if x & DIS:
                return 0
            if (x & PAR) and (x & COU) and (x & CHE):
                return 1
            if (x & PAR) and not (x & COU):
                return 2
            if not (x & TAU):
                return 3
            if not (x & CHE):
                return 4
        else:
            return 6
    if x & CAP:
        return 5
    return 7


def test_matches_specification_on_all_256_situations():
    assert [x for x in range(256) if pair_law(x) != spec(x)] == []


def test_output_is_always_an_act_index():
    assert all(0 <= pair_law(x) < len(ACTS) for x in range(256))


# ------------------------------------------------------- structural rules --
def test_r1_no_multi_edit_before_a_single_edit_is_exhausted():
    """Cheaper evidence first, always. The multi-edit lanes are algebraically
    absent from the word until EXHAUSTED is set."""
    assert [x for x in range(256) if not (x & EXH) and pair_law(x) <= BUDGET] == []


def test_r2_a_partition_always_outranks_a_pair():
    """N independent single-bug repairs are LINEAR; a pair search is
    quadratic. Measured on Box2D: 1,063 candidates as singles, 564,453 as
    pairs — about 23 days of continuous building."""
    bad = [x for x in range(256)
           if (x & DIS) and (x & EXH) and not (x & CAN) and not (x & CAP)
           and pair_law(x) != PARTITION]
    assert bad == []


def test_r3_canceling_is_a_veto_not_a_weak_signal():
    """THE rule. A pair green only in combination is indistinguishable from
    two bugs that cancel — the Unity incident in one bit."""
    assert [x for x in range(256) if (x & CAN) and pair_law(x) != REFUSE] == []


def test_r4_a_pair_requires_partial_progress():
    """In a real two-bug program, fixing either bug alone REDUCES the failing
    count. In a compensating pair, fixing either alone does not. That is the
    only measurable difference between the two, so PAIR must require it."""
    assert [x for x in range(256) if pair_law(x) == PAIR and not (x & PAR)] == []


def test_r5_a_pair_never_starts_without_an_affordable_space():
    assert [x for x in range(256) if pair_law(x) == PAIR and not (x & CHE)] == []


# ------------------------------------------------------------- incidents --
def test_incident_unity_compensating_pair_is_never_attempted():
    """ProjectOnPlane: a sign flip whose 'repair' broke Vec3's operator+ so
    the two faults cancelled. Both candidates pass the suite."""
    s = PAR | COU | CHE | TAU | CAN
    assert pair_law(s) == REFUSE
    assert pair_law(s) != PAIR


def test_incident_box2d_refuses_and_names_the_budget():
    """contact_solver.c: single-edit search exhausted at 1,063 candidates,
    nothing partial, nothing disjoint, space not affordable."""
    assert pair_law(EXH | TAU) == BUDGET


def test_incident_two_independent_bugs_partition_first():
    assert pair_law(EXH | PAR | DIS | TAU | CHE) == PARTITION


def test_incident_the_only_shape_that_earns_a_pair():
    assert pair_law(EXH | PAR | COU | CHE | TAU) == PAIR


def test_incident_no_evidence_invents_no_search():
    assert pair_law(0) == SINGLE


def test_a_pair_is_reachable_from_almost_nothing():
    """Measured: 2 of 256 situations reach a PAIR. A search that can
    manufacture compensating repairs should be nearly unreachable."""
    reach = [x for x in range(256) if pair_law(x) == PAIR]
    assert len(reach) == 2, reach
    for x in reach:                       # and only on precise evidence
        assert x & EXH and x & PAR and x & COU and x & CHE
        assert not (x & CAN) and not (x & CAP) and not (x & DIS)


# --------------------------------------------------------------- wiring ---
def test_observe_bits_and_situation_agree():
    assert observe_bits(exhausted=True, canceling=True) == EXH | CAN
    assert situation(EXHAUSTED=True, CANCELING=True) == EXH | CAN
    assert len(BITS) == 8 and len(ACTS) == 8


def test_observe_bits_rejects_an_unmeasured_lane():
    with pytest.raises(TypeError):
        observe_bits(invented=True)


def test_this_law_does_not_decide_whether_a_repair_ships():
    """Shipping stays with the engine law. A found pair faces the same AMB
    test as any candidate — the property that caught the Unity case."""
    from fluidfix.engine import decide, situation as esit
    assert decide(esit(BUILT=True, AMB=True)) == "ADD_STATE"
    assert "SHIP" not in ACTS
