#!/usr/bin/env python3
"""How many guards can one machine actually run at once?

The claim under test: fluidfix is small, so you can run as many as you like. The tool is small — 5,580 lines,
zero runtime dependencies — but each guard pays for the target's test suite once per candidate, so the ceiling
is set by the suite and the cores, not by fluidfix. This measures the curve.

A tiny synthetic package (fast suite, no dependencies) is cloned N times; each clone gets the SAME injected
fault and its own guard; all N run at once. Reported per N: wall clock of the slowest guard, median guard,
and the slowdown against a single guard running alone.

  PYTHONPATH=<fluidfix>/src python3 scale_many.py <workdir> [--ns 1,2,4,8,12,16,24,32] [--modules 40]
"""
import argparse, json, os, shutil, statistics, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE.parents[1] / "src"
PRISTINE = "    return a * b + c"
BROKEN = "    return a * b - c"


def build(root: Path, modules: int):
    if (root / "pkg").exists():
        return
    (root / "pkg").mkdir(parents=True)
    (root / "pkg" / "__init__.py").write_text("")
    for i in range(modules):
        (root / "pkg" / f"mod_{i:03d}.py").write_text(
            f"def area_{i:03d}(a, b, c):\n{PRISTINE}\n\n\ndef guard_{i:03d}(x, limit):\n"
            f"    if x >= limit:\n        return limit\n    return x + 1\n")
    (root / "tests").mkdir()
    for i in range(modules):
        (root / "tests" / f"test_{i:03d}.py").write_text(
            f"from pkg.mod_{i:03d} import area_{i:03d}, guard_{i:03d}\n\n\n"
            f"def test_{i:03d}():\n    assert area_{i:03d}(2, 3, 4) == 10\n"
            f"    assert guard_{i:03d}(5, 5) == 5 and guard_{i:03d}(4, 5) == 5\n")
    (root / "pyproject.toml").write_text(
        '[project]\nname = "lakepkg"\nversion = "0.1"\n\n[tool.pytest.ini_options]\npythonpath = ["."]\n')
    (root / ".gitignore").write_text("__pycache__/\n.pytest_cache/\n.fluidfix/\n")
    sh(["git", "init", "-q", "-b", "main"], root)
    sh(["git", "add", "-A"], root)
    sh(["git", "-c", "user.name=lake", "-c", "user.email=lake@fluidfix", "commit", "-qm", "green"], root)


def sh(cmd, cwd=None, env=None, timeout=1800):
    return subprocess.run(cmd, cwd=cwd, env=env, timeout=timeout, capture_output=True, text=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("workdir"); ap.add_argument("--ns", default="1,2,4,8,12,16,24,32")
    ap.add_argument("--modules", type=int, default=40)
    ap.add_argument("--python", default="/Library/Frameworks/Python.framework/Versions/3.14/bin/python3")
    a = ap.parse_args()
    work = Path(a.workdir).resolve(); work.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ); env["PYTHONPATH"] = str(SRC)
    template = work / "template"
    build(template, a.modules)

    t = time.time(); g = sh([a.python, "-m", "pytest", "-q", "-p", "no:cacheprovider"], template, env)
    suite_s = round(time.time() - t, 2)
    assert g.returncode == 0, g.stdout[-400:]
    cores = os.cpu_count()
    print(f"synthetic repo: {a.modules} modules, {a.modules} tests, green suite {suite_s}s, {cores} cores", flush=True)

    rows = []
    for N in [int(x) for x in a.ns.split(",")]:
        clones = []
        for i in range(N):
            c = work / f"run{N:02d}_{i:02d}"
            shutil.rmtree(c, ignore_errors=True)
            shutil.copytree(template, c)
            p = c / "pkg" / "mod_000.py"
            p.write_text(p.read_text().replace(PRISTINE, BROKEN, 1))
            sh(["git", "-c", "user.name=lake", "-c", "user.email=lake@fluidfix", "commit", "-qam", "break"], c)
            clones.append(c)
        t0 = time.time(); procs = []
        for c in clones:
            procs.append((c, time.time(), subprocess.Popen(
                [a.python, "-c", "from fluidfix.cli import main; raise SystemExit(main())", "guard", ".", "--budget", "600"],
                cwd=c, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)))
        secs, exact = [], 0
        for c, ts, pr in procs:
            out, _ = pr.communicate(timeout=3600)
            secs.append(round(time.time() - ts, 1))
            if pr.returncode == 0 and PRISTINE in (c / "pkg" / "mod_000.py").read_text():
                exact += 1
        wall = round(time.time() - t0, 1)
        rows.append({"guards": N, "wall_s": wall, "slowest_guard_s": max(secs), "median_guard_s": statistics.median(secs),
                     "cpu_sum_s": round(sum(secs), 1), "byte_exact": exact})
        base = rows[0]["median_guard_s"]
        print(f"  {N:3d} guards  wall {wall:7.1f}s  median guard {statistics.median(secs):6.1f}s  "
              f"slowdown x{statistics.median(secs)/base:4.1f}  byte-exact {exact}/{N}", flush=True)
        for c in clones:
            shutil.rmtree(c, ignore_errors=True)
    out = {"modules": a.modules, "tests": a.modules, "suite_s": suite_s, "cores": cores, "rows": rows}
    (HERE / "scale_many.json").write_text(json.dumps(out, indent=1))
    print("SCALE_MANY_DONE", flush=True)


if __name__ == "__main__":
    main()
