#!/usr/bin/env python
"""The one channel by which class order still reaches a shipped law today.

Only three places in the body read obs.kinds (grep '\\.kinds' over src/fluidfix):

    loop.py:283   mask = mask_of(...)      -- ORDER DISCARDED (a set)
    guard.py:409  signaled=bool(obs.kinds) -- order-insensitive
    guard.py:402  for k in (obs.kinds or [])[:2]  -- ORDER-SENSITIVE

guard.py:402 counts candidates for the FIRST TWO kinds only, and CHEAP is
`0 < n < 8`. So reordering an observation's kinds (e.g. by measured
recurrence) cannot change the class search order at all, but it CAN flip the
CHEAP bit and therefore the LINE order the ranking law produces.

This script takes the real defect lines from the history scan that carry more
than two kinds and asks: over all orderings of that line's kinds, does the
CHEAP bit take both values?

Usage: .venv/bin/python cheap_channel.py     (reads pairs_results.json)
"""
import itertools
import json
import os
import sys

sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix.acts import KINDS, Observation, act_for, candidates   # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
rows = json.load(open(os.path.join(HERE, "pairs_results.json")))

seen, uniq = set(), []
for r in rows:
    key = (r["repo"], r["old"].strip(), r["new"].strip())
    if key in seen:
        continue
    seen.add(key)
    uniq.append(r)


def observed_kinds(line):
    return [k for k, (_, _, sig) in sorted(KINDS.items()) if sig.search(line)]


def cheap(line, order):
    """guard.py:399-405, verbatim in effect."""
    obs = Observation(lineno=1, kinds=list(order))
    n = sum(len(candidates(line.strip(), act_for(k), obs))
            for k in (obs.kinds or [])[:2])
    return 0 < n < 8, n


multi = [r for r in uniq if len(observed_kinds(r["old"])) >= 3]
print(f"unique history lines carrying >=3 kinds (so the [:2] slice can "
      f"differ): {len(multi)}")
flip = 0
for r in multi[:40]:
    ks = observed_kinds(r["old"])
    vals = {}
    for p in itertools.permutations(ks):
        c, n = cheap(r["old"], p)
        vals.setdefault(c, []).append((list(p[:2]), n))
    if len(vals) > 1:
        flip += 1
        t = vals[True][0]
        f = vals[False][0]
        print(f"  FLIPS  {r['repo']:6} {r['sha']} kinds={ks} "
              f"| CHEAP=True at [:2]={t[0]} n={t[1]}; "
              f"CHEAP=False at [:2]={f[0]} n={f[1]}")
        print(f"         line: {r['old'].strip()[:78]}")
print(f"\nlines (of the {min(len(multi),40)} examined) where kind ORDER alone "
      f"flips the CHEAP bit: {flip}")
print("CHEAP is bit 5 of the ranking law's byte; flipping it can move a line's")
print("priority, i.e. the ORDER LINES ARE SEARCHED IN — never the order the")
print("classes are tried in, which loop.py:283 makes unrepresentable.")
