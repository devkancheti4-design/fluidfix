# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 devkancheti4-design
"""Java/JUnit support: a Maven oracle behind the SAME contract surface the
repair loop already speaks — so repair(), SpanEdit, AMB refusal, deadlines,
and the per-candidate failure harvest are REUSED, not reimplemented. The
kernels route integers and edit lines of text; they never knew what Python
was, and they don't need to know what Java is.

    green  -> mvn test exits 0
    red    -> failing test classes parsed from Surefire output; stack-trace
              frames give file:line; JUnit naming convention (FooTest/TestFoo
              <-> Foo.java) gives the affinity fallback for pure assertion
              failures whose traces never leave the test class
    check  -> FAIL-FAST, FULL-CONFIRM: candidates first face only the failing
              test classes (-Dtest=...); only a candidate that clears them
              runs the full suite, which remains the only acceptance gate
"""
from __future__ import annotations

import os
import re
import subprocess
import time

from .localize import Packet, _compress_failure

__all__ = ["JavaOracle", "find_candidate_files_java", "build_packet_java",
           "jguard_once"]

_FRAME = re.compile(r"\(([\w$]+\.java):(\d+)\)")
_FAILTEST = re.compile(r"^\[ERROR\]\s+([\w.$]+)\.(\w+):(\d+)", re.M)
_FAILCLASS = re.compile(r"Tests run:.*?FAILURE.*?in ([\w.$]+)|^\[ERROR\].*?in ([\w.$]+)$", re.M)


class JavaOracle:
    """Duck-typed to what loop.repair() needs: root, timeout, green(),
    check(), clear_pyc(). failing_output() mirrors the pytest oracle."""

    def __init__(self, root: str, mvn: str = "mvn", timeout: int = 600,
                 java_home: str | None = None):
        self.root = os.path.abspath(root)
        self.mvn, self.timeout = mvn, timeout
        self.java_home = java_home or os.environ.get("JAVA_HOME")
        self._fail_classes: list[str] = []

    def run(self, extra: list[str] | None = None,
            timeout: int | None = None) -> tuple[int, str]:
        env = dict(os.environ)
        if self.java_home:
            env["JAVA_HOME"] = self.java_home
        cmd = [self.mvn, "-q", "-B", "test", "-DfailIfNoTests=false"] + (extra or [])
        try:
            p = subprocess.run(cmd, cwd=self.root, capture_output=True,
                               text=True, errors="replace",
                               timeout=timeout or self.timeout, env=env)
            return p.returncode, p.stdout + p.stderr
        except subprocess.TimeoutExpired:
            return 1, "TIMEOUT"

    def _reports_text(self) -> str:
        out = []
        d = os.path.join(self.root, "target", "surefire-reports")
        if os.path.isdir(d):
            for fn in sorted(os.listdir(d)):
                if fn.endswith(".txt"):
                    try:
                        out.append(open(os.path.join(d, fn), encoding="utf-8",
                                        errors="replace").read())
                    except OSError:
                        pass
        return "\n".join(out)

    def failing_output(self) -> tuple[bool, str]:
        rc, out = self.run()
        if rc == 0:
            self._fail_classes = []
            return False, out
        out = out + "\n" + self._reports_text()
        classes: list[str] = []
        for m in _FAILTEST.finditer(out):
            cls = m.group(1).split(".")[-1].split("$")[0]
            if cls not in classes:
                classes.append(cls)
        for m in _FAILCLASS.finditer(out):
            cls = (m.group(1) or m.group(2) or "").split(".")[-1].split("$")[0]
            if cls and cls not in classes:
                classes.append(cls)
        self._fail_classes = classes[:10]
        return True, out

    def green(self, timeout: int | None = None) -> bool:
        rc, _ = self.run(timeout=timeout)
        return rc == 0

    def check(self, timeout: int | None = None) -> tuple[bool, str]:
        def _why(out: str) -> str:
            why = next((l.strip() for l in out.splitlines()
                        if l.startswith("[ERROR]") and
                        (".java" in l or re.search(r":\d+", l))), "")
            if not why:
                why = next((l.strip() for l in out.splitlines()
                            if "ERROR" in l or "FAIL" in l), "suite red")
            return why[:200]

        if self._fail_classes:                       # fail-fast gate
            rc, out = self.run(["-Dtest=" + ",".join(self._fail_classes)],
                               timeout=timeout)
            if rc != 0:
                return False, _why(out)
        rc, out = self.run(timeout=timeout)          # the only acceptance gate
        return (True, "") if rc == 0 else (False, _why(out))

    def clear_pyc(self) -> None:                     # maven recompiles itself
        pass


