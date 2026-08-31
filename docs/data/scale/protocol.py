"""STRICT large-repo benchmark for fluidfix guard. Pre-registered protocol:

- Repos: click (28,581 LOC / 1,990 tests), arrow (19,928 / 1,902),
  sortedcontainers (11,324 / 366). All suites green at baseline.
- Seed 20260831. Mutation sites are found by regex over LIBRARY files only
  (tests/docs/examples excluded), shuffled once with the seed, and taken in
  order — no human choice of sites.
- Classes: cmp-strictness swap, additive +/- flip, numeric literal +1
  (all in the shipped vocabulary), plus one and/or flip per repo
  (OUT of vocabulary — must be REFUSED with the tree unchanged).
- A site whose mutation the suite does not catch (dead mutant) is recorded
  and skipped — standard live-mutant filtering. Target: 2 live per class
  per repo, scan budget 25 attempts per class.
- Per live mutant: commit the break, run
  `fluidfix guard . --commit --python <venv>` and wall-clock it, then score:
  repaired? correct file? byte-exact vs pristine? committed? Reset hard.
- Everything is reported: attempts, dead mutants, failures, refusals.
  Trials run SERIALLY so timings are honest.
"""
import json
import os
import random
import re
import subprocess
import sys
import time

C = os.path.dirname(os.path.abspath(__file__))
FLUIDFIX = "/Users/kanchetidevieswar/neo/fluidfix/.venv/bin/fluidfix"
SEED = 20260831

REPOS = {
    "click": {"lib": "src/click"},
    "arrow": {"lib": "arrow"},
    "sortedcontainers": {"lib": "src/sortedcontainers"},
}

CLASSES = {
    "cmp": (re.compile(r"(?<=[\w\)\]\s])(>=|<=|>|<)(?=[\s\w\(])"),
            {">=": ">", ">": ">=", "<=": "<", "<": "<="}),
    "add": (re.compile(r"(?<=\S) (\+|-) (?=\S)"), {"+": "-", "-": "+"}),
    "lit": (re.compile(r"(?<![\w.])(\d+)(?![\w.])"), None),   # n -> n+1
    "oov": (re.compile(r"\b(and|or)\b"), {"and": "or", "or": "and"}),
}


def sh(cmd, cwd, timeout=600):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                          timeout=timeout)


def suite_fails(py, repo, timeout=240):
    for dp, dn, _ in os.walk(repo):
        dn[:] = [d for d in dn if d != "__pycache__"]
    r = sh([py, "-m", "pytest", "-q", "--tb=no", "-p", "no:cacheprovider",
            "-p", "no:benchmark"], repo, timeout)
    return r.returncode != 0


def find_sites(repo, libdir, cls):
    pat, _ = CLASSES[cls]
    sites = []
    base = os.path.join(repo, libdir)
    for dp, dn, fns in os.walk(base):
        dn[:] = [d for d in dn if d != "__pycache__"]
        for fn in fns:
            if not fn.endswith(".py"):
                continue
            path = os.path.join(dp, fn)
            for i, line in enumerate(open(path, encoding="utf-8").read().split("\n")):
                if line.lstrip().startswith("#"):
                    continue
                for m in pat.finditer(line):
                    sites.append((os.path.relpath(path, repo), i, m.start(1), m.group(1)))
    rng = random.Random(SEED)
    rng.shuffle(sites)
    return sites


def mutate(repo, site, cls):
    rel, i, col, tok = site
    path = os.path.join(repo, rel)
    src = open(path, encoding="utf-8", newline="").read()
    lines = src.split("\n")
    line = lines[i]
    _, table = CLASSES[cls]
    new_tok = str(int(tok) + 1) if cls == "lit" else table[tok]
    new_line = line[:col] + new_tok + line[col + len(tok):]
    if new_line == line:
        return None
    lines[i] = new_line
    open(path, "w", encoding="utf-8", newline="").write("\n".join(lines))
    return {"file": rel, "lineno": i + 1, "orig": line, "mutated": new_line}


