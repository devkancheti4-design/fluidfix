# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 devkancheti4-design
# Commercial licensing: see COMMERCIAL.md.
"""The guard: commit-and-forget maintenance.

    green  -> touch nothing, sleep
    red    -> find the fault file mechanically, localise, observe, route,
              repair — the repo goes back to what it was meant to be
    novel  -> refuse LOUDLY (a machine-readable refusal report), tree
              untouched; teaching the class once (register(), or a compiled
              dictionary) makes its whole family free from then on

Fault-file discovery is mechanical: source files quoted in the failing
traceback (deepest frame preferred, test files excluded), falling back to the
files the failing test executed most, ranked by coverage. No model is needed
to find the file — only, optionally, to name the fault kind.
"""
from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import time
from dataclasses import dataclass, field

from .localize import build_packet
from .loop import RepairResult, repair
from .oracle import Oracle

__all__ = ["GuardReport", "find_candidate_files", "guard_once",
           "rank_observations"]

_ANSI = re.compile(r"\x1b\[[0-9;]*m")


@dataclass
class GuardReport:
    status: str                       # "green" | "repaired" | "refused"
    file: str | None = None
    result: RepairResult | None = None
    candidates: list[str] = field(default_factory=list)
    seconds: float = 0.0
    # --dry-run's restore point: the defect file's bytes as found (broken),
    # captured just before the repair that landed
    before: bytes | None = None

    hint: str = ""
    # engine law HARVEST_COUNTEREXAMPLE, actuated: every candidate rejected
    # on the way to this report, each with the failing test that killed it
    attempts: list = field(default_factory=list)

    def summary(self) -> str:
        if self.status == "green":
            return "suite green — nothing to do"
        if self.status == "repaired":
            return f"{self.file}: {self.result.summary()}"
        base = ("REFUSED: fault is outside the taught vocabulary "
                f"(candidate files tried: {', '.join(self.candidates) or 'none found'}). "
                "teach it once: docs/TEACHING.md (or run: fluidfix kinds)")
        if self.attempts:
            base += (f" {len(self.attempts)} candidate(s) were tried and "
                     "rejected — each is logged with the test that failed "
                     "it in the refusal report.")
        return base + (f"\n  hint: {self.hint}" if self.hint else "")


def _is_test_path(rel: str) -> bool:
    parts = rel.replace("\\", "/").split("/")
    base = parts[-1]
    return (base.startswith("test_") or base.endswith("_test.py")
            or "tests" in parts[:-1] or base == "conftest.py")


