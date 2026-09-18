#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Is the CLASS earning its place in a node's address? A replay over the rulings already recorded.

A net node is addressed by (territory, class, line range). The class comes from fluidfix's own vocabulary,
so an author from outside that vocabulary — a model writing a whole-function rewrite — has no class to be
addressed by. That matters now that the judge has been measured on external patches
(`../certify-2026-09-18`): if the address needs the vocabulary, the net cannot dispatch anyone else.

So: what would the same search have cost addressed by TERRITORY alone? Nothing is re-run. Every number here
comes out of the recorded `nodes_detail` of runs that actually happened — the order territories were first
touched, and what each node cost in suite runs. A territory-only node must try every class in that file, so
its cost is the sum of that file's class-nodes; only the classes the recorded run happened to try are
counted, which makes every figure below a LOWER BOUND.

  python3 addressing.py
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNS = ["net_rich_lenm1-1.json", "net_rich_notdrop-1.json", "net_arrow_lenm1-1.json"]


def replay(path: Path) -> dict:
    d = json.load(open(path))
    nd = d["nodes_detail"]                    # insertion order IS the order the nodes ran
    order, seen, per = [], set(), {}
    for k, v in nd.items():
        rel = k.split("|")[0]
        if rel not in seen:
            seen.add(rel)
            order.append(rel)
        p = per.setdefault(rel, {"runs": 0, "classes": 0, "secs": 0.0})
        p["runs"] += v["suite_runs"]; p["classes"] += 1; p["secs"] += v["seconds"]
    wrel = d["winner"][0]
    upto = order[: order.index(wrel) + 1]
    return {"case": d["case"], "memory_before": d["memory_before"],
            "pairs_possible": d["every_pair_would_be"],
            "class_nodes": d["nodes"], "class_runs": d["suite_runs"], "wall_s": d["wall_s"],
            "territories_touched": len(order), "winner_territory": wrel,
            "territory_rank": order.index(wrel) + 1,
            "territory_runs_lower_bound": sum(per[t]["runs"] for t in upto),
            "classes_tried_per_territory": {t: per[t]["classes"] for t in upto}}


def main():
    out = [replay(HERE / r) for r in RUNS]
    (HERE / "addressing.json").write_text(json.dumps(out, indent=2))
    print(f"{'case':22} {'memory':8} {'class-addressed':>22} {'territory-addressed':>26}")
    for r in out:
        print(f"{r['case']:22} {str(r['memory_before']):8} "
              f"{r['class_nodes']:>4} nodes /{r['class_runs']:>4} runs   "
              f"{r['territory_rank']:>4} of {r['territories_touched']:<3} /"
              f"{r['territory_runs_lower_bound']:>4} runs (>=)")
    print("\nA territory-only address drops the vocabulary out of the node identity, which is what an "
          "external\nauthor would require. Lower bounds: only the classes each recorded run happened to try "
          "are counted.")


if __name__ == "__main__":
    main()
