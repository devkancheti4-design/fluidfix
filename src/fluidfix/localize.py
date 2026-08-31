# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 devkancheti4-design
# Commercial licensing: see COMMERCIAL.md.
"""Mechanical localisation: build a lean observation packet at zero tokens.

Anchor lines in the defect file are the union of
  frames    traceback frames the failure quotes in the defect file
            (precise for import/syntax faults), and
  coverage  the lines the failing test actually executed (pytest --lf under
            pytest-cov — for any runtime fault, the defective line is in
            this set), each expanded to its enclosing simple-statement span,
            because line-granular coverage never marks the continuation
            lines of a multi-line statement.

On the 33-bug benchmark corpus this captured the true defective line in the
packet for 33/33 bugs, at a mean packet size of ~1,060 tokens. The packet is
what an observer sees; nothing else about the project leaves the machine.
"""
from __future__ import annotations

import ast
import json
import os
import re
from dataclasses import dataclass

from .oracle import Oracle

__all__ = ["Packet", "build_packet"]

_ANSI = re.compile(r"\x1b\[[0-9;]*m")


@dataclass
class Packet:
    defect_file: str          # path relative to the project root
    failure: str              # compressed failing-suite output
    lines: list[int]          # 1-based anchor lines, sorted
    src_lines: list[str]      # full defect-file lines (1-based indexing -1)
    mode: str                 # "frames", "coverage", or "frames+coverage"
    truncated: bool = False   # a budget cut anchor lines (engine law: CAPPED)

    def render(self, tag: str = "") -> str:
        prev, excerpt = None, []
        for l in self.lines:
            if prev is not None and l > prev + 1:
                excerpt.append("  ...")
            excerpt.append(f"{l:4d}| {self.src_lines[l - 1].rstrip(chr(13))[:120]}")
            prev = l
        head = (f"### {tag or 'BUG'}  defect file: {self.defect_file}  "
                f"(showing only the {len(self.lines)} lines the failing test "
                f"executed; localisation mode: {self.mode})")
        return (f"{head}\n--- failing suite output (compressed) ---\n{self.failure}\n"
                f"--- executed defect-file lines ---\n" + "\n".join(excerpt))


def _compress_failure(out: str) -> str:
    out = _ANSI.sub("", out)
    lines = out.splitlines()
    starts = [i for i, l in enumerate(lines)
              if l.startswith("____") or re.match(r"=+ ERRORS", l)]
    if starts:
        lines = lines[starts[-1]:]
    keep = [l[:120] for l in lines
            if l.startswith(("E ", ">", "____", "FAILED", "ERROR"))
            or ".py:" in l or l.strip().startswith("assert")]
    txt = "\n".join(keep) or "\n".join(l[:120] for l in lines[-14:])
    if len(txt) > 800:
        txt = txt[:300] + "\n  ...\n" + txt[-450:]
    return txt


def _statement_spans(src: str) -> dict[int, tuple[int, int]]:
    spans: dict[int, tuple[int, int]] = {}
    SIMPLE = (ast.Assign, ast.AugAssign, ast.AnnAssign, ast.Expr, ast.Return,
              ast.Raise, ast.Assert, ast.Import, ast.ImportFrom, ast.Delete)
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return spans
    for node in ast.walk(tree):
        if isinstance(node, SIMPLE) and node.end_lineno - node.lineno <= 40:
            for l in range(node.lineno, node.end_lineno + 1):
                spans.setdefault(l, (node.lineno, node.end_lineno))
    return spans


def build_packet(oracle: Oracle, defect_file: str, coverage_target: str | None = None,
                 max_lines: int = 110) -> Packet | None:
    """Build a lean packet, or None if the suite is green (nothing to observe).

    coverage_target: the --cov target (package name or path); defaults to the
    defect file's top-level package directory, or its module name for a
    root-level file.
    """
    fails, out1 = oracle.failing_output()
    if not fails:
        return None
    path = os.path.join(oracle.root, defect_file)
    with open(path, encoding="utf-8", newline="") as f:
        src = f.read()
    # split on "\n" only: CRLF keeps its "\r" as line content, and form feeds
    # stay inside lines, so numbering matches the tokenizer and coverage.
    src_lines = src.split("\n")

    want = defect_file.replace("\\", "/")

    def _is_defect_path(p: str) -> bool:
        p = p.replace("\\", "/")
        return p == want or p.endswith("/" + want) or want.endswith("/" + p)

    # traceback frames: prefer path-boundary matches; fall back to basename
    # only if no boundary match exists anywhere in the output (a same-named
    # file elsewhere must not inject its line numbers).
    clean = _ANSI.sub("", out1)
    hits = re.findall(r"([\w./\\-]+\.py)[\":,]+\s*(?:line\s+)?(\d+)", clean)
    strong = [(p, ln) for p, ln in hits if _is_defect_path(p)]
    if not strong:
        base = os.path.basename(want)
        strong = [(p, ln) for p, ln in hits if os.path.basename(p) == base]
    frames: set[int] = set()
    for _, ln in strong:
        ln = int(ln)
        frames.update(range(max(1, ln - 12), min(len(src_lines), ln + 12) + 1))

    covered: set[int] = set()
    if coverage_target:
        tgt = coverage_target
    else:
        seg = want.split("/")[0]
        # a root-level defect file is a module: --cov takes its module name,
        # not the filename (--cov=mod.py silently collects nothing)
        tgt = seg[:-3] if seg.endswith(".py") else seg
    cov_json = os.path.join(oracle.root, "_fluidfix_cov.json")
    # NOTE: no -x here — pytest 9.1 + pytest-cov 7.1 silently skip the JSON
    # report when the session ends via exit-first.
    oracle.run(["--lf", "--tb=no", f"--cov={tgt}",
                f"--cov-report=json:{cov_json}"], cache=True)
    if os.path.exists(cov_json):
        try:
            cov = json.load(open(cov_json))
            files = cov.get("files", {})
            # exact relative path first; then path-boundary suffix — a bare
            # endswith lets mypkg/core.py shadow pkg/core.py entirely
            match = next((f for f in files
                          if f.replace("\\", "/") == want), None)
            if match is None:
                match = next((f for f in files if _is_defect_path(f)), None)
            if match is not None:
                covered = set(files[match].get("executed_lines", []))
        finally:
            os.remove(cov_json)

    spans = _statement_spans(src)
    expanded = set(covered)
    for l in covered:
        if l in spans:
            expanded.update(range(spans[l][0], spans[l][1] + 1))

    mode = ("frames+coverage" if frames and expanded else
            "frames" if frames else "coverage")
    lo = [l for l in sorted(frames | expanded) if 1 <= l <= len(src_lines)]
    if len(lo) > max_lines - 30:
        sig = re.compile(r"[<>]=?|\d|\s[-+*/]\s|\band\b|\bor\b|\bTrue\b|\bFalse\b")
        lo = [l for l in lo if sig.search(src_lines[l - 1])] or lo
    truncated = len(lo) > max_lines
    if truncated:
        # SPREAD-sample rather than truncate: taking the FIRST max_lines was
        # measured (Click, seeded bench) to cut defects that sit late in big
        # files out of the packet entirely. A stride keeps whole-file reach.
        stride = len(lo) / max_lines
        lo = [lo[int(i * stride)] for i in range(max_lines)]
    return Packet(defect_file=defect_file, failure=_compress_failure(out1),
                  lines=lo, src_lines=src_lines, mode=mode, truncated=truncated)
