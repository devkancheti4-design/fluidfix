#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Do the 88 real one-line CODE fixes recur in shape? This decides whether teaching from history pays.

`code_vs_text.py` separated logic changes from typos and translated strings. What is left is the teachable
space: 88 fixes, from four repositories, where somebody changed exactly one line of code to fix something.

Each is reduced to a transformation signature — what left, what arrived — with strings, comments,
identifiers and numbers abstracted, so `limit` and `width` are not counted as different faults and a
changed message is not counted as a changed program. A signature seen twice is a candidate class. A
signature seen once is what a model is for.
"""
from __future__ import annotations

import io, json, re, tokenize
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
KEEP = {"True","False","None","and","or","not","if","else","return","in","is","for","while",
        "len","min","max","int","str","sorted","range","self","lambda","import","from"}


def toks(line):
    try:
        ts = list(tokenize.generate_tokens(io.StringIO(line.strip() + "\n").readline))
    except Exception:
        return None
    out = []
    for t in ts:
        if t.type in (tokenize.NL, tokenize.NEWLINE, tokenize.ENDMARKER, tokenize.INDENT, tokenize.DEDENT):
            continue
        if t.type == tokenize.STRING:
            out.append("STR")
        elif t.type == tokenize.COMMENT:
            out.append("CMT")
        elif t.type == tokenize.NUMBER:
            out.append("N")
        elif t.type == tokenize.NAME:
            out.append(t.string if t.string in KEEP else "ID")
        else:
            out.append(t.string)
    return out


def signature(before, after):
    b, a = toks(before), toks(after)
    if b is None or a is None:
        return None
    i = 0
    while i < min(len(b), len(a)) and b[i] == a[i]:
        i += 1
    j = 0
    while j < min(len(b), len(a)) - i and b[len(b)-1-j] == a[len(a)-1-j]:
        j += 1
    gone, arr = " ".join(b[i:len(b)-j]) or "·", " ".join(a[i:len(a)-j]) or "·"
    if len(gone.split()) > 5 or len(arr.split()) > 5:
        return None
    return f"{gone}  →  {arr}"


def main():
    rows = json.load(open(HERE / "code_vs_text.json"))["code_rows"]
    sigs, ex, unclassed = Counter(), {}, 0
    for r in rows:
        s = signature(r["before"], r["after"])
        if s is None:
            unclassed += 1
            continue
        sigs[s] += 1
        ex.setdefault(s, []).append(r)

    rec = [(k, v) for k, v in sigs.most_common() if v >= 2]
    covered = sum(v for _k, v in rec)
    once = sum(v for k, v in sigs.items() if v == 1)
    n = len(rows)
    print(f"{n} real one-line CODE fixes, four repositories\n")
    print(f"{'transformation (names, numbers and strings abstracted)':50} {'n':>4}  repos")
    for k, v in rec:
        repos = ",".join(sorted({x["repo"][:5] for x in ex[k]}))
        print(f"  {k[:48]:48} {v:>4}  {repos}")
    print(f"\nrecurring (seen 2+ times): {len(rec)} distinct shapes covering {covered} of {n} "
          f"({covered/n:.0%})")
    print(f"seen exactly once:         {once} ({once/n:.0%})")
    print(f"too large to reduce:       {unclassed} ({unclassed/n:.0%})")

    cross = [(k, v) for k, v in rec if len({x["repo"] for x in ex[k]}) > 1]
    print(f"\nshapes that recur ACROSS repositories: {len(cross)}"
          + (" — these are the ones worth a dictionary slot" if cross else ""))
    for k, v in cross:
        r = ex[k][0]
        print(f"  {k}   ({v}x, {', '.join(sorted({x['repo'] for x in ex[k]}))})")
        print(f"      - {r['before'].strip()[:80]}")
        print(f"      + {r['after'].strip()[:80]}")

    json.dump({"code_fixes": n, "recurring_shapes": len(rec), "covered": covered, "once": once,
               "unclassed": unclassed, "cross_repo": len(cross),
               "top": [{"sig": k, "n": v, "repos": sorted({x["repo"] for x in ex[k]})} for k, v in rec]},
              open(HERE / "recurrence.json", "w"), indent=1)
    print("\nRECURRENCE_DONE")


if __name__ == "__main__":
    main()
