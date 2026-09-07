#!/usr/bin/env python
"""Log every observation byte the BODY actually hands to the engine law
during guard runs on three small fixtures (the ones tests/test_engine_fusion.py
uses: AMB, single green, REFUTED). Wrapper only — src/ is not edited: the
name `decide` is rebound in fluidfix.engine (guard.py imports it at call
time) and in fluidfix.loop (bound at import time).

Question answered: does any byte the body asks ever carry SELF (bit 7)?
Rerun: .venv/bin/python body_bytes_probe.py
"""
import os, re, sys, tempfile
sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
os.environ.setdefault("FLUIDFIX_CONFIRM", "1")

import fluidfix.engine as engine
import fluidfix.loop as loop
from fluidfix import ACTS, KINDS, MechanicalObserver, Oracle, guard_once
from fluidfix.acts import register
from fluidfix.engine import BITS

asked = []
_real = engine.decide
def spy(sit):
    r = _real(sit)
    asked.append((sit, r))
    return r
engine.decide = spy
loop.decide = spy

def bits(sit):
    b = sit & 0xFF
    on = [n for i, n in enumerate(BITS) if b >> i & 1]
    return "+".join(on) or "(none)"

def run(name, files, setup=None):
    del asked[:]
    saved = dict(KINDS), dict(ACTS)
    d = tempfile.mkdtemp(prefix="selfprobe-", dir=os.path.dirname(os.path.abspath(__file__)))
    try:
        for fn, body in files.items():
            with open(os.path.join(d, fn), "w") as f:
                f.write(body)
        if setup:
            setup()
        oracle = Oracle(d, python=sys.executable)
        rep = guard_once(oracle, MechanicalObserver())
        print(f"--- {name}: status={rep.status}")
        for sit, r in asked:
            print(f"    asked byte {sit & 0xFF:>3} ({bits(sit):<28}) -> {r}"
                  f"{'   SELF SET' if sit & 128 else ''}")
        if not asked:
            print("    (law never consulted)")
    finally:
        KINDS.clear(); KINDS.update(saved[0])
        ACTS.clear(); ACTS.update(saved[1])
        import shutil; shutil.rmtree(d, ignore_errors=True)
    return [s & 0xFF for s, _ in asked]

allbytes = []
allbytes += run("AMB (two greens in one set)",
    {"mod.py": "K = 0\n\ndef f():\n    return K\n",
     "test_mod.py": "from mod import f\n\ndef test_f():\n    assert f() >= 1\n"},
    setup=lambda: register(4, "amb-demo", "demo", re.compile(r"K = "),
                           lambda line, o: ["K = 1", "K = 2"]))
allbytes += run("single green (strictness)",
    {"mod.py": "def cmp(x, t):\n    if x > t:\n        return 1\n    return 0\n",
     "test_mod.py": "from mod import cmp\n\ndef test_c():\n"
                    "    assert cmp(5, 5) == 1 and cmp(4, 5) == 0\n"})
allbytes += run("REFUTED (fault out of vocabulary)",
    {"mod.py": "def f(a, b):\n    return a * b\n",
     "test_mod.py": "from mod import f\n\ndef test_f():\n    assert f(6, 2) == 3\n"})

print()
print(f"distinct bytes asked across the three runs: {sorted(set(allbytes))}")
print(f"any byte with SELF (128) set: {any(b & 128 for b in allbytes)}")
