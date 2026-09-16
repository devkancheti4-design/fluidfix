#!/usr/bin/env python3
"""Pre-registered real-repo protocol for the escalation ladder (2026-09-16).

- Repos: click, arrow, sortedcontainers (the earlier scale benchmark's three; click was
  tuned on, the other two are held-out) and rich (146 source files). Shallow clones,
  each with its own venv, suite green at baseline.
- Seed 20260916. Mutation sites are found by regex over LIBRARY files only, shuffled
  once with the seed, taken in order; no human choice. Dead mutants (suite does not
  catch) are recorded and skipped; liveness is checked twice (red, restore green, red).
- Classes. IN-VOCAB (tier 0 should repair): cmp-strictness swap, additive +/- flip,
  numeric literal +1.  OUT-OF-VOCAB (tier 0 must refuse; the ladder then runs):
  and/or flip, `.get(k, d)` -> `.get(k)`, `if not X` -> `if X`, `range(1, n)` ->
  `range(n)`, `len(x) - 1` -> `len(x)`.
- Per live mutant: commit the break, run tier 0 (`fluidfix guard . --commit --budget 300`),
  score byte-exact vs pristine. Refused OOV cases are saved as ladder cases
  (cases/<repo>/<id>/mutation.json) for ladder.py to run against each author.
- Everything is reported: attempts, dead and flaky mutants, refusals, wrong repairs.

  PYTHONPATH=<fluidfix>/src python3 bench_real.py <repos-dir> click arrow python-sortedcontainers rich
"""
import json, os, random, re, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SEED = 20260916
LIB = {"click": "src/click", "arrow": "arrow", "python-sortedcontainers": "src/sortedcontainers", "rich": "rich"}
CLASSES = {
    # in vocabulary
    "cmp": (re.compile(r"(?<=[\w\)\]\s])(>=|<=|>|<)(?=[\s\w\(])"), {">=": ">", ">": ">=", "<=": "<", "<": "<="}),
    "add": (re.compile(r"(?<=\S) (\+|-) (?=\S)"), {"+": "-", "-": "+"}),
    "lit": (re.compile(r"(?<![\w.])(\d+)(?![\w.])"), None),
    # out of vocabulary
    "andor": (re.compile(r"\b(and|or)\b"), {"and": "or", "or": "and"}),
    "getdef": (re.compile(r"(\.get\([^(),]+, [^()]+\))"), "getdef"),
    "notdrop": (re.compile(r"\b(if not |return not |while not )"), "notdrop"),
    "rangestart": (re.compile(r"\b(range\(1, )"), "rangestart"),
    "lenm1": (re.compile(r"(len\([^()]+\) - 1)"), "lenm1"),
}
IN_VOCAB = ("cmp", "add", "lit"); OOV = ("andor", "getdef", "notdrop", "rangestart", "lenm1")
WANT = {"cmp": 2, "add": 2, "lit": 2, "andor": 1, "getdef": 1, "notdrop": 1, "rangestart": 1, "lenm1": 1}


class _Hung:
    returncode = 124; stdout = "HUNG"; stderr = ""


def sh(cmd, cwd, timeout=900, env=None):
    try:
        return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout, env=env)
    except subprocess.TimeoutExpired:
        return _Hung()


def suite_fails(py, repo):
    """True if red; 'hung' if the suite did not finish (a mutant that loops forever)."""
    r = sh([py, "-m", "pytest", "-q", "--tb=no", "-x", "--timeout=60", "-p", "no:cacheprovider"], repo, 300)
    if r.returncode == 124 or re.search(r"Timeout \(?>\d", r.stdout or ""): return "hung"   # pytest-timeout: 'Failed: Timeout (>60.0s)'
    return r.returncode != 0


def find_sites(repo: Path, lib: str, cls: str):
    pat, _ = CLASSES[cls]; sites = []
    for path in sorted((repo / lib).rglob("*.py")):
        if "__pycache__" in path.parts: continue
        for i, line in enumerate(path.read_text(encoding="utf-8").split("\n")):
            s = line.lstrip()
            if s.startswith("#") or s.startswith('"""') or s.startswith("'''"): continue
            for m in pat.finditer(line):
                sites.append((str(path.relative_to(repo)), i, m.start(1), m.group(1)))
    random.Random(SEED).shuffle(sites); return sites


def mutated_line(line: str, col: int, tok: str, cls: str):
    table = CLASSES[cls][1]
    if cls == "lit": new = str(int(tok) + 1)
    elif table == "getdef": new = re.sub(r"\.get\(([^(),]+), [^()]+\)", r".get(\1)", tok)
    elif table == "notdrop": new = tok.replace("not ", "")
    elif table == "rangestart": new = "range("
    elif table == "lenm1": new = tok[: -len(" - 1")]
    else: new = table[tok]
    out = line[:col] + new + line[col + len(tok):]
    return None if out == line else out


def mutate(repo: Path, site, cls):
    rel, i, col, tok = site; path = repo / rel
    src = path.read_text(encoding="utf-8", newline=""); lines = src.split("\n")
    new = mutated_line(lines[i], col, tok, cls)
    if new is None: return None
    orig = lines[i]; lines[i] = new
    path.write_text("\n".join(lines), encoding="utf-8", newline="")
    return {"file": rel, "lineno": i + 1, "orig": orig, "mutated": new}


