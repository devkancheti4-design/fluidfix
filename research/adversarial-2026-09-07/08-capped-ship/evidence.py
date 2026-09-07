#!/usr/bin/env python
"""Read-only evidence for the 08-capped-ship attack.

Nothing here patches, wraps or weakens fluidfix. It runs `guard_once`
exactly as the CLI does and uses `sys.settrace` -- a pure observer -- to
snapshot two frames while they execute:

    guard.py:509   AFTER `capped0 = capped0 or packet.truncated` has run,
                   so `capped0` is the CAPPED bit the guard has measured.
    loop.py:217    the `decide(situation(...))` call in loop._rule, where
                   `capped`, `set_amb` and `greens` are the byte's inputs.

Then it re-runs the same file at FULL SIGHT (what the law's RAISE_BUDGET
would have bought) and prints what the search finds there instead.

Run:  python evidence.py
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "fixture")
REL = "pkg/geom.py"

sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix.engine import ACTS, BITS, decide, situation      # noqa: E402
from fluidfix.guard import guard_once, rank_observations       # noqa: E402
from fluidfix.localize import build_packet                     # noqa: E402
from fluidfix.loop import repair                               # noqa: E402
from fluidfix.observers import MechanicalObserver              # noqa: E402
from fluidfix.oracle import Oracle                             # noqa: E402

# rebuild the victim repo so the run is from a known state
subprocess.run([sys.executable, os.path.join(HERE, "make_fixture.py")],
               check=True, stdout=subprocess.DEVNULL)

log = []


def tracer(frame, event, arg):
    fn = os.path.basename(frame.f_code.co_filename)
    if fn == "guard.py" and frame.f_code.co_name == "guard_once":
        return local_guard
    if fn == "loop.py" and frame.f_code.co_name == "_rule":
        return local_rule
    return None


def local_guard(frame, event, arg):
    if event == "line" and frame.f_lineno == 509:
        loc = frame.f_locals
        log.append(("guard.py:508 measured",
                    {"rel": loc.get("rel"),
                     "packet.truncated": loc["packet"].truncated,
                     "capped0": loc.get("capped0")}))
    return local_guard


def local_rule(frame, event, arg):
    if event == "line" and frame.f_lineno == 217:
        loc = frame.f_locals
        greens = loc.get("greens") or []
        log.append(("loop.py:217 byte handed to the law",
                    {"BUILT": True,
                     "AMB": bool(loc.get("set_amb")
                                 or len({g[3] for g in greens}) > 1),
                     "CAPPED": loc.get("capped"),
                     "greens": [(g[3], g[0].strip()) for g in greens]}))
    return local_rule


oracle = Oracle(ROOT, python=sys.executable, timeout=120)
sys.settrace(tracer)
try:
    report = guard_once(oracle, MechanicalObserver())
finally:
    sys.settrace(None)

print("=" * 72)
print("GUARD RESULT :", report.status, "->", report.summary())
print("=" * 72)
for tag, d in log:
    print(f"\n{tag}")
    for k, v in d.items():
        print(f"    {k:18} = {v}")

byte_asked = situation(BUILT=True, AMB=False, CAPPED=False)
byte_honest = situation(BUILT=True, AMB=False, CAPPED=True)
print("\n" + "=" * 72)
print(f"byte ACTUALLY asked   BUILT              = {byte_asked} "
      f"(0x{byte_asked:03x}) -> {decide(byte_asked)}")
print(f"byte the guard HAD    BUILT+CAPPED       = {byte_honest} "
      f"(0x{byte_honest:03x}) -> {decide(byte_honest)}")
print("=" * 72)

# ---- what RAISE_BUDGET would have bought: the same file at full sight ----
print("\nCONTROL: the same file, same observer, FULL SIGHT (max_lines=10**9)"
      " -- i.e. what the law's RAISE_BUDGET escalation reaches.\n")
subprocess.run([sys.executable, os.path.join(HERE, "make_fixture.py")],
               check=True, stdout=subprocess.DEVNULL)
oracle2 = Oracle(ROOT, python=sys.executable, timeout=120)
packet = build_packet(oracle2, REL, max_lines=10 ** 9)
print(f"  packet.truncated = {packet.truncated}  anchors={len(packet.lines)}")
obs = rank_observations("\n".join(packet.src_lines),
                        MechanicalObserver().observe([packet])[0], "",
                        root=oracle2.root, rel=REL)
res = repair(oracle2, REL, obs)
print(f"  repaired={res.repaired} refused={res.refused} ambiguous={res.ambiguous}")
print(f"  greens found: {[g.strip() for g in res.greens]}")
print(f"  reason: {res.reason}")
subprocess.run([sys.executable, os.path.join(HERE, "make_fixture.py")],
               check=True, stdout=subprocess.DEVNULL)
print("\n(fixture rebuilt to its as-found broken state)")
print("BITS:", BITS)
print("ACTS:", ACTS)
