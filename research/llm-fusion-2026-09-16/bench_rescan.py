#!/usr/bin/env python3
"""Harness fix, run after the seeded bench: the seeded site finder matched operators INSIDE string literals
(click lit-1: a format spec; rich cmp-1/cmp-2: regex named group / lookbehind). This rescans ONE class of ONE
repo with the same seed and the same rules, skipping every match that tokenize reports inside a STRING token.
Everything else (liveness x2, guard --budget 300, verdicts, saved refusals) is bench_real.py's own code.

  PYTHONPATH=<fluidfix>/src python3 bench_rescan.py <repos-dir> rich cmp [exclude-dir,...]
"""
import io, json, random, re, shutil, sys, time, tokenize
from pathlib import Path
import bench_real as B

HERE = Path(__file__).resolve().parent


def string_spans(path: Path):
    spans = {}
    try:
        for tok in tokenize.generate_tokens(io.StringIO(path.read_text(encoding="utf-8")).readline):
            if tok.type == tokenize.STRING:
                (r0, c0), (r1, c1) = tok.start, tok.end
                for r in range(r0, r1 + 1):
                    spans.setdefault(r, []).append((c0 if r == r0 else 0, c1 if r == r1 else 10**9))
    except (tokenize.TokenError, SyntaxError):
        pass
    return spans


EXCLUDE: list = []   # directory names to skip (e.g. _unicode_data: rich's literal class drew 25/25 dead sites from its tables)


def find_sites(repo: Path, lib: str, cls: str):
    pat, _ = B.CLASSES[cls]; sites = []
    for path in sorted((repo / lib).rglob("*.py")):
        if "__pycache__" in path.parts or any(x in path.parts for x in EXCLUDE): continue
        spans = string_spans(path)
        for i, line in enumerate(path.read_text(encoding="utf-8").split("\n")):
            s = line.lstrip()
            if s.startswith("#") or s.startswith('"""') or s.startswith("'''"): continue
            for m in pat.finditer(line):
                if any(a <= m.start(1) < b for a, b in spans.get(i + 1, [])): continue   # inside a string literal
                sites.append((str(path.relative_to(repo)), i, m.start(1), m.group(1)))
    random.Random(B.SEED).shuffle(sites); return sites


def main():
    repos_dir = Path(sys.argv[1]).resolve(); name, cls = sys.argv[2], sys.argv[3]
    EXCLUDE[:] = sys.argv[4].split(",") if len(sys.argv) > 4 else []
    import os; env = dict(os.environ); env.setdefault("PYTHONPATH", str(HERE.parents[1] / "src"))
    repo = repos_dir / name; py = str(repo / ".venv" / "bin" / "python"); out = HERE / "cases"
    B.sh(["git", "config", "user.email", "bench@fluidfix"], repo); B.sh(["git", "config", "user.name", "bench"], repo)
    log = B.sh(["git", "log", "--format=%H %s", "-n", "20"], repo).stdout.splitlines()
    base = next(l.split()[0] for l in log if not l.split(" ", 1)[1].startswith("bench: inject"))
    B.sh(["git", "reset", "-q", "--hard", base], repo); B.sh(["git", "clean", "-fdq", "-e", ".venv"], repo)
    assert not B.suite_fails(py, repo), f"{name}: baseline suite not green"
    print(f"### rescan {name}/{cls}: baseline green at {base[:7]} (string-literal sites excluded; dirs excluded: {EXCLUDE})", flush=True)
    results = []; got = attempts = 0
    for site in find_sites(repo, B.LIB[name], cls):
        if got >= B.WANT[cls] or attempts >= 25: break
        attempts += 1; mut = B.mutate(repo, site, cls)
        if mut is None: continue
        print(f"  [{name}/{cls}s] try {attempts}: {mut['file']}:{mut['lineno']} {mut['orig'].strip()[:60]!r}", flush=True)
        first = B.suite_fails(py, repo); B.sh(["git", "checkout", "-q", "--", mut["file"]], repo)
        if first == "hung": print(f"  [{name}/{cls}s] HUNG — skipped", flush=True); results.append({"repo": name, "cls": cls, "meta": "hung", "file": mut["file"], "lineno": mut["lineno"]}); continue
        if not first: print(f"  [{name}/{cls}s] dead: {mut['file']}:{mut['lineno']}", flush=True); continue
        if B.suite_fails(py, repo): print("  FLAKY baseline — skipped", flush=True); B.sh(["git", "reset", "-q", "--hard", base], repo); continue
        B.mutate(repo, site, cls)
        if B.suite_fails(py, repo) is not True: B.sh(["git", "checkout", "-q", "--", mut["file"]], repo); print("  FLAKY liveness — skipped", flush=True); continue
        got += 1; cid = f"{cls}-s{got}"
        B.sh(["git", "commit", "-aqm", f"bench: inject {cls} at {mut['file']}:{mut['lineno']}"], repo)
        shutil.rmtree(repo / ".fluidfix", ignore_errors=True); t0 = time.time()
        g = B.sh([py, "-c", "from fluidfix.cli import main; raise SystemExit(main())", "guard", ".", "--commit", "--budget", "300"], repo, 1500, env)
        dt = round(time.time() - t0, 1); o = g.stdout + g.stderr
        cur = (repo / mut["file"]).read_text(encoding="utf-8", newline="").split("\n")[mut["lineno"] - 1]
        m = re.search(r"repaired line \d+ in (\d+) suite runs", o)
        trial = {"repo": name, "cls": cls, "id": cid, "in_vocab": cls in B.IN_VOCAB, "file": mut["file"], "lineno": mut["lineno"], "orig": mut["orig"].strip(), "mutated": mut["mutated"].strip(),
                 "guard_exit": g.returncode, "seconds": dt, "repaired": "repaired" in o, "byte_exact": cur == mut["orig"], "refused": "REFUSED" in o,
                 "suite_runs": int(m.group(1)) if m else None, "hint": (re.search(r"hint: (.*)", o) or [None, ""])[1][:160], "rescan": True}
        v = ("EXACT" if trial["repaired"] and trial["byte_exact"] else "WRONG-GREEN" if trial["repaired"] else "REFUSED" if trial["refused"] else "NO-ACTION")
        trial["verdict"] = v; results.append(trial)
        print(f"  [{name}/{cid}] {mut['file']}:{mut['lineno']} {mut['orig'].strip()[:50]!r} -> {v} in {dt}s runs={trial['suite_runs']}", flush=True)
        d = out / name / cid; d.mkdir(parents=True, exist_ok=True)
        (d / "mutation.json").write_text(json.dumps({**mut, "cls": cls, "base": base}, indent=1))
        ref = repo / ".fluidfix" / "last_refusal.json"
        if v == "REFUSED" and ref.exists(): shutil.copy(ref, d / "refusal_tier0.json")
        B.sh(["git", "reset", "-q", "--hard", base], repo); B.sh(["git", "clean", "-fdq", "-e", ".venv"], repo)
    results.append({"repo": name, "cls": cls, "meta": "scan", "live": got, "attempts": attempts, "rescan": True})
    (HERE / f"bench_rescan_{name}_{cls}.json").write_text(json.dumps(results, indent=1)); print("RESCAN_DONE", flush=True)


if __name__ == "__main__":
    main()
