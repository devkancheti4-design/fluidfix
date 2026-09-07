#!/usr/bin/env python
"""Aggregate log/*.json from rank_winners.py into the distributions the
report quotes. Pure post-processing: no suite runs."""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent.parent / "src"))
from fluidfix.acts import KINDS   # noqa: E402

logs = sorted(HERE.glob("log/*.json"))
runs = [json.loads(p.read_text()) for p in logs]
runs = [r for r in runs if r["group"] != "heavy"]

print(f"fixtures logged: {len(runs)}  (heavy group excluded here)")
rep = [r for r in runs if r["status"] == "repaired"]
ref = [r for r in runs if r["status"] != "repaired"]
print(f"repaired: {len(rep)}   refused: {len(ref)}")
mism = [(r["name"], r["expect"], r["status"]) for r in runs if r["expect"] != r["status"]]
print(f"outcome != what the source test expects: {mism}")

print("\n== per-observation bits over every rank_observations call (all fixtures) ==")
bits_c, prio_c, n_obs = Counter(), Counter(), 0
for r in runs:
    for c in r["rank_calls"]:
        for row in c["rows"]:
            n_obs += 1
            prio_c[row["priority"]] += 1
            for b in row["bits"].split("+"):
                bits_c[b] += 1
print(f"observations ranked: {n_obs}")
print("bit set count:", dict(sorted(bits_c.items(), key=lambda kv: -kv[1])))
print("priority histogram:", dict(sorted(prio_c.items())))

print("\n== rank of the winner (repaired fixtures) ==")
W = [r["winner"] for r in rep]
print("law priority of winner line:", dict(sorted(Counter(w["law_priority"] for w in W).items())))
print("winner bits:", dict(Counter(w["bits"] for w in W).most_common()))
print("position of winner line in RANKED order:", dict(sorted(Counter(w["position_ranked"] for w in W).items())))
print("position of winner line in INPUT (line) order:", dict(sorted(Counter(w["position_input"] for w in W).items())))
print("observations in the winner's packet:", dict(sorted(Counter(w["n_obs"] for w in W).items())))
print("same-priority lines ahead of winner:", dict(sorted(Counter(w["same_priority_ahead"] for w in W).items())))
print("better-priority lines ahead of winner:", dict(sorted(Counter(w["better_priority_ahead"] for w in W).items())))
print("winning kind's position among kinds on its line:",
      dict(sorted(Counter(f"{w['kind_position_in_line']}/{w['kinds_on_line']}" for w in W).items())))
print("class-slot position (line,kind) in body order:",
      dict(sorted(Counter(f"{w['class_slot_position']}/{w['class_slots_total']}" for w in W).items())))
moved = [(r["name"], r["winner"]["position_input"], r["winner"]["position_ranked"]) for r in rep
         if r["winner"]["position_input"] != r["winner"]["position_ranked"]]
print("fixtures where the law moved the winner line (input_pos -> ranked_pos):", moved)

print("\n== suite checks spent before the winner's first green ==")
tot_wasted = tot_other_line = tot_other_kind = tot_same_kind = 0
rows = []
for r in rep:
    w = r["winner"]
    checks = r["checks"]
    fg = w["first_green_check"]
    wasted = checks[: fg - 1]
    # classify each wasted check by (line, kind) using the candidate log
    def locate(ch):
        if not ch["changed"]:
            return (None, None)
        old = ch["changed"][0]["old_lines"]
        ln = int(old.split("-")[0])
        new = ch["changed"][0]["new"]
        for c in r["candidate_calls"]:
            if c["lineno"] == ln or any(cc.startswith("SPAN[") for cc in c["cands"]):
                for cand in c["cands"]:
                    text = cand.split("]", 1)[1] if cand.startswith("SPAN[") else cand
                    if text.strip().replace("\n", "\\n")[:90] == new or text.strip()[:90] == new:
                        return (c["lineno"], c["kind"])
        return (ln, None)
    other_line = other_kind = same_kind = 0
    for ch in wasted:
        ln, k = locate(ch)
        if ln != w["lineno"]:
            other_line += 1
        elif k != w["kind"]:
            other_kind += 1
        else:
            same_kind += 1
    tot_wasted += len(wasted); tot_other_line += other_line
    tot_other_kind += other_kind; tot_same_kind += same_kind
    rows.append((r["name"], r["suite_runs"], len(wasted), other_line, other_kind, same_kind))
print(f"{'fixture':26s} runs wasted  other_line other_kind same_kind")
for nm, runs_, wd, ol, ok_, sk in rows:
    print(f"{nm:26s} {runs_:4d} {wd:6d}  {ol:10d} {ok_:10d} {sk:9d}")
print(f"TOTAL wasted checks before winner: {tot_wasted} = other line {tot_other_line}"
      f" + other kind on winner line {tot_other_kind} + earlier candidate of winning kind {tot_same_kind}")
print(f"total suite runs (incl. red precondition + confirm): {sum(r['suite_runs'] for r in rep)}")

print("\n== per class: how the law ranked its observation slots, and wins ==")
slots = defaultdict(lambda: {"slots": 0, "prio": Counter(), "wins": 0, "tried": 0})
for r in runs:
    names = {int(k): v for k, v in r["taught"].items()}
    for c in r["rank_calls"]:
        for row in c["rows"]:
            for k, cl in zip(row["kinds"], row["classes"]):
                key = f"{k}:{cl}"
                slots[key]["slots"] += 1
                slots[key]["prio"][row["priority"]] += 1
    for c in r["candidate_calls"]:
        k = c["kind"]
        cl = KINDS[k][0] if k in KINDS else names.get(k, "?")
        slots[f"{k}:{cl}"]["tried"] += 1
    if r["winner"]:
        k = r["winner"]["kind"]
        slots[f"{k}:{r['winner']['class']}"]["wins"] += 1
print(f"{'kind:class':30s} slots  prio-hist        cand-sets-tried wins")
for key in sorted(slots, key=lambda s: int(s.split(':')[0])):
    s = slots[key]
    print(f"{key:30s} {s['slots']:5d}  {dict(sorted(s['prio'].items()))!s:16s} {s['tried']:8d} {s['wins']:8d}")

print("\n== refusals: what the law ruled ==")
for r in ref:
    print(f"{r['name']:26s} runs={r['suite_runs']} hint={r['hint'][:110]!r}")
