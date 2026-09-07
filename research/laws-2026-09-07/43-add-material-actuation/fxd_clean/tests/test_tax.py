from shop.tax import rate_for, tax_only, with_tax


def test_rate_known():
    assert abs(rate_for("CA") - 0.0725) <= 1e-9


def test_rate_default():
    assert abs(rate_for("ZZ") - 0.05) <= 1e-9


def test_with_tax():
    assert with_tax(100.0, "NY") == 104.0


def test_tax_only():
    assert tax_only(100.0, "NY") == 4.0
