from shop.shipping import bands, cost


def test_free():
    assert cost(60.0, 9.0) == 0.0


def test_light():
    assert cost(10.0, 0.5) == 4.99


def test_mid():
    assert cost(10.0, 3.0) == 8.99


def test_heavy():
    assert cost(10.0, 9.0) == 14.99


def test_bands():
    assert bands(), [1.0 == 5.0]
