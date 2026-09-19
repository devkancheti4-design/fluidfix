#!/usr/bin/env python3
"""Teach once, by hand, then meet the same fault class as another developer would: on another repository.

Five fault classes the seeded real-repo bench (research/llm-fusion-2026-09-16) refused at tier 0. Each is taught
from ONE worked example — the click case (range start: the sortedcontainers case) — in rules_taught.py /
rules_taught_rangestart.py, written by hand and frozen before any hold-out ran. Then, with that dictionary and
the mechanical observer (no model, zero tokens), the guard meets every OTHER live mutant of the same class the
bench had cut on the other repositories: arrow, sortedcontainers, rich (for range start: the other seeded
range(1, sites of sortedcontainers, liveness checked twice as in the bench). Byte-exact against pristine or not.

  PYTHONPATH=<fluidfix>/src python3 run.py <repos-dir> [--budget 900]
"""
import argparse, json, os, re, shutil, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
BENCH = HERE.parent / "llm-fusion-2026-09-16"
sys.path.insert(0, str(BENCH))
import bench_real as B  # noqa: E402  (mutation operators, site finder, liveness check — the bench's own code)

PLAN = {  # class -> (dictionary, worked example, hold-outs)
    "andor":      ("rules_taught.py", "click/andor-1", ["arrow/andor-1", "python-sortedcontainers/andor-1", "rich/andor-1"]),
    "getdef":     ("rules_taught.py", "click/getdef-1", ["arrow/getdef-1", "rich/getdef-1"]),
    "notdrop":    ("rules_taught.py", "click/notdrop-1", ["arrow/notdrop-1", "python-sortedcontainers/notdrop-1", "rich/notdrop-1"]),
    "lenm1":      ("rules_taught.py", "click/lenm1-1", ["arrow/lenm1-1", "python-sortedcontainers/lenm1-1", "rich/lenm1-1"]),
    "rangestart": ("rules_taught_rangestart.py", "python-sortedcontainers/rangestart-1", "find:python-sortedcontainers"),
}


def sh(cmd, cwd, env=None, timeout=3600):
    try: return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout, env=env)
    except subprocess.TimeoutExpired:
        class H: returncode = 124; stdout = "TIMEOUT"; stderr = ""
        return H()


def load_case(case):
    repo, cid = case.split("/"); return json.load(open(BENCH / "cases" / repo / cid / "mutation.json"))


def find_holdouts(repos, repo_name, cls, teach_lineno, want=2):
    """Other seeded sites of the class in the same library, in the bench's seed order, live twice (bench rule)."""
    repo = repos / repo_name; py = str(repo / ".venv" / "bin" / "python"); base = sh(["git", "rev-parse", "HEAD"], repo).stdout.strip()
    out = []
    for site in B.find_sites(repo, B.LIB[repo_name], cls):
        if site[1] + 1 == teach_lineno or len(out) >= want: continue
        sh(["git", "reset", "-q", "--hard", base], repo); mut = B.mutate(repo, site, cls)
        if mut is None: continue
        first = B.suite_fails(py, repo); sh(["git", "checkout", "-q", "--", mut["file"]], repo)
        if first is not True: print(f"  hold-out candidate {mut['file']}:{mut['lineno']} {'HUNG' if first == 'hung' else 'dead'}", flush=True); continue
        B.mutate(repo, site, cls); live2 = B.suite_fails(py, repo); sh(["git", "checkout", "-q", "--", mut["file"]], repo)
        if live2 is not True: print(f"  hold-out candidate {mut['file']}:{mut['lineno']} flaky", flush=True); continue
        mut.update(cls=cls, base=base); out.append(mut); print(f"  hold-out {cls}-h{len(out)}: {mut['file']}:{mut['lineno']} {mut['orig'].strip()[:60]!r} (live x2)", flush=True)
    sh(["git", "reset", "-q", "--hard", base], repo); return out


