#!/usr/bin/env python
"""Budget sweep on tests/test_span_edits.py::test_budget_hands_first_pass_over_to_escalation.

Rebuilds that fixture byte-for-byte (same filler, same pad search), then runs
guard_once(oracle, MechanicalObserver(), budget=B) with EVERY engine-law ruling
logged (decide() wrapped, src untouched) and every suite run counted.

usage: sweep_budget.py <budget-seconds> <workdir>
Run as:  nice -n 15 timeout 300 .venv/bin/python sweep_budget.py 450 ./fixture_450
"""
import itertools
import json
import os
import sys
import time

from fluidfix import MechanicalObserver, Oracle, guard_once
from fluidfix.localize import build_packet
import fluidfix.engine as engine
import fluidfix.loop as loop
import fluidfix.oracle as oracle_mod

budget = int(sys.argv[1])
workdir = os.path.abspath(sys.argv[2])
os.makedirs(workdir, exist_ok=True)


def say(*a):
    print(*a, flush=True)


# ---- the fixture, verbatim from tests/test_span_edits.py:198-215 ----------
names = ["".join(t) for t in itertools.product("abcdefghij", repeat=3)][:800]
filler = [f"f_{n} = True" for n in names]
fn = ["", "def tier(v, limit):", "    if v > limit:",
      "        return 1", "    return 0", ""]
with open(os.path.join(workdir, "test_mod.py"), "w") as f:
    f.write("from mod import tier\n\ndef test_t():\n"
            "    assert tier(5, 5) == 1 and tier(4, 5) == 0\n")
oracle = Oracle(workdir, python=sys.executable)
placed = False
for pad in range(6):
    body = filler[:400 + pad] + fn + filler[400 + pad:]
    bug_lineno = (400 + pad) + 3
    with open(os.path.join(workdir, "mod.py"), "w") as f:
        f.write("\n".join(body) + "\n")
    pk = build_packet(oracle, "mod.py")
    if pk is not None and pk.truncated and bug_lineno not in pk.lines:
        placed = True
        break
if not placed:
    say("FIXTURE: could not place the bug outside the first-pass sample")
    sys.exit(3)
say(f"FIXTURE: pad={pad} bug_lineno={bug_lineno} packet_lines={len(pk.lines)} "
    f"truncated={pk.truncated} bug_in_packet={bug_lineno in pk.lines}")
src_before = open(os.path.join(workdir, "mod.py"), "rb").read()

# ---- instrumentation: log every ruling, count every suite run -------------
T0 = time.time()
rulings = []
real_decide = engine.decide


def logged_decide(sit):
    r = real_decide(sit)
    bits = "+".join(b for i, b in enumerate(engine.BITS) if (sit >> i) & 1) or "(none)"
    fr = sys._getframe(1)
    rec = {"t": round(time.time() - T0, 1), "bits": bits, "byte": sit & 0xFF,
           "ruling": r, "caller": f"{os.path.basename(fr.f_code.co_filename)}:{fr.f_lineno}",
           "suite_runs_so_far": runs["check"]}
    rulings.append(rec)
    say(f"  RULING t={rec['t']:7.1f}s  {bits:>22} (0x{sit & 0xFF:02x}) -> {r:<22} "
        f"at {rec['caller']}  [suite runs so far: {runs['check']}]")
    return r


engine.decide = logged_decide
loop.decide = logged_decide          # loop.py bound the name at import

runs = {"check": 0, "green": 0, "failing_output": 0, "check_green": 0}
_real_check = oracle_mod.Oracle.check


def counted_check(self, timeout=None):
    runs["check"] += 1
    ok, why = _real_check(self, timeout=timeout)
    if ok:
        runs["check_green"] += 1
        say(f"  GREEN  t={time.time() - T0:7.1f}s  suite run #{runs['check']} passed")
    return ok, why


oracle_mod.Oracle.check = counted_check
_real_green = oracle_mod.Oracle.green


def counted_green(self, timeout=None):
    runs["green"] += 1
    return _real_green(self, timeout=timeout)


oracle_mod.Oracle.green = counted_green
_real_fo = oracle_mod.Oracle.failing_output


def counted_fo(self):
    runs["failing_output"] += 1
    return _real_fo(self)


oracle_mod.Oracle.failing_output = counted_fo

say(f"RUN: budget={budget}s  first_deadline=budget/3={budget / 3:.0f}s  "
    f"FLUIDFIX_CONFIRM={os.environ.get('FLUIDFIX_CONFIRM', '(default 1)')}  start={time.strftime('%H:%M:%S')}")
report = guard_once(oracle, MechanicalObserver(), budget=budget)
elapsed = time.time() - T0
src_after = open(os.path.join(workdir, "mod.py"), "rb").read()

say(f"RESULT: budget={budget} status={report.status} elapsed={elapsed:.1f}s "
    f"suite_runs(check)={runs['check']} greens={runs['check_green']} "
    f"green()={runs['green']} failing_output()={runs['failing_output']}")
say(f"  file={report.file} tree_changed={src_after != src_before}")
if report.result is not None:
    say(f"  result.reason={report.result.reason!r}")
    say(f"  result.suite_runs={report.result.suite_runs} acts_tried={report.result.acts_tried[:10]} "
        f"greens={report.result.greens} ambiguous={report.result.ambiguous}")
    if report.result.new_line:
        say(f"  new_line={report.result.new_line.strip()!r} lineno={report.result.lineno}")
say(f"  hint={report.hint!r}")
say(f"  summary={report.summary()!r}")
say(f"  attempts logged={len(report.attempts)}")
with open(os.path.join(workdir, "rulings.json"), "w") as f:
    json.dump({"budget": budget, "status": report.status, "elapsed": elapsed,
               "runs": runs, "rulings": rulings, "hint": report.hint,
               "reason": report.result.reason if report.result else None}, f, indent=1)