def find_candidate_files(oracle: Oracle, failing_output: str,
                         limit: int = 3) -> list[str]:
    """Project source files implicated by the failure, most suspect first."""
    clean = _ANSI.sub("", failing_output)
    ordered: list[str] = []
    for m in re.finditer(r"([\w./\\-]+\.py)[\":,]", clean):
        p = m.group(1).replace("\\", "/")
        full = p if os.path.isabs(p) else os.path.join(oracle.root, p)
        full = os.path.normpath(full)
        if not full.startswith(oracle.root + os.sep) or not os.path.isfile(full):
            continue
        rel = os.path.relpath(full, oracle.root).replace("\\", "/")
        if _is_test_path(rel):
            continue
        # deepest (latest) traceback frame is closest to the fault
        if rel in ordered:
            ordered.remove(rel)
        ordered.append(rel)
    ordered.reverse()
    if ordered:
        return ordered[:limit]
    # No source frames (pure assertion failure): file-level SPECTRUM
    # localisation. Two coverage runs — the failing test alone (--lf) and the
    # full suite — then rank by how SPECIFIC a file is to the failure:
    #     score = |lines the failing test executes in f| / |lines the whole
    #             suite executes in f|
    # Ranking by raw executed-line count was measured (Click, seeded bench) to
    # bury the defect file under big central modules that every test touches.
    # A filename token shared with the failing test module boosts to front.
    def _cov_counts(args):
        cov_json = os.path.join(oracle.root, "_fluidfix_guard_cov.json")
        oracle.run(args + ["--tb=no", "--cov=.",
                          f"--cov-report=json:{cov_json}"], cache=True)
        out = {}
        if os.path.exists(cov_json):
            try:
                cov = json.load(open(cov_json))
                for f, data in cov.get("files", {}).items():
                    rel = f.replace("\\", "/")
                    if _is_test_path(rel) or not rel.endswith(".py"):
                        continue
                    out[rel] = len(data.get("executed_lines", []))
            finally:
                os.remove(cov_json)
        return out

    fail_cov = _cov_counts(["--lf"])
    full_cov = _cov_counts([])
    # affinity tokens come ONLY from the failing tests' module names —
    # test_termui.py names termui; traceback file mentions are noise
    fail_mods: set[str] = set()
    for m in re.finditer(r"^(?:FAILED|ERROR)\s+\S*?([\w]+)\.py", clean, re.M):
        name = m.group(1).lower()
        name = re.sub(r"^test_?|_?tests?$", "", name)
        fail_mods.update(t for t in re.findall(r"[a-z]{3,}", name))
    ranked2: list[tuple[float, float, int, str]] = []
    for rel, n_fail in fail_cov.items():
        if n_fail == 0:
            continue
        n_full = max(full_cov.get(rel, n_fail), n_fail)
        specificity = n_fail / n_full
        base_tokens = set(re.findall(r"[a-z]{3,}",
                                     os.path.basename(rel).lower()))
        affinity = 1.0 if base_tokens & fail_mods else 0.0
        ranked2.append((affinity, specificity, n_fail, rel))
    # affinity first (the failing test names its subject), then specificity,
    # then substance (n_fail) so trivially-imported stubs sink
    ranked2.sort(key=lambda t: (-t[0], -t[1], -t[2], t[3]))
    return [rel for _, _, _, rel in ranked2[:max(limit, 8)]]


def _name_tokens(name: str) -> set[str]:
    return {w.lower() for w in re.findall(r"[A-Z]?[a-z]{2,}", name)
            if len(w) >= 3 and w.lower() not in ("test", "tests")}


def rank_observations(src: str, observations: list, failing_output: str) -> list:
    """The failing test names its subject — at LINE granularity.
    `FAILED ...::TestOdiaLocale::test_ordinal_number` points at
    class OdiaLocale, def _ordinal_number; observations whose enclosing
    class/def share name tokens with the failing tests are tried first.
    Measured (arrow locales.py:5468): in line order the defect sat ~900th of
    931 observations — beyond any honest wall clock at ~6s of suite per
    candidate — while affinity ranks it into the first handful. Tokens come
    ONLY from FAILED/ERROR node ids, so this is fully generic."""
    toks: set[str] = set()
    clean = _ANSI.sub("", failing_output)
    for m in re.finditer(r"^(?:FAILED|ERROR)\s+\S*?::(\S+)", clean, re.M):
        for part in m.group(1).split("::"):
            toks |= _name_tokens(part.split("[")[0])
    if not toks:
        return observations
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return observations
    line_toks: dict[int, set[str]] = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            nt = _name_tokens(node.name)
            if not nt:
                continue
            for l in range(node.lineno, (node.end_lineno or node.lineno) + 1):
                line_toks.setdefault(l, set()).update(nt)
    order = sorted(range(len(observations)),
                   key=lambda i: (-len(line_toks.get(observations[i].lineno,
                                                     set()) & toks), i))
    return [observations[i] for i in order]


def _has_pytest_cov(oracle: Oracle) -> bool:
    try:
        return subprocess.run([oracle.python, "-c", "import pytest_cov"],
                              capture_output=True, timeout=30).returncode == 0
    except Exception:
        return False


