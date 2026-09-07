import time
from mod import count_above

def test_count_above():
    time.sleep(float(__import__("os").environ.get("VICTIM_SLEEP", "0")))
    assert count_above([1, 5, 5, 9], 5) == 1
