#!/usr/bin/env python
"""Probe, without running the guard, that

  (1) the suite is red as built;
  (2) exactly TWO single-line edits inside fluidfix's own act vocabulary
      turn it green -- LINE_A (compensating) and LINE_B (the true repair);
  (3) build_packet at the guard's pass-0 budget reports truncated=True
      (that is the CAPPED bit guard.py:508 latches) and its anchor list
      contains LINE_A but NOT LINE_B;
  (4) build_packet at full sight reports truncated=False and contains BOTH.

Run:  python probe_packet.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "fixture")
REL = "pkg/geom.py"
PATH = os.path.join(ROOT, REL)

sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix.localize import build_packet          # noqa: E402
from fluidfix.oracle import Oracle                  # noqa: E402

oracle = Oracle(ROOT, python=sys.executable, timeout=120)
src = open(PATH, encoding="utf-8", newline="").read()
raw = src.split("\n")
LINE_B = raw.index("    return min(low, high)") + 1
LINE_A = raw.index("    return ceiling + peak(low, high)") + 1
print(f"LINE_A (compensating site) = {LINE_A}   {raw[LINE_A-1]!r}")
print(f"LINE_B (true defect)       = {LINE_B}   {raw[LINE_B-1]!r}")


def with_line(n, text):
    new = raw[:]
    new[n - 1] = text
    open(PATH, "w", encoding="utf-8", newline="").write("\n".join(new))


try:
    print("\n--- (1) suite as built ---")
    print("green?", oracle.green())

    print("\n--- (2) the two greens ---")
    for n, text, tag in (
            (LINE_B, "    return max(low, high)", "TRUE repair (kind 8 min->max)"),
            (LINE_A, "    return ceiling - peak(low, high)",
             "COMPENSATING (kind 3 additive flip)"),
            (LINE_A, "    return peak(low, high) + ceiling",
             "control: kind 2 swap at LINE_A"),
    ):
        with_line(n, text)
        ok, why = oracle.check(timeout=120)
        print(f"  line {n:3d}  {tag:38}  green={ok}")
        open(PATH, "w", encoding="utf-8", newline="").write(src)

    print("\n--- (3) pass-0 packet (max_lines=110, the guard's default) ---")
    p0 = build_packet(oracle, REL)
    print(f"  truncated = {p0.truncated}   (CAPPED, latched at guard.py:508)")
    print(f"  anchors kept = {len(set(p0.lines))} distinct: {sorted(set(p0.lines))}")
    print(f"  LINE_A in packet? {LINE_A in p0.lines}")
    print(f"  LINE_B in packet? {LINE_B in p0.lines}   <-- never observed")

    print("\n--- (4) full-sight packet (max_lines=10**9) ---")
    p1 = build_packet(oracle, REL, max_lines=10 ** 9)
    print(f"  truncated = {p1.truncated}")
    print(f"  anchors = {len(p1.lines)}")
    print(f"  LINE_A in packet? {LINE_A in p1.lines}")
    print(f"  LINE_B in packet? {LINE_B in p1.lines}")
finally:
    open(PATH, "w", encoding="utf-8", newline="").write(src)
    oracle.clear_pyc()
