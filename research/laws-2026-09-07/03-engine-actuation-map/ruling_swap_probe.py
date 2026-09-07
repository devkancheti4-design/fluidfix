#!/usr/bin/env python
"""Ruling-swap probe for target 03-engine-actuation-map.

Question per site: does the BODY'S BEHAVIOUR depend on the act the law
returns, or is the ruling only printed into a string?  Method: run a fixture
once with the vendored law, then once with `decide()` monkeypatched to return
a DIFFERENT act for that site's byte, and diff what the body did.

  ship        loop.py:217   BUILT           SHIP  -> RESHAPE
  amb         loop.py:217   BUILT+AMB       ADD_STATE -> SHIP
  hidden      loop.py:391   HIDDEN          CHANGE_GRANULARITY -> SHIP
  unread      guard.py:491  UNREAD          ADD_MATERIAL -> RESHAPE
  capped      guard.py:539  CAPPED(+REFUTED) RAISE_BUDGET -> HARVEST_COUNTEREXAMPLE
  refuted     guard.py:612/618 REFUTED       HARVEST_COUNTEREXAMPLE -> RESHAPE
  builtcapped loop.py:217 -> guard.py:497-624  BUILT+CAPPED ruled RAISE_BUDGET
              inside repair(); what does guard_once do with that ruling?

Nothing outside this directory is written: every fixture lives under
./fixtures/<name>/ and is rebuilt from scratch on each run.

Run ONE fixture at a time, bounded:
  ./run_bounded.sh /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python \
      ruling_swap_probe.py <fixture>
"""
import itertools
import json
import os
import re
import shutil
import sys
import time

SRC = "/Users/kanchetidevieswar/neo/fluidfix/src"
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SRC)

import fluidfix.engine as E          # noqa: E402
import fluidfix.loop as L            # noqa: E402
import fluidfix.guard as G           # noqa: E402
from fluidfix import (MechanicalObserver, Observation, Oracle,  # noqa: E402
                      guard_once, repair)
from fluidfix.acts import ACTS as ACTTABLE, KINDS, register  # noqa: E402
from fluidfix.localize import build_packet  # noqa: E402

REAL_DECIDE = E.decide
PY = sys.executable


def install_swap(override: dict):
    """decide() returns the real ruling unless it is a key of `override`."""
    calls = []

    def swapped(sit):
        r = REAL_DECIDE(sit)
        out = override.get(r, r)
        calls.append((sit & 0xFF, r, out))
        return out
    E.decide = swapped
    L.decide = swapped
    return calls


def restore_decide():
    E.decide = REAL_DECIDE
    L.decide = REAL_DECIDE


def fresh(name: str, files: dict) -> str:
    root = os.path.join(HERE, "fixtures", name)
    shutil.rmtree(root, ignore_errors=True)
    os.makedirs(root)
    for fn, body in files.items():
        with open(os.path.join(root, fn), "w", newline="") as f:
            f.write(body)
    return root


def show(tag, report):
    r = report.result
    print(f"  [{tag}] status={report.status!r} file={report.file!r}")
    print(f"  [{tag}] hint={report.hint!r}")
    print(f"  [{tag}] attempts={len(report.attempts)} "
          f"result={'None' if r is None else dict(repaired=r.repaired, ambiguous=r.ambiguous, greens=r.greens, reason=r.reason[:160])}")


def two_runs(name, files, override, run):
    """run(root) twice: real law, then swapped law. Prints both."""
    root = fresh(name, files)
    print(f"== {name}: REAL law ==")
    restore_decide()
    run(root, "real")
    root = fresh(name, files)
    print(f"== {name}: SWAPPED law {override} ==")
    calls = install_swap(override)
    try:
        run(root, "swap")
    finally:
        restore_decide()
    seen = sorted({(b, r, o) for b, r, o in calls})
    print("  decide() calls during the swapped run (byte, real ruling, returned):")
    for b, r, o in seen:
        bits = "+".join(n for i, n in enumerate(E.BITS) if b >> i & 1) or "(none)"
        print(f"    {bits:<20} {r:<22} -> {o}")


