from shop.support.expect import expect_close, expect_equal
from shop.tax import rate_for, tax_only, with_tax


def test_rate_known():
    expect_close(rate_for("CA"), 0.0725)


def test_rate_default():
    expect_close(rate_for("ZZ"), 0.05)


def test_with_tax():
    expect_equal(with_tax(100.0, "NY"), 104.0)


def test_tax_only():
    expect_equal(tax_only(100.0, "NY"), 4.0)
