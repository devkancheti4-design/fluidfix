#!/usr/bin/env python
"""Control: how much of the law-vs-body gap is sight(), and how much is my
tiebreak?

measure.py ordered the law's rows by (priority, -NAMED, -spec, -n_fail): its
last key prefers the file with MORE executed lines.  coracle.cguard_once
orders its coverage extras by (-spec, +n_fail, rel): FEWER lines first.  That
is an opposite tiebreak, so the recorded law_rank could be flattered by it.

This recomputes, offline (no builds, no suite runs), over every red record
that persisted its per-file bytes in `rows`:

  A  sight() priority, law tiebreak      (-spec, -n_fail)   == recorded law_rank
  B  sight() priority, BODY tiebreak     (-spec, +n_fail)
  C  no sight() at all, BODY key only    (-spec, +n_fail)   == the body's rule
                                                               on the same universe

B vs C isolates the SIGHT law's own contribution: same universe, same
tiebreak, the only difference is whether the eight-bit priority tiers first.

rows entry = [rel, priority, n_fail, n_full, bits]

Run:  .venv/bin/python control_tiebreak.py
"""
import json, os, statistics as st

HERE = os.path.dirname(os.path.abspath(__file__))
recs = [json.loads(l) for l in open(os.path.join(HERE, "results.jsonl"))]


def pick(recs):
    """One record per file: the first attempt that turned the suite red, but
    preferring a later re-measurement of that same site when it persisted the
    per-file bytes (`rows`).  Green-only files keep their last green attempt."""
    best = {}
    for r in recs:
        f = r["file"]
        cur = best.get(f)
        if cur is None:
            best[f] = r; continue
        if cur["status"] == "green" and r["status"] != "green":
            best[f] = r; continue
        if (cur["status"] != "green" and r["status"] != "green"
                and cur["line"] == r["line"] and "rows" in r and "rows" not in cur):
            best[f] = r
    return best

last = pick(recs)
red = {f: r for f, r in last.items() if r["status"] != "green"}
have = {f: r for f, r in red.items() if r.get("rows")}
print(f"red defects: {len(red)}   with persisted per-file bytes (`rows`): {len(have)}")
print(f"without rows (measured earlier, before the field existed): "
      f"{', '.join(sorted(set(red) - set(have))) or 'none'}\n")


def rank(rows, rel, key):
    order = [t[0] for t in sorted(rows, key=key)]
    return order.index(rel) + 1 if rel in order else None


A, B, C, D, E, BODY = [], [], [], [], [], []
print(f"{'file':26s} {'body':>5s} {'A law':>6s} {'B law':>6s} {'C nolaw':>8s} "
      f"{'D nolaw':>8s} {'E named':>8s}")
for f in sorted(have):
    r = have[f]
    rows = r["rows"]                      # [rel, pri, n_fail, n_full, bits]

    def spec(t):
        return t[2] / max(t[3], t[2], 1)

    a = rank(rows, f, lambda t: (t[0] != t[0],))  # placeholder, replaced below
    a = rank(rows, f, lambda t: (t[1], -(1.0 if t[4].get("named") else 0.0),
                                 -spec(t), -t[2], t[0]))
    b = rank(rows, f, lambda t: (t[1], -spec(t), t[2], t[0]))
    c = rank(rows, f, lambda t: (-spec(t), t[2], t[0]))
    # D: sight() deleted entirely, but the LAW's tiebreak kept
    d = rank(rows, f, lambda t: (-spec(t), -t[2], t[0]))
    # E: only the NAMED bit kept (the one lane coracle already implements),
    #    plus the law's tiebreak -- no other sight bit, no priority tiers
    e = rank(rows, f, lambda t: (-(1.0 if t[4].get("named") else 0.0),
                                 -spec(t), -t[2], t[0]))
    bd = r.get("body_rank")
    for lst, v in ((A, a), (B, b), (C, c), (D, d), (E, e), (BODY, bd)):
        if v is not None:
            lst.append(v)
    print(f"{f:26s} {str(bd or 'MISS'):>5s} {str(a):>6s} {str(b):>6s} {str(c):>8s} "
          f"{str(d):>8s} {str(e):>8s}")


def line(name, vals, n):
    if not vals:
        print(f"{name:44s} unmeasured")
        return
    print(f"{name:44s} top-1 {sum(1 for v in vals if v == 1):2d}/{n}   "
          f"top-3 {sum(1 for v in vals if v <= 3):2d}/{n}   "
          f"median {st.median(vals):>4g}   mean {st.mean(vals):4.1f}   worst {max(vals)}")


n = len(have)
print()
line("BODY, real candidate list", BODY, n)
line("A  sight() + law tiebreak (-n_fail)", A, n)
line("B  sight() + BODY tiebreak (+n_fail)", B, n)
line("C  no sight(), BODY key only", C, n)
line("D  no sight(), LAW tiebreak (-n_fail)", D, n)
line("E  NAMED bit only + LAW tiebreak", E, n)
if A and D:
    d2 = [x - y for x, y in zip(A, D)]
    print(f"\nA vs D, same tiebreak, sight()'s eight-bit tiering the only difference:")
    print(f"  sight() moves the true file UP on {sum(1 for x in d2 if x < 0)}/{len(d2)}, "
          f"DOWN on {sum(1 for x in d2 if x > 0)}, unchanged on {sum(1 for x in d2 if x == 0)}")
    print(f"  median rank {st.median(D):g} (no law) -> {st.median(A):g} (law)")
if B and C:
    d = [c - b for b, c in zip(B, C)]
    print(f"\nB vs C, same universe and same tiebreak, sight() the only difference:")
    print(f"  sight() moves the true file UP on {sum(1 for x in d if x > 0)}/{len(d)}, "
          f"DOWN on {sum(1 for x in d if x < 0)}, unchanged on {sum(1 for x in d if x == 0)}")
    print(f"  median rank {st.median(C):g} -> {st.median(B):g}   "
          f"median improvement {st.median(d):+g} places")
