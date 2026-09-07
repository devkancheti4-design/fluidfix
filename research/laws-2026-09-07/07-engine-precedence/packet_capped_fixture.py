#!/usr/bin/env python
"""07-engine-precedence: does a green found under a TRUNCATED packet ship as
BUILT alone (CAPPED measured at guard.py:508 but not delivered to loop.py:217)?

Shape: the real defect (`>` for `>=` in grade()) sits at the END of a long
covered file, outside the round-1 spread sample; a compensating site
(`return grade(v - 0, limit)` -> kind-1 decrement -> `v - -1` == v + 1)
sits at the TOP, inside the sample. Fillers `f_x = x and y` pass the packet's
signal filter (\\band\\b) but match no KINDS regex, so they cost no suite runs.

Run (one real suite run, under nice + the timeout shim next to this file):
    cd <this dir> && nice -n 15 ./timeout.sh 300 \\
        /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python packet_capped_fixture.py
"""
import itertools
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix import MechanicalObserver, Oracle, guard_once      # noqa: E402
from fluidfix.engine import decide, situation                     # noqa: E402
from fluidfix.localize import build_packet                        # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE / "fixture-packet-capped"
COMPENSATOR = "    return grade(v - 0, limit)"
BUG = "    if v > limit:"
TRUE_FIX = "    if v >= limit:"


def layout(n_filler: int) -> tuple[list[str], int, int]:
    names = ["".join(t) for t in itertools.product("abcdefghij", repeat=3)][:n_filler]
    body = ["x = None", "y = None", "",
            "def tier(v, limit):", COMPENSATOR, ""]
    comp_lineno = body.index(COMPENSATOR) + 1
    body += [f"f_{n} = x and y" for n in names]
    body += ["", "def grade(v, limit):", BUG, "        return 1", "    return 0", ""]
    bug_lineno = len(body) - 3
    assert body[bug_lineno - 1] == BUG and body[comp_lineno - 1] == COMPENSATOR
    return body, comp_lineno, bug_lineno


if ROOT.exists():
    shutil.rmtree(ROOT)
ROOT.mkdir()
(ROOT / "test_mod.py").write_text(
    "from mod import tier\n\ndef test_t():\n"
    "    assert tier(5, 5) == 1 and tier(4, 5) == 0\n")
oracle = Oracle(str(ROOT), python=sys.executable)

placed = None
for n_filler in range(800, 830):
    body, comp_lineno, bug_lineno = layout(n_filler)
    (ROOT / "mod.py").write_text("\n".join(body) + "\n")
    pk = build_packet(oracle, "mod.py")
    if pk is None:
        print("packet is None (no coverage?)"); sys.exit(2)
    ok = pk.truncated and comp_lineno in pk.lines and bug_lineno not in pk.lines
    print(f"fillers={n_filler:3d} truncated={pk.truncated} sampled={len(pk.lines)} "
          f"compensator@{comp_lineno} in sample={comp_lineno in pk.lines} "
          f"bug@{bug_lineno} in sample={bug_lineno in pk.lines}")
    if ok:
        placed = (n_filler, comp_lineno, bug_lineno)
        break
if placed is None:
    print("could not place: compensator in sample AND bug outside sample"); sys.exit(3)

src_before = (ROOT / "mod.py").read_text()
print(f"\nround-1 packet CAPPED (packet.truncated) = {pk.truncated}  "
      f"<- guard.py:508 measures this")
print("law on the byte the guard HOLDS  BUILT+CAPPED ->",
      decide(situation(BUILT=True, CAPPED=True)))
print("law on the byte loop.py:217 ASKS BUILT        ->",
      decide(situation(BUILT=True)))

report = guard_once(oracle, MechanicalObserver())
print(f"\nguard_once status = {report.status}")
res = report.result
if res is not None:
    print(f"  suite_runs   = {res.suite_runs}")
    print(f"  lineno       = {res.lineno}")
    print(f"  old_line     = {res.old_line!r}")
    print(f"  new_line     = {res.new_line!r}")
    print(f"  greens       = {res.greens}")
    print(f"  reason       = {res.reason}")
print(f"  hint         = {report.hint!r}")
src_after = (ROOT / "mod.py").read_text()
lines_after = src_after.split("\n")
print(f"\ntree changed        = {src_after != src_before}")
print(f"real bug still there = {lines_after[placed[2] - 1] == BUG}   "
      f"(line {placed[2]}: {lines_after[placed[2] - 1]!r})")
print(f"compensator shipped  = {lines_after[placed[1] - 1] != COMPENSATOR}   "
      f"(line {placed[1]}: {lines_after[placed[1] - 1]!r})")
print(f"suite green now      = {oracle.green()}")
