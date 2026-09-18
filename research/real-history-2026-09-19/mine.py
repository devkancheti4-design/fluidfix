#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Shape coverage on REAL fixes — the number every growth claim was waiting on.

Everything measured so far has run on faults we seeded or models wrote to our prompts. Both are corpora we
built, so neither can say what fraction of the bugs a team ACTUALLY fixes are mechanical. That number
decides whether a self-healing CI is a product or a slogan, and it cannot come from a corpus of ours.

It can come from git. Four real repositories, their whole recorded history, and the commits where somebody
fixed something. For each one the diff is measured, not read:

    ONE-LINE      exactly one existing line replaced by one line, in one hunk
    INSERTION     lines added, none changed
    DELETION      lines removed, none added
    STRUCTURAL    anything else

and then, for the one-line fixes only, the harder question: **does fluidfix's vocabulary actually produce
that line?** Every shipped and taught class is applied to the original line, and a class counts only when
one of its candidates equals the committed fix, character for character. No test suite is involved and no
credit is given for being close.

The filter is stated rather than tuned: a commit whose subject says it fixes something, touching exactly one
Python file that is not a test, with a diff of at most 40 changed lines, and not a merge or a revert.

  python3 mine.py <repos-root> [--max-lines 40]
"""
from __future__ import annotations

import argparse, json, re, subprocess, sys, time
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "src"))
from fluidfix.acts import KINDS, ACTS, Observation, act_for, load_dictionary   # noqa: E402

DICTS = [HERE.parents[1] / "examples" / "taught-2026-09-16" / "rules_session.py",
         HERE.parents[1] / "examples" / "taught-2026-09-18" / "kinds_from_ladder.py"]

FIX = re.compile(r"\b(fix|fixes|fixed|bug|regression|correct|incorrect|wrong|broken|typo|off.by.one)\b", re.I)
SKIP = re.compile(r"\b(merge|revert|bump|release|changelog|lint|format|typing|docs?|readme|test)\b", re.I)


def sh(args, cwd):
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=180).stdout


def fixes(repo: Path, max_lines: int):
    """Every commit that claims to fix something and touches exactly one non-test Python file."""
    log = sh(["git", "log", "--no-merges", "--format=%H%x00%s"], repo).strip().split("\n")
    out = []
    for line in log:
        if "\x00" not in line:
            continue
        sha, subj = line.split("\x00", 1)
        if not FIX.search(subj) or SKIP.search(subj):
            continue
        files = [f for f in sh(["git", "show", "--name-only", "--format=", sha], repo).split("\n") if f.strip()]
        py = [f for f in files if f.endswith(".py")]
        if len(files) != 1 or len(py) != 1:
            continue
        rel = py[0]
        if "test" in rel.lower() or "/docs/" in rel or rel.startswith("docs/"):
            continue
        diff = sh(["git", "show", "--format=", "-U0", sha, "--", rel], repo)
        minus = [l[1:] for l in diff.split("\n") if l.startswith("-") and not l.startswith("---")]
        plus = [l[1:] for l in diff.split("\n") if l.startswith("+") and not l.startswith("+++")]
        hunks = diff.count("\n@@")
        if len(minus) + len(plus) > max_lines or (not minus and not plus):
            continue
        out.append({"sha": sha[:10], "subject": subj[:90], "file": rel,
                    "hunks": hunks, "minus": minus, "plus": plus})
    return out


def shape(c):
    m, p, h = len(c["minus"]), len(c["plus"]), c["hunks"]
    if h == 1 and m == 1 and p == 1:
        return "ONE-LINE"
    if m == 0 and p > 0:
        return "INSERTION"
    if p == 0 and m > 0:
        return "DELETION"
    return "STRUCTURAL"


def vocabulary_produces(before: str, after: str):
    """Does any class propose EXACTLY this line? Character for character; nothing is given for near misses."""
    hits = []
    for kind, entry in sorted(KINDS.items()):
        sig = entry[2]
        if sig is None or not sig.search(before):
            continue
        applier = ACTS.get(act_for(kind))
        if applier is None:
            continue
        obs = Observation(lineno=1); obs.kinds = [kind]; obs.all_lines = [before]
        try:
            proposed = applier(before, obs)
        except Exception:
            continue
        for cand in (proposed if isinstance(proposed, list) else [proposed]):
            if isinstance(cand, str) and cand.rstrip() == after.rstrip():
                hits.append(entry[0])
                break
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root"); ap.add_argument("--max-lines", type=int, default=40)
    a = ap.parse_args()
    for d in DICTS:
        load_dictionary(str(d))

    root = Path(a.root)
    report, t0 = [], time.time()
    print(f"{'repo':24} {'commits':>8} {'fix commits':>12} {'single-file':>12}")
    allc = []
    for repo in sorted(p for p in root.iterdir() if (p / ".git").is_dir()):
        total = sh(["git", "rev-list", "--count", "HEAD"], repo).strip()
        cs = fixes(repo, a.max_lines)
        for c in cs:
            c["repo"] = repo.name
        allc += cs
        print(f"{repo.name:24} {total:>8} {'—':>12} {len(cs):>12}")

    tally = Counter(shape(c) for c in allc)
    print(f"\n{len(allc)} real single-file fix commits, diff measured not read\n")
    print(f"{'shape':14} {'n':>5} {'share':>7}")
    for k, v in tally.most_common():
        print(f"{k:14} {v:>5} {v/len(allc):>6.0%}")

    ones = [c for c in allc if shape(c) == "ONE-LINE"]
    covered = []
    for c in ones:
        hits = vocabulary_produces(c["minus"][0], c["plus"][0])
        c["classes"] = hits
        if hits:
            covered.append(c)
    print(f"\nof the {len(ones)} ONE-LINE fixes, the vocabulary produces the committed line exactly "
          f"in {len(covered)} ({len(covered)/max(1,len(ones)):.0%})")
    for c in covered[:14]:
        print(f"    {c['repo']:20} {','.join(c['classes'])[:34]:34} {c['subject'][:44]}")
        print(f"        - {c['minus'][0].strip()[:82]}")
        print(f"        + {c['plus'][0].strip()[:82]}")

    out = {"commits": len(allc), "tally": dict(tally), "one_line": len(ones),
           "vocabulary_exact": len(covered),
           "rows": [{k: v for k, v in c.items() if k not in ("minus", "plus")} |
                    {"before": c["minus"][0] if len(c["minus"]) == 1 else None,
                     "after": c["plus"][0] if len(c["plus"]) == 1 else None} for c in allc]}
    (HERE / "real_history.json").write_text(json.dumps(out, indent=1, default=str))
    print(f"\n{round(time.time()-t0,1)}s  MINE_DONE")


if __name__ == "__main__":
    main()
