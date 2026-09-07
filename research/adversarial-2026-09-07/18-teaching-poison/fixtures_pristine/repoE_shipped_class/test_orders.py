from orders import refund


def test_refund():
    assert refund(10, 4) == 6
