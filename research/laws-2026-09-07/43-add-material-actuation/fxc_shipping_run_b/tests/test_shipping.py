from shop.shipping import bands, cost
from shop.support.expect import expect_equal


def test_free():
    expect_equal(cost(60.0, 9.0), 0.0)


def test_light():
    expect_equal(cost(10.0, 0.5), 4.99)


def test_mid():
    expect_equal(cost(10.0, 3.0), 8.99)


def test_heavy():
    expect_equal(cost(10.0, 9.0), 14.99)


def test_bands():
    expect_equal(bands(), [1.0, 5.0])


def test_light_boundary():
    expect_equal(cost(10.0, 1.0), 4.99)
