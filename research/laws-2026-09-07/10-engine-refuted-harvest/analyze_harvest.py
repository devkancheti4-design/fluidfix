"""What the harvest actually carries: reads a .fluidfix/last_refusal.json
and tabulates information content. usage: analyze_harvest.py <json> [defect_at]"""
import json, sys
from collections import Counter
j = json.load(open(sys.argv[1]))
want = sys.argv[2] if len(sys.argv) > 2 else None
rc = j.get("rejected_candidates", [])
print("status:", j.get("status"), " seconds:", j.get("seconds"))
print("hint:", (j.get("hint") or "")[:200])
print("candidate files:", j.get("candidates"))
print("rejected_candidates persisted:", len(rc))
whys = Counter(e["why"] for e in rc)
print("distinct 'why' values:", len(whys))
for w, n in whys.most_common(12):
    print(f"  {n:4d}  {w[:120]!r}")
files = Counter(e["at"].split(":")[0] for e in rc)
print("entries per file:", dict(files))
sites = sorted({e["at"] for e in rc})
print("distinct sites:", len(sites), " first/last:", sites[:3], sites[-3:])
if want:
    hit = [e for e in rc if e["at"] == want]
    print(f"entries at the defect site {want}: {len(hit)}")
    for e in hit[:5]:
        print("   ", e["tried"][:100], "->", e["why"][:80])
