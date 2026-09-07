#!/usr/bin/env python
"""11-rank-exhaustive: MEASURE the RETRIED veto instead of projecting it.

veto_potential.py ends with a projection ("escalation suite runs would be
about 3").  A projection is not a measurement.  This script measures the
same fixture twice, changing exactly ONE thing and touching no file in src/:

  A  baseline          -- guard.py as it ships: neither call site passes
                          `retried=`, so the law reads RETRIED = 0.
  B  veto supplied     -- a shim wraps guard.rank_observations and, on the
                          ESCALATION call only, passes
                              retried = {linenos already rejected}
                          built from the previous repair()'s tried_log.
                          That is precisely the data guard_once already has
                          in its local `attempts` list at guard.py:585
                          (accumulated at :518), whose entries carry
                          "at" = f"{defect_file}:{lineno}" (loop.py:331).

Nothing in src/ is edited; both arms monkeypatch this process only.

Run:  nice -n 15 ./timeout.sh 300 \
        /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python veto_measured.py
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
FILLER = 105

names = ["a", "b", "c", "d", "e", "g", "h", "i", "j", "k"]
src = ["def f(x, " + ", ".join(names) + "):", "    ok = True",
       "    u = x", "    v = x"]
src += ["    u = u * v"] * FILLER
for nm in names[:-1]:
    src.append(f"    ok = ok and (x >= {nm})")
src.append("    ok = ok and (x > k)")            # THE DEFECT: > for >=
src.append("    return ok")
MOD = "\n".join(src) + "\n"
DEFECT_LINE = len(src) - 1
TEST = ("from mod import f\n\nT = (5,) * 10\n\ndef test_f():\n"
        "    assert f(6, *T) is True\n    assert f(5, *T) is True\n"
        "    assert f(4, *T) is False\n")

_repair = G.repair
_rank_obs = G.rank_observations


def arm(supply_veto: bool):
    """Install the spies; return the per-call log list."""
    log = []
    rejected_lines: set = set()          # stands in for guard_once's `attempts`
    calls = {"n": 0}

    def spy_repair(oracle, rel, observations, **kw):
        t = time.time()
        res = _repair(oracle, rel, observations, **kw)
        for e in res.tried_log:          # "at" == f"{file}:{lineno}"
            m = re.search(r":(\d+)(?:-\d+)?$", e["at"])
            if m:
                rejected_lines.add(int(m.group(1)))
        log.append({"order": [o.lineno for o in observations],
                    "suite_runs": res.suite_runs, "repaired": res.repaired,
                    "lineno": res.lineno, "secs": time.time() - t,
                    "n_rejected_known_before": len(rejected_lines)})
        return res

    def spy_rank_obs(src_, obs, out, **kw):
        calls["n"] += 1
        if supply_veto and calls["n"] >= 2:      # the escalation call
            kw["retried"] = set(rejected_lines)
        return _rank_obs(src_, obs, out, **kw)

    G.repair = spy_repair
    G.rank_observations = spy_rank_obs
    return log, rejected_lines


def run(label, supply_veto):
    log, rejected = arm(supply_veto)
    d = tempfile.mkdtemp(prefix="vm_", dir=HERE)
    try:
        open(os.path.join(d, "mod.py"), "w").write(MOD)
        open(os.path.join(d, "test_mod.py"), "w").write(TEST)
        t0 = time.time()
        rep = guard_once(Oracle(d, python=sys.executable), MechanicalObserver())
        wall = time.time() - t0
    finally:
        shutil.rmtree(d, ignore_errors=True)
        G.repair = _repair
        G.rank_observations = _rank_obs
    total = sum(c["suite_runs"] for c in log)
    print(f"\n=== {label} ===")
    print(f"status={rep.status} file={rep.file} wall={wall:.1f}s "
          f"defect line={DEFECT_LINE}")
    for i, c in enumerate(log):
        pos = (c["order"].index(DEFECT_LINE)
               if DEFECT_LINE in c["order"] else None)
        print(f"  repair call {i} ({'pass 0' if i == 0 else 'escalation'}): "
              f"suite_runs={c['suite_runs']} repaired={c['repaired']} "
              f"at={c['lineno']} {c['secs']:.1f}s")
        print(f"    order={c['order']}")
        print(f"    defect line position in order: {pos} of "
              f"{len(c['order'])}")
    print(f"  TOTAL suite runs across passes: {total}")
    return {"total": total, "wall": wall, "log": log, "status": rep.status}


A = run("A  baseline (ships today: RETRIED never supplied)", False)
B = run("B  veto supplied at the escalation call from tried_log", True)

print("\n================ RESULT ================")
esc_a = A["log"][1]["suite_runs"] if len(A["log"]) > 1 else None
esc_b = B["log"][1]["suite_runs"] if len(B["log"]) > 1 else None
print(f"escalation-pass suite runs   A={esc_a}   B={esc_b}")
print(f"total suite runs             A={A['total']}   B={B['total']}")
print(f"wall seconds                 A={A['wall']:.1f}   B={B['wall']:.1f}")
print(f"both repaired the defect     A={A['status']}   B={B['status']}")
if esc_a and esc_b:
    print(f"escalation suite runs saved by the veto: {esc_a - esc_b} "
          f"({100.0 * (esc_a - esc_b) / esc_a:.0f}% of the escalation pass)")