def main():
    only = set(sys.argv[1:])
    results = []
    for name, cfg in REPOS.items():
        if only and name not in only:
            continue
        d = os.path.join(C, name)
        repo, py = os.path.join(d, "repo"), os.path.join(d, "venv", "bin", "python")
        sh(["git", "config", "user.email", "bench@fluidfix"], repo)
        sh(["git", "config", "user.name", "bench"], repo)
        sh(["git", "reset", "-q", "--hard"], repo)
        sh(["git", "clean", "-fdq"], repo)
        base = sh(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        assert not suite_fails(py, repo), f"{name}: baseline suite not green"
        print(f"### {name}: baseline green at {base[:7]}", flush=True)

        for cls in ("cmp", "add", "lit", "oov"):
            want = 1 if cls == "oov" else 2
            got = attempts = 0
            for site in find_sites(repo, cfg["lib"], cls):
                if got >= want or attempts >= 25:
                    break
                attempts += 1
                mut = mutate(repo, site, cls)
                if mut is None:
                    continue
                # DETERMINISTIC liveness: fail -> restore green -> fail again.
                # Guards the benchmark against flaky/timing tests and
                # near-equivalent mutants scoring as live.
                first = suite_fails(py, repo)
                sh(["git", "checkout", "-q", "--", mut["file"]], repo)
                if not first:
                    print(f"  [{name}/{cls}] dead: {mut['file']}:{mut['lineno']}", flush=True)
                    continue
                if suite_fails(py, repo):
                    print(f"  [{name}/{cls}] FLAKY baseline red after restore — site skipped, "
                          f"{mut['file']}:{mut['lineno']}", flush=True)
                    sh(["git", "reset", "-q", "--hard", base], repo)
                    continue
                mutate(repo, site, cls)
                if not suite_fails(py, repo):
                    sh(["git", "checkout", "-q", "--", mut["file"]], repo)
                    print(f"  [{name}/{cls}] FLAKY liveness (failed once, not twice) — skipped, "
                          f"{mut['file']}:{mut['lineno']}", flush=True)
                    continue
                got += 1
                sh(["git", "commit", "-aqm", f"bench: inject {cls}"], repo)
                t0 = time.time()
                g = sh([FLUIDFIX, "guard", ".", "--commit", "--python", py],
                       repo, timeout=900)
                dt = round(time.time() - t0, 1)
                out = g.stdout + g.stderr
                cur = open(os.path.join(repo, mut["file"]), encoding="utf-8",
                           newline="").read().split("\n")[mut["lineno"] - 1]
                trial = {
                    "repo": name, "cls": cls, "file": mut["file"],
                    "lineno": mut["lineno"], "guard_exit": g.returncode,
                    "seconds": dt,
                    "repaired": "repaired" in out,
                    "right_file": f"{os.path.basename(mut['file'])}:" in out,
                    "byte_exact": cur == mut["orig"],
                    "refused": "REFUSED" in out,
                    "committed": "committed" in out,
                }
                results.append(trial)
                v = ("EXACT" if trial["repaired"] and trial["byte_exact"] else
                     "REFUSED" if trial["refused"] else
                     "GREEN-ONLY" if trial["repaired"] else "NO-ACTION")
                print(f"  [{name}/{cls}] {mut['file']}:{mut['lineno']} -> {v} in {dt}s "
                      f"(attempts so far {attempts})", flush=True)
                sh(["git", "reset", "-q", "--hard", base], repo)
                sh(["git", "clean", "-fdq"], repo)
            results.append({"repo": name, "cls": cls, "meta": "scan",
                            "live": got, "attempts": attempts})
    json.dump(results, open(os.path.join(C, "big_bench_results.json"), "w"), indent=1)
    trials = [r for r in results if "meta" not in r]
    iv = [r for r in trials if r["cls"] != "oov"]
    ov = [r for r in trials if r["cls"] == "oov"]
    print("\n==== SUMMARY ====")
    print(f"in-vocab live trials : {len(iv)}")
    print(f"  repaired byte-exact: {sum(1 for r in iv if r['repaired'] and r['byte_exact'])}")
    print(f"  green-only         : {sum(1 for r in iv if r['repaired'] and not r['byte_exact'])}")
    print(f"  refused/no-action  : {sum(1 for r in iv if not r['repaired'])}")
    if iv:
        ts = sorted(r["seconds"] for r in iv)
        print(f"  seconds min/median/max: {ts[0]} / {ts[len(ts)//2]} / {ts[-1]}")
    print(f"OOV trials           : {len(ov)}, refused: {sum(1 for r in ov if r['refused'])}, "
          f"wrongly repaired: {sum(1 for r in ov if r['repaired'])}")
    print("BENCH_DONE")


if __name__ == "__main__":
    main()
