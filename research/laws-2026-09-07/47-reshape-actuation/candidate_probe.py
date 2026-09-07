#!/usr/bin/env python
"""Which candidates each act emits for the fixture lines (no suite runs)."""
import sys
sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix.acts import Observation, act_for, candidates
for line in ('    if n > 10:', '    if n >= 11:', '    return base - delta'):
    print(f"line {line!r}")
    for k in (0, 1, 2, 3):
        o = Observation(lineno=2, kinds=[k])
        print(f"   kind {k} -> act {act_for(k)} -> "
              f"{[c for c in candidates(line, act_for(k), o)]}")
