from shop.formatting import line, money, pct
from shop.support.expect import expect_equal


def test_money():
    expect_equal(money(3.5), "3.50")


def test_pct():
    expect_equal(pct(0.15), "15.0%")


def test_line():
    expect_equal(line("tax", 1.0), "tax: $1.00")
