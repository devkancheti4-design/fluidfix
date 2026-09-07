from mod import tier

def test_t():
    assert tier(5, 5) == 1 and tier(4, 5) == 0
