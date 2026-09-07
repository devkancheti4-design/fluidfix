#!/usr/bin/env python
"""Static facts for target 06 — no guard run.

1. The engine law's rulings on every combination of the three bits loop.py's
   _rule() packs (BUILT/AMB/CAPPED), and on the two bits guard.py packs at the
   escalation gate (CAPPED/REFUTED); plus all 256 inputs split by CAPPED.
2. The fixture's search-space arithmetic: how many observations/candidates the
   first-pass packet (110 lines) and the full-sight packet carry, where the
   ranking law puts the bug line, and how long one suite run costs here.

usage: static_analysis.py <workdir>
"""
import itertools
import os
import sys
import time

from fluidfix import MechanicalObserver, Oracle
from fluidfix.acts import act_for, candidates
from fluidfix.engine import ACTS, BITS, decide, situation
from fluidfix.guard import rank_observations
from fluidfix.localize import build_packet


def say(*a):
    print(*a, flush=True)


say("== 1. rulings on the bits the body can pack ==")
say("loop.py:217  decide(situation(BUILT=True, AMB=..., CAPPED=...)) — 4 reachable + 4 unreachable (BUILT is always True there):")
for built in (1, 0):
    for amb in (0, 1):
        for capped in (0, 1):
            s = situation(BUILT=built, AMB=amb, CAPPED=capped)
            tag = "reachable from _rule" if built else "NOT packable by _rule (BUILT hardwired True)"
            say(f"  BUILT={built} AMB={amb} CAPPED={capped}  byte=0x{s & 0xFF:02x} -> {decide(s):<22} {tag}")
say("guard.py:539 decide(situation(CAPPED=capped0, REFUTED=acts0)) — the escalation gate:")
for capped in (0, 1):
    for ref in (0, 1):
        s = situation(CAPPED=capped, REFUTED=ref)
        say(f"  CAPPED={capped} REFUTED={ref}  byte=0x{s & 0xFF:02x} -> {decide(s)}")

say("\n== all 256 inputs, split by the CAPPED bit (bit 5) ==")
from collections import Counter
c_on, c_off = Counter(), Counter()
capped_not_raise = []
for x in range(256):
    r = decide(x | (2 << 8))
    if x & (1 << BITS.index("CAPPED")):
        c_on[r] += 1
        if r != "RAISE_BUDGET":
            capped_not_raise.append((x, r))
    else:
        c_off[r] += 1
say(f"  CAPPED=1 (128 inputs): {dict(c_on)}")
say(f"  CAPPED=0 (128 inputs): {dict(c_off)}")
say(f"  CAPPED=1 inputs NOT ruled RAISE_BUDGET: {len(capped_not_raise)}")
for x, r in capped_not_raise:
    bits = "+".join(b for i, b in enumerate(BITS) if (x >> i) & 1)
    say(f"    0x{x:02x} {bits:<45} -> {r}")

# ---- 2. the fixture ------------------------------------------------------
workdir = os.path.abspath(sys.argv[1])
os.makedirs(workdir, exist_ok=True)
names = ["".join(t) for t in itertools.product("abcdefghij", repeat=3)][:800]
filler = [f"f_{n} = True" for n in names]
fn = ["", "def tier(v, limit):", "    if v > limit:",
      "        return 1", "    return 0", ""]
with open(os.path.join(workdir, "test_mod.py"), "w") as f:
    f.write("from mod import tier\n\ndef test_t():\n"
            "    assert tier(5, 5) == 1 and tier(4, 5) == 0\n")
oracle = Oracle(workdir, python=sys.executable)
for pad in range(6):
    body = filler[:400 + pad] + fn + filler[400 + pad:]
    bug_lineno = (400 + pad) + 3
    with open(os.path.join(workdir, "mod.py"), "w") as f:
        f.write("\n".join(body) + "\n")
    pk = build_packet(oracle, "mod.py")
    if pk is not None and pk.truncated and bug_lineno not in pk.lines:
        break
say(f"\n== 2. fixture arithmetic (pad={pad}, bug at mod.py:{bug_lineno}, file has {len(body)} lines) ==")
fails, out = oracle.failing_output()
obs = MechanicalObserver()


def describe(tag, packet):
    observations = rank_observations("\n".join(packet.src_lines),
                                     obs.observe([packet])[0], out,
                                     root=oracle.root, rel="mod.py")
    ncand = 0
    kinds = Counter()
    for o in observations:
        line = packet.src_lines[o.lineno - 1]
        o.file, o.root, o.all_lines = "mod.py", oracle.root, packet.src_lines
        for k in o.kinds:
            kinds[k] += 1
            cs = [c for c in candidates(line, act_for(k), o) if c != line]
            ncand += len(cs)
    pos = next((i for i, o in enumerate(observations) if o.lineno == bug_lineno), None)
    say(f"  {tag}: packet lines={len(packet.lines)} truncated={packet.truncated} "
        f"bug_in_packet={bug_lineno in packet.lines}")
    say(f"    observations={len(observations)} kinds histogram={dict(kinds)} "
        f"distinct candidates (= max suite runs, before dedup)={ncand}")
    say(f"    ranking-law position of the bug line among observations: "
        f"{pos if pos is not None else 'absent'} (0 = tried first)")
    if pos is not None:
        say(f"    bug line kinds={observations[pos].kinds}; candidates before it: "
            f"{sum(len([c for c in candidates(packet.src_lines[o.lineno-1], act_for(k), o) if c != packet.src_lines[o.lineno-1]]) for o in observations[:pos] for k in o.kinds)}")
    return observations


describe("first pass  (build_packet default max_lines=110)", pk)
pk990 = build_packet(oracle, "mod.py", max_lines=990)
describe("escalation  (max_lines=990, guard.py:578)", pk990)
if pk990.truncated:
    pkfull = build_packet(oracle, "mod.py", max_lines=10 ** 9)
    describe("escalation  (max_lines=1e9, guard.py:582)", pkfull)

say("\n  one suite run (oracle.check, fail-fast --lf path) on this fixture:")
for i in range(3):
    t = time.time()
    ok, why = oracle.check()
    say(f"    run {i + 1}: ok={ok} {time.time() - t:.2f}s")