def guard_once(oracle: Oracle, observer, files: list[str] | None = None,
               coverage_target: str | None = None,
               candidate_timeout: int | None = None,
               escalate: bool = True,
               escalate_budget: int = 600,
               budget: int | None = None) -> GuardReport:
    """One guard pass, governed by the engine law: a refusal is not the end
    until the law says so. CAPPED (a budget truncated the search) rules
    RAISE_BUDGET and the pass retries DEPTH-FIRST — each candidate file in
    rank order gets full sight (packet raised until untruncated) before the
    next file is tried, all under one wall-clock budget; AMB, UNREAD and
    REFUTED rule honest stops with specific reports.

    `budget` (optional) caps the ENTIRE pass: the first pass may spend at
    most half of it — measured (v0.7 span bench, arrow locales.py): span
    classes multiply suite runs per observation, and an unbounded first
    pass on a promiscuous signal can burn the whole clock BEFORE reaching
    the escalation stage whose full sight + affinity ranking actually sees
    the defect. Bounding the first pass forces that handoff; expiry of the
    whole budget is an honest refusal. AMB-proof atomicity is preserved
    (deadlines are only checked between observations and between kinds)."""
    from .engine import decide, situation

    t0 = time.time()
    total_deadline = t0 + budget if budget else None
    # first pass gets a THIRD of the budget; escalation gets the rest.
    # Measured (v0.7 span bench round 2): a half/half split let blind
    # first-pass grinding starve the full-sight escalation stage that
    # actually repairs — termui's round-1 win regressed to a refusal.
    first_deadline = t0 + budget / 3 if budget else None
    fails, out = oracle.failing_output()
    if not fails:
        clear_refusal(oracle.root)
        return GuardReport(status="green", seconds=time.time() - t0)
    candidates = files or find_candidate_files(oracle, out)
    hint = ""
    capped0 = acts0 = False
    attempts: list = []
    full_sight: set[str] = set()      # pass-0 packet was complete: nothing
                                      # a bigger budget could add for this file
    if not candidates and not _has_pytest_cov(oracle):
        # a needed tool reads nothing: ASK the law rather than assume
        if decide(situation(UNREAD=True)) == "ADD_MATERIAL":
            hint = ("pytest-cov is not installed in the target interpreter, so "
                    "coverage-based localisation was unavailable — install it "
                    f"({oracle.python} -m pip install pytest-cov) and re-run; "
                    "on large codebases it is how the fault file gets found. "
                    "(engine law: UNREAD -> ADD_MATERIAL)")
    for rel in candidates:
        if total_deadline is not None and time.time() > total_deadline:
            return GuardReport(
                status="refused", candidates=candidates,
                seconds=time.time() - t0, attempts=attempts,
                hint=(f"--budget exhausted ({budget}s) during the first "
                      "pass — raise --budget, tighten taught-class signals, "
                      "or fix by hand"))
        packet = build_packet(oracle, rel, coverage_target=coverage_target)
        if packet is None:
            continue
        capped0 = capped0 or packet.truncated
        if not packet.truncated:
            full_sight.add(rel)
        observations = rank_observations("\n".join(packet.src_lines),
                                         observer.observe([packet])[0], out)
        before = open(os.path.join(oracle.root, rel), "rb").read()
        result = repair(oracle, rel, observations,
                        candidate_timeout=candidate_timeout,
                        deadline=first_deadline)
        attempts += result.tried_log
        acts0 = acts0 or bool(result.acts_tried)
        if result.repaired:
            clear_refusal(oracle.root)
            return GuardReport(status="repaired", file=rel, result=result,
                               candidates=candidates,
                               seconds=time.time() - t0, before=before)
        if result.ambiguous:                     # engine law: BUILT+AMB -> ADD_STATE
            return GuardReport(status="refused", file=rel,
                               candidates=candidates, result=result,
                               seconds=time.time() - t0,
                               hint=result.reason, attempts=attempts)

    # ---- the engine law rules on the refusal -------------------------------
    # Measure what actually blocked, then do what the law says. Only
    # RAISE_BUDGET retries; everything else is an honest, specific stop.
    # a truncated candidate-file list is also a CAPPED budget: more files
    # were implicated by coverage than the first pass tried
    all_files = files or find_candidate_files(oracle, out, limit=999)
    capped0 = capped0 or len(all_files) > len(candidates)
    if escalate and decide(situation(CAPPED=capped0, REFUTED=acts0)) == "RAISE_BUDGET":
        # DEPTH-FIRST: the budget belongs to the best-ranked file first.
        # Measured (arrow locales.py:5468): breadth-first factor rounds spent
        # the whole clock re-grinding truncated packets across 24 files and
        # never reached the sight that sees the bug — rank-1 file,
        # untruncated packet, observer flags the line. So: raise THIS file's
        # sight until the cap is gone (990, then unbounded), look once,
        # move on. The wall clock is the only other stop, checked inside
        # repair() too so one huge file cannot overshoot the budget.
        deadline = time.time() + escalate_budget
        if total_deadline is not None:
            # --budget dominates: escalation gets ALL remaining wall clock
            deadline = total_deadline
        any_acts = False
        for rel in all_files:
            if time.time() > deadline:
                return GuardReport(
                    status="refused", candidates=candidates,
                    seconds=time.time() - t0, attempts=attempts,
                    hint=(f"escalation budget exhausted ({escalate_budget}s) "
                          "with CAPPED still ruling RAISE_BUDGET — raise "
                          "--escalate-budget, use --observer claude, or fix "
                          "by hand (the search space is real, the clock ran out)"))
            if rel in full_sight:
                continue    # pass 0 already searched this file's COMPLETE
                            # packet — a bigger budget adds nothing here
            packet = build_packet(oracle, rel, coverage_target=coverage_target,
                                  max_lines=990)
            if packet is not None and packet.truncated \
                    and time.time() < deadline:
                packet = build_packet(oracle, rel, coverage_target=coverage_target,
                                      max_lines=10 ** 9)   # cap gone, full sight
            if packet is None or time.time() > deadline:
                continue    # never spend an observer call on a dead deadline
            observations = rank_observations("\n".join(packet.src_lines),
                                             observer.observe([packet])[0], out)
            # a wrong rank-1 file must not starve every other candidate:
            # one file gets at most half the escalation budget (adversarial
            # review, 2026-08-31 — depth-first starvation)
            file_share = ((deadline - time.time()) / 2
                          if total_deadline is not None else escalate_budget / 2)
            before = open(os.path.join(oracle.root, rel), "rb").read()
            result = repair(oracle, rel, observations,
                            candidate_timeout=candidate_timeout,
                            deadline=min(deadline,
                                         time.time() + file_share))
            attempts += result.tried_log
            any_acts = any_acts or bool(result.acts_tried)
            if result.repaired:
                result.reason += " (engine law: CAPPED -> RAISE_BUDGET, depth-first)"
                clear_refusal(oracle.root)
                return GuardReport(status="repaired", file=rel, result=result,
                                   candidates=candidates,
                                   seconds=time.time() - t0, before=before)
            if result.ambiguous:
                return GuardReport(status="refused", file=rel,
                                   candidates=candidates, result=result,
                                   seconds=time.time() - t0,
                                   hint=result.reason, attempts=attempts)
        if any_acts and not hint and \
                decide(situation(REFUTED=True)) == "HARVEST_COUNTEREXAMPLE":
            hint = ("every generated candidate was rejected by the suite "
                    "(engine law: REFUTED -> HARVEST_COUNTEREXAMPLE) — "
                    "the refusal report lists what was tried; teach the "
                    "class or fix by hand")
    if not hint and acts0 and \
            decide(situation(REFUTED=True)) == "HARVEST_COUNTEREXAMPLE":
        hint = ("every generated candidate was rejected by the suite "
                "(engine law: REFUTED -> HARVEST_COUNTEREXAMPLE) — the "
                "refusal report lists each one with the test that killed it")
    return GuardReport(status="refused", candidates=candidates,
                       seconds=time.time() - t0, hint=hint,
                       attempts=attempts)


