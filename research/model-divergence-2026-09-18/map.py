#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Map every model's distribution over the same inputs, and ask what one model's uncertainty predicts.

`sampling.py` gives, per model and per input, the distribution of answers over 20 draws. Laying those maps
on top of each other asks a question worth more than any single map:

    when ONE model is internally split on an input, is that input also contested BETWEEN models?

If it is, spec ambiguity is detectable with a single model and no ground truth — draw twenty times, and the
inputs your own samples disagree on are the inputs your prose failed to pin down. If it is not, within-model
spread is idiosyncrasy and says nothing about the specification.

Reported alongside: how PEAKED each model is (normalised entropy over its own answers), and whether the
models' modal answers agree at all.

  python3 map.py
"""
from __future__ import annotations

import json, math
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent


def entropy(counts: dict) -> float:
    n = sum(counts.values())
    if n <= 1 or len(counts) <= 1:
        return 0.0
    h = -sum((c / n) * math.log2(c / n) for c in counts.values() if c)
    return h / math.log2(len(counts)) if len(counts) > 1 else 0.0


def main():
    runs = {}
    for f in sorted(HERE.glob("sampling_*.json")):
        d = json.load(open(f))
        runs[d["model"]] = {s["spec"]: s for s in d["specs"]}
    models = sorted(runs)
    if len(models) < 2:
        print("need at least two sampling runs"); return
    print(f"models: {', '.join(models)}\n")

    # ---------------------------------------------------------- per-model sharpness
    print(f"{'model':20} {'pass':>8} {'programs':>9} {'behaviours':>11} {'mean entropy':>13} "
          f"{'inputs it is split on':>22}")
    sharp = {}
    for m in models:
        specs = runs[m]
        tot_pass = sum(s["passed"] for s in specs.values())
        tot_n = sum(s["n"] for s in specs.values())
        progs = sum(s["distinct_texts"] for s in specs.values())
        behs = sum(s["distinct_behaviours"] for s in specs.values())
        ents, split, allin = [], 0, 0
        for s in specs.values():
            for e in s.get("per_input", []):
                if not e["answers"]:
                    continue
                allin += 1
                ents.append(entropy(e["answers"]))
                split += len(e["answers"]) > 1
        sharp[m] = {"pass": f"{tot_pass}/{tot_n}", "programs": progs, "behaviours": behs,
                    "mean_entropy": round(sum(ents) / len(ents), 3) if ents else 0.0,
                    "split": split, "inputs": allin}
        print(f"{m:20} {sharp[m]['pass']:>8} {progs:>9} {behs:>11} "
              f"{sharp[m]['mean_entropy']:>13.3f} {f'{split} of {allin}':>22}")

    # ---------------------------------------------------------- the prediction test
    rows, table = [], Counter()
    for spec in sorted(set().union(*[set(runs[m]) for m in models])):
        present = [m for m in models if spec in runs[m]]
        if len(present) < 2:
            continue
        maps = {m: {json.dumps(e["input"]): e["answers"] for e in runs[m][spec].get("per_input", [])}
                for m in present}
        keys = set.intersection(*[set(maps[m]) for m in present])
        for k in sorted(keys):
            dists = {m: maps[m][k] for m in present if maps[m][k]}
            if len(dists) < 2:
                continue
            within = any(len(d) > 1 for d in dists.values())
            modal = {m: max(d.items(), key=lambda kv: kv[1])[0] for m, d in dists.items()}
            across = len(set(modal.values())) > 1
            table[(within, across)] += 1
            rows.append({"spec": spec, "input": json.loads(k), "within_split": within,
                         "across_split": across, "modal": modal,
                         "dists": {m: d for m, d in dists.items()}})

    a = table[(True, True)]; b = table[(True, False)]; c = table[(False, True)]; d = table[(False, False)]
    p_given_split = a / (a + b) if a + b else 0.0
    p_given_agree = c / (c + d) if c + d else 0.0
    print(f"\nDoes one model's internal split predict disagreement BETWEEN models?  "
          f"({a + b + c + d} shared inputs)")
    print(f"  {'':34}{'models disagree':>17}{'models agree':>15}")
    print(f"  at least one model internally split {a:>13}{b:>15}   -> {p_given_split:.0%} disagree")
    print(f"  every model internally unanimous    {c:>13}{d:>15}   -> {p_given_agree:.0%} disagree")
    lift = (p_given_split / p_given_agree) if p_given_agree else float("inf")
    print(f"  lift: {lift:.1f}x" if p_given_agree else "  lift: infinite (unanimity never disagreed)")

    (HERE / "map.json").write_text(json.dumps(
        {"models": models, "sharpness": sharp,
         "contingency": {"split_and_disagree": a, "split_but_agree": b,
                         "unanimous_but_disagree": c, "unanimous_and_agree": d},
         "p_disagree_given_split": round(p_given_split, 3),
         "p_disagree_given_unanimous": round(p_given_agree, 3),
         "rows": rows}, indent=1, default=str))

    print("\nInputs every model is UNANIMOUS on yet the models still disagree "
          "(single-model sampling would miss these):")
    missed = [r for r in rows if not r["within_split"] and r["across_split"]]
    for r in missed[:12]:
        print(f"  {r['spec']:16} {str(r['input'])[:30]:30} " +
              ", ".join(f"{m.split(':')[0]}={str(v)[:18]}" for m, v in sorted(r["modal"].items())))
    print(f"  ... {len(missed)} in total" if len(missed) > 12 else f"  {len(missed)} in total")
    print("MAP_DONE")


if __name__ == "__main__":
    main()
