"""pytest plugin: log every engine-law consultation the body makes during a
test run, WITHOUT editing src/ or tests/.

loop.py binds `decide` at import (`from .engine import decide`), so both the
engine module attribute and loop's bound name are wrapped. guard.py imports
inside guard_once(), so patching the engine module covers it.

Use:
  PYTHONPATH=<this dir> .venv/bin/python -m pytest -p log_decide_plugin tests/...
Writes  <this dir>/decide_log.jsonl  (one line per decide() call) and a
summary to stderr at session end.
"""
import collections
import json
import os
import traceback

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, "decide_log.jsonl")
_calls = []
_current = {"test": None}


def _wrap(real):
    def logged(sit):
        act = real(sit)
        # the innermost frame inside src/fluidfix that made the call
        site = None
        for fr in reversed(traceback.extract_stack(limit=8)[:-1]):
            if "/src/fluidfix/" in fr.filename:
                site = f"{os.path.basename(fr.filename)}:{fr.lineno}"
                break
        rec = {"test": _current["test"], "x": sit & 0xFF, "act": act, "site": site}
        _calls.append(rec)
        with open(LOG, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec) + "\n")
        return act
    logged._real = real
    return logged


def pytest_sessionstart(session):
    import fluidfix.engine as engine
    import fluidfix.loop as loop
    if os.path.exists(LOG):
        os.remove(LOG)
    w = _wrap(engine.decide)
    engine.decide = w
    loop.decide = w


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item):
    _current["test"] = item.nodeid
    yield
    _current["test"] = None


def pytest_sessionfinish(session, exitstatus):
    import sys
    from fluidfix.engine import BITS
    by_x = collections.Counter((c["x"], c["act"], c["site"]) for c in _calls)
    print("\n=== engine-law consultations observed (x, act, site) -> count ===",
          file=sys.stderr)
    for (x, act, site), n in sorted(by_x.items(), key=lambda kv: (kv[0][0], str(kv[0][2]))):
        site = site or "<test-direct>"
        bits = "+".join(b for i, b in enumerate(BITS) if x >> i & 1) or "<empty>"
        print(f"  x={x:3d} {bits:28} -> {act:22} @ {site:14} x{n}", file=sys.stderr)
    print(f"distinct situations observed: {sorted({c['x'] for c in _calls})}",
          file=sys.stderr)