def propose_repair(root: str, report: GuardReport) -> tuple[str, str]:
    """--dry-run's propose-only channel: with the repaired file on disk,
    capture the broken->repaired unified diff, restore the tree byte-exactly
    to the broken state, and write the diff to .fluidfix/proposed.patch
    (`git apply`-ready from root). Returns (patch_path, diff_text)."""
    rel = report.file.replace(os.sep, "/")
    path = os.path.join(root, report.file)
    after = open(path, "rb").read()
    diff = None
    try:
        p = subprocess.run(["git", "-C", root, "diff", "--", rel],
                           capture_output=True, text=True, timeout=30)
        if p.returncode == 0 and p.stdout:
            diff = p.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    with open(path, "wb") as f:
        f.write(report.before)
    if diff is not None:
        # git diff is index->worktree, not broken->repaired: trust it only
        # if it applies to the restored broken tree (an uncommitted defect
        # breaks that identity)
        try:
            if subprocess.run(["git", "-C", root, "apply", "--check", "-"],
                              input=diff, capture_output=True, text=True,
                              timeout=30).returncode != 0:
                diff = None
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            diff = None
    if diff is None:
        import difflib
        diff = "".join(difflib.unified_diff(
            report.before.decode("utf-8").splitlines(keepends=True),
            after.decode("utf-8").splitlines(keepends=True),
            fromfile=f"a/{rel}", tofile=f"b/{rel}"))
    d = os.path.join(root, ".fluidfix")
    os.makedirs(d, exist_ok=True)
    patch = os.path.join(d, "proposed.patch")
    with open(patch, "w", encoding="utf-8", newline="") as f:
        f.write(diff)
    return patch, diff