def run_case(repos, repo_name, mut, dictionary, budget, env):
    repo = repos / repo_name; py = str(repo / ".venv" / "bin" / "python")
    sh(["git", "reset", "-q", "--hard", mut["base"]], repo); sh(["git", "clean", "-fdq", "-e", ".venv"], repo)
    path = repo / mut["file"]; lines = path.read_text(encoding="utf-8", newline="").split("\n")
    assert lines[mut["lineno"] - 1] == mut["orig"], f"{mut['file']}:{mut['lineno']} base line drifted"
    lines[mut["lineno"] - 1] = mut["mutated"]; path.write_text("\n".join(lines), encoding="utf-8", newline="")
    sh(["git", "-c", "user.name=bench", "-c", "user.email=bench@fluidfix", "commit", "-qam", f"bench: inject {mut['cls']} at {mut['file']}:{mut['lineno']}"], repo)
    shutil.rmtree(repo / ".fluidfix", ignore_errors=True)
    t0 = time.time()
    g = sh([py, "-c", "from fluidfix.cli import main; raise SystemExit(main())", "guard", ".", "--commit", "--budget", str(budget),
            "--dictionary", str(HERE / dictionary)], repo, env=env, timeout=budget * 4)
    dt = round(time.time() - t0, 1); o = (g.stdout or "") + (g.stderr or "")
    cur = path.read_text(encoding="utf-8", newline="").split("\n")[mut["lineno"] - 1]
    m = re.search(r"repaired line (\d+) in (\d+) suite runs", o)
    res = {"guard_exit": g.returncode, "seconds": dt, "repaired": "repaired" in o, "byte_exact": cur == mut["orig"],
           "suite_runs": int(m.group(2)) if m else None, "repaired_line": int(m.group(1)) if m else None,
           "hint": (re.search(r"hint: (.*)", o) or [None, ""])[1][:200], "guard_tail": o[-900:]}
    res["verdict"] = "EXACT" if res["repaired"] and res["byte_exact"] else "WRONG-GREEN" if res["repaired"] else "REFUSED" if "REFUSED" in o else f"exit{g.returncode}"
    sh(["git", "reset", "-q", "--hard", mut["base"]], repo); sh(["git", "clean", "-fdq", "-e", ".venv"], repo)
    return res


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("repos_dir"); ap.add_argument("--budget", type=int, default=900); a = ap.parse_args()
    repos = Path(a.repos_dir).resolve(); env = dict(os.environ); env["PYTHONPATH"] = str(HERE.parents[1] / "src")
    results = []; out = HERE / "results.json"
    print(f"observer: mechanical (default) — no model, zero tokens; budget {a.budget} s per case; dictionaries frozen before this run", flush=True)
    for cls, (dictionary, teach, holdouts) in PLAN.items():
        print(f"### {cls}: dictionary {dictionary}", flush=True)
        repo_name, _ = teach.split("/"); mut = load_case(teach)
        r = run_case(repos, repo_name, mut, dictionary, a.budget, env)
        row = {"cls": cls, "role": "worked-example", "case": teach, "repo": repo_name, "file": mut["file"], "lineno": mut["lineno"], "orig": mut["orig"].strip(), "mutated": mut["mutated"].strip(), **r}
        results.append(row); out.write_text(json.dumps(results, indent=1))
        print(f"  [{cls}] worked example {teach} -> {r['verdict']} in {r['seconds']}s runs={r['suite_runs']}", flush=True)
        if isinstance(holdouts, str) and holdouts.startswith("find:"):
            hrepo = holdouts[5:]; found = find_holdouts(repos, hrepo, cls, mut["lineno"])
            hold = [(f"{hrepo}/{cls}-h{i+1}", hrepo, m) for i, m in enumerate(found)]
            for cid, _, m in hold: d = HERE / "cases" / hrepo / cid.split("/")[1]; d.mkdir(parents=True, exist_ok=True); (d / "mutation.json").write_text(json.dumps(m, indent=1))
        else:
            hold = [(c, c.split("/")[0], load_case(c)) for c in holdouts]
        for case, hrepo, m in hold:
            r = run_case(repos, hrepo, m, dictionary, a.budget, env)
            row = {"cls": cls, "role": "hold-out", "case": case, "repo": hrepo, "file": m["file"], "lineno": m["lineno"], "orig": m["orig"].strip(), "mutated": m["mutated"].strip(), **r}
            results.append(row); out.write_text(json.dumps(results, indent=1))
            print(f"  [{cls}] hold-out {case} {m['file']}:{m['lineno']} -> {r['verdict']} in {r['seconds']}s runs={r['suite_runs']}", flush=True)
    ho = [r for r in results if r["role"] == "hold-out"]; we = [r for r in results if r["role"] == "worked-example"]
    print(f"TALLY worked examples {sum(r['verdict']=='EXACT' for r in we)}/{len(we)} exact | hold-outs {sum(r['verdict']=='EXACT' for r in ho)}/{len(ho)} exact, "
          f"{sum(r['verdict']=='WRONG-GREEN' for r in ho)} wrong-green, {sum(r['verdict']=='REFUSED' for r in ho)} refused | tokens 0")
    print("TEACH_DONE", flush=True)


if __name__ == "__main__":
    main()
