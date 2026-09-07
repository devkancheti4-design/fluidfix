"""Pool every fixture_a batch (original 50 per level + one 50-run replication
per level) into one false-accept table. Run: .venv/bin/python pool.py"""
import json, os, collections
HERE = os.path.dirname(os.path.abspath(__file__))
FILES = ["results_fixture_a.jsonl", "results_fixture_a_rep0.jsonl",
         "results_fixture_a_rep1.jsonl", "results_fixture_a_rep.jsonl"]
rows = [dict(json.loads(l), src=f) for f in FILES
        for l in open(os.path.join(HERE, f))]
by = collections.defaultdict(list)
for r in rows:
    by[r["confirm"]].append(r)
print(f"fixture_a, pooled over {len(FILES)} batches: {len(rows)} runs\n")
print(f"{'CONFIRM':>7} {'N':>4} {'CORRECT':>8} {'FALSE_ACCEPT':>13} "
      f"{'false-accept rate':>18} {'HIDDEN fired':>13}")
for c in sorted(by):
    rs = by[c]
    cnt = collections.Counter(r["label"] for r in rs)
    fa = cnt["FALSE_ACCEPT"]
    print(f"{c:>7} {len(rs):>4} {cnt['CORRECT']:>8} {fa:>13} "
          f"{100*fa/len(rs):>17.1f}% {sum(r['hidden_fired'] for r in rs):>13}")
print("\nper-batch, to show the batch-to-batch spread:")
for c in sorted(by):
    per = collections.defaultdict(lambda: [0, 0])
    for r in by[c]:
        per[r["src"]][0] += 1
        per[r["src"]][1] += r["label"] == "FALSE_ACCEPT"
    print(f"  CONFIRM={c}: " + "  ".join(
        f"{k.replace('results_fixture_a', '').replace('.jsonl', '') or '(first)'}"
        f"={v[1]}/{v[0]}" for k, v in per.items()))
