#!/usr/bin/env python
"""Where the repaired/refused threshold actually sits, and which constant sets it.

Pure arithmetic over the recorded fixture_<B>/rulings.json — runs no suite.

Two candidate constants could cut the escalation search:
  (a) total_deadline  = t0 + budget                    (guard.py:439/548-550)
  (b) file_share cap  = now + (deadline - now) / 2     (guard.py:591-592)
      "one file gets at most half the escalation budget" (depth-first
      starvation guard, adversarial review 2026-08-31)
This script predicts the escalation cut time under each and compares it to
the observed time of the last ruling, so the reader can see which one binds.
"""
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
    if not os.path.exists(rj):
        continue
    j = json.load(open(rj))
    r = j["rulings"]
    gate = next((x for x in r if x["caller"].startswith("guard.py:539")), None)
    t1 = gate["t"] if gate else None            # first pass ended here
    last = r[-1]
    pred_total = float(b)                        # (a)
    pred_share = t1 + (b - t1) / 2 if t1 is not None else None   # (b)
    rows.append(dict(budget=b, status=j["status"], t1=t1,
                     first_pass_runs=gate["suite_runs_so_far"] if gate else None,
                     end=round(j["elapsed"], 1), runs=j["runs"]["check"],
                     pred_total=pred_total,
                     pred_share=round(pred_share, 1) if pred_share else None,
                     last=f"{last['bits']} (0x{last['byte']:02x}) -> {last['ruling']}"))

hdr = ["budget", "status", "first_pass_end_s", "first_pass_runs", "end_s",
       "suite_runs", "cut predicted by total_deadline", "cut predicted by file_share/2",
       "last ruling"]
print("| " + " | ".join(hdr) + " |")
print("|" + "---|" * len(hdr))
for x in rows:
    print("| {budget} | {status} | {t1} | {first_pass_runs} | {end} | {runs} | "
          "{pred_total} | {pred_share} | {last} |".format(**x))

print()
# The escalation search needs W seconds of work after the first pass ends.
# Take W from the runs that FINISHED it (status == repaired).
done = [x for x in rows if x["status"] == "repaired"]
if done:
    Ws = [(x["budget"], round(x["end"] - x["t1"], 1)) for x in done]
    print("escalation work W = end - first_pass_end, on the runs that finished it:")
    for b, w in Ws:
        print(f"  budget={b}: W={w}s")
    wmin, wmax = min(w for _, w in Ws), max(w for _, w in Ws)
    print(f"  W range on this loaded machine: {wmin}s .. {wmax}s "
          f"(same 804 suite runs every time)")
    print()
    print("file_share/2 binds when  W > (budget - t1)/2, i.e. budget < t1 + 2W.")
    t1s = [x["t1"] for x in rows if x["t1"] is not None]
    t1lo, t1hi = min(t1s), max(t1s)
    print(f"  t1 (first pass, 110 runs) measured range: {t1lo}s .. {t1hi}s")
    print(f"  => threshold budget = t1 + 2W  in  "
          f"[{t1lo + 2 * wmin:.0f}s .. {t1hi + 2 * wmax:.0f}s]")
    print(f"  total_deadline alone would put the threshold at t1 + W = "
          f"[{t1lo + wmin:.0f}s .. {t1hi + wmax:.0f}s]")
print()
print("observed bracket:", ", ".join(
    f"{x['budget']}={x['status']}" for x in rows))
