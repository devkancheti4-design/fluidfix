# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 devkancheti4-design
# Commercial licensing: see COMMERCIAL.md.
"""Which files should this team test FIRST?

fluidfix maintains exactly what your tests cover. That makes "what should we
test?" the highest-value question a team can ask before adopting it — and the
repository already knows the answer, because every bug fix in its history
names the file that broke.

    defect density   how often a file appears in bug-fix commits
    coverage gap     how little of it the suite executes today
    priority         density x gap — where a test buys the most guarding

WHY DENSITY BEATS UNIFORM COVERAGE. Measured on Box2D's own history
(2026-09-04, 1,383 commits, 207 of them bug fixes touching 201 engine files):

    to guard 30% of historical defects   test  19 files   ( 9% of the engine)
    to guard 50%                         test  45 files   (22%)
    to guard 60%                         test  61 files   (30%)
    to guard 80%                         test 103 files   (51%)

So 60% of defects costs 30% of files, not 60% — defects cluster, and coverage
aimed at the cluster is about twice as efficient as coverage spread evenly.
"Get to 60% coverage" sounds like a year nobody will fund; "test the 61 files
your own history already named" is a sprint.

For a live-service product the ranking is even cheaper to obtain: three months
of incidents IS the density measurement, and every incident is a test that
pays twice — once as a regression guard, once as a worked example a fault
class can be taught from.

This module reads git history only. Coverage, when a caller supplies it,
sharpens the ranking; without it the density ranking still stands.
"""
from __future__ import annotations

import collections
import os
import re
import subprocess

__all__ = ["bugfix_churn", "rank_hotspots", "coverage_to_reach"]

# A commit that repairs something, in the vocabulary maintainers actually use.
_FIX = re.compile(
    r"\b(fix(e[sd])?|bug|crash|regress(ion)?s?|incorrect|wrong|broken|"
    r"leak|assert|error|fault|defect|hotfix|patch)\b", re.I)

# Sources that cannot carry a shipped defect: tests, demos, vendored trees.
_SKIP = re.compile(
    r"(^|/)(tests?|testing|testbed|samples?|examples?|benchmarks?|extern|"
    r"external|third_party|vendor|deps|docs?|build|shared)(/|$)", re.I)

_CODE = (".c", ".h", ".cc", ".cpp", ".cxx", ".hpp", ".hh", ".py", ".java",
         ".cs", ".rs", ".go", ".ts", ".js")


def bugfix_churn(root: str, commits: int = 4000
                 ) -> tuple[collections.Counter, int, int]:
    """(file -> bug-fix touches, commits scanned, bug-fix commits found).

    Reads `git log` only — no build, no network, no checkout. Returns an empty
    counter rather than raising when the directory is not a git repository,
    because a caller asking "what should I test?" should get an answer about
    what CAN be determined, not an exception."""
    try:
        out = subprocess.run(
            ["git", "-C", root, "log", f"-n{commits}",
             "--format=@@@%s", "--name-only"],
            capture_output=True, text=True, errors="replace",
            timeout=300).stdout
    except Exception:                                       # noqa: BLE001
        return collections.Counter(), 0, 0

    churn: collections.Counter = collections.Counter()
    scanned = fixes = 0
    is_fix = False
    for line in out.split("\n"):
        line = line.strip()
        if not line:
            continue
        if line.startswith("@@@"):
            scanned += 1
            is_fix = bool(_FIX.search(line[3:]))
            fixes += is_fix
            continue
        if not is_fix or not line.endswith(_CODE) or _SKIP.search(line):
            continue
        churn[line] += 1
    return churn, scanned, fixes


def coverage_to_reach(churn: collections.Counter,
                      shares=(0.3, 0.5, 0.6, 0.8)) -> list[tuple[float, int]]:
    """[(share of historical defects, files that must be tested to reach it)].

    This is the number that reframes the ask: a share of DEFECTS, not a share
    of lines."""
    total = sum(churn.values())
    if not total:
        return []
    out, run, targets = [], 0, sorted(shares)
    i = 0
    for _rank, (_f, n) in enumerate(churn.most_common(), 1):
        run += n
        while i < len(targets) and run / total >= targets[i]:
            out.append((targets[i], _rank))
            i += 1
    while i < len(targets):                      # unreachable shares
        out.append((targets[i], len(churn)))
        i += 1
    return out


def rank_hotspots(root: str, churn: collections.Counter,
                  covered: dict | None = None, limit: int = 25) -> list[dict]:
    """Rank files by defect density x coverage gap.

    `covered` maps repo-relative path -> set of executed line numbers, exactly
    what the C oracle's gcov tier produces. Absent, every file is treated as
    unknown coverage and the ranking is density alone — still the right
    ordering, just without the gap multiplier.
    """
    rows = []
    for rel, hits in churn.most_common():
        total = _code_lines(os.path.join(root, rel))
        if not total:
            continue
        if covered is None:
            frac, gap = None, 1.0
        else:
            frac = min(len(covered.get(rel, ())) / total, 1.0)
            gap = 1.0 - frac
        # A header of pure DECLARATIONS cannot be tested directly and its
        # coverage cannot be measured honestly: under any optimising build
        # its inline bodies are attributed to the caller's translation unit,
        # so it reads near 0% however well exercised it is. Measured on
        # Box2D: math_functions.h shows 4% while fluidfix repaired b2Cross
        # in it twice, from failing tests. Rank such files, but never above
        # a source file with real defect density.
        decl_only = (rel.endswith((".h", ".hpp", ".hh"))
                     and _statement_density(os.path.join(root, rel)) < 0.15)
        rows.append({"file": rel, "defects": hits, "lines": total,
                     "covered": frac, "declarations": decl_only,
                     "priority": hits * gap * (0.25 if decl_only else 1.0)})
    rows.sort(key=lambda r: (-r["priority"], -r["defects"], r["file"]))
    return rows[:limit]


def _code_only(path: str) -> list[str]:
    """Non-blank, non-comment lines. Shared by both measures below, because
    computing statement density over PROSE reads a documented header of pure
    declarations as if it were implementation: Box2D's box2d.h scored 0.198
    on its doc comments alone ("if", "for", "=" all occur in English)."""
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            src = fh.read().split("\n")
    except OSError:
        return []
    out, in_block = [], False
    for line in src:
        t = line.strip()
        if not t:
            continue
        if in_block:
            if "*/" in t:
                in_block = False
            continue
        if t.startswith("/*"):
            in_block = "*/" not in t
            continue
        if t.startswith(("//", "*", "#include", "#ifndef", "#define",
                         "#endif", "#ifdef", "#pragma", "}")):
            continue
        out.append(t)
    return out


def _statement_density(path: str) -> float:
    """Fraction of CODE lines that look like executable statements rather
    than declarations — the cheap way to tell a header of prototypes from a
    header carrying inline implementations."""
    code = _code_only(path)
    if not code:
        return 1.0
    stmt = sum(1 for l in code
               if ("=" in l or l.startswith(("return", "if", "for", "while")))
               and not l.endswith(");"))
    return stmt / len(code)


def _code_lines(path: str) -> int:
    return len(_code_only(path))
