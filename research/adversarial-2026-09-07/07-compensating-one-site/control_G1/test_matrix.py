from matrix import cell


def test_small_symmetric():
    assert cell([[1, 5], [5, 2]]) == 5


def test_other_symmetric():
    assert cell([[0, 7], [7, 3]]) == 7
