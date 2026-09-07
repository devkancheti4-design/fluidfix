#!/usr/bin/env python
"""Tabulate the sweep: one row per fixture_<budget>/rulings.json (+ *.out for
runs the 300s timeout killed before rulings.json was written)."""
import glob
import json
import os
import re

here = os.path.dirname(os.path.abspath(__file__))
rows = []
for d in sorted(glob.glob(os.path.join(here, "fixture_[0-9]*")),
                key=lambda p: int(re.search(r"fixture_(\d+)", p).group(1))):
    b = int(re.search(r"fixture_(\d+)", d).group(1))
    rj = os.path.join(d, "rulings.json")
    out = os.path.join(here, f"sweep_{b}.out")
    if os.path.exists(rj):
        j = json.load(open(rj))
        r = j["rulings"]
        gate = next((x for x in r if x["caller"].startswith("guard.py:539")), None)
        final = r[-1] if r else None
        first_pass_end = gate["t"] if gate else None
        first_pass_runs = gate["suite_runs_so_far"] if gate else None
        rows.append((b, j["status"], round(j["elapsed"], 1), first_pass_end, first_pass_runs,
                     j["runs"]["check"], j["runs"]["check_green"],
                     f"{final['bits']}->{final['ruling']}@{final['caller']}" if final else "-",
                     (j.get("reason") or j.get("hint") or "")[:90]))
    else:
        txt = open(out).read() if os.path.exists(out) else ""
        killed = "[timeout.py]" in txt
        greens = txt.count("GREEN ")
        last = [l for l in txt.splitlines() if "RULING" in l]
        rows.append((b, "KILLED by timeout 300" if killed else "no result", "-", "-", "-",
                     "-", greens, last[-1].strip()[:80] if last else "-", ""))

hdr = ("budget", "status", "elapsed_s", "first_pass_end_s", "first_pass_runs",
       "suite_runs", "greens", "final ruling", "reason/hint")
print("| " + " | ".join(hdr) + " |")
print("|" + "---|" * len(hdr))
for row in rows:
    print("| " + " | ".join(str(c) for c in row) + " |")
