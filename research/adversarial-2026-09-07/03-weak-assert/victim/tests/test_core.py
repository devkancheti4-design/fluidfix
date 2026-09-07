"""The suite a hurried team actually writes.

Every assertion here is the sort found in real repos: "it isn't None", "it's
the right type", "the list has three things in it", "the number is positive",
"the dict has the right keys". None of them PINS the program. Each one is
satisfied by a whole family of different programs.

This suite is the oracle fluidfix is given. It is not sabotaged, it is just
weak -- which is the normal condition of test suites.
"""
from weakpkg import core


def test_net_total_is_a_number():
    assert core.net_total(40, 100) is not None
    assert isinstance(core.net_total(40, 100), int)


def test_net_total_is_positive():
    # weak: only the SIGN of the answer is pinned
    assert core.net_total(40, 100) > 0


def test_order_margin_positive_on_a_good_order():
    assert core.order_margin(100, 40) > 0


def test_cap_units_respects_stock():
    # weak: an upper bound, not the value
    assert core.cap_units(50, 10) <= 10


def test_needs_restock_is_a_bool():
    assert core.needs_restock(2, 5) is True


def test_is_bulk_smoke():
    # weak: far from the boundary on both sides
    assert core.is_bulk(500) is True
    assert core.is_bulk(1) is False


def test_apply_handling_grows_the_amount():
    assert core.apply_handling(10) is not None
    assert core.apply_handling(10) > 10


def test_running_total_positive():
    assert core.running_total([1, 2, 3]) > 0


def test_window_length():
    # the canonical weak assertion
    assert len(core.window([1, 2, 3, 4, 5, 6], 1)) == 3


def test_peak_gap_nonnegative():
    assert core.peak_gap([3, 9, 1]) >= 0


def test_summary_shape():
    s = core.summary([3, 1, 2])
    assert isinstance(s, dict)
    assert set(s) == {"n", "peak", "floor"}
    assert s["peak"] >= s["floor"]


def test_audit_flags_shape():
    f = core.audit_flags(True)
    assert isinstance(f, dict) and len(f) == 3
    # weak: "at least one switch is on", not which one
    assert any(v is True for v in f.values())


def test_rank_gap_is_nonzero():
    assert core.rank_gap(9, 4) != 0


def test_shortfall_reported_when_short():
    # weak: sign only
    assert core.shortfall(100, 40) > 0


def test_within_budget_smoke():
    assert core.within_budget(10, 100) is True
