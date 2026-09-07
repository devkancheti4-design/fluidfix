import time
from vpkg.calc import bill, discount, total


def test_total():
    assert total(3, 2.0) == 6.0


def test_discount_boundary():
    assert discount(10) == 0.9
    assert discount(9) == 1.0


def test_bill():
    assert bill(10, 2.0) == 18.0


def test_slow_marker():
    # deliberate: makes each suite run take ~1.2s so concurrent runs interleave
    time.sleep(3.0)
    assert True
