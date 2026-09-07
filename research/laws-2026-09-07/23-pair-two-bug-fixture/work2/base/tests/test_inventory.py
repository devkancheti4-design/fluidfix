from inventory import needs_reorder, restock_amount


def test_restock_amount():
    assert restock_amount(2, 10) == 8


def test_needs_reorder():
    assert needs_reorder(2, 10) is True
