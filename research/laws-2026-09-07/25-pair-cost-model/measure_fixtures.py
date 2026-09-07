#!/usr/bin/env python
"""Measure the single-edit candidate space on the shipped Python fixtures.

Builds each fixture in a temp dir under THIS agent's directory, asks the
real localiser for the real packet (one pytest run each -- these fixtures
are 4..800 lines and take ~1s), then counts candidates statically.

Run under the timeout wrapper:
  ./timeoutwrap.sh 300 /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python measure_fixtures.py
"""
from __future__ import annotations

import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
sys.path.insert(0, HERE)

from fluidfix.localize import build_packet  # noqa: E402
from fluidfix.oracle import Oracle  # noqa: E402

from count_candidates import pairs, report  # noqa: E402

PY = "/Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python"

# --- fixture sources, copied verbatim from the shipped tests ---------------
# tests/test_guard.py:8
GUARD_BUGGY = ("def count_above(xs, t):\n    n = 0\n    for x in xs:\n"
               "        if x >= t:\n            n += 1\n    return n\n")
GUARD_TEST = ("from mod import count_above\n\ndef test_c():\n"
              "    assert count_above([1, 5, 5, 9], 5) == 1\n")


def _span_budget_fixture():
    """tests/test_span_edits.py:191 -- 800 filler lines + a 6-line function."""
    import itertools
    names = ["".join(t) for t in itertools.product("abcdefghij", repeat=3)][:800]
    filler = [f"f_{n} = True" for n in names]
    fn = ["", "def tier(v, limit):", "    if v > limit:",
          "        return 1", "    return 0", ""]
    body = filler[:400] + fn + filler[400:]
    return "\n".join(body) + "\n", (
        "from mod import tier\n\ndef test_t():\n"
        "    assert tier(5, 5) == 1 and tier(4, 5) == 0\n")


FIXTURES = [
    ("tests/test_guard.py BUGGY (count_above, strictness)",
     GUARD_BUGGY, GUARD_TEST),
    ("tests/test_span_edits.py budget fixture (806-line mod.py)",
     *_span_budget_fixture()),
]


def main():
    os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    ns = []
    for tag, mod_src, test_src in FIXTURES:
        with tempfile.TemporaryDirectory(dir=HERE, prefix="fix_") as d:
            open(os.path.join(d, "mod.py"), "w").write(mod_src)
            open(os.path.join(d, "test_mod.py"), "w").write(test_src)
            oracle = Oracle(d, python=PY)
            pk = build_packet(oracle, "mod.py")
            if pk is None:
                print(f"--- {tag}\n    SUITE GREEN -- no packet"); continue
            print(f"    [packet mode={pk.mode} truncated={pk.truncated}]")
            n = report(tag, pk.src_lines, pk.lines, "mod.py", d,
                       secs_per_cand=None)
            ns.append((tag, n))
    print()
    print("=== fixture summary: n single-edit candidates -> C(n,2) pairs ===")
    for tag, n in ns:
        print(f"  {n:6d} -> {pairs(n):10d}   {tag}")


if __name__ == "__main__":
    main()
