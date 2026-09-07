#!/usr/bin/env python
"""Where the suite runs before the winner actually go: LINE order (which the
ranking law rules) vs CLASS order on that line (which no law rules) vs
candidate order inside one set.

GROUND TRUTH is the check log: Oracle.check was monkeypatched, so every real
suite run is recorded together with the diff that was on disk at the time.
Each pre-green check is attributed to a (line, kind) slot by walking the
candidate sets in the exact order the body asked for them and consuming
candidates until one matches the text the check saw on disk. Candidates the
body skips without a suite run (NOPROGRESS, out-of-bounds or non-anchored
SpanEdit) are skipped by the same walk, so the attribution is exact rather
than inferred; any check that cannot be matched is reported as UNMATCHED
instead of being silently bucketed.

Pure post-processing; no suite runs.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent

runs = [json.loads(p.read_text()) for p in sorted(HERE.glob("log/*.json"))]
runs = [r for r in runs if r["group"] != "heavy"]
rep = [r for r in runs if r["status"] == "repaired"]
print(f"repaired fixtures: {len(rep)}")


def norm(cand: str) -> str:
    """the same normalisation Oracle.check's recorder applied to the diff"""
    text = cand.split("]", 1)[1] if cand.startswith("SPAN[") else cand
    return "\\n".join(x.strip() for x in text.split("\n"))[:90]


def attribute(r):
    """[(lineno, kind)] for each recorded suite run that applied a candidate"""
    flat = [(c["lineno"], c["kind"], norm(t)) for c in r["candidate_calls"] for t in c["cands"]]
    out, p = [], 0
    for ch in r["checks"]:
        if not ch["changed"]:            # red precondition run: tree is clean
            out.append(("CLEAN", None))
            continue
        seen = ch["changed"][0]["new"]
        hit = None
        for q in range(p, len(flat)):
            if flat[q][2] == seen:
                hit, p = q, q + 1
                break
        out.append((flat[hit][0], flat[hit][1]) if hit is not None else ("UNMATCHED", None))
    return out


print("\n== red suite runs before the first green, split by dimension ==")
print(f"{'fixture':26s} {'win':10s} {'prio':4s} {'ln_pos':7s} {'kd_pos':7s} "
      f"{'pre':3s} {'line':4s} {'kind':4s} {'cand':4s} {'clean':5s} unm")
T = Counter()
for r in sorted(rep, key=lambda r: r["name"]):
    w = r["winner"]
    att = attribute(r)
    fg = w["first_green_check"]
    pre = att[: fg - 1]                      # every suite run before the first green
    line = kind = cand = clean = unm = 0
    for ln, k in pre:
        if ln == "CLEAN":
            clean += 1
        elif ln == "UNMATCHED":
            unm += 1
        elif ln != w["lineno"]:
            line += 1
        elif k != w["kind"]:
            kind += 1
        else:
            cand += 1
    assert line + kind + cand + clean + unm == len(pre)
    for key, v in (("pre", len(pre)), ("line", line), ("kind", kind),
                   ("cand", cand), ("clean", clean), ("unm", unm)):
        T[key] += v
    T["runs"] += r["suite_runs"] or 0
    print(f"{r['name']:26s} L{w['lineno']}k{w['kind']:<6d} {w['law_priority']!s:4s} "
          f"{w['position_ranked']}/{w['n_obs']:<5} {w['kind_position_in_line']}/{w['kinds_on_line']:<5} "
          f"{len(pre):3d} {line:4d} {kind:4d} {cand:4d} {clean:5d} {unm:3d}")
print(f"{'TOTAL':26s} {'':10s} {'':4s} {'':7s} {'':7s} "
      f"{T['pre']:3d} {T['line']:4d} {T['kind']:4d} {T['cand']:4d} {T['clean']:5d} {T['unm']:3d}")
print(f"total suite runs over the {len(rep)} repaired fixtures (red precondition,"
      f" every candidate, confirm): {T['runs']}")
wasted = T["line"] + T["kind"] + T["cand"]
d = wasted or 1
print(f"WASTED runs (a candidate applied, suite red, before the winner): {wasted}")
print(f"  LINE dimension      (ranking law rules this) {T['line']:3d} = {100*T['line']//d}%")
print(f"  CLASS dimension     (no law rules this)      {T['kind']:3d} = {100*T['kind']//d}%")
print(f"  CANDIDATE dimension (dictionary order)       {T['cand']:3d} = {100*T['cand']//d}%")
print(f"  unmatched checks (attribution failed): {T['unm']}")

print("\n== the CLASS dimension: what order does the body use? ==")
print("loop.py:283  mask = mask_of(k for k in obs.kinds if 0 <= k <= 15)")
print("loop.py:297  kind = kind_of(EMIT(mask));  loop.py:298  mask = ADVANCE(mask)")
print("EMIT is m & -m -> lowest set bit -> classes are tried in ASCENDING KIND-ID")
print("order. Kind id is the number the dictionary registered the class under. It")
print("is not evidence, and rank.py never sees it: the ranking law ranks LINES.")

pos = Counter(f"{r['winner']['kind_position_in_line']}/{r['winner']['kinds_on_line']}" for r in rep)
print("\nwinning class's position among the classes on its own line (body order):",
      dict(sorted(pos.items())))
first = sum(v for k, v in pos.items() if k.split("/")[0] == "1")
print(f"winner was the FIRST class tried on its line in {first}/{len(rep)} fixtures;"
      f" NOT first in {len(rep)-first}")

print("\n== counterfactual: break the class tie by candidate-set size ==")
print("(CHEAP is measured per LINE at guard.py:401-403 over the first TWO kinds")
print(" only, and is never used to order kinds. Only sets the body actually tried")
print(" have a measured size, so this is a LOWER BOUND: a cheaper class that was")
print(" never reached could add runs. That part is unmeasured.)")
saved = 0
for r in rep:
    w = r["winner"]
    att = attribute(r)
    sizes = {}
    for c in r["candidate_calls"]:
        sizes.setdefault((c["lineno"], c["kind"]), c["n"])
    wn = sizes.get((w["lineno"], w["kind"]))
    if wn is None:
        continue
    for ln, k in att[: w["first_green_check"] - 1]:
        if ln == w["lineno"] and k != w["kind"] and sizes.get((ln, k), 0) > wn:
            saved += 1
print(f"wasted runs spent on a same-line class whose candidate set was LARGER"
      f" than the winner's: {saved} of {T['kind']}")

print("\n== which classes win, and which are tried without ever winning ==")
tried, wins = Counter(), Counter()
for r in runs:
    for c in r["candidate_calls"]:
        tried[c["kind"]] += c["n"]
    if r["winner"]:
        wins[r["winner"]["kind"]] += 1
print(f"{'kind':5s} {'candidates offered':18s} {'fixtures won':12s}")
for k in sorted(tried, key=lambda x: (x is None, x)):
    print(f"{k!s:5s} {tried[k]:18d} {wins.get(k, 0):12d}")
