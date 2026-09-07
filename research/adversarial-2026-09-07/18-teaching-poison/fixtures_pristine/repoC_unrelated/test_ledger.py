from ledger import parse_row


def test_rows():
    assert parse_row("widget,4") == ["widget", "4"]
