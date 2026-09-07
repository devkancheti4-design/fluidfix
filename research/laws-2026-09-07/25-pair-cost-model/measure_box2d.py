#!/usr/bin/env python
"""Single-edit candidate counts on Box2D src/contact_solver.c, three regimes.

  A  whole file, uncapped        -- the candidate space the shipped
                                    vocabulary can express on that file
  B  the packet the body really  -- build_packet_c(max_lines=110), affinity
     builds, no gcov                mode (no frames, no coverage)
  C  the packet with gcov        -- build_packet_c(covered=<executed lines>)
                                    if a coverage set is supplied

Plus a repo-wide sweep: per-file capped counts over every Box2D .c/.h the
guard would consider, so the 38-file / 1,063-candidate figure recorded on
the project's games page can be checked for scale.

Run under the timeout wrapper.
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
sys.path.insert(0, HERE)

from fluidfix.coracle import _c_sources, build_packet_c  # noqa: E402

from count_candidates import enumerate_candidates, pairs, report  # noqa: E402

ROOT = os.path.join(HERE, "box2d_copy")
REL = "src/contact_solver.c"

# Failing output of the recorded refusal: the failing tests name no source
# file at all (coracle.py:317-320), so no frame can point into any file.
FAILING = ("test failed: MultithreadingTest\n"
           "test failed: DeterminismTest\n")


class _StubOracle:
    """build_packet_c touches only .root."""
    def __init__(self, root):
        self.root = root


def code_lines(src_lines):
    """The uncapped 'affinity' line list build_packet_c falls back to."""
    return [i + 1 for i, l in enumerate(src_lines)
            if l.strip() and not l.lstrip().startswith(
                ("//", "*", "/*", "#include", "#ifndef", "#define",
                 "#endif", "#ifdef"))]


def main():
    o = _StubOracle(ROOT)
    src = open(os.path.join(ROOT, REL), encoding="utf-8", newline="").read()
    src_lines = src.split("\n")

    print("=" * 74)
    print("A. WHOLE FILE, UNCAPPED (no 110-line packet cap)")
    all_code = code_lines(src_lines)
    nA = report("A contact_solver.c uncapped", src_lines, all_code, REL, ROOT)

    print()
    print("=" * 74)
    print("B. THE PACKET THE BODY ACTUALLY BUILDS (build_packet_c, no gcov)")
    pk = build_packet_c(o, REL, FAILING)
    print(f"    [packet mode={pk.mode} truncated={pk.truncated} "
          f"lines={len(pk.lines)}]")
    nB = report("B contact_solver.c, packet-capped", pk.src_lines, pk.lines,
                REL, ROOT)

    nC = None
    covjson = os.path.join(HERE, "coverage.json")
    if os.path.exists(covjson):
        cov = json.load(open(covjson))
        lines = set(cov.get(REL, []))
        if lines:
            print()
            print("=" * 74)
            print(f"C. THE PACKET WITH GCOV COVERAGE ({len(lines)} executed lines)")
            pkc = build_packet_c(o, REL, FAILING, covered=lines)
            print(f"    [packet mode={pkc.mode} truncated={pkc.truncated} "
                  f"lines={len(pkc.lines)}]")
            nC = report("C contact_solver.c, coverage-anchored",
                        pkc.src_lines, pkc.lines, REL, ROOT)

    print()
    print("=" * 74)
    print("D. REPO-WIDE SWEEP: capped candidate count per Box2D source file")
    srcs = _c_sources(ROOT)
    tot = 0
    rows = []
    # exclude this agent's own build/covbuild trees: _c_sources skips only
    # the FAST build dir, so once the gcov tier has run its `covbuild` tree
    # is walked as production source (see covbuild_leak.py -- reported
    # separately as a defect, kept out of the honest repo-wide count here).
    for rel in sorted(r for r in set(srcs.values())
                      if not r.startswith(("build/", "covbuild/"))):
        try:
            sl = open(os.path.join(ROOT, rel), encoding="utf-8",
                      newline="").read().split("\n")
        except OSError:
            continue
        p = build_packet_c(o, rel, FAILING)
        if p is None:
            continue
        n, _, _, _, _ = enumerate_candidates(sl, p.lines, rel, ROOT)
        rows.append((n, rel))
        tot += n
    rows.sort(reverse=True)
    print(f"    files considered                   : {len(rows)}")
    print(f"    total single-edit candidates       : {tot}")
    print(f"    mean per file                      : {tot / max(1, len(rows)):.1f}")
    print(f"    top 12 files:")
    for n, rel in rows[:12]:
        print(f"      {n:5d}  {rel}")
    for k in (38, len(rows)):
        top = sum(n for n, _ in rows[:k])
        print(f"    sum over the {k:3d} richest files       : {top}"
              f"   -> C(n,2) = {pairs(top):,}")

    print()
    print("=" * 74)
    print("SUMMARY  n -> C(n,2)")
    for tag, n in (("A uncapped whole file", nA),
                   ("B packet-capped (what the body does)", nB),
                   ("C coverage-anchored", nC)):
        if n is not None:
            print(f"  {n:6d} -> {pairs(n):12,d}   {tag}")
    print(f"  {tot:6d} -> {pairs(tot):12,d}   D whole Box2D src, packet-capped")


if __name__ == "__main__":
    main()
