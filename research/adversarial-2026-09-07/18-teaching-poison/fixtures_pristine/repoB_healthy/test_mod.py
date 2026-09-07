from mod import net_change, over_limit

def test_net():
    assert net_change(10, 4) == 6

def test_limit():
    assert over_limit(101) is True
