#!/usr/bin/env python3
"""Agent 38 — how much of the ORDER was decided by the law, and how much by
the code tiebreak underneath it.

sorted(key=lambda i: (law_priority(i), -tokens(i), i)) in guard.py:425 and
ranked2.sort(key=(sight(...), -spec, -nfail, rel)) in guard.py:300.
A block of consecutive rank/sight records in the log is one sort: if the law
returned ONE priority for every element of that block, the law contributed
nothing to that ordering and the code tiebreak decided it alone.
"""
import collections
import glob
import json
import os

D = os.path.dirname(os.path.abspath(__file__))
BODY = {"guard.py", "loop.py", "acts.py"}

recs = []
for p in sorted(glob.glob(os.path.join(D, "logs", "*.jsonl"))):
    for line in open(p):
        recs.append(json.loads(line))


def blocks(law):
    """Records of OTHER laws called from inside the key function (rank's
    priority() calls act_for() -> router, and candidates() -> lanes) are
    skipped, so a sort's key calls stay contiguous."""
    inner = {"router", "lanes.EMIT", "lanes.ADVANCE", "lanes.HALT"}
    out, cur = [], []
    for r in recs:
        if r["law"] in inner:
            continue
        if r["law"] == law and r["site"].split(":")[0] in BODY:
            cur.append(r)
        elif cur:
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


for law, site in (("rank", "guard.py:406 (LINE order)"),
                  ("sight", "guard.py:280 (FILE order)")):
    bs = blocks(law)
    multi = [b for b in bs if len(b) > 1]
    flat = [b for b in multi if len({x["ruling"] for x in b}) == 1]
    n_el = sum(len(b) for b in bs)
    print("=" * 70)
    print("%s — %s" % (law.upper(), site))
    print("=" * 70)
    print("sorts observed                : %d  (%d elements)" % (len(bs), n_el))
    print("sorts with >1 element         : %d" % len(multi))
    print("  ...where the law gave ONE priority to every element")
    print("     (order decided ENTIRELY by the code tiebreak) : %d  (%.1f%%)"
          % (len(flat), 100.0 * len(flat) / max(1, len(multi))))
    print("  ...where the law separated at least two elements : %d  (%.1f%%)"
          % (len(multi) - len(flat),
             100.0 * (len(multi) - len(flat)) / max(1, len(multi))))
    els = [x for b in bs for x in b]
    c = collections.Counter(x["ruling"] for b in bs for x in b)
    top = c.most_common(1)[0]
    print("priority histogram            : %s" % dict(sorted(c.items())))
    print("modal priority %s covers        : %d of %d elements (%.1f%%)"
          % (top[0], top[1], len(els), 100.0 * top[1] / max(1, len(els))))
    print()
