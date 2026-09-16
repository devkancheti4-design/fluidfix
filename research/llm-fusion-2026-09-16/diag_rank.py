#!/usr/bin/env python3
"""Why did the guard open the files in that order? Re-apply one saved case on a clone and print
the ranking the guard computes (fresh process, same code), with the evidence the SIGHT law had.
  PYTHONPATH=<fluidfix>/src python3 diag_rank.py <repos-dir> arrow/cmp-1"""
import json, os, subprocess, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
repos, case = Path(sys.argv[1]), sys.argv[2]; repo_name, cid = case.split("/")
mut = json.load(open(HERE / "cases" / repo_name / cid / "mutation.json")); repo = repos / repo_name; py = str(repo / ".venv" / "bin" / "python")
def sh(c, **k): return subprocess.run(c, cwd=repo, capture_output=True, text=True, **k)
sh(["git", "reset", "-q", "--hard", mut["base"]]); sh(["git", "clean", "-fdq", "-e", ".venv"])
p = repo / mut["file"]; L = p.read_text(encoding="utf-8", newline="").split("\n"); assert L[mut["lineno"] - 1] == mut["orig"]; L[mut["lineno"] - 1] = mut["mutated"]; p.write_text("\n".join(L), encoding="utf-8", newline="")
env = dict(os.environ, PYTHONPATH=str(HERE.parents[1] / "src"))
r = sh([py, str(HERE / "rank_helper.py"), str(repo)], env=env)
d = json.loads(r.stdout.strip().splitlines()[-1]); ranked = d["ranked"]
print(case, "true file", mut["file"], "rank", ranked.index(mut["file"]) + 1 if mut["file"] in ranked else None, "of", len(ranked))
print(" ranked:", ranked[:8]); print(" pointed:", d.get("pointed")); print(" red:", d["red"])
sh(["git", "reset", "-q", "--hard", mut["base"]])
