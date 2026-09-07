"""False-accept / false-reject sweep over FLUIDFIX_CONFIRM on a flaky fixture.

For each CONFIRM in the given list, N fresh copies of the fixture are made and
`fluidfix repair <copy> --file calc.py --json` is run on each, one at a time,
under `nice -n 15` and `timeout 300`. Every run's parsed result is appended to
results_<fixture>.jsonl; a summary table is printed at the end.

Usage:
  .venv/bin/python run_flaky.py fixture_a 30 0 1 2
"""
import json, os, shutil, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
FLUIDFIX = "/Users/kanchetidevieswar/neo/fluidfix/.venv/bin/fluidfix"


def classify(rc, out):
    """Outcome label from the CLI's exit code and its JSON (when present)."""
    try:
        j = json.loads(out[out.index("{"):])
    except (ValueError, json.JSONDecodeError):
        j = None
    if rc == 3:
        return "GREEN_ABORT", j
    if j is None:
        return f"NO_JSON(rc={rc})", j
    if j.get("repaired"):
        nl = (j.get("new_line") or "").strip()
        if nl == "return a + b":
            return "CORRECT", j
        if nl == "return b - a":
            return "FALSE_ACCEPT", j
        return f"REPAIRED_OTHER({nl})", j
    if j.get("ambiguous"):
        return "REFUSED_AMB", j
    return "REFUSED", j


def one_run(fixture, confirm, i):
    src = os.path.join(HERE, fixture)
    root = os.path.join(HERE, "runs", fixture, f"c{confirm}", f"r{i:03d}")
    if os.path.exists(root):
        shutil.rmtree(root)
    shutil.copytree(src, root)
    env = dict(os.environ, FLUIDFIX_CONFIRM=str(confirm),
               PYTHONDONTWRITEBYTECODE="1")
    # macOS has no `timeout` binary: the 300 s cap is enforced by subprocess
    cmd = ["nice", "-n", "15", FLUIDFIX, "repair", root,
           "--file", "calc.py", "--json"]
    pylog = None
    if os.environ.get("PYWRAP"):
        # count real interpreter invocations (pytest runs) from outside
        pylog = os.path.join(root, "pycalls.log")
        env["FLUIDFIX_PYLOG"] = pylog
        cmd += ["--python", os.path.join(HERE, "pywrap.sh")]
    t0 = time.time()
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, env=env,
                           timeout=300)
        rc, out = p.returncode, p.stdout
    except subprocess.TimeoutExpired as e:
        rc, out = -1, (e.stdout or b"").decode() if isinstance(e.stdout, bytes) else (e.stdout or "")
    dt = time.time() - t0
    label, j = classify(rc, out)
    hidden = 0
    tried = []
    if j:
        for e in j.get("tried_log", []):
            tried.append({"tried": e.get("tried"), "why": (e.get("why") or "")[:160]})
            if "HIDDEN -> CHANGE_GRANULARITY" in (e.get("why") or ""):
                hidden += 1
    rec = {"fixture": fixture, "confirm": confirm, "run": i, "rc": rc,
           "label": label, "wall_s": round(dt, 2),
           "suite_runs": j.get("suite_runs") if j else None,
           "greens": j.get("greens") if j else None,
           "hidden_fired": hidden, "tried": tried,
           "reason": (j.get("reason") if j else out.strip()[-300:])}
    if pylog and os.path.exists(pylog):
        calls = open(pylog).read().splitlines()
        rec["pytest_invocations"] = sum(1 for c in calls if "-m pytest" in c)
        rec["pytest_args"] = [c.split("-p no:benchmark", 1)[-1].strip()
                              for c in calls if "-m pytest" in c]
    # the copy's final calc.py is the evidence of what shipped
    with open(os.path.join(root, "calc.py")) as f:
        rec["final_calc_line2"] = f.read().split("\n")[1]
    return rec


def main():
    fixture = sys.argv[1]
    n = int(sys.argv[2])
    confirms = [int(c) for c in sys.argv[3:]] or [0, 1, 2]
    # TAG lets an independent replication write to its own results file
    suffix = os.environ.get("TAG", "_wrapped" if os.environ.get("PYWRAP") else "")
    out_path = os.path.join(HERE, f"results_{fixture}{suffix}.jsonl")
    with open(out_path, "a") as out:
        for c in confirms:
            for i in range(n):
                rec = one_run(fixture, c, i)
                out.write(json.dumps(rec) + "\n")
                out.flush()
                print(f"{fixture} CONFIRM={c} run {i:3d}: {rec['label']:14s} "
                      f"suite_runs={rec['suite_runs']} hidden={rec['hidden_fired']} "
                      f"pytest={rec.get('pytest_invocations', '-')} "
                      f"{rec['wall_s']}s", flush=True)
    print("wrote", out_path)


if __name__ == "__main__":
    main()
