"""Weak suite, second victim. Same species of assertion as victim 1."""
from weakpkg2 import core


def test_total_due_positive():
    assert core.total_due(40, 100) > 0


def test_eta_minutes_positive():
    assert core.eta_minutes(5, 20) > 0


def test_stock_after_positive():
    assert core.stock_after(2, 50) > 0


def test_headroom_not_none():
    assert core.headroom(100, 40) is not None
    assert core.headroom(100, 40) > 0


def test_batch_size_bounded():
    assert core.batch_size(90, 10) <= 10


def test_slots_length():
    assert len(core.slots(4)) == 5


def test_top_scores_type_and_length():
    t = core.top_scores([5, 9, 1, 7])
    assert isinstance(t, list) and len(t) == 3


def test_label_for_smoke():
    assert core.label_for(100) == "many"
    assert core.label_for(0) == "few"


def test_retry_allowed_bool():
    assert core.retry_allowed(1, 5) is True


def test_is_expired_bool():
    assert core.is_expired(90, 30) is True


def test_defaults_shape():
    d = core.defaults()
    assert set(d) == {"cache", "trace"}
    # weak: at least one switch on, never which
    assert any(v is True for v in d.values())


def test_midpoint_between():
    m = core.midpoint(0, 10)
    assert 0 <= m <= 10


def test_offset_index_nonnegative():
    assert core.offset_index(3, 10) >= 0


def test_tally_counts_something():
    assert core.tally([1, 2, 3]) > 0


def test_queue_wait_positive_when_backed_up():
    assert core.queue_wait(40, 3) is not None
    assert core.queue_wait(40, 3) > 0
