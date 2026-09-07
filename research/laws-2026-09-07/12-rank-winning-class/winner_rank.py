#!/usr/bin/env python
"""The target's headline number: the distribution of the RANK OF THE WINNER,
plus how well each priority class predicts the winner (precision/recall over
the fixture set). Pure post-processing; no suite runs."""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
runs = [json.loads(p.read_text()) for p in sorted(HERE.glob("log/*.json"))]
runs = [r for r in runs if r["group"] != "heavy"]
rep = [r for r in runs if r["status"] == "repaired"]


def winning_table(r):
    """the ranking call that governed the file the repair landed in"""
    return next((c for c in reversed(r["rank_calls"]) if c["rel"] == r["file"]), None)


print("== distribution of the rank of the winner (27 repaired fixtures) ==")
print("law priority of the winning line:",
      dict(sorted(Counter(r["winner"]["law_priority"] for r in rep).items())))
print("winner's position in the law's RANKED order:",
      dict(sorted(Counter(r["winner"]["position_ranked"] for r in rep).items())))
print("winner's position in raw LINE order (what you get with no law):",
      dict(sorted(Counter(r["winner"]["position_input"] for r in rep).items())))
print("winner's bits:", dict(Counter(r["winner"]["bits"] for r in rep).most_common()))

print("\n== does a priority class predict the winner? ==")
print("counted over the governing ranking table of each repaired fixture")
tp = Counter(); fp = Counter(); tables = 0
for r in rep:
    t = winning_table(r)
    if t is None:
        continue
    tables += 1
    wl = r["winner"]["lineno"]
    for row in t["rows"]:
        (tp if row["lineno"] == wl else fp)[row["priority"]] += 1
print(f"governing tables: {tables}")
print(f"{'priority':9s} {'observations':13s} {'were the winner':16s} precision")
for p in sorted(set(tp) | set(fp)):
    n = tp[p] + fp[p]
    print(f"{p:<9d} {n:<13d} {tp[p]:<16d} {tp[p]}/{n} = {100*tp[p]//n}%")

print("\n== when the law gave NO discrimination (all observations same priority) ==")
flat = [r for r in rep if winning_table(r)
        and len({x["priority"] for x in winning_table(r)["rows"]}) == 1]
print(f"fixtures whose governing table is a single flat priority class: {len(flat)}/{tables}")
print("  of those, winner already first in line order:",
      sum(1 for r in flat if r["winner"]["position_input"] == 1), "/", len(flat))
print("  fixture / n_obs / winner input pos:",
      [(r["name"], r["winner"]["n_obs"], r["winner"]["position_input"]) for r in flat])

print("\n== where the law actually MOVED the winner up ==")
moved = [(r["name"], r["winner"]["position_input"], r["winner"]["position_ranked"])
         for r in rep if r["winner"]["position_input"] != r["winner"]["position_ranked"]]
print(f"{len(moved)}/{len(rep)} fixtures:", moved)
print("suite runs those moves saved (each skipped line costs its candidate sets):")
tot = 0
for r in rep:
    w = r["winner"]
    if w["position_input"] == w["position_ranked"]:
        continue
    t = winning_table(r)
    order = t["input_order"]
    ahead = order[: order.index(w["lineno"])]
    ranked_ahead = [x["lineno"] for x in t["rows"][: w["position_ranked"] - 1]]
    skipped = [l for l in ahead if l not in ranked_ahead]
    cost = sum(c["n"] for c in r["candidate_calls"] if c["lineno"] in skipped)
    n_sets = sum(1 for c in r["candidate_calls"] if c["lineno"] in skipped)
    tot += len(skipped)
    print(f"  {r['name']:24s} lines jumped: {skipped}"
          f"  (candidate sets those lines were later asked for: {n_sets}, candidates: {cost})")
print(f"lines the law jumped over, total: {tot}")
print("NOTE: a line the law demoted below the winner is usually never asked for a")
print("candidate set at all, so its avoided cost is not in this log -> unmeasured.")

print("\n== refusals: the ranking the law produced before the engine law stopped ==")
for r in runs:
    if r["status"] == "repaired":
        continue
    tbl = [(c["rel"], [(x["lineno"], x["priority"], x["bits"]) for x in c["rows"]])
           for c in r["rank_calls"]]
    print(f"{r['name']:26s} status={r['status']} runs={r['suite_runs']}")
    for rel, rows in tbl:
        print(f"    {rel}: {rows}")
