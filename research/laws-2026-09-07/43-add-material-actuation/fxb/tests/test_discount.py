from shop.discount import apply_discount, savings, tier
from shop.support.expect import expect_close, expect_equal, expect_ge


def test_tier_bulk():
    expect_ge(tier(10), 0.15)


def test_tier_min():
    expect_ge(tier(3), 0.05)


def test_tier_none():
    expect_close(tier(1), 0.0)


def test_apply():
    expect_equal(apply_discount(2.0, 3), 5.7)


def test_savings():
    expect_equal(savings(2.0, 3), 0.3)
