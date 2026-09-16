"""Is the tree dirty after a guard run with the taught dictionary? Apply the case, run the guard, then inspect
git before any reset. Also records every FAILED line the guard's own runs reported, in order."""
import json, os, subprocess, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
repos, case, dictionary = Path(sys.argv[1]), sys.argv[2], sys.argv[3]; repo_name, cid = case.split("/")
mut = json.load(open(HERE / "cases" / repo_name / cid / "mutation.json")); repo = repos / repo_name; py = str(repo / ".venv/bin/python")
def sh(c, **k): return subprocess.run(c, cwd=repo, capture_output=True, text=True, **k)
sh(["git", "reset", "-q", "--hard", mut["base"]]); sh(["git", "clean", "-fdq", "-e", ".venv"])
p = repo / mut["file"]; L = p.read_text(encoding="utf-8", newline="").split("\n"); assert L[mut["lineno"]-1] == mut["orig"]; L[mut["lineno"]-1] = mut["mutated"]; p.write_text("\n".join(L), encoding="utf-8", newline="")
sh(["git", "-c", "user.name=bench", "-c", "user.email=bench@fluidfix", "commit", "-qam", "bench: inject"])
env = dict(os.environ, PYTHONPATH=str(HERE.parents[1] / "src"))
t0 = time.time(); g = sh([py, "-c", "from fluidfix.cli import main; raise SystemExit(main())", "guard", ".", "--budget", "300", "--dictionary", dictionary], env=env, timeout=1500)
print("guard exit", g.returncode, "in", round(time.time() - t0, 1), "s")
st = sh(["git", "status", "--porcelain"]).stdout; print("git status after guard (should be empty apart from .fluidfix):"); print(st or "  <clean>")
d = sh(["git", "diff", "--stat"]).stdout; print("git diff --stat:"); print(d or "  <none>")
print("--- guard tail ---"); print((g.stdout + g.stderr)[-1200:])
