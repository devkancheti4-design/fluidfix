#!/usr/bin/env python
"""On the `framed` fixture: what the coverage tier + SIGHT law WOULD rank if
the body consulted them when a traceback frame exists (today it returns the
framed files alone and never reaches the SIGHT branch).

Report-only prototype of the missing actuation: hand find_candidate_files
the same failing output with the frame's "pkg/api.py:" mention removed, so
the branch that measures the SIGHT byte per executed file runs, then put
the frame evidence back by hand for the FRAMED bit (the byte the law would
have seen). Runs pytest on a fresh copy under work/; edits nothing in src/.

    nice -n 15 ./tmo.sh 300 .venv/bin/python framed_widen.py
"""
import json
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")

import fluidfix.sight as sight_mod                       # noqa: E402
from fluidfix import Oracle                               # noqa: E402
from fluidfix.guard import find_candidate_files           # noqa: E402
from fluidfix.sight import BITS, sight                    # noqa: E402

RECORDED: dict[str, int] = {}
_real = sight_mod.observe_bits


def _rec(**kw):
    b = _real(**kw)
    rel = sys._getframe(1).f_locals.get("rel")
    if rel is not None:
        RECORDED[rel] = b
    return b


def bits_of(b):
    return "|".join(x for i, x in enumerate(BITS) if b >> i & 1) or "-"


def main():
    src = os.path.join(HERE, "fixtures", "framed")
    root = os.path.join(HERE, "work", "framed-widen")
    if os.path.isdir(root):
        shutil.rmtree(root)
    shutil.copytree(src, root)
    oracle = Oracle(root, python=sys.executable)
    fails, out = oracle.failing_output()
    assert fails
    # as the body sees it today
    ev: dict = {}
    today = find_candidate_files(oracle, out, evidence=ev)
    print(f"today (frame branch):   {today}  evidence={json.dumps(ev)}")

    # guard_once's escalation stage re-asks with limit=999 and grows CAPPED
    # only if that returns MORE files than the first pass. The frame branch
    # returns ordered[:limit], and `ordered` holds only files the traceback
    # named, so limit=999 changes nothing and RAISE_BUDGET re-searches the
    # same single wrong file.
    allf = find_candidate_files(oracle, out, limit=999)
    print(f"escalation (limit=999): {allf}  "
          f"capped0 grows? {len(allf) > len(today)}")

    # the frame mention blinded: the ONLY change is that "pkg/api.py:35:"
    # no longer matches the frame regex, so the coverage tier runs
    blinded = re.sub(r"pkg/api\.py[\":,]", "pkg/api_py ", out)
    sight_mod.observe_bits = _rec
    try:
        ev2: dict = {}
        widened = find_candidate_files(oracle, blinded, evidence=ev2)
    finally:
        sight_mod.observe_bits = _real
    print(f"coverage tier + SIGHT:  {widened}  evidence={json.dumps(ev2)}")
    print("per-file byte as measured on the blinded output, and the byte the "
          "law WOULD see with FRAMED restored for api.py:")
    for rel in widened:
        b = RECORDED.get(rel, 0)
        b_true = b | 1 if rel == "pkg/api.py" else b
        print(f"   {rel:<14} measured=0x{b:02x} {bits_of(b):<24} p={sight(b)}   "
              f"with FRAMED: 0x{b_true:02x} {bits_of(b_true):<24} p={sight(b_true)}")

    # Is the FRAMED lane reachable AT ALL in the branch where SIGHT runs?
    # guard.py:131-150 takes branch 1 whenever a mentioned .py path resolves
    # to an existing non-test file inside the root; only then is `ordered`
    # non-empty. guard.py:218 rebuilds framed_files from the SAME regex but
    # without the exists/not-a-test filter. So FRAMED can fire in branch 2
    # only when the failure names a path that does NOT resolve but whose
    # BASENAME matches a real source file. Rewrite the frame to a
    # non-existent directory and watch exactly that happen.
    ghost = out.replace("pkg/api.py", "zzz/api.py")
    sight_mod.observe_bits = _rec
    RECORDED.clear()
    try:
        ev3: dict = {}
        ghosted = find_candidate_files(oracle, ghost, evidence=ev3)
    finally:
        sight_mod.observe_bits = _real
    print("\nFRAMED reachability inside the SIGHT branch "
          "(frame rewritten to a non-existent zzz/api.py):")
    print(f"   order={ghosted}  evidence={json.dumps(ev3)}")
    for rel in ghosted:
        b = RECORDED.get(rel, 0)
        print(f"   {rel:<14} byte=0x{b:02x} {bits_of(b):<34} p={sight(b)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
