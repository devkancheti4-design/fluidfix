"""Render the measured results as a markdown table from results/*.json."""
import glob
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ORDER = ["g0", "g1c1", "g1c2", "g1c4", "g2", "g3"]
NAME = {"g0": "rung 0  suite, 1 run (CONFIRM=0)",
        "g1c1": "rung 1  suite, 1+1 runs (CONFIRM=1, shipped default)",
        "g1c2": "rung 1  suite, 1+2 runs (CONFIRM=2)",
        "g1c4": "rung 1  suite, 1+4 runs (CONFIRM=4)",
        "g2": "rung 2  per-test record, 1 run",
        "g3": "rung 3  per-test record + k=4 fine records per target"}
BUCKETS = ["CORRECT", "FALSE_ACCEPT", "REFUSED", "NO_FAILING_TEST",
           "HARNESS_ERROR"]

for shape in ("A", "B"):
    print(f"\n### shape {shape}\n")
    print("| config | n | CORRECT | FALSE_ACCEPT | REFUSED | NO_FAILING_TEST "
          "| pytest invocations/search (full+node) | s/search |")
    print("|---|---|---|---|---|---|---|---|")
    for c in ORDER:
        p = os.path.join(HERE, "results", f"shape{shape}_{c}.json")
        if not os.path.exists(p):
            continue
        d = json.load(open(p))
        n = d["trials"]
        g = d["counts"]
        cells = []
        for b in BUCKETS[:4]:
            v = g.get(b, 0)
            cells.append(f"{v} ({100.0*v/n:.0f}%)")
        print(f"| {NAME[c]} | {n} | " + " | ".join(cells) +
              f" | {d['mean_invocations']} "
              f"({d['mean_full_runs']}+{d['mean_node_runs']}) "
              f"| {d['mean_seconds']} |")
