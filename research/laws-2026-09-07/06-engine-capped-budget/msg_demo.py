#!/usr/bin/env python
"""F5: the BUILT+CAPPED -> RAISE_BUDGET message is written, then thrown away.

Three parts, all read-only w.r.t. src/:

  A. call loop.repair() DIRECTLY with a deadline that lands AFTER a green is
     found but BEFORE the observation list is exhausted. That is exactly the
     situation loop.py:217 `_rule(capped=True)` is written for: BUILT=1,
     AMB=0, CAPPED=1 -> byte 0x21 -> RAISE_BUDGET. Print every field of the
     Result the law's ruling produced.
  B. run the SAME fixture at the SAME clock through guard_once(budget=...),
     the path a user actually takes, and print the GuardReport the user sees.
  C. enumerate, statically, every caller of repair()/guard_once() and which
     Result fields each one reads.

The fixture is deliberately tiny (bug FIRST, 70 filler lines after it) so a
green arrives in a few suite runs and the whole demo costs ~20s.

usage: msg_demo.py <workdir>
Run as: nice -n 15 timeout.py 300 .venv/bin/python msg_demo.py ./fixture_msg
"""
import itertools
import os
import re
import subprocess
import sys
import time

from fluidfix import MechanicalObserver, Oracle, guard_once
from fluidfix.localize import build_packet
from fluidfix.loop import repair
from fluidfix.guard import rank_observations
import fluidfix.engine as engine
import fluidfix.loop as loop
import fluidfix.oracle as oracle_mod

workdir = os.path.abspath(sys.argv[1])
os.makedirs(workdir, exist_ok=True)
SRC = "/Users/kanchetidevieswar/neo/fluidfix/src/fluidfix"


def say(*a):
    print(*a, flush=True)


# ---- fixture: bug FIRST so a green arrives early, filler after -------------
names = ["".join(t) for t in itertools.product("abcdefghij", repeat=3)][:70]
filler = [f"f_{n} = True" for n in names]
fn = ["def tier(v, limit):", "    if v > limit:",
      "        return 1", "    return 0", ""]
body = fn + filler
bug_lineno = 2
with open(os.path.join(workdir, "mod.py"), "w") as f:
    f.write("\n".join(body) + "\n")
with open(os.path.join(workdir, "test_mod.py"), "w") as f:
    f.write("from mod import tier\n\ndef test_t():\n"
            "    assert tier(5, 5) == 1 and tier(4, 5) == 0\n")
oracle = Oracle(workdir, python=sys.executable)
pk = build_packet(oracle, "mod.py")
say(f"FIXTURE: {len(body)} lines, bug at mod.py:{bug_lineno}, packet lines="
    f"{len(pk.lines)} truncated={pk.truncated} bug_in_packet={bug_lineno in pk.lines}")

# ---- instrumentation -------------------------------------------------------
T0 = time.time()
runs = {"check": 0}
real_decide = engine.decide


def logged_decide(sit):
    r = real_decide(sit)
    bits = "+".join(b for i, b in enumerate(engine.BITS) if (sit >> i) & 1) or "(none)"
    fr = sys._getframe(1)
    say(f"  RULING t={time.time() - T0:6.1f}s  {bits:>16} (0x{sit & 0xFF:02x}) -> {r:<22} "
        f"at {os.path.basename(fr.f_code.co_filename)}:{fr.f_lineno}"
        f"  [suite runs so far: {runs['check']}]")
    return r


engine.decide = logged_decide
loop.decide = logged_decide          # loop.py bound the name at import
_real_check = oracle_mod.Oracle.check


def counted_check(self, timeout=None):
    runs["check"] += 1
    ok, why = _real_check(self, timeout=timeout)
    if ok:
        say(f"  GREEN  t={time.time() - T0:6.1f}s  suite run #{runs['check']} passed")
    return ok, why


oracle_mod.Oracle.check = counted_check

_fails, out = oracle.failing_output()
observations = rank_observations("\n".join(pk.src_lines),
                                 MechanicalObserver().observe([pk])[0], out,
                                 root=oracle.root, rel="mod.py")
say(f"OBSERVATIONS: {len(observations)}; rank of the bug line = "
    f"{[o.lineno for o in observations].index(bug_lineno)} (0 = tried first)")

# ---- A. the ruling, in the Result the law produced --------------------------
say("\n== A. loop.repair(deadline=t+6s) — the law rules on BUILT+CAPPED ==")
before = open(os.path.join(workdir, "mod.py"), "rb").read()
res = repair(oracle, "mod.py", observations, deadline=time.time() + 6)
after = open(os.path.join(workdir, "mod.py"), "rb").read()
say(f"  res.repaired={res.repaired}  res.refused={res.refused}  "
    f"res.ambiguous={res.ambiguous}")
say(f"  res.greens={res.greens}")
say(f"  res.suite_runs={res.suite_runs}  observations tried (acts_tried)="
    f"{len(res.acts_tried)} of {len(observations)}")
say(f"  tree_changed={after != before}")
say(f"  res.reason={res.reason!r}")

# ---- B. the same clock through the door a user uses -------------------------
say("\n== B. guard_once(budget=18) — the same fixture, the report a user sees ==")
open(os.path.join(workdir, "mod.py"), "wb").write(before)   # restore the bug
T0 = time.time()
runs["check"] = 0
report = guard_once(oracle, MechanicalObserver(), budget=18)
say(f"  status={report.status}  elapsed={time.time() - T0:.1f}s  "
    f"suite_runs={runs['check']}")
say(f"  report.result={report.result!r}")
say(f"  report.hint={report.hint!r}")
say(f"  report.summary()={report.summary()!r}")

# ---- C. who reads what ------------------------------------------------------
say("\n== C. every caller of repair()/guard_once(), and the fields it reads ==")
pat = re.compile(r"(result|res|rep|report)\.(repaired|ambiguous|refused|reason|greens)\b")
for fname in sorted(os.listdir(SRC)):
    if not fname.endswith(".py"):
        continue
    for i, line in enumerate(open(os.path.join(SRC, fname)), 1):
        if pat.search(line):
            say(f"  {fname}:{i}: {line.rstrip()[:110]}")
say("\n  grep -rn 'search was cut' src tests docs:")
say(subprocess.run(["grep", "-rn", "search was cut",
                    "/Users/kanchetidevieswar/neo/fluidfix/src",
                    "/Users/kanchetidevieswar/neo/fluidfix/tests",
                    "/Users/kanchetidevieswar/neo/fluidfix/docs"],
                   capture_output=True, text=True).stdout.rstrip() or "  (no match)")
