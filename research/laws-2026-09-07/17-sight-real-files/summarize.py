#!/usr/bin/env python
"""Summarise results.jsonl: latest record per file. For every red defect,
the true file's rank under (a) the body's order (cguard_once candidates),
(b) the SIGHT law on the C-measured byte, (c) the SIGHT law with the SCARCE
bit forced off (the only shipped signal narrow enough to set it in C is
the Python-vocabulary `\\b(True|False)\\b`), recomputed from the persisted
per-file bytes. Prints a markdown table + top-1/top-3/median."""
import json, os, statistics, sys
sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix.sight import sight, observe_bits
HERE = os.path.dirname(os.path.abspath(__file__))
latest = {}
for line in open(os.path.join(HERE, "results.jsonl")):
    r = json.loads(line); latest[r["file"]] = r
recs = sorted(latest.values(), key=lambda r: r["n"])
N = int(sys.argv[1]) if len(sys.argv) > 1 else 20

def law_rank(r, drop=()):
    rows = r.get("rows")
    if not rows:
        return None
    keyed = []
    for rel, pri, n_fail, n_full, bits in rows:
        b = dict(bits)
        for k in drop: b[k] = False
        p = sight(observe_bits(**b))
        spec = n_fail / max(n_full, n_fail, 1)
        keyed.append((p, -(1.0 if b["named"] else 0.0), -spec, -n_fail, rel))
    keyed.sort()
    order = [k[4] for k in keyed]
    return order.index(r["file"]) + 1 if r["file"] in order else None

def stats(ranks, label):
    known = [x for x in ranks if x is not None]
    absent = sum(1 for x in ranks if x is None)
    top1 = sum(1 for x in known if x == 1); top3 = sum(1 for x in known if x <= 3)
    med = statistics.median(known) if known else None
    med_all = statistics.median([x if x is not None else 10**6 for x in ranks]) if ranks else None
    print(f"{label:34s} n={len(ranks)} top-1={top1} top-3={top3} median(ranked)={med} "
          f"absent={absent} median(absent counted as last)={med_all if med_all is None or med_all < 10**6 else 'absent'}")

print("| # | file:line | mutation | failing test(s) | body rank / len | law rank (measured) | law rank (SCARCE off) | true byte | spec>=0.9 share |")
print("|---|---|---|---|---|---|---|---|---|")
red, body_ranks, law_ranks, law2_ranks = [], [], [], []
for r in recs:
    if len(red) >= N: break
    if r["status"] != "refused":
        print(f"| {r['n']} | {r['file']}:{r['line']} | `{r['old'].strip()}`->`{r['new'].strip()}` | {r['status']}: {r.get('note','')[:60]} | - | - | - | - | - |")
        continue
    red.append(r)
    lr, lr2 = r.get("law_rank"), law_rank(r, drop=("scarce",))
    rows = r.get("rows") or []
    hi = sum(1 for _, _, nf, nu, _ in rows if nf / max(nu, nf, 1) >= 0.9)
    share = f"{hi}/{len(rows)}" if rows else "unmeasured"
    bits = r.get("true_bits") or {}
    on = ",".join(k.upper() for k, v in bits.items() if v) or ("absent" if not bits else "none")
    body_ranks.append(r.get("body_rank")); law_ranks.append(lr); law2_ranks.append(lr2)
    print(f"| {r['n']} | {r['file']}:{r['line']} | `{r['old'].strip()}`->`{r['new'].strip()}` | {', '.join(r.get('fail_tests') or ['(none reported)'])} "
          f"| {r.get('body_rank')} / {r.get('body_len')} | {lr} | {lr2} | {on} | {share} |")
print()
print(f"red defects counted: {len(red)}")
stats(body_ranks, "body order (cguard_once)")
stats(law_ranks, "SIGHT law, byte as measured")
stats(law2_ranks, "SIGHT law, SCARCE forced off")
