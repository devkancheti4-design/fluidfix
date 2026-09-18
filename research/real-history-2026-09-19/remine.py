#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Re-mine without the bias that ruined the first pass — and count what the first pass threw away.

The first pass demanded a commit touch EXACTLY ONE file. A well-made bug fix changes the code and adds a
regression test, so that filter excluded every properly-tested fix and kept the ones too trivial to test.
Half the survivors were typos, which should have been the clue.

This pass keeps a commit when it changes exactly one non-test source file, with any number of test files
alongside, and records whether a test came with it. A fix that ships its own regression test is worth far
more than a cleaner statistic: **the test is the judge**, and it makes the repair runnable rather than
merely comparable to what the maintainer happened to type.

  python3 remine.py <repos-root>
"""
from __future__ import annotations

import argparse, json, re, subprocess, sys, time
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIX = re.compile(r"\b(fix|fixes|fixed|bug|regression|correct|incorrect|wrong|broken|typo|off.by.one)\b", re.I)
SKIP = re.compile(r"\b(merge|revert|bump|release|changelog|lint|format|typing)\b", re.I)


def sh(args, cwd):
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=180).stdout


def is_test(p):
    b = p.lower()
    return "test" in b.split("/")[-1] or "/tests/" in b or b.startswith("tests/")


def mine(repo: Path, max_lines: int):
    log = [l for l in sh(["git", "log", "--no-merges", "--format=%H%x00%s"], repo).strip().split("\n") if "\x00" in l]
    out = []
    for line in log:
        sha, subj = line.split("\x00", 1)
        if not FIX.search(subj) or SKIP.search(subj):
            continue
        files = [f for f in sh(["git", "show", "--name-only", "--format=", sha], repo).split("\n") if f.strip()]
        if not files:
            continue
        src = [f for f in files if f.endswith(".py") and not is_test(f)
               and not f.startswith("docs/") and "/docs/" not in f]
        tests = [f for f in files if f.endswith(".py") and is_test(f)]
        other = [f for f in files if f not in src and f not in tests]
        if len(src) != 1:
            continue
        if other and any(not o.endswith((".rst", ".md", ".txt", ".cfg", ".toml")) for o in other):
            continue
        diff = sh(["git", "show", "--format=", "-U0", sha, "--", src[0]], repo)
        minus = [l[1:] for l in diff.split("\n") if l.startswith("-") and not l.startswith("---")]
        plus = [l[1:] for l in diff.split("\n") if l.startswith("+") and not l.startswith("+++")]
        if len(minus) + len(plus) > max_lines or (not minus and not plus):
            continue
        out.append({"repo": repo.name, "sha": sha, "subject": subj[:90], "file": src[0],
                    "tests": tests, "hunks": diff.count("\n@@"),
                    "minus": minus, "plus": plus,
                    "one_line": diff.count("\n@@") == 1 and len(minus) == 1 and len(plus) == 1})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root"); ap.add_argument("--max-lines", type=int, default=40)
    a = ap.parse_args()
    allc, t0 = [], time.time()
    print(f"{'repo':26} {'kept':>6} {'with a regression test':>24}")
    for repo in sorted(p for p in Path(a.root).iterdir() if (p / ".git").is_dir()):
        cs = mine(repo, a.max_lines)
        witht = sum(1 for c in cs if c["tests"])
        allc += cs
        print(f"{repo.name:26} {len(cs):>6} {witht:>24}")

    withtest = [c for c in allc if c["tests"]]
    ones = [c for c in allc if c["one_line"]]
    ones_t = [c for c in withtest if c["one_line"]]
    print(f"\n{len(allc)} fix commits touching exactly one source file (tests alongside allowed)")
    print(f"  the first pass, demanding exactly ONE file in total, kept 289 — it discarded "
          f"{len(withtest)} fixes that shipped a regression test")
    print(f"\n{'':40} {'n':>5} {'one-line':>10}")
    print(f"{'  all fix commits kept':40} {len(allc):>5} {len(ones):>10}")
    print(f"{'  of those, shipping a regression test':40} {len(withtest):>5} {len(ones_t):>10}")
    print(f"{'  no test shipped':40} {len(allc)-len(withtest):>5} {len(ones)-len(ones_t):>10}")
    print(f"\none-line share WITH a test:    {len(ones_t)/max(1,len(withtest)):.0%}")
    print(f"one-line share WITHOUT a test: {(len(ones)-len(ones_t))/max(1,len(allc)-len(withtest)):.0%}")

    json.dump({"kept": len(allc), "with_test": len(withtest), "one_line": len(ones),
               "one_line_with_test": len(ones_t),
               "rows": [{k: v for k, v in c.items()} for c in allc]},
              open(HERE / "remine.json", "w"), indent=1)
    print(f"\n{round(time.time()-t0,1)}s  REMINE_DONE")


if __name__ == "__main__":
    main()
