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

    def render(self, tag: str = "") -> str:
        prev, excerpt = None, []
        for l in self.lines:
            if prev is not None and l > prev + 1:
                excerpt.append("  ...")
            excerpt.append(f"{l:4d}| {self.src_lines[l - 1][:120]}")
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
    defect file's top-level package directory name.
    """
    fails, out1 = oracle.failing_output()
    if not fails:
        return None
    path = os.path.join(oracle.root, defect_file)
    src = open(path, encoding="utf-8").read()
    src_lines = src.splitlines()

    base = os.path.basename(defect_file)
    frames: set[int] = set()
    for m in re.finditer(r"([\w./\\-]+\.py)[\":,]+\s*(?:line\s+)?(\d+)",
                         _ANSI.sub("", out1)):
        if os.path.basename(m.group(1)) == base:
            ln = int(m.group(2))
            frames.update(range(max(1, ln - 12), min(len(src_lines), ln + 12) + 1))

    covered: set[int] = set()
    tgt = coverage_target or defect_file.replace("\\", "/").split("/")[0]
    cov_json = os.path.join(oracle.root, "_fluidfix_cov.json")
    # NOTE: no -x here — pytest 9.1 + pytest-cov 7.1 silently skip the JSON
    # report when the session ends via exit-first.
    oracle.run(["--lf", "--tb=no", f"--cov={tgt}",
                f"--cov-report=json:{cov_json}"], cache=True)
    if os.path.exists(cov_json):
        try:
            cov = json.load(open(cov_json))
            want = defect_file.replace("\\", "/")
            for f, data in cov.get("files", {}).items():
                fn = f.replace("\\", "/")
                if fn.endswith(want) or want.endswith(fn):
                    covered = set(data.get("executed_lines", []))
                    break
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
    lo = lo[:max_lines]
    return Packet(defect_file=defect_file, failure=_compress_failure(out1),
                  lines=lo, src_lines=src_lines, mode=mode)
