#!/usr/bin/env python3
"""Replay the refused cases from bench_real.py through the escalation ladder with one author.

For each cases/<repo>/<id>/mutation.json: reset the clone to its base commit, re-apply the
exact mutation, commit it, run fuse.py with the chosen backend, and score the file against the
PRISTINE line. Tokens come from the backend's own counts (Ollama: prompt_eval_count/eval_count;
file author: characters/4, marked approximate).

  python3 ladder.py <repos-dir> --backend ollama --model qwen3.5:4b [--tier2-model ID] [--only click]
  python3 ladder.py <repos-dir> --backend file --label fable-5.1 --stage collect|run
"""
import argparse, json, os, re, shutil, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
FUSE = HERE / "fuse.py"


def sh(cmd, cwd, env=None, timeout=1800):
    try: return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout, env=env)
    except subprocess.TimeoutExpired:
        class H: returncode = 124; stdout = "TIMEOUT"; stderr = ""
        return H()


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("repos_dir"); ap.add_argument("--backend", default="ollama")
    ap.add_argument("--model", default="qwen3.5:4b"); ap.add_argument("--tier2-model"); ap.add_argument("--label")
    ap.add_argument("--only"); ap.add_argument("--stage", default="run"); ap.add_argument("--out")
    ap.add_argument("--budget", type=int, default=300, help="wall-clock budget per guard run, as in bench_real.py")
    ap.add_argument("--classes", help="comma-separated fault classes to replay (default: all saved cases)")
    a = ap.parse_args()
    label = a.label or (a.model if a.backend == "ollama" else a.backend)
    out = Path(a.out or (HERE / f"ladder_{re.sub(r'[^A-Za-z0-9.]+', '-', label)}.json"))
    done = {r["case"]: r for r in json.load(open(out))} if out.exists() else {}
    results = list(done.values())
    for mfile in sorted((HERE / "cases").rglob("mutation.json")):
        repo_name, cid = mfile.parent.parent.name, mfile.parent.name
        case = f"{repo_name}/{cid}"
        if a.only and a.only not in case: continue
        if case in done and a.stage == "run": continue
        mut = json.load(open(mfile)); repo = Path(a.repos_dir) / repo_name; py = str(repo / ".venv" / "bin" / "python")
        if a.classes and mut["cls"] not in a.classes.split(","): continue
        env = dict(os.environ); env["PYTHONPATH"] = str(HERE.parents[1] / "src")
        sh(["git", "reset", "-q", "--hard", mut["base"]], repo); sh(["git", "clean", "-fdq", "-e", ".venv"], repo)
        path = repo / mut["file"]; lines = path.read_text(encoding="utf-8", newline="").split("\n")
        assert lines[mut["lineno"] - 1] == mut["orig"], f"{case}: base line drifted"
        lines[mut["lineno"] - 1] = mut["mutated"]; path.write_text("\n".join(lines), encoding="utf-8", newline="")
        sh(["git", "-c", "user.name=bench", "-c", "user.email=bench@fluidfix", "commit", "-qam", f"bench: inject {cid}"], repo)
        shutil.rmtree(repo / ".fluidfix", ignore_errors=True)
        cmd = [py, str(FUSE), ".", "--backend", a.backend, "--incident", case, "--report", str(mfile.parent / f"report_{label}.json"),
               "--budget", str(a.budget)]
        if (mfile.parent / "refusal_tier0.json").exists(): cmd += ["--refusal", str(mfile.parent / "refusal_tier0.json")]
        if a.backend == "ollama": cmd += ["--tier1-model", a.model, "--tier2-model", a.tier2_model or a.model]
        elif a.backend.startswith("file"): cmd += ["--author-dir", str(mfile.parent / f"author_{label}"), "--author-label", label]
        t0 = time.time(); r = sh(cmd, repo, env=env, timeout=2400); wall = round(time.time() - t0, 1)
        cur = path.read_text(encoding="utf-8", newline="").split("\n")[mut["lineno"] - 1]
        rep_path = mfile.parent / f"report_{label}.json"
        rep = json.load(open(rep_path)) if rep_path.exists() and r.returncode != 3 else {}
        if r.returncode == 3:
            print(f"{case}: awaiting author — packet written under {mfile.parent / ('author_' + label)}", flush=True)
            sh(["git", "reset", "-q", "--hard", mut["base"]], repo); continue
        outcome = rep.get("outcome", f"exit{r.returncode}")
        if r.returncode not in (0, 2, 3): print(f"{case}: fuse.py exit {r.returncode}\n" + (r.stderr or r.stdout or "")[-800:], flush=True)
        exact = cur == mut["orig"]; changed = cur != mut["mutated"]
        verdict = ("EXACT" if outcome in ("tier1", "tier2") and exact else "WRONG-GREEN" if outcome in ("tier1", "tier2") and changed
                   else "SUSPECT" if outcome in ("tier1", "tier2") else "REFUSED" if outcome.startswith("refused") else outcome)
        row = {"case": case, "cls": mut["cls"], "file": mut["file"], "orig": mut["orig"].strip(), "mutated": mut["mutated"].strip(),
               "author": label, "outcome": outcome, "verdict": verdict, "tokens": rep.get("tokens"), "tiers": rep.get("tiers"), "wall_s": wall}
        results = [x for x in results if x["case"] != case] + [row]
        tk = (rep.get("tokens") or {}).get("total", "-")
        print(f"{case:28} {mut['cls']:10} -> {verdict:12} via {outcome:20} tokens={tk} {wall}s", flush=True)
        sh(["git", "reset", "-q", "--hard", mut["base"]], repo); sh(["git", "clean", "-fdq", "-e", ".venv"], repo)
        out.write_text(json.dumps(results, indent=1))
    print("LADDER_DONE", label)


if __name__ == "__main__":
    main()
