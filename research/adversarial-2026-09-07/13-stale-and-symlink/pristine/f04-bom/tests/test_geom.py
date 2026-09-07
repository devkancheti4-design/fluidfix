import pkg.geom as g


def test_add():
    assert g.add(2, 3) == 5


def test_scale():
    assert g.scale(2, 3) == 6
