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

    def summary(self) -> str:
        if self.status == "green":
            return "suite green — nothing to do"
        if self.status == "repaired":
            return f"{self.file}: {self.result.summary()}"
        return ("REFUSED: fault is outside the taught vocabulary "
                f"(candidate files tried: {', '.join(self.candidates) or 'none found'}). "
                "Teach the class once — register() an observation + transform — "
                "and its whole family becomes free.")


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
    # no source frames (pure assertion failure): rank by the failing test's
    # own coverage — run recorded by the caller's failing_output(), so --lf
    # re-runs exactly it. No -x: exit-first suppresses the JSON report.
    cov_json = os.path.join(oracle.root, "_fluidfix_guard_cov.json")
    oracle.run(["--lf", "--tb=no", "--cov=.",
                f"--cov-report=json:{cov_json}"], cache=True)
    ranked: list[tuple[int, str]] = []
    if os.path.exists(cov_json):
        try:
            cov = json.load(open(cov_json))
            for f, data in cov.get("files", {}).items():
                rel = f.replace("\\", "/")
                if _is_test_path(rel) or not rel.endswith(".py"):
                    continue
                ranked.append((len(data.get("executed_lines", [])), rel))
        finally:
            os.remove(cov_json)
    ranked.sort(reverse=True)
    return [rel for _, rel in ranked[:limit]]


def guard_once(oracle: Oracle, observer, files: list[str] | None = None,
               coverage_target: str | None = None,
               candidate_timeout: int | None = None) -> GuardReport:
    t0 = time.time()
    fails, out = oracle.failing_output()
    if not fails:
        return GuardReport(status="green", seconds=time.time() - t0)
    candidates = files or find_candidate_files(oracle, out)
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
                       seconds=time.time() - t0)


def commit_repair(root: str, report: GuardReport) -> bool:
    """Opt-in: commit a successful restoration. Only the repaired file."""
    if report.status != "repaired":
        return False
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
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired,
            FileNotFoundError):
        return False


def write_refusal(root: str, report: GuardReport) -> str:
    """A machine-readable teach-me signal, written where CI can pick it up."""
    d = os.path.join(root, ".fluidfix")
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, "last_refusal.json")
    json.dump({"status": report.status, "candidates": report.candidates,
               "seconds": report.seconds,
               "hint": "fault class is outside the taught vocabulary; "
                       "register() it once and its family becomes free"},
              open(path, "w"), indent=1)
    return path
