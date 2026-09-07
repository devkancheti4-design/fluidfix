#!/usr/bin/env python
"""Exposure census for the F4 shape: a line that carries the signal of TWO or
more shipped kinds is a line where two DIFFERENT acts can each propose a
green at ONE site — the shape loop.py measures as AMB=False (set_amb needs
one set; sites needs two lines).

Counts, per source tree, lines matching >=1 kind signal and >=2 kind
signals, plus the most common kind pairs. Read-only over the trees named
on the command line. No suite is run.

    <venv>/bin/python multikind_census.py PATH [PATH...]
"""
from __future__ import annotations

import collections
import os
import sys

sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix.acts import KINDS  # noqa: E402

EXT = {".py", ".c", ".h", ".cc", ".cpp", ".hpp"}


def census(root: str) -> dict:
    n_lines = n_sig = n_multi = 0
    pairs: collections.Counter = collections.Counter()
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d not in {".git", ".venv", "__pycache__",
                                            "build", "research", "node_modules"}]
        for f in fn:
            if os.path.splitext(f)[1] not in EXT:
                continue
            try:
                with open(os.path.join(dp, f), encoding="utf-8",
                          errors="replace") as fh:
                    for line in fh:
                        line = line.rstrip("\r\n")
                        if not line.strip() or line.lstrip().startswith(("#", "//", "*", "/*")):
                            continue
                        n_lines += 1
                        ks = [k for k, (_, _, sig) in sorted(KINDS.items())
                              if sig.search(line)]
                        if ks:
                            n_sig += 1
                        if len(ks) >= 2:
                            n_multi += 1
                            for i in range(len(ks)):
                                for j in range(i + 1, len(ks)):
                                    pairs[(ks[i], ks[j])] += 1
            except OSError:
                continue
    return dict(root=root, lines=n_lines, signal_lines=n_sig,
                multi_kind_lines=n_multi, top_pairs=pairs.most_common(8))


if __name__ == "__main__":
    for root in sys.argv[1:]:
        c = census(root)
        frac = c["multi_kind_lines"] / c["signal_lines"] if c["signal_lines"] else 0
        print(f"{c['root']}\n  code lines {c['lines']}, >=1 kind signal "
              f"{c['signal_lines']}, >=2 kind signals {c['multi_kind_lines']} "
              f"({frac:.1%} of signal lines)")
        print("  top kind pairs:", ", ".join(
            f"({a},{b})x{n}" for (a, b), n in c["top_pairs"]))
