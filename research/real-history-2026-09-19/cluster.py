#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Do real one-line fixes RECUR in shape? If they do, teaching from a team's history pays; if not, it does not.

`mine.py` found that 46% of real single-file fix commits across four repositories replace exactly one line —
a far higher ceiling for a line-rewriting vocabulary than we expected — while today's vocabulary produces
only 3% of those lines exactly. The gap is the teachable space, and whether it is worth anything depends
entirely on one thing: do the same TRANSFORMATIONS come back?

So each one-line fix is reduced to a transformation signature, mechanically: the tokens that left, the
tokens that arrived, with identifiers and numbers abstracted away so that `limit` and `width` do not count
as different faults. Signatures that recur are candidate classes. Signatures that appear once are what a
model is for.
"""
from __future__ import annotations

import json, re, sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOK = re.compile(r"[A-Za-z_]\w*|\d+|[^\s\w]")


KEEP = {"True", "False", "None", "and", "or", "not", "if", "else", "return", "in", "is",
        "for", "while", "len", "min", "max", "int", "str", "sorted", "range", "self"}


def abstract(tok: str) -> str:
    """A name is a name and a number is a number: `limit` and `width` are not different faults."""
    if re.fullmatch(r"\d+", tok):
        return "N"
    if re.fullmatch(r"[A-Za-z_]\w*", tok):
        return tok if tok in KEEP else "ID"
    return tok


def signature(before: str, after: str):
    """What changed, with names and values abstracted. Returns (gone, arrived) as token tuples."""
    b = [abstract(t) for t in TOK.findall(before)]
    a = [abstract(t) for t in TOK.findall(after)]
    # strip the common prefix and suffix so only the changed middle remains
    i = 0
    while i < min(len(b), len(a)) and b[i] == a[i]:
        i += 1
    j = 0
    while j < min(len(b), len(a)) - i and b[len(b)-1-j] == a[len(a)-1-j]:
        j += 1
    gone, arrived = b[i:len(b)-j], a[i:len(a)-j]
    return " ".join(gone) or "·", " ".join(arrived) or "·"


def main():
    d = json.load(open(HERE / "real_history.json"))
    ones = [r for r in d["rows"] if r["before"] is not None and r["after"] is not None
            and r["hunks"] == 1]
    sigs = Counter()
    examples = {}
    for r in ones:
        g, a = signature(r["before"], r["after"])
        if len(g.split()) > 6 or len(a.split()) > 6:
            key = "(a long rewrite)"
        else:
            key = f"{g}  ->  {a}"
        sigs[key] += 1
        examples.setdefault(key, []).append(r)

    print(f"{len(ones)} one-line fixes from real history, reduced to transformation signatures\n")
    rec = [(k, v) for k, v in sigs.most_common() if v >= 2 and k != "(a long rewrite)"]
    once = sum(v for k, v in sigs.items() if v == 1)
    longr = sigs.get("(a long rewrite)", 0)
    print(f"{'signature (names and numbers abstracted)':52} {'n':>4}")
    for k, v in rec[:16]:
        print(f"  {k[:50]:50} {v:>4}")
    tot_rec = sum(v for _k, v in rec)
    print(f"\nrecurring signatures: {len(rec)} distinct, covering {tot_rec} of {len(ones)} fixes "
          f"({tot_rec/len(ones):.0%})")
    print(f"seen exactly once:    {once} ({once/len(ones):.0%})")
    print(f"long rewrites on one line: {longr} ({longr/len(ones):.0%})")

    print("\nthe three most common, with a real example of each:")
    for k, v in rec[:3]:
        r = examples[k][0]
        print(f"\n  {k}   ({v} times)")
        print(f"    {r['repo']}  {r['subject'][:62]}")
        print(f"    - {r['before'].strip()[:86]}")
        print(f"    + {r['after'].strip()[:86]}")

    json.dump({"one_line": len(ones), "recurring_signatures": len(rec), "covered_by_recurring": tot_rec,
               "once_only": once, "long_rewrites": longr,
               "top": [{"sig": k, "n": v} for k, v in rec[:25]]},
              open(HERE / "clusters.json", "w"), indent=1)
    print("\nCLUSTER_DONE")


if __name__ == "__main__":
    main()