def _java_sources(root: str) -> dict[str, str]:
    """basename -> repo-relative path, MAIN sources only (tests excluded)."""
    out: dict[str, str] = {}
    for dp, dn, fns in os.walk(root):
        dn[:] = [d for d in dn if d not in (".git", "target", "node_modules")]
        rel_dp = os.path.relpath(dp, root).replace("\\", "/")
        if "/test/" in f"/{rel_dp}/":
            continue
        for fn in fns:
            if fn.endswith(".java"):
                out.setdefault(fn, f"{rel_dp}/{fn}".lstrip("./"))
    return out


def find_candidate_files_java(oracle: JavaOracle, failing_output: str,
                              limit: int = 5) -> list[str]:
    """Stack-trace frames first (deepest-in-main-source preferred), then the
    JUnit naming convention: FooTest / TestFoo names Foo.java."""
    srcs = _java_sources(oracle.root)
    ordered: list[str] = []
    for m in _FRAME.finditer(failing_output):
        rel = srcs.get(m.group(1))
        if rel and rel not in ordered:
            ordered.append(rel)
    for cls in oracle._fail_classes:
        base = re.sub(r"Tests?$|^Test", "", cls)
        for cand in (f"{base}.java",):
            rel = srcs.get(cand)
            if rel and rel not in ordered:
                ordered.append(rel)
    return ordered[:limit]


def build_packet_java(oracle: JavaOracle, defect_file: str,
                      failing_output: str, max_lines: int = 110) -> Packet | None:
    """Frames in this file (±12 lines each) when the trace names it; else
    every code line, signal-filtered and spread-sampled — same Packet type,
    same truncation semantics the engine law's CAPPED ruling reads."""
    path = os.path.join(oracle.root, defect_file)
    try:
        src = open(path, encoding="utf-8", newline="").read()
    except OSError:
        return None
    src_lines = src.split("\n")
    base = os.path.basename(defect_file)
    frames: set[int] = set()
    for m in _FRAME.finditer(failing_output):
        if m.group(1) == base:
            ln = int(m.group(2))
            frames.update(range(max(1, ln - 12),
                                min(len(src_lines), ln + 12) + 1))
    lo = sorted(frames) if frames else [
        i + 1 for i, l in enumerate(src_lines)
        if l.strip() and not l.lstrip().startswith(("//", "*", "/*", "import ",
                                                    "package "))]
    filtered = False
    if len(lo) > max_lines - 30:
        sig = re.compile(r"[<>]=?|\d|\s[-+*/]\s|&&|\|\||true|false")
        kept = [l for l in lo if sig.search(src_lines[l - 1])] or lo
        filtered = len(kept) < len(lo)
        lo = kept
    truncated = len(lo) > max_lines or filtered
    if len(lo) > max_lines:
        stride = len(lo) / max_lines
        lo = [lo[int(i * stride)] for i in range(max_lines)]
    return Packet(defect_file=defect_file,
                  failure=_compress_failure(failing_output),
                  lines=lo, src_lines=src_lines,
                  mode="frames" if frames else "affinity",
                  truncated=truncated)


def jguard_once(oracle: JavaOracle, observer, candidate_timeout=None,
                budget: int | None = None):
    """One Java guard pass. Same shape as guard_once's first pass; the
    engine-law escalation ladder arrives with the coverage tier (JaCoCo)."""
    from .guard import GuardReport
    from .loop import repair

    t0 = time.time()
    deadline = t0 + budget if budget else None
    fails, out = oracle.failing_output()
    if not fails:
        return GuardReport(status="green", seconds=time.time() - t0)
    candidates = find_candidate_files_java(oracle, out)
    attempts: list = []
    for rel in candidates:
        if deadline is not None and time.time() > deadline:
            return GuardReport(status="refused", candidates=candidates,
                               seconds=time.time() - t0, attempts=attempts,
                               hint=f"--budget exhausted ({budget}s)")
        packet = build_packet_java(oracle, rel, out)
        if packet is None:
            continue
        observations = observer.observe([packet])[0]
        result = repair(oracle, rel, observations,
                        candidate_timeout=candidate_timeout, deadline=deadline)
        attempts += result.tried_log
        if result.repaired:
            return GuardReport(status="repaired", file=rel, result=result,
                               candidates=candidates, seconds=time.time() - t0)
        if result.ambiguous:
            return GuardReport(status="refused", file=rel, result=result,
                               candidates=candidates, seconds=time.time() - t0,
                               hint=result.reason, attempts=attempts)
    return GuardReport(status="refused", candidates=candidates,
                       seconds=time.time() - t0, attempts=attempts)
