"""Summarise results_<fixture>.jsonl into a table. Usage: summarize.py fixture_a"""
import json, os, sys
from collections import Counter, defaultdict
HERE = os.path.dirname(os.path.abspath(__file__))
fx = sys.argv[1]
rows = [json.loads(l) for l in open(os.path.join(HERE, f"results_{fx}.jsonl"))]
by = defaultdict(list)
for r in rows:
    by[r["confirm"]].append(r)
print(f"{fx}: {len(rows)} runs")
print(f"{'CONFIRM':>7} {'N':>3} {'CORRECT':>8} {'FALSE_ACC':>9} {'REF_AMB':>7} "
      f"{'REFUSED':>7} {'GREEN_AB':>8} {'other':>5} | {'hidden fired':>12} "
      f"{'mean suite_runs':>15} {'mean wall s':>11}")
for c in sorted(by):
    rs = by[c]
    cnt = Counter(r["label"] for r in rs)
    other = sum(v for k, v in cnt.items() if k not in
                ("CORRECT", "FALSE_ACCEPT", "REFUSED_AMB", "REFUSED", "GREEN_ABORT"))
    hid = sum(r["hidden_fired"] for r in rs)
    sr = [r["suite_runs"] for r in rs if r["suite_runs"] is not None]
    msr = sum(sr) / len(sr) if sr else float("nan")
    mw = sum(r["wall_s"] for r in rs) / len(rs)
    print(f"{c:>7} {len(rs):>3} {cnt['CORRECT']:>8} {cnt['FALSE_ACCEPT']:>9} "
          f"{cnt['REFUSED_AMB']:>7} {cnt['REFUSED']:>7} {cnt['GREEN_ABORT']:>8} "
          f"{other:>5} | {hid:>12} {msr:>15.2f} {mw:>11.2f}")
    fa = cnt["FALSE_ACCEPT"]
    print(f"        false-accept rate = {fa}/{len(rs)} = {100*fa/len(rs):.1f}%   "
          f"correct-repair rate = {cnt['CORRECT']}/{len(rs)} = {100*cnt['CORRECT']/len(rs):.1f}%")
    # which candidate the HIDDEN lane fired on
    hc = Counter(t["tried"].strip() for r in rs for t in r["tried"]
                 if "HIDDEN -> CHANGE_GRANULARITY" in t["why"])
    if hc:
        print(f"        HIDDEN fired on: {dict(hc)}")
