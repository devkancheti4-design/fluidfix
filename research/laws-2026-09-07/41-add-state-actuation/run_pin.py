#!/usr/bin/env python
"""Measure the ADD_STATE actuation prototype on the 12 ambiguous fixtures
from research/adversarial-2026-09-07/07-compensating-one-site (copied here as
fixtures_07.py, unmodified).

Per fixture:
  1. build a throwaway repo under runs/<name>/ holding the DEFECT
  2. SANITY: pristine green, defect red
  3. `fluidfix repair . --file <mod> --json`  -> res.greens (>=2 candidates),
     res.lineno.  This is exactly what loop.py holds at line 217.
  4. restore the defect (step 3 may have shipped one green)
  5. difftest.differentiate(...)  -> witness + pinning test  (NO ground truth)
  6. SEPARATION (no ground truth): pin the test to candidate i, then run the
     suite with candidate j on the line, for every (i, j). The test separates
     iff green exactly when i == j.
  7. END TO END (ground truth used ONLY to play the user): pin the test to
     whichever candidate equals the PRISTINE line, drop it in the repo, put
     the DEFECT back, re-run fluidfix repair, and record what ships.

usage: nice -n 15 ./tmo 1500 .venv/bin/python run_pin.py
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from fixtures_07 import FIXTURES                                # noqa: E402
import difftest                                                 # noqa: E402

VENV = "/Users/kanchetidevieswar/neo/fluidfix/.venv"
PY = os.path.join(VENV, "bin", "python")
FLUIDFIX = os.path.join(VENV, "bin", "fluidfix")
RUNS = os.path.join(HERE, "runs")
PIN = "test_fluidfix_pin.py"


def sh(args, cwd, timeout=300):
    return subprocess.run(["nice", "-n", "15"] + args, cwd=cwd,
                          capture_output=True, text=True, timeout=timeout)


def write_line(d, fx, line):
    with open(os.path.join(d, fx["module"]), "w", encoding="utf-8",
              newline="") as f:
        f.write(fx["head"] + line + "\n")


def build(fx, line):
    d = os.path.join(RUNS, fx["name"])
    os.makedirs(d, exist_ok=True)
    write_line(d, fx, line)
    with open(os.path.join(d, "test_" + fx["module"]), "w", encoding="utf-8",
              newline="") as f:
        f.write(fx["tests"])
    return d


def suite_green(d):
    p = sh([PY, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider"], d)
    return p.returncode == 0


def main():
    shutil.rmtree(RUNS, ignore_errors=True)
    os.makedirs(RUNS)
    rows = []
    for fx in FIXTURES:
        rec = {"name": fx["name"], "module": fx["module"],
               "pristine": fx["pristine"], "defect": fx["defect"]}

        d = build(fx, fx["pristine"])
        rec["sanity_pristine_green"] = suite_green(d)
        d = build(fx, fx["defect"])
        rec["sanity_defect_red"] = not suite_green(d)

        # -- 3. what the loop holds when it asks the law -------------------
        p = sh([FLUIDFIX, "repair", ".", "--file", fx["module"], "--json"], d,
               timeout=600)
        try:
            res = json.loads(p.stdout[p.stdout.index("{"):])
        except (ValueError, json.JSONDecodeError):
            rec["error"] = (p.stdout + p.stderr)[-500:]
            rows.append(rec)
            continue
        greens = res["greens"]
        rec.update(baseline_status="repaired" if res["repaired"] else "refused",
                   baseline_ambiguous=res["ambiguous"], greens=greens,
                   n_greens=len(greens), baseline_lineno=res["lineno"])
        on_disk = open(os.path.join(d, fx["module"]),
                       encoding="utf-8").read().rstrip("\n").split("\n")[-1]
        rec["baseline_shipped"] = on_disk
        rec["baseline_correct"] = (on_disk == fx["pristine"])
        if len(greens) < 2:
            rec["skip"] = "fewer than two greens - not an AMB situation"
            rows.append(rec)
            continue

        lineno = res["lineno"] or (fx["head"].count("\n") + 1)
        write_line(d, fx, fx["defect"])                       # 4. defect back

        # -- 5. GENERATE (no ground truth) ---------------------------------
        gen = difftest.differentiate(d, fx["module"], lineno, greens, HERE)
        rec["gen"] = {k: v for k, v in gen.items() if k != "test_text"}
        if not gen.get("separated"):
            rows.append(rec)
            print(f"  {fx['name']}: NO WITNESS ({gen.get('failed')})")
            continue
        with open(os.path.join(d, "_pin_template.py"), "w",
                  encoding="utf-8") as f:
            f.write(gen["test_text"])

        # -- 6. SEPARATION matrix (no ground truth) ------------------------
        matrix = []
        for i in range(len(greens)):
            with open(os.path.join(d, PIN), "w", encoding="utf-8") as f:
                f.write(difftest.pinned(gen["test_text"], i))
            row = []
            for j in range(len(greens)):
                write_line(d, fx, greens[j])
                row.append(suite_green(d))
            matrix.append(row)
        os.remove(os.path.join(d, PIN))
        rec["separation_matrix"] = matrix
        rec["separates"] = all(matrix[i][j] == (i == j)
                               for i in range(len(greens))
                               for j in range(len(greens)))

        # -- 7. END TO END: the user answers with their intent -------------
        try:
            pick = greens.index(fx["pristine"])
        except ValueError:
            rec["e2e"] = "pristine line is not among the greens"
            write_line(d, fx, fx["defect"])
            rows.append(rec)
            continue
        rec["pinned_candidate"] = pick
        with open(os.path.join(d, PIN), "w", encoding="utf-8") as f:
            f.write(difftest.pinned(gen["test_text"], pick))
        write_line(d, fx, fx["defect"])
        p = sh([FLUIDFIX, "repair", ".", "--file", fx["module"], "--json"], d,
               timeout=600)
        try:
            res2 = json.loads(p.stdout[p.stdout.index("{"):])
        except (ValueError, json.JSONDecodeError):
            rec["e2e_error"] = (p.stdout + p.stderr)[-500:]
            rows.append(rec)
            continue
        after = open(os.path.join(d, fx["module"]),
                     encoding="utf-8").read().rstrip("\n").split("\n")[-1]
        rec.update(after_status="repaired" if res2["repaired"] else "refused",
                   after_ambiguous=res2["ambiguous"],
                   after_greens=res2["greens"], after_shipped=after,
                   after_correct=(after == fx["pristine"]),
                   after_suite_runs=res2["suite_runs"])
        rows.append(rec)
        print(f"  {fx['name']}: witness={gen['witness_call']} "
              f"separates={rec['separates']} "
              f"before={'CORRECT' if rec['baseline_correct'] else 'WRONG'} "
              f"after={'CORRECT' if rec['after_correct'] else 'WRONG'}")

    with open(os.path.join(HERE, "results_pin.json"), "w") as f:
        json.dump(rows, f, indent=1)

    amb = [r for r in rows if r.get("n_greens", 0) >= 2]
    sep = [r for r in amb if r.get("separates")]
    e2e = [r for r in amb if r.get("after_correct")]
    print("\n" + "=" * 104)
    print(f"{'fixture':<44}{'greens':>7}{'witness':>26}{'sep':>6}"
          f"{'before':>9}{'after':>9}")
    print("-" * 104)
    for r in rows:
        g = r.get("gen", {})
        print(f"{r['name']:<44}{r.get('n_greens', 0):>7}"
              f"{str(g.get('witness_call', '-'))[:25]:>26}"
              f"{str(r.get('separates', '-')):>6}"
              f"{('CORRECT' if r.get('baseline_correct') else 'WRONG'):>9}"
              f"{('CORRECT' if r.get('after_correct') else 'WRONG'):>9}")
    print("-" * 104)
    print(f"ambiguous fixtures (>=2 greens): {len(amb)}")
    print(f"pinning test generated AND separates: {len(sep)}/{len(amb)}")
    print(f"correct program on disk BEFORE the pin: "
          f"{sum(1 for r in amb if r.get('baseline_correct'))}/{len(amb)}")
    print(f"correct program on disk AFTER the pin:  {len(e2e)}/{len(amb)}")


if __name__ == "__main__":
    main()
