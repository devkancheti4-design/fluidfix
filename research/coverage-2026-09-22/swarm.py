#!/usr/bin/env python3
"""Union the nets. Reports coverage against ALL mined fixes, not only the ones that were reachable."""
import json, subprocess, sys
from collections import Counter
from pathlib import Path
R = Path(__file__).resolve().parents[2]
NETS = ["shipped",
        "examples/taught-2026-09-16/rules_session.py", "examples/taught-2026-09-16/rules_session_b.py",
        "examples/taught-2026-09-19/corpus.py", "examples/taught-2026-09-19/spans.py",
        "examples/taught-2026-09-19/literal_either_way.py", "examples/taught-2026-09-19/combined.py"]
rows = json.load(open(R / "research/real-history-2026-09-19/remine.json"))["rows"]
one = [i for i, r in enumerate(rows) if len(r["minus"]) == 1 and r["plus"]]
small = [i for i, r in enumerate(rows) if len(r["minus"]) + len(r["plus"]) <= 10]

rec_all, reach_all, per = set(), {}, []
for n in NETS:
    out = subprocess.run([sys.executable, str(R / "research/coverage-2026-09-22/census.py"), n],
                         capture_output=True, text=True, cwd=R).stdout.strip().splitlines()[-1]
    d = json.loads(out)
    rec, rch = set(d["recognised"]), {i: (k, nm) for i, k, nm in d["reached"]}
    per.append((n.split("/")[-1], len(rec), len(rch)))
    rec_all |= rec
    for i, v in rch.items(): reach_all.setdefault(i, v)

print(f"mined real fixes                       {len(rows)}")
print(f"  removed side is one line             {len(one)}")
print(f"  whole diff is 10 lines or fewer      {len(small)}")
print()
print(f"{'net':28} {'recognises':>10} {'reaches':>8}")
for n, a, b in per: print(f"{n:28} {a:>10} {b:>8}")
print(f"{'SWARM (union)':28} {len(rec_all):>10} {len(reach_all):>8}")
print()
print(f"coverage, the knowledge question only (no suite ran):")
print(f"  of the {len(one)} one-line fixes            {len(reach_all)}  ({100*len(reach_all)/max(1,len(one)):.1f}%)")
print(f"  of all {len(rows)} real fixes             {len(reach_all)}  ({100*len(reach_all)/len(rows):.1f}%)")
print()
print("what it reached, by class:")
for (k, nm), c in Counter(reach_all.values()).most_common(): print(f"  kind {k:<2} {nm:36} {c}")
print()
print("reached fixes:")
for i, (k, nm) in sorted(reach_all.items()):
    r = rows[i]; print(f"  {r['repo']:22} {r['sha'][:10]}  {r['minus'][0].strip()[:38]:38} -> {' | '.join(p.strip() for p in r['plus'])[:40]}")
json.dump({"one_line": len(one), "total": len(rows), "reached": sorted(reach_all), "per_net": per},
          open(R / "research/coverage-2026-09-22/coverage.json", "w"), indent=1)
