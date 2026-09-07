from gate import alarm


def test_first_reading_at_limit_is_above():
    assert alarm([7, 3], 3) is True


def test_first_reading_below_limit():
    assert alarm([1, 0], 5) is False


def test_first_reading_clearly_above():
    assert alarm([9, 8], 2) is True
