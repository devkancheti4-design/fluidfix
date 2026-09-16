#!/usr/bin/env python3
"""Hundreds of files: does the guard find the one that broke, and how fast?

Generates a package of N modules (default 300) with cross-module calls and a shared
core, and a suite of N tests in a handful of test files whose names share no token
with the modules. Seeded: picks K modules, injects one shipped-vocabulary defect in
each, one at a time, and measures (a) the rank the file localiser gives the true
file before any repair, (b) the guard's wall-clock and outcome against pristine bytes.

  PYTHONPATH=<fluidfix>/src python3 scale_localise.py [--n 300] [--k 10] [--seed 20260916]
"""
import argparse, json, os, random, re, shutil, subprocess, sys, tempfile, time
from pathlib import Path

PY = sys.executable
SHAPES = [  # (pristine fragment, defective fragment, shipped kind)
    ("return a * b + c", "return a * b - c", "3 flipped-additive"),
    ("if x >= limit:", "if x > limit:", "0 strictness"),
    ("return max(v, floor)", "return min(v, floor)", "8 minmax-swap"),
    ("return v[1:]", "return v[2:]", "1 literal-off-by-one"),
    ("total += step", "total -= step", "9 flipped-augmented-assign"),
    ("return lo < hi", "return lo > hi", "10 flipped-comparison-direction"),
]


def module_src(i, n):
    a, b = (i + 7) % n, (i + 13) % n
    return f'''from pkg.core import scale, clamp


def area_{i:03d}(a, b, c):
    return a * b + c


def guard_{i:03d}(x, limit):
    if x >= limit:
        return limit
    return x + 1


def floor_{i:03d}(v, floor):
    return max(v, floor)


def tail_{i:03d}(v):
    return v[1:]


def accumulate_{i:03d}(steps):
    total = 0
    for step in steps:
        total += step
    return scale(total)


def ordered_{i:03d}(lo, hi):
    return lo < hi


def blend_{i:03d}(a, b, c, limit):
    from pkg.mod_{a:03d} import area_{a:03d}      # cross-module calls, resolved lazily (the package is a cycle)
    from pkg.mod_{b:03d} import guard_{b:03d}
    return clamp(area_{a:03d}(a, b, c) + guard_{b:03d}(a, limit), limit)
'''


def test_src(batch, ids):
    lines = [f"from pkg.mod_{i:03d} import area_{i:03d}, guard_{i:03d}, floor_{i:03d}, tail_{i:03d}, accumulate_{i:03d}, ordered_{i:03d}, blend_{i:03d}" for i in ids]
    for i in ids:
        lines += [f"""

def test_c{i:04d}():
    assert area_{i:03d}(2, 3, 4) == 10
    assert guard_{i:03d}(5, 5) == 5 and guard_{i:03d}(4, 5) == 5
    assert floor_{i:03d}(2, 3) == 3
    assert tail_{i:03d}([1, 2, 3]) == [2, 3]
    assert accumulate_{i:03d}([1, 2, 3]) == 12
    assert ordered_{i:03d}(1, 2) is True and ordered_{i:03d}(2, 1) is False
    assert isinstance(blend_{i:03d}(1, 2, 3, 100), int)"""]
    return "\n".join(lines) + "\n"


def build(root: Path, n: int):
    (root / "pkg").mkdir(parents=True)
    (root / "pkg" / "__init__.py").write_text("")
    (root / "pkg" / "core.py").write_text("def scale(v):\n    return v * 2\n\n\ndef clamp(v, limit):\n    return v if v <= limit else limit\n")
    for i in range(n): (root / "pkg" / f"mod_{i:03d}.py").write_text(module_src(i, n))
    (root / "tests").mkdir()
    per = 30
    for b in range(0, n, per):
        (root / "tests" / f"test_batch_{b // per:02d}.py").write_text(test_src(b, range(b, min(n, b + per))))
    (root / "pyproject.toml").write_text('[project]\nname = "scalepkg"\nversion = "0.1"\n\n[tool.pytest.ini_options]\npythonpath = ["."]\n')
    (root / ".gitignore").write_text("__pycache__/\n.pytest_cache/\n.fluidfix/\n")


