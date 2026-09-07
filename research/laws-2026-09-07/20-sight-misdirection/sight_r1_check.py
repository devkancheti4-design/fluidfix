#!/usr/bin/env python
"""Is widening the traceback-frame branch SAFE for the framed file?

The proposal in this report is that the body stop early-returning the
framed files alone and instead hand FRAMED to the SIGHT law as one bit of
eight, letting the coverage tier contribute the other candidates. The
obvious worry is that this could DEMOTE the framed file below a
circumstantial one. R1 says it cannot. This enumerates all 256 x 256 pairs
to show it, and separately shows how many of the 256 bytes reach each
priority, so "priority 1 is never emitted" is measured rather than quoted.

    nice -n 15 ./tmo.sh 60 .venv/bin/python sight_r1_check.py
"""
import collections
import sys

sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix.sight import BITS, sight            # noqa: E402

FRAMED = 1 << BITS.index("FRAMED")
UBIQ = 1 << BITS.index("UBIQUITOUS")


def main():
    framed_p = {b: sight(b) for b in range(256) if b & FRAMED}
    other_p = {b: sight(b) for b in range(256) if not b & FRAMED}

    bad = [(b, c) for b in framed_p for c in other_p
           if framed_p[b] > other_p[c]]
    print(f"framed bytes: {len(framed_p)}   non-framed bytes: {len(other_p)}")
    print(f"pairs where a FRAMED file loses to a non-framed file: {len(bad)}")
    print(f"distinct priorities a FRAMED byte can take: "
          f"{sorted(set(framed_p.values()))}")

    # R2 on the exact byte the misdirection produces: a framed file that is
    # also UBIQUITOUS must still be priority 0.
    worst = FRAMED | UBIQ | 0xFF & ~FRAMED & ~UBIQ  # framed + every other bit
    print(f"sight(FRAMED|UBIQUITOUS)      = {sight(FRAMED | UBIQ)}")
    print(f"sight(every bit set)          = {sight(worst)}")
    print(f"sight(UBIQUITOUS alone)       = {sight(UBIQ)}")

    hist = collections.Counter(sight(b) for b in range(256))
    print("priority histogram over all 256 inputs: "
          f"{dict(sorted(hist.items()))}")
    print("priority 1 emitted:", 1 in hist)
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
