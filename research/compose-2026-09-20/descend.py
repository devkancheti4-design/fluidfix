#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Connecting two taught classes, by descent.

`shapes_repair` accepts a candidate only when the WHOLE suite goes green. With two faults present, a
perfectly correct fix for one of them leaves the suite red and is discarded — indistinguishable, to a
boolean runner, from a fix that did nothing. The vocabulary already held both repairs; the harness threw
them away.

A runner that reports WHICH tests fail changes that. A correct partial fix has a signature a boolean
cannot see: the failing set STRICTLY SHRINKS and no passing test starts failing. That is enough to step.

Acceptance is unchanged where it matters. An intermediate step is provisional, not certified; only the
final state is judged by the whole suite going green, and if descent never reaches green every edit is
rolled back and the answer is still refusal."""
from __future__ import annotations
import subprocess, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "research/life-fluidfix-2026-09-18"))
from life_fluidfix import shape_candidates, load_dictionary
from fluidfix.props import check, REFUTED

DICT = str(ROOT / "examples/taught-2026-09-19/corpus.py")


def _apply_one(base, kind, hist, final):
    """The one-hop result for this class, for property checking: the next line in the composition."""
    for j, (k, _n, b) in enumerate(hist):
        if b is base and k == kind:
            return hist[j + 1][2] if j + 1 < len(hist) else final
    return final


def failing(code: str, tests: list) -> frozenset:
    """Which of the caller's tests fail. One subprocess, one line of output per test."""
    harness = code + "\n\n_f = []\n"
    for i, t in enumerate(tests):
        harness += f"try:\n    {t}\nexcept Exception:\n    _f.append({i})\n"
    harness += "print(','.join(map(str, _f)))\n"
    try:
        r = subprocess.run([sys.executable, "-c", harness], capture_output=True, text=True, timeout=10)
    except subprocess.TimeoutExpired:
        return frozenset(range(len(tests)))
    if r.returncode != 0:
        return frozenset(range(len(tests)))          # did not even import: everything fails
    out = r.stdout.strip()
    return frozenset(int(x) for x in out.split(",") if x != "")


def line_candidates(line, lineno, all_lines, depth=2):
    """Every candidate for this line, including COMPOSED ones: a class's rewrite fed back through the
    vocabulary so a second class can act on the result.

    Needed because descent is blind to a fault it cannot observe alone. On
    `return words[len(words)] and fallback` neither single repair changes which tests fail — the index
    error and the wrong operator mask each other — so the step has no gradient. Composing first and
    testing the pair restores it. Cost is candidates-per-line squared, and a line yields one to three."""
    seen, out = {line}, []
    frontier = [(line, ())]
    for _ in range(depth):
        nxt = []
        for base, hist in frontier:
            for kind, name, cand in shape_candidates(base, lineno, all_lines):
                if cand in seen:
                    continue
                seen.add(cand)
                rec = (cand, hist + ((kind, name, base),))
                out.append(rec)
                nxt.append(rec)
        frontier = nxt
    return out


def descend(code: str, tests: list, max_steps: int = 6, use_property: bool = True, depth: int = 1):
    """Greedy descent over the taught vocabulary. Returns a dict or None."""
    original = code
    lines = code.split("\n")
    runs = 1
    cur = failing("\n".join(lines), tests)
    if not cur:
        return None                                   # not red to begin with
    steps, blocked = [], 0
    for _ in range(max_steps):
        best = None
        for i, line in enumerate(lines):
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            for cand, hist in line_candidates(line, i + 1, lines, depth):
                if cand == line:
                    continue
                if use_property:
                    bad = False
                    for k, _n2, base in hist:         # every hop must keep its class's property
                        v, _w, _c = check(k, base, _apply_one(base, k, hist, cand))
                        if v == REFUTED:
                            bad = True; break
                    if bad:
                        blocked += 1
                        continue                      # refused for free, before any test runs
                kind = hist[-1][0]; name = " + ".join(h[1] for h in hist)
                trial = lines[:]
                trial[i] = cand
                try:
                    compile("\n".join(trial), "<c>", "exec")
                except SyntaxError:
                    continue
                runs += 1
                got = failing("\n".join(trial), tests)
                if got < cur:                         # strict subset: fewer failures, no new ones
                    best = (i, cand, kind, name, got, line)
                    break
            if best:
                break
        if not best:
            break
        i, cand, kind, name, got, was = best
        lines[i] = cand
        steps.append({"kind": kind, "shape": name, "line": i + 1,
                      "before": was.strip(), "after": cand.strip(),
                      "failing": f"{len(cur)} -> {len(got)}"})
        cur = got
        if not cur:
            return {"code": "\n".join(lines), "steps": steps, "runs": runs,
                    "blocked_by_property": blocked}
    return {"code": original, "steps": steps, "runs": runs, "blocked_by_property": blocked,
            "refused": True}
