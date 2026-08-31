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

import json
import os
import re
import subprocess
import time
from dataclasses import dataclass, field

from .localize import build_packet
from .loop import RepairResult, repair
from .oracle import Oracle

__all__ = ["GuardReport", "find_candidate_files", "guard_once"]

_ANSI = re.compile(r"\x1b\[[0-9;]*m")


@dataclass
class GuardReport:
    status: str                       # "green" | "repaired" | "refused"
    file: str | None = None
    result: RepairResult | None = None
    candidates: list[str] = field(default_factory=list)
    seconds: float = 0.0

    hint: str = ""

    def summary(self) -> str:
        if self.status == "green":
            return "suite green — nothing to do"
        if self.status == "repaired":
            return f"{self.file}: {self.result.summary()}"
        base = ("REFUSED: fault is outside the taught vocabulary "
                f"(candidate files tried: {', '.join(self.candidates) or 'none found'}). "
                "Teach the class once — register() an observation + transform — "
                "and its whole family becomes free.")
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


def _has_pytest_cov(oracle: Oracle) -> bool:
    try:
        return subprocess.run([oracle.python, "-c", "import pytest_cov"],
                              capture_output=True, timeout=30).returncode == 0
    except Exception:
        return False


def guard_once(oracle: Oracle, observer, files: list[str] | None = None,
               coverage_target: str | None = None,
               candidate_timeout: int | None = None) -> GuardReport:
    t0 = time.time()
    fails, out = oracle.failing_output()
    if not fails:
        return GuardReport(status="green", seconds=time.time() - t0)
    candidates = files or find_candidate_files(oracle, out)
    hint = ""
    if not candidates and not _has_pytest_cov(oracle):
        hint = ("pytest-cov is not installed in the target interpreter, so "
                "coverage-based localisation was unavailable — install it "
                f"({oracle.python} -m pip install pytest-cov) and re-run; "
                "on large codebases it is how the fault file gets found.")
    for rel in candidates:
        packet = build_packet(oracle, rel, coverage_target=coverage_target)
        if packet is None:
            continue
        observations = observer.observe([packet])[0]
        result = repair(oracle, rel, observations,
                        candidate_timeout=candidate_timeout)
        if result.repaired:
            return GuardReport(status="repaired", file=rel, result=result,
                               candidates=candidates,
                               seconds=time.time() - t0)
    return GuardReport(status="refused", candidates=candidates,
                       seconds=time.time() - t0, hint=hint)


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


def write_refusal(root: str, report: GuardReport) -> str:
    """A machine-readable teach-me signal, written where CI can pick it up."""
    d = os.path.join(root, ".fluidfix")
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, "last_refusal.json")
    json.dump({"status": report.status, "candidates": report.candidates,
               "seconds": report.seconds,
               "hint": report.hint or
                       "fault class is outside the taught vocabulary; "
                       "register() it once and its family becomes free"},
              open(path, "w"), indent=1)
    return path
