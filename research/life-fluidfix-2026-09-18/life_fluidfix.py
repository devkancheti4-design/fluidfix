#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""fluidfix's taught shapes as a free, VERIFIED tier inside the Life Debugger's ladder.

The Life Debugger (github.com/devkancheti4-design/life-debugger, AGPL-3.0) escalates:

    TIER 1  FACTS      static anti-patterns + the runtime error class — names the problem, $0
    TIER 2  LIFE       replays a fix it has already been given, $0
    TIER 3  REASONER   a model writes a fix — and nothing checks it

Two gaps: tier 1 can only NAME a bug, never repair it, and a tier-3 fix is trusted on sight. fluidfix closes
both with the thing it already owns — a vocabulary of fault SHAPES, each with a signal that says which lines
can exhibit it and an applier that proposes the correction, and the rule that only the test may accept a
candidate. So this inserts:

    TIER 1.5  SHAPES   fluidfix's shipped + taught classes propose; the caller's own test judges;
                       a candidate that does not turn the test green is rolled back, byte-exact, $0

and puts the same judge in front of tier 3: a model's fix is now run before it is believed. What survives is
learned into the Life, so the second occurrence of a shape replays for free, exactly as before.

    from life_fluidfix import debug_fused
    rep = debug_fused(code, test="assert total([1,2]) == 3")

No product change: KINDS, the appliers and the dictionary loader are fluidfix's own.
"""
import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "src"))
sys.path.insert(0, str(HERE.parent / "lake-2026-09-18"))      # the vendored Life (life.py)

from fluidfix.acts import KINDS, ACTS, Observation, act_for, load_dictionary   # noqa: E402
from life import Life                                                          # noqa: E402

MAX_CANDIDATES_PER_LINE = 8
DB = str(HERE / "life_fluidfix.json")


# ------------------------------------------------------------------ the judge (the caller's own test)
def run_test(code: str, test: str | None, timeout: int = 6) -> bool:
    """True when the code plus the caller's test runs clean. This is the only thing that may accept a fix."""
    script = code + (("\n" + test) if test else "")
    try:
        r = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return False
    return r.returncode == 0


# ------------------------------------------------------------------ TIER 1.5: the taught shapes
def shape_candidates(line: str, lineno: int, all_lines: list[str]):
    """Every repair fluidfix's vocabulary proposes for this line, with the shape that proposed it."""
    out = []
    for kind, entry in sorted(KINDS.items()):
        name, _desc, signal = entry[0], entry[1], entry[2]
        if signal is None or not signal.search(line):
            continue
        applier = ACTS.get(act_for(kind))
        if applier is None:
            continue
        obs = Observation(lineno=lineno)
        obs.kinds = [kind]
        obs.all_lines = all_lines
        try:
            proposed = applier(line, obs)
        except Exception:                      # a rule that raises is a rule that abstains
            continue
        for cand in (proposed if isinstance(proposed, list) else [proposed])[:MAX_CANDIDATES_PER_LINE]:
            if isinstance(cand, str) and cand != line:
                out.append((kind, name, cand))
    return out


def shapes_repair(code: str, test: str, dictionary: str | None = None):
    """Try the taught shapes, line by line, judging every candidate with the caller's test.

    Returns {"code", "kind", "shape", "line", "before", "after", "tests_run"} or None. Nothing is accepted
    on resemblance: a candidate is kept only because the test went green, and every rejected candidate is
    rolled back exactly."""
    if dictionary:
        load_dictionary(dictionary)
    lines = code.split("\n")
    runs = 0
    for i, line in enumerate(lines):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        for kind, name, cand in shape_candidates(line, i + 1, lines):
            trial = lines[:]                      # the rollback is the copy: the original is never mutated
            trial[i] = cand
            candidate_code = "\n".join(trial)
            try:
                compile(candidate_code, "<candidate>", "exec")
            except SyntaxError:
                continue                          # costs no test run
            runs += 1
            if run_test(candidate_code, test):
                return {"code": candidate_code, "kind": kind, "shape": name, "line": i + 1,
                        "before": line.strip(), "after": cand.strip(), "tests_run": runs}
    return None


def _sig(code: str) -> str:
    return hashlib.md5(re.sub(r"\s+", " ", code).encode()).hexdigest()[:16]


# ------------------------------------------------------------------ the fused ladder
def debug_fused(code: str, test: str | None = None, reasoner=None, dictionary: str | None = None,
                life: Life | None = None, db: str = DB):
    """FACTS -> LIFE -> SHAPES (free, verified) -> REASONER (verified before it is believed).

    Returns a report saying who fixed it, what it cost, and how many test runs were paid.
    `handled_by` is never "fixed" unless the test actually passed.
    """
    life = life if life is not None else Life(db)
    rep = {"fix": None, "handled_by": None, "shape": None, "tests_run": 0, "tokens": 0,
           "verified": False, "escalated": False}

    if test is not None and run_test(code, test):
        rep["handled_by"] = "nothing to fix (the test already passes)"
        return rep

    sig = _sig(code)

    # TIER 2 — the Life replays a shape it has already been taught, for free
    known = life.recall("shape:" + sig)
    if known and test is not None:
        kind_s, lineno_s, after = known.split("|", 2)
        lines = code.split("\n")
        idx = int(lineno_s) - 1
        if 0 <= idx < len(lines):
            trial = lines[:]
            trial[idx] = (lines[idx][: len(lines[idx]) - len(lines[idx].lstrip())]) + after
            rep["tests_run"] += 1
            if run_test("\n".join(trial), test):
                rep.update(fix="\n".join(trial), handled_by="life (replayed a known shape, $0)",
                           shape=KINDS.get(int(kind_s), ("?",))[0], verified=True)
                return rep                       # replayed AND re-verified: memory never overrides the test

    # TIER 1.5 — fluidfix's taught shapes propose, the caller's test judges
    if test is not None:
        got = shapes_repair(code, test, dictionary)
        rep["tests_run"] += got["tests_run"] if got else 0
        if got:
            life.learn("shape:" + sig, f"{got['kind']}|{got['line']}|{got['after']}")
            life.learn("shapes-that-answered", f"kind:{got['kind']}")
            life.save()
            rep.update(fix=got["code"], handled_by=f"fluidfix shape {got['kind']} ({got['shape']}), $0",
                       shape=got["shape"], verified=True)
            return rep

    # TIER 3 — a model, and its answer faces the same judge
    if reasoner is not None:
        proposed = reasoner(code, test)
        rep["escalated"] = True
        rep["tokens"] = getattr(reasoner, "last_tokens", 0)
        if proposed and test is not None:
            rep["tests_run"] += 1
            if run_test(proposed, test):
                rep.update(fix=proposed, handled_by="reasoner (verified by the test)", verified=True)
                return rep
        rep.update(fix=proposed, handled_by="reasoner proposed, TEST REJECTED IT", verified=False)
        return rep

    rep["handled_by"] = "no shape matched and no reasoner attached — abstained"
    return rep