def commit_repair(root: str, report: GuardReport) -> str:
    """Opt-in: commit a successful restoration (only the repaired file).
    Returns "committed", "clean" (restoration already matches HEAD — the
    defect was never committed), or "failed"."""
    if report.status != "repaired":
        return "failed"
    try:
        if subprocess.run(["git", "-C", root, "diff", "--quiet", "--",
                           report.file], timeout=30).returncode == 0:
            return "clean"
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return "failed"
    r = report.result
    msg = (f"fluidfix: restore {report.file}:{r.lineno}\n\n"
           f"- {r.old_line.strip()}\n+ {r.new_line.strip()}\n\n"
           f"Routed by the fluidfix kernel ({r.reason}); accepted by the "
           f"project's own suite in {r.suite_runs} runs.")
    try:
        subprocess.run(["git", "-C", root, "add", "--", report.file],
                       check=True, capture_output=True, timeout=30)
        subprocess.run(["git", "-C", root, "commit", "-m", msg],
                       check=True, capture_output=True, timeout=30)
        return "committed"
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired,
            FileNotFoundError):
        return "failed"


def clear_refusal(root: str) -> None:
    """write_refusal's counterpart: a green or repaired pass retires the
    stale teach-me signal (guard_once callers key on the file's existence)."""
    try:
        os.remove(os.path.join(root, ".fluidfix", "last_refusal.json"))
    except OSError:
        pass


def write_refusal(root: str, report: GuardReport) -> str:
    """A machine-readable teach-me signal, written where CI can pick it up."""
    d = os.path.join(root, ".fluidfix")
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, "last_refusal.json")
    json.dump({"status": report.status, "candidates": report.candidates,
               "seconds": report.seconds,
               "hint": report.hint or
                       "fault class is outside the taught vocabulary; "
                       "register() it once and its family becomes free",
               # engine law: REFUTED -> HARVEST_COUNTEREXAMPLE — what was
               # tried, and the exact failing test that rejected each
               "rejected_candidates": report.attempts[:200]},
              open(path, "w"), indent=1)
    return path
