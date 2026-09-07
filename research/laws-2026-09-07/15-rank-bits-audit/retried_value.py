#!/usr/bin/env python
"""What the DEAD retried lane would buy, measured.

retried_cost.py showed the escalation pass re-tries 100% of pass 0's rejected
candidates. But RETRIED is a RANKING veto, not a skip: it only moves a tried
line to priority 7. It buys something only when the escalation packet contains
lines pass 0 never saw. This fixture makes that case and measures the delay.

The trick: localize.build_packet's anchor filter (localize.py:165) keeps only
lines matching  [<>]=? | \\d | \\s[-+*/]\\s | and | or | True | False .
A line like `total = max(total, total)` matches NONE of those, so pass 0's
truncated packet drops it -- yet acts.KINDS[8] (`\\b(?:min|max)\\(`) DOES flag
it, so the escalation packet (max_lines=990, no filter) observes it as fresh.

  ./run.sh /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python retried_value.py
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import time

sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

HERE = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.join(HERE, "retried_value_fixture")
PY = "/Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python"

DIGIT_LINES, MAX_LINES = (10, 25, 40), (60, 70, 80)
body = ["def compute(n):", "    total = n"]
for i in range(84):
    if i in DIGIT_LINES:
        # carries a digit -> survives the anchor filter, seen in BOTH passes
        body.append("    total = total + 1")
    elif i in MAX_LINES:
        # NO digit, NO spaced +-*/, NO <> -> the anchor filter drops it in
        # pass 0, but acts.KINDS[8] flags it in the full-sight pass.
        # (the comment must stay digit-free or the filter keeps the line)
        body.append("    total = max(total, total)   # widen")
    else:
        body.append("    total = total")
body.append("    return total")
MOD = "\n".join(body) + "\n"
TEST = ("from mod import compute\n\n\n"
        "def test_compute():\n    assert compute(3) == 999\n")

if os.path.isdir(FIX):
    shutil.rmtree(FIX)
os.makedirs(FIX)
open(os.path.join(FIX, "mod.py"), "w").write(MOD)
open(os.path.join(FIX, "test_mod.py"), "w").write(TEST)

import fluidfix.guard as G          # noqa: E402
from fluidfix.oracle import Oracle  # noqa: E402
from fluidfix.observers import MechanicalObserver  # noqa: E402
from fluidfix.rank import BITS, observe_bits, rank  # noqa: E402

PASSES: list[dict] = []
_orig_ro, _orig_repair = G.rank_observations, G.repair


def _ro(src, observations, failing_output, *, root=None, rel=None,
        retried=None):
    out = _orig_ro(src, observations, failing_output, root=root, rel=rel,
                   retried=retried)
    PASSES.append({"rel": rel, "retried_kwarg": retried,
                   "distinct_in": sorted({o.lineno for o in observations}),
                   "order_out": [o.lineno for o in out],
                   "src": src, "failing_output": failing_output})
    return out


def _repair(oracle, defect_file, observations, **kw):
    res = _orig_repair(oracle, defect_file, observations, **kw)
    if PASSES:
        PASSES[-1]["suite_runs"] = res.suite_runs
        PASSES[-1]["tried_at"] = [e["at"] for e in res.tried_log]
        PASSES[-1]["tried_keys"] = sorted({(e["at"], e["tried"])
                                           for e in res.tried_log})
    return res


G.rank_observations, G.repair = _ro, _repair

oracle = Oracle(FIX, python=PY)
t0 = time.time()
report = G.guard_once(oracle, MechanicalObserver(), files=["mod.py"],
                      escalate=True, escalate_budget=120, budget=240)
elapsed = time.time() - t0

out = []


def say(s=""):
    print(s)
    out.append(s)


say(f"== fixture {FIX}  mod.py {len(MOD.split(chr(10)))} lines")
say(f"== status={report.status}  seconds={elapsed:.1f}")
say(f"== ranking calls: {len(PASSES)}")
for i, p in enumerate(PASSES):
    say(f"  call {i}: retried kwarg={p['retried_kwarg']!r}  "
        f"distinct observed lines={p['distinct_in']}  "
        f"suite_runs={p.get('suite_runs')}")
say()

if len(PASSES) >= 2:
    p0, p1 = PASSES[0], PASSES[1]
    tried0 = {int(a.split(":")[1].split("-")[0]) for a in p0.get("tried_at", [])}
    fresh = [l for l in p1["distinct_in"] if l not in tried0]
    stale = [l for l in p1["distinct_in"] if l in tried0]
    say(f"pass 0 actually TRIED lines : {sorted(tried0)}")
    say(f"escalation packet observes  : {p1['distinct_in']}")
    say(f"  of those, FRESH (never tried): {fresh}")
    say(f"  of those, already rejected   : {stale}")
    say()
    # TODAY's order, as the body produced it
    order_today = []
    for l in p1["order_out"]:
        if l not in order_today:
            order_today.append(l)
    say(f"TODAY the escalation order (first occurrence of each line) is:")
    say(f"  {order_today}")
    first_fresh = min((order_today.index(l) for l in fresh), default=None)
    say(f"  first FRESH line sits at position {first_fresh} of "
        f"{len(order_today)}")
    say()
    # WITH the veto: re-rank the same observations, passing the retried set
    # the body already holds in result.tried_log.
    class _O:
        def __init__(self, ln, kinds):
            self.lineno, self.kinds = ln, kinds
            self.literal_value = self.literal_occurrence = None
            self.op_occurrence = None
            self.note = ""
    from fluidfix.localize import Packet  # noqa: E402
    obs_re = MechanicalObserver().observe([Packet(
        defect_file="mod.py", failure="", lines=p1["distinct_in"],
        src_lines=p1["src"].split("\n"), mode="x", truncated=False)])[0]
    with_veto = _orig_ro(p1["src"], obs_re, p1["failing_output"],
                         root=FIX, rel="mod.py", retried=tried0)
    order_veto = []
    for o in with_veto:
        if o.lineno not in order_veto:
            order_veto.append(o.lineno)
    say("WITH retried=<pass 0's own tried_log lines> passed to the SAME "
        "function:")
    say(f"  {order_veto}")
    ff = min((order_veto.index(l) for l in fresh), default=None)
    say(f"  first FRESH line sits at position {ff} of {len(order_veto)}")
    say()
    # cost of the delay, in suite runs
    at_seq = p1.get("tried_at", [])
    runs_before_fresh = 0
    for a in at_seq:
        ln = int(a.split(":")[1].split("-")[0])
        if ln in fresh:
            break
        runs_before_fresh += 1
    say(f"MEASURED: the escalation pass paid {runs_before_fresh} suite runs "
        f"on already-rejected lines")
    say(f"          before its first candidate on a FRESH line "
        f"(total escalation suite_runs={p1.get('suite_runs')}).")
    say(f"          With the veto those {runs_before_fresh} runs come LAST, "
        f"not first.")
    say()
    say("byte-level check on one fresh vs one stale line "
        "(both SIGNALED+CHEAP):")
    a = observe_bits(signaled=True, cheap=True)
    b = observe_bits(signaled=True, cheap=True, retried=True)
    say(f"  fresh 0x{a:02x} -> rank {rank(a)}   "
        f"stale 0x{b:02x} -> rank {rank(b)}")

say()
say("report.hint: " + str(report.hint)[:240])
open(os.path.join(HERE, "retried_value.out"), "w").write("\n".join(out) + "\n")
