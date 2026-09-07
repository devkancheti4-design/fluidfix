"""26-router-exhaustive: what the routing buys, in candidate count.

Each candidate is one suite run. Builds a FRESH copy of every fixture (the
live_trace.py run repairs its own copies, so they must not be reused) and
compares, on the exact line the mechanical observer reports:

  routed       candidates from act_for(kind) only, for the kinds observed
  all-appliers candidates from every applier in ACTS, i.e. what a body with
               no routing law would have to try

Run: ./run.sh 300 /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python cost.py
"""
import os
import shutil
import sys
import textwrap

sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fixtures_def import FIXTURES  # noqa: E402
from fluidfix import MechanicalObserver, Oracle, build_packet  # noqa: E402
from fluidfix.acts import ACTS, act_for, candidates  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(HERE, "fixtures_cost")
shutil.rmtree(WORK, ignore_errors=True)

tot_r = tot_u = 0
print(f"{'fixture':<24} {'kinds':<14} {'routed':>7} {'all-appliers':>13} {'saved':>7}")
for name, (src, test) in FIXTURES.items():
    d = os.path.join(WORK, name)
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "mod.py"), "w").write(textwrap.dedent(src))
    open(os.path.join(d, "test_mod.py"), "w").write(textwrap.dedent(test))
    oracle = Oracle(d, python=sys.executable)
    packet = build_packet(oracle, "mod.py", coverage_target="mod")
    if packet is None:
        print(f"{name:<24} {'(suite green)':<14}")
        continue
    obs_list = MechanicalObserver().observe([packet])[0]
    r = u = 0
    kinds = set()
    for obs in obs_list:
        line = packet.src_lines[obs.lineno - 1].rstrip("\r")
        kinds |= set(obs.kinds)
        r += sum(len([c for c in candidates(line, act_for(k), obs) if c != line])
                 for k in obs.kinds)
        u += sum(len([c for c in candidates(line, a, obs) if c != line])
                 for a in sorted(ACTS))
    tot_r += r
    tot_u += u
    print(f"{name:<24} {str(sorted(kinds)):<14} {r:>7} {u:>13} {u - r:>7}")
print(f"{'TOTAL':<24} {'':<14} {tot_r:>7} {tot_u:>13} {tot_u - tot_r:>7}")
print(f"\nrouted / unrouted candidates = {tot_r}/{tot_u} = "
      f"{tot_r / tot_u:.3f}   (each candidate is one suite run)")
