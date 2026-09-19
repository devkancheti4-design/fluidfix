#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The net, one level up: the taught classes are the territory and their own suite is the judge.

A class is code with a spec. That makes it a territory, and everything the net does to a repository it can
do here — dispatch, grow by ruling, certify, roll back byte-exact. The audit I ran by hand is what this
suite encodes, and the point is that nobody should have to run it by hand again: an incident that shows a
class is wrong becomes a test, the class's suite goes red, and the net descends.

  PYTHONPATH=<fluidfix>/src python3 descend.py
"""
import os, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE.parents[1] / "src"
TERR = HERE / "classes"
PY = str(HERE.parents[1] / ".venv" / "bin" / "python")
DICTS = [HERE.parents[1] / "examples" / "taught-2026-09-16" / "rules_session.py",
         HERE.parents[1] / "examples" / "taught-2026-09-18" / "kinds_from_ladder.py",
         HERE.parents[1] / "examples" / "taught-2026-09-19" / "rules_placed.py"]

GUARD = """
import sys
src, rel = sys.argv[1], sys.argv[2]
dicts = [d for d in sys.argv[3:6] if d]
sys.path.insert(0, src)
from fluidfix import Oracle
from fluidfix.acts import load_dictionary
from fluidfix.localize import build_packet
from fluidfix.guard import rank_observations
from fluidfix.loop import repair
from fluidfix.observers import MechanicalObserver
for d in dicts:
    load_dictionary(d)
o = Oracle(".", python=sys.executable, timeout=300)
red, out = o.failing_output()
if not red:
    print("RESULT=NOT-RED"); raise SystemExit(3)
pk = build_packet(o, rel, max_lines=10**9)
if pk is None:
    print("RESULT=NO-PACKET"); raise SystemExit(3)
print("executed=%d" % len(pk.lines))
obs = rank_observations("\\n".join(pk.src_lines), MechanicalObserver().observe([pk])[0], out, root=".", rel=rel)
print("observations=%d" % len(obs))
if not obs:
    print("RESULT=NO-OBSERVATIONS"); raise SystemExit(2)
res = repair(o, rel, obs)
print("suite_runs=%d" % res.suite_runs)
print("RESULT=" + ("REPAIRED" if res.repaired else "REFUSED"))
print("RULING=" + (res.ruling or ""))
print(res.summary()[:400])
"""

env = dict(os.environ); env["PYTHONPATH"] = str(SRC)
before = (TERR / "appliers.py").read_text()

r = subprocess.run([PY, "-m", "pytest", "-q", "--no-header", "-p", "no:cacheprovider"],
                   cwd=TERR, capture_output=True, text=True, timeout=300)
fails = [l.split(" ")[1] for l in r.stdout.split("\n") if l.startswith("FAILED") and len(l.split(" ")) > 1]
print(f"the classes territory is {'RED' if r.returncode else 'GREEN'} — "
      f"{len(fails)} failing:\n" + "".join(f"    {f}\n" for f in fails))

g = subprocess.run([PY, "-c", GUARD, str(SRC), "appliers.py", *[str(d) for d in DICTS]],
                   cwd=TERR, env=env, capture_output=True, text=True, timeout=1800)
txt = (g.stdout or "") + (g.stderr or "")
print("the guard, with every taught class available to it:")
for line in txt.strip().split("\n"):
    print("    " + line[:110])

after = (TERR / "appliers.py").read_text()
print(f"\n    rolled back byte-exact: {before == after}")
