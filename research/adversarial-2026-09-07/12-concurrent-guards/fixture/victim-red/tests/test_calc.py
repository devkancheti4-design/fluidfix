import time
from vpkg.calc import bill, grade, total


def test_total():
    assert total(3, 2.0) == 6.0


def test_grade_fail():
    assert grade(50) == "F"


def test_grade_pass():
    assert grade(70) == "P"


def test_bill():
    assert bill(10, 2.0) == 20.0


def test_slow_marker():
    time.sleep(3.0)
    assert True
