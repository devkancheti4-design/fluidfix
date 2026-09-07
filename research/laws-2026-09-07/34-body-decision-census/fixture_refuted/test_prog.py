import time
from prog import add


def test_add():
    time.sleep(0.5)          # makes each suite run ~0.9s so the deadline is
    assert add(2, 3) == 5    # reached deterministically, not by a race
