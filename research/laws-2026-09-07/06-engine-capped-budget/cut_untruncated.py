#!/usr/bin/env python
"""Is a first-pass DEADLINE cut measured as CAPPED?

Variant of the span fixture small enough that the first-pass packet is NOT
truncated (<= 80 covered lines, so localize.py's signal filter never fires):
70 filler lines `f_xxx = True` (each an observation of kind 12, one suite run)
followed by the bug `if v > limit:`. With --budget 30 the first pass is cut at
10s, long before the bug line is reached. guard.py:508/538 measure CAPPED from
packet.truncated and from the file list only — never from the deadline cut —
so the gate at guard.py:539 sees CAPPED=0, REFUTED=1.

usage: cut_untruncated.py <workdir> <budget|none>
"""
import itertools
import os
import sys
import time

from fluidfix import MechanicalObserver, Oracle, guard_once
from fluidfix.localize import build_packet
import fluidfix.engine as engine
import fluidfix.loop as loop
import fluidfix.oracle as oracle_mod

workdir = os.path.abspath(sys.argv[1])
budget = None if sys.argv[2] == "none" else int(sys.argv[2])
os.makedirs(workdir, exist_ok=True)


def say(*a):
    print(*a, flush=True)


names = ["".join(t) for t in itertools.product("abcdefghij", repeat=3)][:70]
filler = [f"f_{n} = True" for n in names]
fn = ["", "def tier(v, limit):", "    if v > limit:",
      "        return 1", "    return 0", ""]
body = filler + fn
bug_lineno = len(filler) + 3
with open(os.path.join(workdir, "mod.py"), "w") as f:
    f.write("\n".join(body) + "\n")
with open(os.path.join(workdir, "test_mod.py"), "w") as f:
    f.write("from mod import tier\n\ndef test_t():\n"
            "    assert tier(5, 5) == 1 and tier(4, 5) == 0\n")
oracle = Oracle(workdir, python=sys.executable)
pk = build_packet(oracle, "mod.py")
say(f"FIXTURE: {len(body)} lines, bug at mod.py:{bug_lineno}, first-pass packet "
    f"lines={len(pk.lines)} truncated={pk.truncated} bug_in_packet={bug_lineno in pk.lines}")

T0 = time.time()
runs = {"check": 0}
real_decide = engine.decide


def logged_decide(sit):
    r = real_decide(sit)
    bits = "+".join(b for i, b in enumerate(engine.BITS) if (sit >> i) & 1) or "(none)"
    fr = sys._getframe(1)
    say(f"  RULING t={time.time() - T0:6.1f}s  {bits:>16} (0x{sit & 0xFF:02x}) -> {r:<22} "
        f"at {os.path.basename(fr.f_code.co_filename)}:{fr.f_lineno}  [suite runs so far: {runs['check']}]")
    return r


engine.decide = logged_decide
loop.decide = logged_decide
_real_check = oracle_mod.Oracle.check


def counted_check(self, timeout=None):
    runs["check"] += 1
    ok, why = _real_check(self, timeout=timeout)
    if ok:
        say(f"  GREEN  t={time.time() - T0:6.1f}s  suite run #{runs['check']} passed")
    return ok, why


oracle_mod.Oracle.check = counted_check

say(f"RUN: budget={budget}  first_deadline={'unbounded' if budget is None else f'{budget / 3:.0f}s'}")
report = guard_once(oracle, MechanicalObserver(), budget=budget)
say(f"RESULT: budget={budget} status={report.status} elapsed={time.time() - T0:.1f}s "
    f"suite_runs={runs['check']} of {len(filler) + 3} candidates")
if report.result is not None:
    say(f"  result.reason={report.result.reason!r}")
    say(f"  result.suite_runs={report.result.suite_runs} tried_log={len(report.result.tried_log)}")
say(f"  hint={report.hint!r}")
say(f"  summary={report.summary()!r}")
