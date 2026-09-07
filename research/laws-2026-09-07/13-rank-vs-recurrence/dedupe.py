#!/usr/bin/env python
"""Third pass: unique (repo, old, new) pairs only (Box2D's history repeats
the same change on several branches), version-bump lines excluded from the
coarse counts, and the kind-order table recomputed on the unique set."""
import collections, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scan_history import KINDS, replay, loop_order, observed_kinds, act_for, candidates, Observation
HERE = os.path.dirname(os.path.abspath(__file__))
rows = json.load(open(os.path.join(HERE, "pairs_results.json")))
VERSION = re.compile(r"version", re.I)
uniq, seen = [], set()
for r in rows:
    key = (r["repo"], r["old"].strip(), r["new"].strip())
    if key in seen: continue
    seen.add(key); uniq.append(r)
print(f"paired lines: {len(rows)} -> unique (repo,old,new): {len(uniq)}")
for repo in ("box2d", "cglm"):
    c = collections.Counter(r["coarse"] for r in uniq if r["repo"] == repo
                            and r["coarse"] != "multi-token" and not VERSION.search(r["old"]))
    print(f"{repo}: coarse one-token labels, unique, version lines excluded: {dict(c.most_common())}")
    cc = collections.Counter(r["coarse"] for r in uniq if r["repo"] == repo and r["coarse"] != "multi-token"
                             and not VERSION.search(r["old"]) and not r["old"].strip().startswith(("//", "*", "/*", "#include")))
    print(f"{repo}: ... and comment/#include lines excluded: {dict(cc.most_common())}")
reach = [r for r in uniq if r["win_kind"] is not None]
print(f"reachable unique pairs: {len(reach)} "
      f"({collections.Counter(r['repo'] for r in reach)})")
print("winning class, unique pairs:", collections.Counter((r['repo'], KINDS[r['win_kind']][0]) for r in reach).most_common())
LOOP = loop_order()
def ncands(old, k):
    obs = Observation(lineno=1, kinds=[k])
    return len([c for c in candidates(old, act_for(k), obs) if isinstance(c, str) and c != old])
orders = {}
for r in reach:
    ks = observed_kinds(r["old"])
    same = [q for q in reach if q["repo"] == r["repo"] and q is not r]
    f_same = collections.Counter(q["win_kind"] for q in same)
    cost = {k: ncands(r["old"], k) for k in ks}
    for name, o in {
        "loop (kind id, lanes.EMIT)": LOOP,
        "recurrence same repo, LOO": sorted(KINDS, key=lambda k: (-f_same[k], k)),
        "cheapest kind first": sorted(KINDS, key=lambda k: (cost.get(k, 0), k)),
        "winner first (oracle bound)": [r["win_kind"]] + [k for k in LOOP if k != r["win_kind"]],
    }.items():
        pos, _, _ = replay(r["old"], r["new"], o)
        orders.setdefault(name, collections.Counter())[r["repo"]] += pos
        orders[name]["total"] += pos
        orders[name]["n"] += 1
print("\n=== candidates tried on the defect line before the exact fix, unique reachable pairs ===")
for name, c in orders.items():
    print(f"  {name:32} box2d={c['box2d']:3} cglm={c['cglm']:3} total={c['total']:3}  (n={c['n']//1})")
# how many unique reachable pairs have >1 kind on the line (order can matter at all)
multi = [r for r in reach if len(observed_kinds(r["old"])) > 1]
print(f"unique reachable pairs with >1 kind on the line (order can matter): {len(multi)} of {len(reach)}")
for r in multi:
    print(f"   {r['repo']:6} {r['sha']} kinds={observed_kinds(r['old'])} win={KINDS[r['win_kind']][0]} pos_loop={r['pos_loop']} | {r['old'].strip()[:60]}")
