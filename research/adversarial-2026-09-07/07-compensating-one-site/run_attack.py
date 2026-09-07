#!/usr/bin/env python
"""Reproduce attack 07-compensating-one-site over the 12 fixtures.

For each fixture:
  1. build a throwaway repo under runs/<name>/
  2. SANITY: the PRISTINE program must leave the suite green
  3. SANITY: the DEFECT program must leave the suite red
  4. run `fluidfix repair . --file <module> --json` (mechanical observer)
  5. record what was written to disk, and whether it equals the pristine line
  6. DIFFERENTIAL: evaluate `probe` under pristine vs under the shipped
     program — a differing value proves they are two PROGRAMS, not two
     spellings of one

Writes results.json and prints a table. One suite run at a time, nice+timeout.

usage:  ./tmo 1200 .venv/bin/python run_attack.py
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from fixtures import FIXTURES                                   # noqa: E402

VENV = "/Users/kanchetidevieswar/neo/fluidfix/.venv"
PY = os.path.join(VENV, "bin", "python")
FLUIDFIX = os.path.join(VENV, "bin", "fluidfix")
RUNS = os.path.join(HERE, "runs")


def sh(args, cwd, timeout=300):
    return subprocess.run(["nice", "-n", "15"] + args, cwd=cwd,
                          capture_output=True, text=True, timeout=timeout)


def build(fx, line):
    d = os.path.join(RUNS, fx["name"])
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, fx["module"]), "w", encoding="utf-8",
              newline="") as f:
        f.write(fx["head"] + line + "\n")
    with open(os.path.join(d, "test_" + fx["module"]), "w", encoding="utf-8",
              newline="") as f:
        f.write(fx["tests"])
    return d


def suite_green(d):
    p = sh([PY, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider"], d)
    return p.returncode == 0, p.stdout[-400:]


def probe_value(fx, line):
    """Evaluate the fixture's differential probe against `line`."""
    d = os.path.join(RUNS, "_probe")
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d)
    with open(os.path.join(d, fx["module"]), "w", encoding="utf-8") as f:
        f.write(fx["head"] + line + "\n")
    mod = fx["module"][:-3]
    src = (f"from {mod} import *\n"
           f"print(repr({fx['probe']}))\n")
    with open(os.path.join(d, "_p.py"), "w", encoding="utf-8") as f:
        f.write(src)
    p = sh([PY, "-B", "_p.py"], d, timeout=60)
    return (p.stdout.strip() or ("ERROR: " + p.stderr.strip()[-160:]))


def main():
    shutil.rmtree(RUNS, ignore_errors=True)
    os.makedirs(RUNS)
    rows = []
    for fx in FIXTURES:
        rec = {"name": fx["name"], "module": fx["module"],
               "pristine": fx["pristine"], "defect": fx["defect"]}

        d = build(fx, fx["pristine"])
        ok, out = suite_green(d)
        rec["sanity_pristine_green"] = ok
        if not ok:
            rec["sanity_note"] = out
        d = build(fx, fx["defect"])
        ok, out = suite_green(d)
        rec["sanity_defect_red"] = (not ok)

        p = sh([FLUIDFIX, "repair", ".", "--file", fx["module"], "--json"],
               d, timeout=600)
        try:
            res = json.loads(p.stdout[p.stdout.index("{"):])
        except (ValueError, json.JSONDecodeError):
            rec["error"] = (p.stdout + p.stderr)[-600:]
            rows.append(rec)
            continue

        on_disk = open(os.path.join(d, fx["module"]), encoding="utf-8").read()
        shipped = on_disk.rstrip("\n").split("\n")[-1]
        rec.update(
            fluidfix_status=("repaired" if res["repaired"] else "refused"),
            fluidfix_reason=res["reason"],
            fluidfix_ambiguous=res["ambiguous"],
            greens=res["greens"],
            n_greens=len(res["greens"]),
            shipped_line=shipped,
            suite_runs=res["suite_runs"],
            acts_tried=res["acts_tried"],
            shipped_equals_pristine=(shipped == fx["pristine"]),
        )
        if res["repaired"]:
            pv = probe_value(fx, fx["pristine"])
            sv = probe_value(fx, shipped)
            rec.update(probe=fx["probe"], probe_pristine=pv, probe_shipped=sv,
                       probe_differs=(pv != sv))
        rows.append(rec)
        print(f"  {fx['name']}: {rec.get('fluidfix_status')} "
              f"greens={rec.get('n_greens')} "
              f"correct={rec.get('shipped_equals_pristine')}")

    shutil.rmtree(os.path.join(RUNS, "_probe"), ignore_errors=True)
    with open(os.path.join(HERE, "results.json"), "w") as f:
        json.dump(rows, f, indent=1)

    # ------------------------------------------------------------ report --
    shipped = [r for r in rows if r.get("fluidfix_status") == "repaired"]
    wrong = [r for r in shipped if not r["shipped_equals_pristine"]]
    print("\n" + "=" * 100)
    print(f"{'fixture':<48} {'status':<9} {'greens':>6} {'ships':<8} {'probe differs':<13}")
    print("-" * 100)
    for r in rows:
        print(f"{r['name']:<48} {r.get('fluidfix_status', 'ERR'):<9} "
              f"{r.get('n_greens', 0):>6} "
              f"{('CORRECT' if r.get('shipped_equals_pristine') else 'WRONG'):<8} "
              f"{str(r.get('probe_differs', '-')):<13}")
    print("-" * 100)
    print(f"fixtures: {len(rows)}   shipped a repair: {len(shipped)}   "
          f"shipped the WRONG program: {len(wrong)} "
          f"({100.0 * len(wrong) / max(1, len(shipped)):.0f}% of ships)")
    print(f"refused as AMBIGUOUS: "
          f"{sum(1 for r in rows if r.get('fluidfix_ambiguous'))}")
    bad_sanity = [r["name"] for r in rows
                  if not (r["sanity_pristine_green"] and r["sanity_defect_red"])]
    print(f"fixtures failing sanity (pristine green / defect red): "
          f"{bad_sanity or 'none'}")


if __name__ == "__main__":
    main()
