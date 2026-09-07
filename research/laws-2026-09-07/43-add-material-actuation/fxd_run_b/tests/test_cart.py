from shop.cart import item_count, subtotal


def test_item_count():
    assert item_count([(1.0, 2), (2.0, 3)]) == 5


def test_subtotal_small():
    assert subtotal([(1.0, 1)]) == 1.0
