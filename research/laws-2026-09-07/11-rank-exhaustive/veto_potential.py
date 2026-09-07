#!/usr/bin/env python
"""11-rank-exhaustive: what the unmeasured RETRIED veto would be worth.

*** ITS CLOSING PROJECTION IS SUPERSEDED AND WAS WRONG. ***
The last line of this script PROJECTS that with RETRIED measured the
escalation pass would cost "about 3" suite runs.  veto_measured.py MEASURES
it: 22 baseline vs 22 with the veto supplied -- zero saved.  The projection
assumed repair() stops at the first green; it does not.  loop.py:244-263
collects greens across the WHOLE observation list on purpose, because AMB
cannot be observed from a single candidate set, so ORDER decides WHICH green
ships, never how many runs it costs.  The veto's real worth is in the
deadline-limited case -- see veto_deadline.py and REPORT.md findings 8-9.
Do not cite the projected number below as a measurement.

Fixture (built here, tests/ untouched): one defect file whose failing test
executes 116 signal-bearing lines, so pass 0's packet is stride-sampled to
110 (localize.build_packet, max_lines=110) and the defect -- the LAST kept
line, index 115 -- is dropped.  Pass 0 rejects every candidate on the
other flagged lines; the engine rules CAPPED+REFUTED -> RAISE_BUDGET; the
escalation pass rebuilds a full packet and calls rank_observations again
WITHOUT a `retried` set (guard.py:585).  The law therefore sees the same
byte for the already-rejected lines as for the untried defect line and the
body re-tries the rejected ones first.  This script counts that.

Run (one at a time, per BRIEF):
  nice -n 15 ./timeout.sh 300 /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python veto_potential.py
"""
import os
import shutil
import sys
import tempfile
import time

sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
import fluidfix.guard as G                                        # noqa: E402
import fluidfix.rank as R                                         # noqa: E402
from fluidfix import MechanicalObserver, Oracle, guard_once      # noqa: E402
from fluidfix.rank import BITS                                    # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
FILLER = 105                      # kept lines: 1 (ok = True) + 105 + 10 = 116

names = ["a", "b", "c", "d", "e", "g", "h", "i", "j", "k"]
src = ["def f(x, " + ", ".join(names) + "):",
       "    ok = True",           # kept (True), flagged (True/False kind)
       "    u = x",               # not kept
       "    v = x"]               # not kept
src += ["    u = u * v"] * FILLER  # kept (spaced *), NOT flagged by any kind
for nm in names[:-1]:
    src.append(f"    ok = ok and (x >= {nm})")   # kept + flagged
src.append("    ok = ok and (x > k)")            # THE DEFECT: > for >=
src.append("    return ok")                      # not kept
MOD = "\n".join(src) + "\n"
DEFECT_LINE = len(src) - 1                       # 1-based line of the defect
TEST = ("from mod import f\n\nT = (5,) * 10\n\ndef test_f():\n"
        "    assert f(6, *T) is True\n    assert f(5, *T) is True\n"
        "    assert f(4, *T) is False\n")

calls = []
_repair = G.repair


def spy_repair(oracle, rel, observations, **kw):
    t = time.time()
    res = _repair(oracle, rel, observations, **kw)
    calls.append({"rel": rel, "order": [o.lineno for o in observations],
                  "suite_runs": res.suite_runs, "repaired": res.repaired,
                  "lineno": res.lineno,
                  "tried": [(e["at"], e["tried"]) for e in res.tried_log],
                  "tried_more": res.tried_more, "secs": time.time() - t})
    return res


G.repair = spy_repair
bytes_seen = {}
_rank = R.rank


def spy_rank(x):
    bytes_seen[x] = bytes_seen.get(x, 0) + 1
    return _rank(x)


R.rank = spy_rank


def bits(x):
    return "+".join(b for i, b in enumerate(BITS) if (x >> i) & 1) or "none"


d = tempfile.mkdtemp(prefix="veto_", dir=HERE)
try:
    open(os.path.join(d, "mod.py"), "w").write(MOD)
    open(os.path.join(d, "test_mod.py"), "w").write(TEST)
    t0 = time.time()
    rep = guard_once(Oracle(d, python=sys.executable), MechanicalObserver())
    print(f"guard_once: status={rep.status} file={rep.file} "
          f"total={time.time() - t0:.1f}s  defect line={DEFECT_LINE}")
    print(f"rank() bytes seen: " +
          ", ".join(f"{x}={bits(x)}->rank {_rank(x)} x{n}"
                    for x, n in sorted(bytes_seen.items())))
    for i, c in enumerate(calls):
        print(f"\nrepair() call {i} (pass {'0' if i == 0 else 'escalation'}): "
              f"{c['rel']} observations={len(c['order'])} "
              f"suite_runs={c['suite_runs']} repaired={c['repaired']} "
              f"at line {c['lineno']} in {c['secs']:.1f}s")
        print(f"   line order handed to repair(): {c['order']}")
        print(f"   defect line in order: {DEFECT_LINE in c['order']}"
              f"{'  position ' + str(c['order'].index(DEFECT_LINE)) if DEFECT_LINE in c['order'] else ''}")
        print(f"   rejected candidates logged: {len(c['tried'])} "
              f"(+{c['tried_more']} beyond the 64-entry cap)")
    if len(calls) >= 2:
        p0 = set(calls[0]["tried"])
        esc = calls[1]["tried"]
        repeats = [t for t in esc if t in p0]
        lines_repeated = sorted({t[0] for t in repeats})
        print(f"\nRE-TRIED in escalation (already rejected in pass 0): "
              f"{len(repeats)} candidates on {len(lines_repeated)} lines "
              f"(pass-0 log capped at 64: {len(calls[0]['tried'])}"
              f"+{calls[0]['tried_more']})")
        print(f"   escalation suite runs = {calls[1]['suite_runs']}; of which "
              f"repeats = {len(repeats)}. NOTE: an earlier version of this "
              f"script projected that the veto would cut the pass to about "
              f"{calls[1]['suite_runs'] - len(repeats)} runs. That projection "
              f"is WRONG -- veto_measured.py measures 22 vs 22 (no saving on "
              f"a completed search, because repair() never stops at the first "
              f"green). See REPORT.md findings 8-9.")
    else:
        print("\nescalation pass NOT reached -- fixture did not do what was "
              "intended; see status above")
finally:
    shutil.rmtree(d, ignore_errors=True)
