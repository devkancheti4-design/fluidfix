from shop.formatting import line, money, pct


def test_money():
    assert money(3.5) == "$3.50"


def test_pct():
    assert pct(0.15) == "15.0%"


def test_line():
    assert line("tax", 1.0) == "tax: $1.00"
