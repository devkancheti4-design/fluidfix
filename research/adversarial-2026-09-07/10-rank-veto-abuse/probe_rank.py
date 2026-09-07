#!/usr/bin/env python
"""Read-only probe: what does fluidfix's own machinery see on the victim?

Prints the pass-0 packet's truncation state, and the ranking law's priority
for every observation, in the order guard.py would examine them -- first with
retried=set() (what guard.py ACTUALLY passes: nothing), then with retried=
the lines pass 0 already rejected (what the law was written to be given).

Nothing here modifies fluidfix; it calls its public functions.
"""
import sys

from fluidfix.guard import rank_observations
from fluidfix.localize import build_packet
from fluidfix.observers import MechanicalObserver
from fluidfix.oracle import Oracle

root = sys.argv[1]
o = Oracle(root, python=sys.executable, timeout=300)
fails, out = o.failing_output()
pkt = build_packet(o, "pkg/core.py")
print(f"pass-0 packet: lines={len(pkt.lines)} truncated={pkt.truncated} "
      f"mode={pkt.mode}")
pkt2 = build_packet(o, "pkg/core.py", max_lines=990)
print(f"escalation packet: lines={len(pkt2.lines)} truncated={pkt2.truncated}")

obs = MechanicalObserver().observe([pkt])[0]
print(f"observations at pass 0: {len(obs)}")

src = "\n".join(pkt.src_lines)


def show(tag, retried):
    ordered = rank_observations(src, list(obs), out, root=root,
                                rel="pkg/core.py", retried=retried)
    pos = {o_.lineno: i for i, o_ in enumerate(ordered)}
    defect = [o_ for o_ in obs
              if pkt.src_lines[o_.lineno - 1].strip().startswith("return x")]
    d = defect[0].lineno
    print(f"  {tag}: defect line {d} is examined at position "
          f"{pos[d] + 1} of {len(ordered)}; first 3 = "
          f"{[o_.lineno for o_ in ordered[:3]]}")
    return d


d = show("retried=set()      (what guard.py passes)", set())
rejected = {o_.lineno for o_ in obs if o_.lineno != d}
show("retried=pass-0 rejects (what rank.py documents)", rejected)
