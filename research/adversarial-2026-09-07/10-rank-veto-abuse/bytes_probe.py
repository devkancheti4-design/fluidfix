#!/usr/bin/env python
"""Print the exact observation BYTE guard.py hands the ranking law.

The only instrumentation is a read-only TAP around fluidfix.rank.rank: it
records (byte -> priority) and returns the law's own answer unchanged. No
law is altered, no defence disabled, no fluidfix file edited.

usage: bytes_probe.py <victim-root>
"""
import sys

import fluidfix.rank as rank_mod
from fluidfix.localize import build_packet
from fluidfix.observers import MechanicalObserver
from fluidfix.oracle import Oracle

root = sys.argv[1]
_real = rank_mod.rank
seen = []


def tap(observations: int) -> int:
    p = _real(observations)
    seen.append((observations, p))
    return p


rank_mod.rank = tap
import fluidfix.guard as guard          # noqa: E402  (import after the tap)

o = Oracle(root, python=sys.executable, timeout=300)
fails, out = o.failing_output()
pkt = build_packet(o, "pkg/core.py")
obs = MechanicalObserver().observe([pkt])[0]
src = "\n".join(pkt.src_lines)

for tag, retried in (("AS SHIPPED (guard.py never passes retried=)", set()),
                     ("WITH THE VETO FED", {o_.lineno for o_ in obs
                                            if o_.lineno != 284})):
    seen.clear()
    ordered = guard.rank_observations(src, list(obs), out, root=root,
                                      rel="pkg/core.py", retried=retried)
    # rank() is called once per observation, in `observations` order
    by_line = {o_.lineno: seen[i] for i, o_ in enumerate(obs)}
    pos = {o_.lineno: i + 1 for i, o_ in enumerate(ordered)}
    print(f"\n--- {tag} ---")
    for lbl, ln in (("decoy   pkg/core.py:9  `acc.append(a + b)`", 9),
                    ("DEFECT  pkg/core.py:284 `return x - y`", 284)):
        b, p = by_line[ln]
        names = "|".join(n for i, n in enumerate(rank_mod.BITS) if b >> i & 1)
        print(f"  {lbl}\n      byte=0b{b:08b} ({b}) = {names or 'NONE'}"
              f"  ->  law returns priority {p};  examined "
              f"{pos[ln]} of {len(ordered)}")