def main():
    repos_dir = Path(sys.argv[1]).resolve(); names = sys.argv[2:] or list(LIB)
    env = dict(os.environ); env.setdefault("PYTHONPATH", str(HERE.parents[1] / "src"))
    out = HERE / "cases"; out.mkdir(exist_ok=True)
    results = []
    for name in names:
        repo = repos_dir / name; py = str(repo / ".venv" / "bin" / "python")
        sh(["git", "config", "user.email", "bench@fluidfix"], repo); sh(["git", "config", "user.name", "bench"], repo)
        # a killed run can leave HEAD on a "bench: inject" commit; walk back to the last real commit
        log = sh(["git", "log", "--format=%H %s", "-n", "20"], repo).stdout.splitlines()
        base = next(l.split()[0] for l in log if not l.split(" ", 1)[1].startswith("bench: inject"))
        sh(["git", "reset", "-q", "--hard", base], repo); sh(["git", "clean", "-fdq", "-e", ".venv"], repo)
        assert not suite_fails(py, repo), f"{name}: baseline suite not green"
        print(f"### {name}: baseline green at {base[:7]}", flush=True)
        for cls in IN_VOCAB + OOV:
            got = attempts = 0
            for site in find_sites(repo, LIB[name], cls):
                if got >= WANT[cls] or attempts >= 25: break
                attempts += 1
                mut = mutate(repo, site, cls)
                if mut is None: continue
                print(f"  [{name}/{cls}] try {attempts}: {mut['file']}:{mut['lineno']} {mut['orig'].strip()[:60]!r}", flush=True)
                first = suite_fails(py, repo); sh(["git", "checkout", "-q", "--", mut["file"]], repo)
                if first == "hung": print(f"  [{name}/{cls}] HUNG (mutant loops forever) — skipped: {mut['file']}:{mut['lineno']}", flush=True); results.append({"repo": name, "cls": cls, "meta": "hung", "file": mut["file"], "lineno": mut["lineno"]}); continue
                if not first: print(f"  [{name}/{cls}] dead: {mut['file']}:{mut['lineno']}", flush=True); continue
                if suite_fails(py, repo):
                    print(f"  [{name}/{cls}] FLAKY baseline — skipped", flush=True); sh(["git", "reset", "-q", "--hard", base], repo); continue
                mutate(repo, site, cls)
                if suite_fails(py, repo) is not True:
                    sh(["git", "checkout", "-q", "--", mut["file"]], repo); print(f"  [{name}/{cls}] FLAKY liveness — skipped", flush=True); continue
                got += 1; cid = f"{cls}-{got}"
                sh(["git", "commit", "-aqm", f"bench: inject {cls} at {mut['file']}:{mut['lineno']}"], repo)
                import shutil; shutil.rmtree(repo / ".fluidfix", ignore_errors=True)
                t0 = time.time()
                g = sh([py, "-c", "from fluidfix.cli import main; raise SystemExit(main())", "guard", ".", "--commit", "--budget", "300"], repo, 1500, env)
                dt = round(time.time() - t0, 1); o = g.stdout + g.stderr
                cur = (repo / mut["file"]).read_text(encoding="utf-8", newline="").split("\n")[mut["lineno"] - 1]
                m = re.search(r"repaired line \d+ in (\d+) suite runs", o)
                trial = {"repo": name, "cls": cls, "id": cid, "in_vocab": cls in IN_VOCAB, "file": mut["file"], "lineno": mut["lineno"],
                         "orig": mut["orig"].strip(), "mutated": mut["mutated"].strip(), "guard_exit": g.returncode, "seconds": dt,
                         "repaired": "repaired" in o, "byte_exact": cur == mut["orig"], "refused": "REFUSED" in o,
                         "suite_runs": int(m.group(1)) if m else None, "hint": (re.search(r"hint: (.*)", o) or [None, ""])[1][:160]}
                v = ("EXACT" if trial["repaired"] and trial["byte_exact"] else "WRONG-GREEN" if trial["repaired"] else "REFUSED" if trial["refused"] else "NO-ACTION")
                trial["verdict"] = v; results.append(trial)
                print(f"  [{name}/{cid}] {mut['file']}:{mut['lineno']} {mut['orig'].strip()[:50]!r} -> {v} in {dt}s runs={trial['suite_runs']}", flush=True)
                if v == "REFUSED":
                    d = out / name / cid; d.mkdir(parents=True, exist_ok=True)
                    (d / "mutation.json").write_text(json.dumps({**mut, "cls": cls, "base": base}, indent=1))
                    ref = repo / ".fluidfix" / "last_refusal.json"
                    if ref.exists(): shutil.copy(ref, d / "refusal_tier0.json")
                sh(["git", "reset", "-q", "--hard", base], repo); sh(["git", "clean", "-fdq", "-e", ".venv"], repo)
            results.append({"repo": name, "cls": cls, "meta": "scan", "live": got, "attempts": attempts})
        (HERE / "bench_real_results.json").write_text(json.dumps(results, indent=1))
    trials = [r for r in results if "meta" not in r]
    iv = [r for r in trials if r["in_vocab"]]; ov = [r for r in trials if not r["in_vocab"]]
    print("\n==== TIER 0 SUMMARY ====")
    print(f"in-vocab live: {len(iv)}  byte-exact: {sum(r['verdict']=='EXACT' for r in iv)}  wrong-green: {sum(r['verdict']=='WRONG-GREEN' for r in iv)}  refused: {sum(r['verdict']=='REFUSED' for r in iv)}")
    print(f"OOV live: {len(ov)}  refused (correct): {sum(r['verdict']=='REFUSED' for r in ov)}  wrong-green: {sum(r['verdict']=='WRONG-GREEN' for r in ov)}  exact: {sum(r['verdict']=='EXACT' for r in ov)}")
    print("BENCH_DONE")


if __name__ == "__main__":
    main()