# ------------------------------------------------------------------ ship --
def fx_ship():
    files = {"mod.py": "def cmp(x, t):\n    if x > t:\n        return 1\n    return 0\n",
             "test_mod.py": "from mod import cmp\n\ndef test_c():\n"
                            "    assert cmp(5, 5) == 1 and cmp(4, 5) == 0\n"}

    def run(root, tag):
        rep = guard_once(Oracle(root, python=PY), MechanicalObserver())
        show(tag, rep)
        print(f"  [{tag}] mod.py line 2 now: {open(os.path.join(root, 'mod.py')).read().splitlines()[1]!r}")
    two_runs("ship", files, {"SHIP": "RESHAPE"}, run)


# ------------------------------------------------------------------- amb --
def fx_amb():
    files = {"mod.py": "K = 0\n\ndef f():\n    return K\n",
             "test_mod.py": "from mod import f\n\ndef test_f():\n    assert f() >= 1\n"}

    def run(root, tag):
        register(4, "amb-demo", "two suite-passing candidates", re.compile(r"K = "),
                 lambda line, o: ["K = 1", "K = 2"])
        rep = guard_once(Oracle(root, python=PY), MechanicalObserver())
        show(tag, rep)
        print(f"  [{tag}] mod.py line 1 now: {open(os.path.join(root, 'mod.py')).read().splitlines()[0]!r}")
    two_runs("amb", files, {"ADD_STATE": "SHIP"}, run)


# ---------------------------------------------------------------- hidden --
class FlipOracle(Oracle):
    """A suite that does not hold still: check() alternates green/red, so a
    green from one run is always contradicted by the confirm run. No pytest
    subprocess is spawned at all."""
    def __init__(self, root):
        self.root = os.path.abspath(root); self.python = PY; self.timeout = 30
        self.per_test_timeout = 30; self.extra_args = []; self._fastgate_ok = True
        self._has_timeout = False; self.n = 0
    def clear_pyc(self): pass
    def green(self, timeout=None): return False
    def check(self, timeout=None):
        self.n += 1
        return (True, "") if self.n % 2 else (False, "FAILED test_mod.py::test_f - flaky")


def fx_hidden():
    files = {"mod.py": "def f(a, b):\n    return a - b\n"}

    def run(root, tag):
        res = repair(FlipOracle(root), "mod.py", [Observation(lineno=2, kinds=[3])])
        print(f"  [{tag}] repaired={res.repaired} refused={res.refused} greens={res.greens} reason={res.reason!r}")
        for e in res.tried_log:
            print(f"  [{tag}] tried={e['tried']!r} why={e['why']!r}")
        print(f"  [{tag}] mod.py line 2 now: {open(os.path.join(root, 'mod.py')).read().splitlines()[1]!r}")
    os.environ["FLUIDFIX_CONFIRM"] = "1"
    two_runs("hidden", files, {"CHANGE_GRANULARITY": "SHIP"}, run)
    print("== hidden: REAL law, FLUIDFIX_CONFIRM=0 (lane switched off by env var) ==")
    os.environ["FLUIDFIX_CONFIRM"] = "0"
    restore_decide()
    run(fresh("hidden", files), "confirm0")


# ---------------------------------------------------------------- unread --
def fx_unread():
    files = {"mod.py": "def f(a, b):\n    return a * b\n",
             "test_mod.py": "from mod import f\n\ndef test_f():\n    assert f(6, 2) == 3\n"}

    def run(root, tag):
        G._has_pytest_cov = lambda oracle: False
        G.find_candidate_files = lambda *a, **k: []
        rep = guard_once(Oracle(root, python=PY), MechanicalObserver())
        show(tag, rep)
        print(f"  [{tag}] candidates={rep.candidates} (nothing was added in either run)")
    two_runs("unread", files, {"ADD_MATERIAL": "RESHAPE"}, run)


# --------------------------------------------------------------- refuted --
def fx_refuted():
    files = {"mod.py": "def f(a, b):\n    return a * b\n",
             "test_mod.py": "from mod import f\n\ndef test_f():\n    assert f(6, 2) == 3\n"}

    def run(root, tag):
        rep = guard_once(Oracle(root, python=PY), MechanicalObserver())
        show(tag, rep)
        for e in rep.attempts:
            print(f"  [{tag}] harvested: at={e['at']} tried={e['tried']!r} why={e['why'][:80]!r}")
        p = G.write_refusal(root, rep)
        d = json.load(open(p))
        print(f"  [{tag}] last_refusal.json: hint={d['hint'][:60]!r}... rejected_candidates={len(d['rejected_candidates'])}")
    two_runs("refuted", files, {"HARVEST_COUNTEREXAMPLE": "RESHAPE"}, run)


