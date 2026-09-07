#!/usr/bin/env python
"""Second pass over pairs_results.json (no git, no suite): more kind orders,
per-commit view, and the direction of the unreachable off-by-one pairs."""
import collections, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scan_history import KINDS, replay, loop_order, observed_kinds, act_for, candidates, Observation
HERE = os.path.dirname(os.path.abspath(__file__))
rows = json.load(open(os.path.join(HERE, "pairs_results.json")))
reach = [r for r in rows if r["win_kind"] is not None]
LOOP = loop_order()

def ncands(old, k):
    obs = Observation(lineno=1, kinds=[k])
    return len([c for c in candidates(old, act_for(k), obs) if isinstance(c, str) and c != old])

orders = {}
for r in reach:
    ks = observed_kinds(r["old"])
    same = [q for q in reach if q["repo"] == r["repo"] and q is not r]
    pooled = [q for q in reach if q is not r]
    f_same = collections.Counter(q["win_kind"] for q in same)
    f_pool = collections.Counter(q["win_kind"] for q in pooled)
    # per-COMMIT recurrence (one vote per commit, not per line)
    f_commit = collections.Counter()
    for sha, k in {(q["sha"], q["win_kind"]) for q in same}:
        f_commit[k] += 1
    cost = {k: ncands(r["old"], k) for k in ks}
    cand_orders = {
        "loop (kind id, lanes.EMIT)": LOOP,
        "recurrence per line, same repo, LOO": sorted(KINDS, key=lambda k: (-f_same[k], k)),
        "recurrence per commit, same repo, LOO": sorted(KINDS, key=lambda k: (-f_commit[k], k)),
        "recurrence pooled both repos, LOO": sorted(KINDS, key=lambda k: (-f_pool[k], k)),
        "cheapest kind first (fewest candidates on this line)": sorted(KINDS, key=lambda k: (cost.get(k, 0), k)),
        "winner first (oracle bound)": [r["win_kind"]] + [k for k in LOOP if k != r["win_kind"]],
    }
    for name, o in cand_orders.items():
        pos, _, _ = replay(r["old"], r["new"], o)
        orders.setdefault(name, collections.Counter())[r["repo"]] += pos
        orders[name]["total"] += pos

print("=== suite runs on the defect line, summed over the 52 reachable pairs ===")
for name, c in orders.items():
    print(f"  {name:55} box2d={c['box2d']:3} cglm={c['cglm']:3} total={c['total']:3}")

print("\n=== per-COMMIT view of the reachable pairs (one row per commit) ===")
bycommit = collections.OrderedDict()
for r in reach:
    bycommit.setdefault((r["repo"], r["sha"]), []).append(r)
print(f"{'repo':6} {'sha':10} {'lines':>5} {'winning kinds':40} subject")
for (repo, sha), rs in bycommit.items():
    ks = sorted({KINDS[r['win_kind']][0] for r in rs})
    print(f"{repo:6} {sha:10} {len(rs):>5} {','.join(ks):40} {rs[0]['subject'][:60]}")
print("distinct commits:", collections.Counter(repo for repo, _ in bycommit))
print("winning class by distinct commit:",
      collections.Counter((repo, KINDS[r['win_kind']][0]) for (repo, sha), rs in bycommit.items() for r in rs[:1]))

print("\n=== off-by-one labeled pairs: direction of the maintainer's fix ===")
d = collections.Counter()
for r in rows:
    if r["coarse"] == "off-by-one":
        p, q = r["tok"]
        pi, qi = int(re.sub(r"\D", "", p)), int(re.sub(r"\D", "", q))
        direction = "fix DECREMENTS (bug = correct+1; shipped class)" if qi < pi else "fix INCREMENTS (bug = correct-1; NO shipped class)"
        d[(r["repo"], direction, "reachable" if r["win_kind"] is not None else "unreachable")] += 1
for k, v in sorted(d.items()):
    print(f"  {k[0]:6} {k[1]:52} {k[2]:12} {v}")
print("\nunreachable DECREMENT off-by-one pairs (why did the shipped applier miss?):")
for r in rows:
    if r["coarse"] == "off-by-one" and r["win_kind"] is None:
        p, q = r["tok"]
        if int(re.sub(r"\D", "", q)) < int(re.sub(r"\D", "", p)):
            print("  ", r["repo"], r["sha"], r["old"].strip()[:60], "=>", r["new"].strip()[:60])

print("\n=== sign labeled pairs not reachable ===")
for r in rows:
    if r["coarse"] == "sign" and r["win_kind"] is None:
        print("  ", r["repo"], r["sha"], r["tok"], "|", r["old"].strip()[:55], "=>", r["new"].strip()[:55])
print("\n=== compare labeled pairs not reachable ===")
for r in rows:
    if r["coarse"] == "compare" and r["win_kind"] is None:
        print("  ", r["repo"], r["sha"], r["tok"], "|", r["old"].strip()[:55], "=>", r["new"].strip()[:55])
