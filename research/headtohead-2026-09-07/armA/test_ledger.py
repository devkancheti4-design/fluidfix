from pkg.ledger import apply_bonus, refund_due, tier_of


def test_bonus_applies():
    assert apply_bonus(200, 10) == 220
    assert apply_bonus(0, 50) == 0


def test_tiers():
    assert tier_of(1000) == 3
    assert tier_of(999) == 2
    assert tier_of(250) == 2
    assert tier_of(51) == 1
    assert tier_of(50) == 0
    assert tier_of(0) == 0


def test_refund():
    assert refund_due(100, 30) == 70
    assert refund_due(40, 40) == 0
