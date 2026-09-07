#!/usr/bin/env python
"""11-rank-exhaustive: where the RETRIED veto actually pays.

veto_measured.py showed the veto reorders correctly (defect line last ->
first) but saves ZERO suite runs on a COMPLETED search.  The reason is in
loop.py:244-263: repair() deliberately collects greens across the WHOLE
observation list and asks the engine law once at the end, because AMB
cannot be observed from a single candidate set.  So in a search that runs
to completion, ORDER decides WHICH green ships, never HOW MANY runs cost.

Order therefore pays only when the search is CUT SHORT -- the CAPPED lane.
This script measures that case: same fixture, same two arms, but with a
tight escalation budget so the escalation pass hits its deadline.

  A  baseline       -- RETRIED never supplied (ships today)
  B  veto supplied  -- retried = {linenos already rejected in pass 0}

Nothing in src/ is edited.

Run:  nice -n 15 ./timeout.sh 300 \
        /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python veto_deadline.py
"""
import os
import re
import shutil
import sys
import tempfile
import time

sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
import fluidfix.guard as G                                    # noqa: E402
from fluidfix import MechanicalObserver, Oracle, guard_once    # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ESCALATE_BUDGET = int(os.environ.get("ESC_BUDGET", "8"))   # file_share = /2

names = ["a", "b", "c", "d", "e", "g", "h", "i", "j", "k"]
src = ["def f(x, " + ", ".join(names) + "):", "    ok = True",
       "    u = x", "    v = x"]
src += ["    u = u * v"] * 105
for nm in names[:-1]:
    src.append(f"    ok = ok and (x >= {nm})")
src.append("    ok = ok and (x > k)")            # THE DEFECT
src.append("    return ok")
MOD = "\n".join(src) + "\n"
DEFECT_LINE = len(src) - 1
TEST = ("from mod import f\n\nT = (5,) * 10\n\ndef test_f():\n"
        "    assert f(6, *T) is True\n    assert f(5, *T) is True\n"
        "    assert f(4, *T) is False\n")

_repair = G.repair
_rank_obs = G.rank_observations


def run(label, supply_veto):
    log, rejected, calls = [], set(), {"n": 0}

    def spy_repair(oracle, rel, observations, **kw):
        res = _repair(oracle, rel, observations, **kw)
        for e in res.tried_log:
            m = re.search(r":(\d+)(?:-\d+)?$", e["at"])
            if m:
                rejected.add(int(m.group(1)))
        log.append({"order": [o.lineno for o in observations],
                    "suite_runs": res.suite_runs, "repaired": res.repaired,
                    "lineno": res.lineno, "reason": (res.reason or "")[:90]})
        return res

    def spy_rank_obs(s_, obs, out, **kw):
        calls["n"] += 1
        if supply_veto and calls["n"] >= 2:
            kw["retried"] = set(rejected)
        return _rank_obs(s_, obs, out, **kw)

    G.repair, G.rank_observations = spy_repair, spy_rank_obs
    d = tempfile.mkdtemp(prefix="vd_", dir=HERE)
    try:
        open(os.path.join(d, "mod.py"), "w").write(MOD)
        open(os.path.join(d, "test_mod.py"), "w").write(TEST)
        t0 = time.time()
        rep = guard_once(Oracle(d, python=sys.executable), MechanicalObserver(),
                         escalate_budget=ESCALATE_BUDGET)
        wall = time.time() - t0
    finally:
        shutil.rmtree(d, ignore_errors=True)
        G.repair, G.rank_observations = _repair, _rank_obs

    print(f"\n=== {label} (escalate_budget={ESCALATE_BUDGET}s) ===")
    print(f"  guard status = {rep.status}   file={rep.file}   "
          f"wall={wall:.1f}s   defect line={DEFECT_LINE}")
    for i, c in enumerate(log):
        pos = (c["order"].index(DEFECT_LINE)
               if DEFECT_LINE in c["order"] else None)
        print(f"  repair call {i} ({'pass 0' if i == 0 else 'escalation'}): "
              f"runs={c['suite_runs']} repaired={c['repaired']} at={c['lineno']}")
        print(f"    defect line position in order: {pos} of {len(c['order'])}")
        if c["reason"]:
            print(f"    reason: {c['reason']}")
    return {"status": rep.status, "wall": wall, "log": log}


A = run("A  baseline  (RETRIED never supplied)", False)
B = run("B  veto supplied at the escalation call", True)

print("\n================ RESULT (deadline-limited escalation) ================")
print(f"  A baseline      status={A['status']:<10} wall={A['wall']:.1f}s")
print(f"  B with veto     status={B['status']:<10} wall={B['wall']:.1f}s")
rep_a = any(c["repaired"] for c in A["log"])
rep_b = any(c["repaired"] for c in B["log"])
print(f"  defect repaired A={rep_a}   B={rep_b}")
if rep_b and not rep_a:
    print("  => the veto turned a budget-limited REFUSAL into a REPAIR")
elif rep_a == rep_b:
    print("  => same outcome in both arms at this budget; "
          "see positions above for the ordering difference")
