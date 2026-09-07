from mod import net_change

def test_fee_smaller():
    assert net_change(10, 4) == 6

def test_fee_larger():
    # the ticket said "the app showed -3, users expect 3"
    assert net_change(5, 8) == 3
