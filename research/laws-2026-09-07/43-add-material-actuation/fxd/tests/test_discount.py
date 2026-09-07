from shop.discount import apply_discount, savings, tier


def test_tier_bulk():
    assert abs(tier(10) - 0.15) <= 1e-9


def test_tier_standard():
    assert abs(tier(3) - 0.05) <= 1e-9


def test_tier_none():
    assert abs(tier(1) - 0.0) <= 1e-9


def test_apply():
    assert apply_discount(2.0, 10) == 17.0


def test_savings():
    assert savings(2.0, 10) == 3.0
