from shipping import split_codes


def test_codes():
    assert split_codes("AB,CD") == ["AB", "CD"]
