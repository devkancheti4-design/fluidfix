#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""One net's coverage of real history. usage: census.py <dictionary-or-'shipped'>

For every mined fix whose removed side is one line: does this net RECOGNISE the line (a signal fires), and
does it REACH the fix (some candidate equals what the maintainer actually wrote, whitespace-insensitive)?
No test runs. This is the knowledge question only: could it have proposed the right line.

Prints JSON so a driver can union the nets — that union is the swarm, one overseer over N processes."""
import json, re, sys
from pathlib import Path
R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / "src")); sys.path.insert(0, str(R / "research/life-fluidfix-2026-09-18"))
from life_fluidfix import shape_candidates, load_dictionary

which = sys.argv[1]
if which != "shipped":
    load_dictionary(str(R / which))

rows = json.load(open(R / "research/real-history-2026-09-19/remine.json"))["rows"]
norm = lambda s: re.sub(r"\s+", " ", s.strip())

recognised, reached = [], []
for i, r in enumerate(rows):
    minus, plus = r["minus"], r["plus"]
    if len(minus) != 1 or not plus:
        continue
    line = minus[0]
    want = norm("\n".join(plus))
    cands = shape_candidates(line, 1, minus)
    if not cands:
        continue
    recognised.append(i)
    for kind, name, c in cands:
        if norm(c) == want:
            reached.append([i, kind, name]); break

print(json.dumps({"net": which, "recognised": recognised, "reached": reached}))