def sh(cmd, cwd, env=None, timeout=1800):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout, env=env)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--n", type=int, default=300); ap.add_argument("--k", type=int, default=10)
    ap.add_argument("--seed", type=int, default=20260916); ap.add_argument("--out", default="scale_results.json")
    a = ap.parse_args()
    env = dict(os.environ); env.setdefault("PYTHONPATH", str(Path(__file__).resolve().parents[2] / "src"))
    root = Path(tempfile.mkdtemp(prefix="scale-")) / "repo"; build(root, a.n)
    sh(["git", "init", "-q", "-b", "main"], root); sh(["git", "-c", "user.name=t", "-c", "user.email=t@t", "add", "-A"], root)
    sh(["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "green"], root)
    base = sh(["git", "rev-parse", "HEAD"], root).stdout.strip()
    t0 = time.time(); g = sh([PY, "-m", "pytest", "-q", "-p", "no:cacheprovider"], root); suite_s = time.time() - t0
    assert g.returncode == 0, g.stdout[-500:]
    n_files = len(list((root / "pkg").glob("*.py"))); n_tests = int(re.search(r"(\d+) passed", g.stdout).group(1))
    print(f"repo: {n_files} source files, {n_tests} tests, suite {suite_s:.1f}s", flush=True)
    rng = random.Random(a.seed); picks = rng.sample(range(a.n), a.k)
    HELPER = str(Path(__file__).resolve().parent / "rank_helper.py")
    results = []
    for j, i in enumerate(picks):
        pristine, defect, kind = SHAPES[j % len(SHAPES)]
        rel = f"pkg/mod_{i:03d}.py"; p = root / rel; src = p.read_text()
        assert src.count(pristine) == 1
        # every case starts from the pristine commit: a refusal must not leave its defect for the next case
        sh(["git", "reset", "-q", "--hard", base], root); sh(["git", "clean", "-qfdx"], root); src = p.read_text()
        assert src.count(pristine) == 1
        p.write_text(src.replace(pristine, defect))
        sh(["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qam", f"break {rel}"], root)
        # (a) the ranking, in a fresh process, exactly as the guard computes it
        t1 = time.time(); rk = json.loads(sh([PY, HELPER, str(root)], root, env=env).stdout.strip().splitlines()[-1]); loc_s = time.time() - t1
        assert rk["red"], f"{rel} {kind}: defect invisible to the suite"
        ranked = rk["ranked"]; rank = ranked.index(rel) + 1 if rel in ranked else None
        # (b) the guard, as the CLI, in a fresh process
        t2 = time.time(); gd = sh([PY, "-c", "from fluidfix.cli import main; raise SystemExit(main())", "guard", ".", "--commit"], root, env=env); wall = time.time() - t2
        exact = p.read_text() == src
        m = re.search(r"repaired line (\d+) in (\d+) suite runs", gd.stdout)
        status = "repaired" if gd.returncode == 0 and m else ("refused" if gd.returncode == 2 else f"exit{gd.returncode}")
        results.append(dict(file=rel, kind=kind, rank_of_true_file=rank, ranked=ranked[:5], localise_s=round(loc_s, 1), status=status,
                            byte_exact=exact, suite_runs=int(m.group(2)) if m else None, wall_s=round(wall, 1)))
        print(f"{rel} {kind:32} rank={rank} of {len(ranked)}  loc={loc_s:4.1f}s  {status:9} exact={exact} runs={m.group(2) if m else '-'} {wall:5.1f}s", flush=True)
    Path(a.out).write_text(json.dumps({"n_files": n_files, "n_tests": n_tests, "suite_s": round(suite_s, 1), "seed": a.seed, "results": results}, indent=1))
    ok = sum(r["byte_exact"] and r["status"] == "repaired" for r in results); top1 = sum(r["rank_of_true_file"] == 1 for r in results)
    print(f"TALLY byte-exact {ok}/{len(results)}  rank-1 {top1}/{len(results)}  median wall {sorted(r['wall_s'] for r in results)[len(results)//2]}s")


if __name__ == "__main__":
    main()
