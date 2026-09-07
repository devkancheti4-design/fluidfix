import time
from mod import f, g, K

def test_f():
    if K == 1:
        time.sleep(2.5)
    assert f() == 1

def test_g():
    assert g(1) == 6
