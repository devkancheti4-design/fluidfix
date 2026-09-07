#!/usr/bin/env python
"""MEASURE the cost of the RETRIED bit the body never passes.

The ranking law's bit 7 (RETRIED) is a VETO: "a line already tried and
rejected this pass goes last whatever else is true of it" (rank.py:23-25).
Neither guard.py call site (511, 585) passes `retried=`, so the veto lane is
dead. This script builds a fixture that makes guard_once take BOTH passes
over the SAME file and counts how many candidate/suite runs pass 1 spends
re-trying exactly what pass 0 already rejected.

  ./run.sh /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python retried_cost.py

Writes retried_cost.out next to this script. Fixture lives in ./retried_fixture
(created fresh each run). No src/ edits: loop.repair and guard.rank_observations
are wrapped from the outside.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time

sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

HERE = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.join(HERE, "retried_fixture")
PY = "/Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python"

# ---------------------------------------------------------------- fixture --
# ~90 executed lines. Most carry no signal token (no digit, no comparison,
# no spaced +-*/), so localize.build_packet's filter at localize.py:164-172
# drops them and sets truncated=True at max_lines=110 -> the engine law sees
# CAPPED and guard_once escalates over the SAME file at max_lines=990, where
# nothing is dropped. Six lines DO carry digits: those are the ones the
# mechanical observer flags, and the ones both passes try.
body = ["def compute(n):", "    total = n"]
for i in range(84):
    if i in (10, 25, 40, 55, 70, 80):
        body.append(f"    total = total + 1   # signal line {i}")
    else:
        body.append("    total = total")
body.append("    return total")
MOD = "\n".join(body) + "\n"
TEST = ("from mod import compute\n\n\n"
        "def test_compute():\n"
        "    assert compute(3) == 999\n")

if os.path.isdir(FIX):
    shutil.rmtree(FIX)
os.makedirs(FIX)
open(os.path.join(FIX, "mod.py"), "w").write(MOD)
open(os.path.join(FIX, "test_mod.py"), "w").write(TEST)

import fluidfix.guard as G          # noqa: E402
import fluidfix.loop as L           # noqa: E402
from fluidfix.oracle import Oracle  # noqa: E402
from fluidfix.observers import MechanicalObserver  # noqa: E402

# ------------------------------------------------------------------ taps --
PASSES: list[dict] = []      # one entry per rank_observations call
_orig_ro = G.rank_observations
_orig_repair = L.repair


def _ro(src, observations, failing_output, *, root=None, rel=None,
        retried=None):
    out = _orig_ro(src, observations, failing_output, root=root, rel=rel,
                   retried=retried)
    PASSES.append({"rel": rel, "n_obs": len(observations),
                   "retried_kwarg": None if retried is None else sorted(retried),
                   "order_in": [o.lineno for o in observations],
                   "order_out": [o.lineno for o in out],
                   "tried_keys": None, "suite_runs": None})
    return out


def _repair(oracle, defect_file, observations, **kw):
    res = _orig_repair(oracle, defect_file, observations, **kw)
    if PASSES:
        PASSES[-1]["tried_keys"] = sorted(
            {(e["at"], e["tried"]) for e in res.tried_log})
        PASSES[-1]["suite_runs"] = res.suite_runs
        PASSES[-1]["tried_more"] = res.tried_more
    return res


G.rank_observations = _ro
# guard.py:29 does `from .loop import RepairResult, repair` at MODULE level,
# so the name guard_once actually calls is guard.repair — patch that one.
G.repair = _repair
L.repair = _repair

# -------------------------------------------------------------------- run --
oracle = Oracle(FIX, python=PY)
t0 = time.time()
report = G.guard_once(oracle, MechanicalObserver(), files=["mod.py"],
                      escalate=True, escalate_budget=120, budget=240)
elapsed = time.time() - t0

out = []


def say(s=""):
    print(s)
    out.append(s)


say("== fixture: %s (mod.py %d lines, one failing test)"
    % (FIX, len(MOD.split(chr(10)))))
say("== guard_once(files=['mod.py'], escalate=True, escalate_budget=120, "
    "budget=240)")
say(f"== status={report.status}  seconds={elapsed:.1f}  "
    f"attempts_logged={len(report.attempts or [])}")
say()
say(f"rank_observations calls (the body's ONLY ranking path): {len(PASSES)}")
for i, p in enumerate(PASSES):
    say(f"  call {i}: rel={p['rel']!r}  n_obs={p['n_obs']}  "
        f"retried kwarg = {p['retried_kwarg']!r}")
    say(f"           order out = {p['order_out']}")
    say(f"           suite_runs = {p['suite_runs']}  "
        f"distinct rejected candidates = "
        f"{len(p['tried_keys'] or [])}"
        f"  (+{p.get('tried_more', 0)} beyond the 64-entry log cap)")
say()

if len(PASSES) >= 2:
    a = set(PASSES[0]["tried_keys"] or [])
    b = set(PASSES[1]["tried_keys"] or [])
    dup = a & b
    say("OVERLAP between pass 0 and the escalation pass over the SAME file:")
    say(f"  pass 0 rejected      : {len(a)} distinct candidates")
    say(f"  escalation rejected  : {len(b)} distinct candidates")
    say(f"  IDENTICAL (file:line, candidate text) in both: {len(dup)}")
    if b:
        say(f"  -> {len(dup)}/{len(b)} = {len(dup) / len(b):.0%} of the "
            f"escalation pass's rejected candidates were already rejected "
            f"in pass 0")
    say("  each such candidate costs one full suite run "
        "(loop.py:355 res.suite_runs += 1)")
    say()
    say("  first 8 duplicated candidates (at, text):")
    for at, txt in sorted(dup)[:8]:
        say(f"    {at:14s} {txt[:56]!r}")
    say()
    retried_lines = sorted({int(at.split(':')[1].split('-')[0])
                            for at, _ in a})
    say(f"  the `retried` set the body COULD have passed at guard.py:585, "
        f"derived from pass 0's own result.tried_log: {retried_lines}")
    from fluidfix.rank import BITS, observe_bits, rank
    say("  what the law would have ruled for those lines with that set:")
    for ln in retried_lines[:6]:
        no_veto = observe_bits(signaled=True, cheap=True)
        veto = observe_bits(signaled=True, cheap=True, retried=True)
        say(f"    line {ln:3d}: byte 0x{no_veto:02x} -> rank {rank(no_veto)} "
            f"(today)   byte 0x{veto:02x} -> rank {rank(veto)} (with RETRIED)")
else:
    say("only one ranking call happened — the escalation pass did not "
        "re-rank this file. See retried_cost.out for the reason.")

say()
say("report.hint: " + str(report.hint)[:300])
open(os.path.join(HERE, "retried_cost.out"), "w").write("\n".join(out) + "\n")
json.dump(PASSES, open(os.path.join(HERE, "retried_cost.json"), "w"), indent=1)
