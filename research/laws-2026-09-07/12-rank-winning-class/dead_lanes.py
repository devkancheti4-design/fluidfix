#!/usr/bin/env python
"""Exhaustive check: when SIGNALED is set and RETRIED is clear, do RECENT,
CHEAP and DENSE ever change the ranking law's output? Also: how often the
body actually set those bits in the logged runs, and does the RECENT
measurement work at all (read-only git on the fluidfix repo itself)."""
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))
from fluidfix.rank import BITS, rank   # noqa: E402

SIG, RET = 1 << BITS.index("SIGNALED"), 1 << BITS.index("RETRIED")
HIGH = sum(1 << BITS.index(b) for b in ("RECENT", "CHEAP", "DENSE"))
changed = [(x, rank(x), rank(x & ~HIGH)) for x in range(256)
           if (x & SIG) and not (x & RET) and rank(x) != rank(x & ~HIGH)]
n_sig = sum(1 for x in range(256) if (x & SIG) and not (x & RET))
print(f"bytes with SIGNALED=1, RETRIED=0: {n_sig}; of those, clearing RECENT/CHEAP/DENSE"
      f" changes rank() on {len(changed)}: {changed}")
# and without SIGNALED, the lanes DO matter (the law is not degenerate):
matter = [x for x in range(256) if not (x & SIG) and not (x & RET) and rank(x) != rank(x & ~HIGH)]
print(f"bytes with SIGNALED=0, RETRIED=0 where those lanes change rank(): {len(matter)}")

print("\nbits measured in the logged runs (every observation the body ranked):")
c, n = Counter(), 0
for p in sorted(HERE.glob("log/*.json")):
    r = json.loads(p.read_text())
    for call in r["rank_calls"]:
        for row in call["rows"]:
            n += 1
            for b in row["bits"].split("+"):
                c[b] += 1
print(f"observations: {n}; SIGNALED set on {c['SIGNALED']}; RECENT {c['RECENT']}; CHEAP {c['CHEAP']};"
      f" DENSE {c['DENSE']}; FAILONLY {c['FAILONLY']}; RETRIED {c['RETRIED']}; FRAME {c['FRAME']}; NAMED {c['NAMED']}")

print("\nRECENT measurement path (read-only git on the fluidfix repo, not a fixture):")
from fluidfix.guard import _recent_lines   # noqa: E402
rl = _recent_lines(str(ROOT), "src/fluidfix/rank.py")
print(f"_recent_lines(fluidfix, src/fluidfix/rank.py) -> {len(rl)} lines touched by the last 40 commits")

print("\nrank_observations call sites in guard.py and whether `retried=` is passed:")
import re   # noqa: E402
src = (ROOT / "src/fluidfix/guard.py").read_text().split("\n")
for i, l in enumerate(src, 1):
    if "rank_observations(" in l and "def " not in l:
        blk = " ".join(x.strip() for x in src[i - 1:i + 3])
        print(f"  guard.py:{i}: retried passed = {'retried=' in blk}")
