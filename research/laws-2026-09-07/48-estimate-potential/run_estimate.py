#!/usr/bin/env python3
"""Run `fluidfix estimate` over a set of roots, ONE AT A TIME, and classify
each outcome as NUMBER or REFUSAL, naming the observation that was missing.

Every child is launched through ./tmo (nice -n 15 + a perl alarm), because
this machine has no coreutils `timeout`.

usage:
  python run_estimate.py <outfile.md> <root> [<root> ...]
  optional per-root suffix "::--suite-timeout=5" to pass extra flags.
"""
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
TMO = os.path.join(HERE, "tmo")
FF = "/Users/kanchetidevieswar/neo/fluidfix/.venv/bin/fluidfix"
PY = "/Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python"

# (marker in stdout, verdict, the observation that is missing)
RULES = [
    ("EXPECTED REPAIR TIME on this repo\n  typical", "NUMBER", "-"),
    ("unmeasurable here, and that IS the answer",
     "REFUSAL", "suite runtime (suite exceeded --suite-timeout)"),
    ("has no pytest, so no test has been judged",
     "REFUSAL", "a pytest importable by the target interpreter"),
    ("pytest collected NO TESTS",
     "REFUSAL", "any collectable pytest test in this root"),
    ("pytest usage/configuration error",
     "REFUSAL", "a pytest invocation this repo's config accepts"),
    ("pytest hit an internal error",
     "REFUSAL", "a pytest run that did not crash"),
    ("reported no test results",
     "REFUSAL", "a summary line naming passed/failed/error counts"),
    ("could not run the suite", "REFUSAL", "a runnable suite process"),
]


def classify(out):
    for marker, verdict, missing in RULES:
        if marker in out:
            return verdict, missing
    return "UNCLASSIFIED", "?"


def main(argv):
    outfile, roots = argv[0], argv[1:]
    rows = []
    for spec in roots:
        extra = []
        root = spec
        if "::" in spec:
            root, tail = spec.split("::", 1)
            extra = tail.split()
        name = os.path.basename(root.rstrip("/"))
        base = [] if "--python" in " ".join(extra) else ["--python", PY]
        cmd = [TMO, "400", FF, "estimate", root] + base + extra
        t0 = time.time()
        p = subprocess.run(cmd, capture_output=True, text=True)
        wall = time.time() - t0
        out = p.stdout + p.stderr
        verdict, missing = classify(out)
        rows.append(dict(repo=name, root=root, extra=" ".join(extra),
                         rc=p.returncode, wall=round(wall, 2),
                         verdict=verdict, missing=missing, out=out))
        print(f"{name:38s} rc={p.returncode} {verdict:13s} {missing}")
        sys.stdout.flush()

    with open(os.path.join(HERE, outfile), "w") as f:
        n = len(rows)
        got = sum(r["verdict"] == "NUMBER" for r in rows)
        f.write(f"# raw `fluidfix estimate` runs\n\n"
                f"{got}/{n} got a number; {n - got}/{n} refused.\n\n")
        for r in rows:
            f.write(f"\n## {r['repo']}  ({r['verdict']}, exit {r['rc']}, "
                    f"{r['wall']}s wall)\n\n")
            f.write(f"missing observation: {r['missing']}\n\n")
            f.write("```\n$ fluidfix estimate {} --python .venv/bin/python {}\n"
                    .format(r["root"], r["extra"]))
            f.write(r["out"].rstrip() + "\n```\n")
    with open(os.path.join(HERE, outfile.replace(".md", ".json")), "w") as f:
        json.dump(rows, f, indent=1)
    n = len(rows)
    got = sum(r["verdict"] == "NUMBER" for r in rows)
    print(f"\n{got}/{n} number, {n - got}/{n} refusal")


if __name__ == "__main__":
    main(sys.argv[1:])
