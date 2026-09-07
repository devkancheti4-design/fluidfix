#!/usr/bin/env python
"""What FAILONLY would say at FUNCTION granularity on the `named` fixture.

The body measures specificity per FILE (lines the failing test executes in
f / lines the whole suite executes in f). This script re-measures it per
top-level function from the same two coverage runs the body makes, and
prints which functions the failing test executes ALONE. Report-only:
runs pytest on a fresh copy under work/, edits nothing in src/.

    nice -n 15 ./tmo.sh 300 .venv/bin/python func_spectrum.py
"""
import ast
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable


def cov(root, extra, tag):
    out = os.path.join(root, f"_cov_{tag}.json")
    subprocess.run([PY, "-m", "pytest", "-q", "--tb=no"] + extra +
                   ["--cov=.", f"--cov-report=json:{out}"],
                   cwd=root, capture_output=True, text=True, timeout=240)
    data = json.load(open(out))
    return {f.replace("\\", "/"): set(d["executed_lines"])
            for f, d in data["files"].items() if f.startswith("pkg/")}


def main():
    src = os.path.join(HERE, "fixtures", "named")
    root = os.path.join(HERE, "work", "named-funcspec")
    if os.path.isdir(root):
        shutil.rmtree(root)
    shutil.copytree(src, root)
    # populate lastfailed exactly as the body does (a -x run), then the two
    # coverage runs the body makes: --lf and the full suite
    subprocess.run([PY, "-m", "pytest", "-x", "-q", "--tb=no"], cwd=root,
                   capture_output=True, text=True, timeout=240)
    lf = cov(root, ["--lf"], "lf")
    full = cov(root, [], "full")

    print("file-level (what the body measures)   n_fail  n_full  specificity")
    for rel in sorted(full):
        nf, nfull = len(lf.get(rel, ())), len(full[rel])
        if nf:
            print(f"  {rel:<22} {nf:>6} {nfull:>7}   {nf / max(nfull, nf):.2f}")

    print("\nfunction-level (unmeasured by the body today)")
    print("  function                         n_fail  n_full  spec   verdict")
    for rel in sorted(full):
        tree = ast.parse(open(os.path.join(root, rel), encoding="utf-8").read())
        for node in tree.body:
            if not isinstance(node, ast.FunctionDef):
                continue
            body_lines = set(range(node.body[0].lineno, node.end_lineno + 1))
            nf = len(lf.get(rel, set()) & body_lines)
            nfull = len(full[rel] & body_lines)
            if nf == 0:
                continue
            spec = nf / max(nfull, nf)
            verdict = "FAILONLY (>=0.9)" if spec >= 0.9 else ""
            print(f"  {rel + ':' + node.name:<32} {nf:>6} {nfull:>7}   "
                  f"{spec:.2f}   {verdict}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
