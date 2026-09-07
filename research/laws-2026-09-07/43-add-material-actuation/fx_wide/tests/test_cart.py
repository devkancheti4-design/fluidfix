from shop.cart import item_count, subtotal
from shop.support.expect import expect_equal


def test_item_count():
    expect_equal(item_count([(1.0, 2), (2.0, 3)]), 5)


def test_subtotal_small():
    expect_equal(subtotal([(1.0, 1)]), 1.0)