# ---------------------------------------------------------------- capped --
def fx_capped():
    names = ["".join(t) for t in itertools.product("abcdefghij", repeat=3)][:800]
    filler = [f"f_{n} = True" for n in names]
    fn = ["", "def tier(v, limit):", "    if v > limit:", "        return 1", "    return 0", ""]
    test = "from mod import tier\n\ndef test_t():\n    assert tier(5, 5) == 1 and tier(4, 5) == 0\n"

    def layout(root):
        oracle = Oracle(root, python=PY)
        for pad in range(6):
            body = filler[:400 + pad] + fn + filler[400 + pad:]
            bug = (400 + pad) + 3
            open(os.path.join(root, "mod.py"), "w").write("\n".join(body) + "\n")
            pk = build_packet(oracle, "mod.py")
            if pk is not None and pk.truncated and bug not in pk.lines:
                print(f"  layout: bug at line {bug}, packet truncated={pk.truncated}, bug sampled={bug in pk.lines}")
                return oracle
        raise SystemExit("could not place the bug outside the round-1 sample")

    def run(root, tag):
        oracle = layout(root)
        rep = guard_once(oracle, MechanicalObserver())
        show(tag, rep)
    two_runs("capped", {"test_mod.py": test}, {"RAISE_BUDGET": "HARVEST_COUNTEREXAMPLE"}, run)


# ----------------------------------------------------------- builtcapped --
class FakeClock:
    """loop.py's clock. `offset` is bumped by a taught applier so the very
    next deadline check inside repair() expires — deterministically, with a
    green already in hand."""
    offset = 0.0
    def time(self): return time.time() + FakeClock.offset


def fx_builtcapped():
    files = {"mod.py": "K = 0\nJ = 0\n\ndef f():\n    return K + J\n",
             "test_mod.py": "from mod import f\n\ndef test_f():\n    assert f() == 1\n"}
    root = fresh("builtcapped", files)
    register(4, "green-class", "the real fix", re.compile(r"K = "), lambda line, o: ["K = 1"])

    def bump(line, o):
        FakeClock.offset += 10_000.0      # the wall clock 'runs out' here
        return ["K = 7"]
    register(5, "bump-class", "burns the clock", re.compile(r"K = "), bump)
    register(6, "never-class", "never reached", re.compile(r"K = "), lambda line, o: ["K = 9"])
    L.time = FakeClock()                  # only loop.py's clock is faked
    captured = []
    real_repair = G.repair

    def rec(*a, **k):
        r = real_repair(*a, **k)
        captured.append(r)
        return r
    G.repair = rec
    restore_decide()
    print("== builtcapped: REAL law, guard_once(budget=3000) so repair() gets first_deadline=t0+1000 ==")
    rep = guard_once(Oracle(root, python=PY), MechanicalObserver(), budget=3000)
    for i, r in enumerate(captured):
        print(f"  repair() call {i}: repaired={r.repaired} ambiguous={r.ambiguous} greens={r.greens} acts_tried={r.acts_tried}")
        print(f"  repair() call {i}: reason={r.reason!r}")
    show("guard", rep)
    print(f"  guard summary(): {rep.summary()!r}")
    p = G.write_refusal(root, rep)
    d = json.load(open(p))
    print(f"  last_refusal.json hint: {d['hint']!r}")
    print(f"  'candidate passes' in guard hint: {'candidate passes' in (rep.hint or '')}")
    print(f"  'RAISE_BUDGET' in guard hint:     {'RAISE_BUDGET' in (rep.hint or '')}")
    print(f"  'REFUTED' in guard hint:          {'REFUTED' in (rep.hint or '')}")
    print(f"  mod.py line 1 now: {open(os.path.join(root, 'mod.py')).read().splitlines()[0]!r}")


FIXTURES = dict(ship=fx_ship, amb=fx_amb, hidden=fx_hidden, unread=fx_unread,
                capped=fx_capped, refuted=fx_refuted, builtcapped=fx_builtcapped)

if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else ""
    if which not in FIXTURES:
        raise SystemExit(f"usage: {sys.argv[0]} {{{'|'.join(FIXTURES)}}}")
    t0 = time.time()
    FIXTURES[which]()
    print(f"-- {which}: {time.time() - t0:.1f}s wall")
