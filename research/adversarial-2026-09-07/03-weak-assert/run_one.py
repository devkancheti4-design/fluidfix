#!/usr/bin/env python
"""Run ONE injected defect end to end.

    run_one.py <defect-id>

  1. fresh copy of victim/ into runs/<id>/
  2. apply the mutant line
  3. run the weak suite: GREEN -> the defect is undetected, record and stop
     (fluidfix is right to refuse; this case is not in the attack denominator)
  4. RED -> `fluidfix repair --file weakpkg/core.py --json`
  5. compare the resulting core.py to the PRISTINE original, byte for byte

Writes runs/<id>/result.json.
"""
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
VENV = "/Users/kanchetidevieswar/neo/fluidfix/.venv"
PY = os.path.join(VENV, "bin", "python")
FF = os.path.join(VENV, "bin", "fluidfix")
TIMEOUT = os.path.join(HERE, "timeout.sh")
VICTIM = os.environ.get("VICTIM", "victim")
PKG = os.environ.get("PKG", "weakpkg")
RUNS = os.environ.get("RUNS", "runs")
DEFECTS = os.environ.get("DEFECTS", "defects.json")


def sh(args, secs, cwd=None):
    p = subprocess.run([TIMEOUT, str(secs)] + args, cwd=cwd,
                       capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def main():
    did = int(sys.argv[1])
    defects = json.load(open(os.path.join(HERE, DEFECTS)))
    d = next(x for x in defects if x["id"] == did)

    run = os.path.join(HERE, RUNS, f"{did:02d}")
    shutil.rmtree(run, ignore_errors=True)
    shutil.copytree(os.path.join(HERE, VICTIM), run)

    core = os.path.join(run, PKG, "core.py")
    pristine = open(core, encoding="utf-8", newline="").read()
    raw = pristine.split("\n")
    i = d["lineno"] - 1
    assert raw[i].rstrip("\r") == d["orig"], (raw[i], d["orig"])
    raw[i] = d["mutant"]
    mutated = "\n".join(raw)
    with open(core, "w", encoding="utf-8", newline="") as fh:
        fh.write(mutated)

    res = dict(d)
    rc, out = sh([PY, "-m", "pytest", "-q", "--no-header", "--tb=no"], 120, cwd=run)
    res["suite_red"] = (rc != 0)
    res["baseline_rc"] = rc
    if rc == 0:
        res["outcome"] = "undetected-by-weak-suite"
        json.dump(res, open(os.path.join(run, "result.json"), "w"), indent=1)
        print(f"[{did:02d}] UNDETECTED (suite still green with the defect in)")
        return

    rc, out = sh([FF, "repair", ".", "--file", f"{PKG}/core.py",
                  "--python", PY, "--json"], 600, cwd=run)
    res["fluidfix_rc"] = rc
    res["fluidfix_out"] = out[-6000:]
    try:
        res["report"] = json.loads(out[out.index("{"):out.rindex("}") + 1])
    except (ValueError, json.JSONDecodeError):
        res["report"] = None

    final = open(core, encoding="utf-8", newline="").read()
    res["final_equals_pristine"] = (final == pristine)
    res["final_equals_mutant"] = (final == mutated)
    fl = final.split("\n")
    res["final_line"] = fl[i] if i < len(fl) else None

    rep = res["report"] or {}
    if rep.get("repaired"):
        res["outcome"] = ("SHIPPED-CORRECT" if res["final_equals_pristine"]
                          else "SHIPPED-WRONG")
    elif res["final_equals_pristine"]:
        res["outcome"] = "refused-tree-clean"
    else:
        res["outcome"] = "refused-TREE-DIRTY" if not res["final_equals_mutant"] \
            else "refused-tree-restored-to-defect"
    res["greens"] = rep.get("greens")
    res["reason"] = rep.get("reason")
    json.dump(res, open(os.path.join(run, "result.json"), "w"), indent=1)
    print(f"[{did:02d}] {res['outcome']}  line {d['lineno']}  "
          f"{d['kind_name']}\n     defect : {d['mutant'].strip()}\n"
          f"     orig   : {d['orig'].strip()}\n"
          f"     shipped: {(res['final_line'] or '').strip()}\n"
          f"     greens : {res['greens']}\n     reason : {res['reason']}")


if __name__ == "__main__":
    main()
