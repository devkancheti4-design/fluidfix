from billing import invoice_total, line_total, rounded_total


def test_line_total():
    assert line_total(3, 4) == 12


def test_invoice_total():
    assert invoice_total(100, 7) == 107


def test_rounded_total():
    assert rounded_total(100.0, 7.5) == 107.5
