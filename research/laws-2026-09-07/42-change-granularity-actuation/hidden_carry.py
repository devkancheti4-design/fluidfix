"""Does a search that OBSERVED HIDDEN still end by asking the law a
situation with HIDDEN clear?

loop.py:391 sets HIDDEN per candidate and throws it away.  loop.py:217
(`_rule`) is the only place a search-ending situation is built, and it passes
BUILT/AMB/CAPPED only.  So a search that saw the suite fail to hold still, and
then found a green, ships under BUILT -> SHIP.  The honest situation is
BUILT+HIDDEN, on which the law rules CHANGE_GRANULARITY.

This script runs the SHIPPED loop at FLUIDFIX_CONFIRM=1 and counts how often
that happens.  usage: hidden_carry.py SHAPE TRIALS
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
sys.path.insert(0, HERE)

from fluidfix import loop                              # noqa: E402
from fluidfix.engine import decide, situation          # noqa: E402
from granularity import LadderOracle                   # noqa: E402
from run_experiment import CORRECT, observations       # noqa: E402

shape, trials = sys.argv[1], int(sys.argv[2])
os.environ["FLUIDFIX_CONFIRM"] = "1"
os.makedirs(HERE + "/work", exist_ok=True)
rows = []
for _ in range(trials):
    work = tempfile.mkdtemp(prefix="hc", dir=HERE + "/work")
    root = os.path.join(work, "repo")
    shutil.copytree(os.path.join(HERE, "fixtures", f"shape{shape}"), root)
    orc = LadderOracle(root, python=sys.executable, timeout=60, rung=1)
    res = loop.repair(orc, "src.py", observations(root), candidate_timeout=60)
    saw_hidden = any("HIDDEN ->" in (t.get("why") or "")
                     for t in res.tried_log)
    rows.append(dict(saw_hidden=saw_hidden, repaired=res.repaired,
                     reason=res.reason[:90], new_line=res.new_line))
    shutil.rmtree(work, ignore_errors=True)

both = [r for r in rows if r["saw_hidden"] and r["repaired"]]
print(json.dumps(dict(
    shape=shape, trials=trials,
    saw_hidden=sum(r["saw_hidden"] for r in rows),
    repaired=sum(r["repaired"] for r in rows),
    saw_hidden_AND_shipped=len(both),
    shipped_correct_among_those=sum(1 for r in both
                                    if r["new_line"] == CORRECT),
    shipped_wrong_among_those=sum(1 for r in both
                                  if r["new_line"] != CORRECT),
    law_on_BUILT=decide(situation(BUILT=True)),
    law_on_BUILT_HIDDEN=decide(situation(BUILT=True, HIDDEN=True)),
    example_reason=(both[0]["reason"] if both else None)), indent=1))
with open(os.path.join(HERE, "results", f"hidden_carry_{shape}.json"), "w") as f:
    json.dump(rows, f, indent=1)
