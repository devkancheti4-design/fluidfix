#!/usr/bin/env python3
"""Follow the guard's own advice on a budget refusal: replay one saved case with a bigger --budget.

  PYTHONPATH=<fluidfix>/src python3 rerun_budget.py <repos-dir> click/cmp-1 --budget 900
Writes cases/<case>/rerun_budget<N>.json. The clone is reset to the case's base commit first.
"""
import argparse, json, os, re, shutil, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent


def sh(cmd, cwd, env=None, timeout=3600):
    try: return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout, env=env)
    except subprocess.TimeoutExpired:
        class H: returncode = 124; stdout = "TIMEOUT"; stderr = ""
        return H()


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("repos_dir"); ap.add_argument("case"); ap.add_argument("--budget", type=int, default=900)
    ap.add_argument("--extra", default="", help="extra guard flags, e.g. \"--test-timeout 10\"; recorded in the result")
    ap.add_argument("--tag", default="", help="suffix for the result file name")
    ap.add_argument("--pip", action="store_true", help="judge with the fluidfix installed in the clone's venv (PyPI release), not the source tree")
    a = ap.parse_args()
    repo_name, cid = a.case.split("/"); d = HERE / "cases" / repo_name / cid; mut = json.load(open(d / "mutation.json"))
    repo = Path(a.repos_dir) / repo_name; py = str(repo / ".venv" / "bin" / "python")
    env = dict(os.environ); env.pop("PYTHONPATH", None)
    if not a.pip: env["PYTHONPATH"] = str(HERE.parents[1] / "src")
    sh(["git", "reset", "-q", "--hard", mut["base"]], repo); sh(["git", "clean", "-fdq", "-e", ".venv"], repo)
    g0 = sh([py, "-m", "pytest", "-q", "--tb=no", "-x", "--timeout=60", "-p", "no:cacheprovider"], repo, timeout=600)
    assert g0.returncode == 0, "base not green: " + g0.stdout[-300:]
    path = repo / mut["file"]; lines = path.read_text(encoding="utf-8", newline="").split("\n")
    assert lines[mut["lineno"] - 1] == mut["orig"], "base line drifted"
    lines[mut["lineno"] - 1] = mut["mutated"]; path.write_text("\n".join(lines), encoding="utf-8", newline="")
    sh(["git", "-c", "user.name=bench", "-c", "user.email=bench@fluidfix", "commit", "-qam", f"bench: inject {cid}"], repo)
    shutil.rmtree(repo / ".fluidfix", ignore_errors=True)
    t0 = time.time()
    g = sh([py, "-c", "from fluidfix.cli import main; raise SystemExit(main())", "guard", ".", "--commit", "--budget", str(a.budget)] + a.extra.split(), repo, env=env, timeout=a.budget * 4)
    dt = round(time.time() - t0, 1); o = (g.stdout or "") + (g.stderr or "")
    cur = path.read_text(encoding="utf-8", newline="").split("\n")[mut["lineno"] - 1]
    m = re.search(r"repaired line \d+ in (\d+) suite runs", o)
    ref = repo / ".fluidfix" / "last_refusal.json"; refusal = json.load(open(ref)) if ref.exists() else None
    res = {"case": a.case, "budget": a.budget, "extra": a.extra, "tag": a.tag, "code": "pip fluidfix in venv" if a.pip else "source tree", "guard_exit": g.returncode, "seconds": dt, "repaired": "repaired" in o, "byte_exact": cur == mut["orig"],
           "suite_runs": int(m.group(1)) if m else None, "rejected": len((refusal or {}).get("rejected_candidates", [])) if refusal else None,
           "hint": (re.search(r"hint: (.*)", o) or [None, ""])[1][:200], "stdout_tail": o[-1500:]}
    res["verdict"] = "EXACT" if res["repaired"] and res["byte_exact"] else "WRONG-GREEN" if res["repaired"] else "REFUSED" if "REFUSED" in o else f"exit{g.returncode}"
    (d / f"rerun_budget{a.budget}{a.tag}.json").write_text(json.dumps(res, indent=1))
    (d / f"rerun_budget{a.budget}{a.tag}.guard.txt").write_text(o)   # the full guard output, for the write-up
    if refusal: (d / f"refusal_rerun{a.budget}{a.tag}.json").write_text(json.dumps(refusal, indent=1))   # the post-fix refusal, for the ladder
    print(f"{a.case} budget={a.budget}{(' ' + a.extra) if a.extra else ''}{a.tag} -> {res['verdict']} in {dt}s runs={res['suite_runs']} rejected={res['rejected']} hint={res['hint'][:100]!r}", flush=True)
    sh(["git", "reset", "-q", "--hard", mut["base"]], repo); sh(["git", "clean", "-fdq", "-e", ".venv"], repo)


if __name__ == "__main__":
    main()
