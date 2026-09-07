#!/usr/bin/env python
"""Final tally for target 17-sight-real-files (agent 17, continuation run).

Reads results.jsonl (one record per injected single-token defect) and prints:
  A. per-file table: the last record for each file, its status, the rank the
     C BODY gave the true file, the rank the SIGHT LAW would have given it.
  B. top-1 / top-3 / median for both rankings over the files that produced an
     observable (red) defect.
  C. the observation-quality split: how many red defects yielded named failing
     tests at all, and how many cleared the body's credibility floor.

Run:  .venv/bin/python summarize2.py
"""
import json, os, statistics as st

HERE = os.path.dirname(os.path.abspath(__file__))
recs = [json.loads(l) for l in open(os.path.join(HERE, "results.jsonl"))]

# last record per file wins (retries append after the original green attempt)

def pick(recs):
    """One record per file: the first attempt that turned the suite red, but
    preferring a later re-measurement of that same site when it persisted the
    per-file bytes (`rows`).  Green-only files keep their last green attempt."""
    best = {}
    for r in recs:
        f = r["file"]
        cur = best.get(f)
        if cur is None:
            best[f] = r; continue
        if cur["status"] == "green" and r["status"] != "green":
            best[f] = r; continue
        if (cur["status"] != "green" and r["status"] != "green"
                and cur["line"] == r["line"] and "rows" in r and "rows" not in cur):
            best[f] = r
    return best

attempts = {}
for r in recs:
    attempts[r['file']] = attempts.get(r['file'], 0) + 1
last = pick(recs)

red = {f: r for f, r in last.items() if r["status"] != "green"}
green = {f: r for f, r in last.items() if r["status"] == "green"}

print("A. PER-FILE  (last attempt per file; 'tries' = injections needed to turn the suite red)")
print(f"{'file':26s} {'tries':>5s} {'line':>6s} {'status':8s} {'bodyN':>5s} {'bodyR':>5s} "
      f"{'lawN':>4s} {'lawR':>4s} {'cred':>4s} failing tests")
for f in sorted(last):
    r = last[f]
    ft = ",".join(r.get("fail_tests") or []) or "-"
    print(f"{f:26s} {attempts[f]:5d} {r['line']:6d} {r['status']:8s} "
          f"{str(r.get('body_len', '-')):>5s} {str(r.get('body_rank') or 'MISS' if r['status'] != 'green' else '-'):>5s} "
          f"{str(r.get('lanes', {}).get('universe', '-')):>4s} "
          f"{str(r.get('law_rank') or ('MISS' if r['status'] != 'green' else '-')):>4s} "
          f"{str(r.get('credible', '-'))[:4]:>4s} {ft[:44]}")

print(f"\nfiles injected: {len(last)}   red (observable): {len(red)}   "
      f"green (defect invisible to the suite): {len(green)}")
print("green files:", ", ".join(sorted(green)) or "none")


def tally(name, key, pool):
    vals = [r.get(key) for r in pool.values()]
    hit = [v for v in vals if v is not None]
    miss = len(vals) - len(hit)
    if not hit:
        print(f"\n{name}: no ranked file -- unmeasured")
        return
    print(f"\n{name}  over {len(vals)} red defects")
    print(f"  true file ranked at all : {len(hit)}/{len(vals)}   not in the list at all: {miss}")
    print(f"  top-1 : {sum(1 for v in hit if v == 1)}/{len(vals)}"
          f"  ({sum(1 for v in hit if v == 1) / len(vals) * 100:.0f}% of red defects)")
    print(f"  top-3 : {sum(1 for v in hit if v <= 3)}/{len(vals)}"
          f"  ({sum(1 for v in hit if v <= 3) / len(vals) * 100:.0f}%)")
    print(f"  top-5 : {sum(1 for v in hit if v <= 5)}/{len(vals)}"
          f"  ({sum(1 for v in hit if v <= 5) / len(vals) * 100:.0f}%)")
    print(f"  median rank among the {len(hit)} ranked: {st.median(hit):g}   "
          f"mean {st.mean(hit):.1f}   worst {max(hit)}")
    print(f"  ranks: {sorted(hit)}")


print("\nB. RANKINGS")
tally("BODY file order (coracle.find_candidate_files_c)", "body_rank", red)
tally("SIGHT law order (sight() on the same coverage)", "law_rank", red)

# law order only exists where the body produced named failing tests
named = {f: r for f, r in red.items() if r.get("fail_tests")}
unnamed = {f: r for f, r in red.items() if not r.get("fail_tests")}
print("\nC. OBSERVATION QUALITY")
print(f"  red defects with >=1 NAMED failing test : {len(named)}/{len(red)}")
print(f"  red defects with NO named failing test  : {len(unnamed)}/{len(red)}"
      f"  -> {', '.join(sorted(unnamed))}")
print(f"  red defects the body called 'credible'  : "
      f"{sum(1 for r in red.values() if r.get('credible'))}/{len(red)}"
      f"   (coracle floor: >=5 non-test files in the failing tests' coverage)")
print("  on the named subset only:")
tally("  BODY", "body_rank", named)
tally("  LAW ", "law_rank", named)

print("\nD. WHERE THE TWO ORDERS DISAGREE (named subset)")
print(f"{'file':26s} {'body':>5s} {'law':>5s} {'delta':>6s}  bits set")
deltas = []
for f in sorted(named):
    r = named[f]
    b, l = r.get("body_rank"), r.get("law_rank")
    d = (b - l) if (b and l) else None
    if d is not None:
        deltas.append(d)
    bits = ",".join(k.upper() for k, v in (r.get("true_bits") or {}).items() if v) or "-"
    print(f"{f:26s} {str(b or 'MISS'):>5s} {str(l or 'MISS'):>5s} "
          f"{('%+d' % d) if d is not None else '   -':>6s}  {bits}")
if deltas:
    print(f"\n  law ranks the true file HIGHER than the body on {sum(1 for d in deltas if d > 0)}"
          f"/{len(deltas)} defects, lower on {sum(1 for d in deltas if d < 0)}, tied on "
          f"{sum(1 for d in deltas if d == 0)}; median delta {st.median(deltas):+g}")

print("\nE. SIGHT BITS ACTUALLY SET on the true file (named subset)")
allbits = ["framed", "scarce", "literal", "failonly", "named", "touched", "small", "ubiquitous"]
for bit in allbits:
    n = sum(1 for r in named.values() if (r.get("true_bits") or {}).get(bit))
    print(f"  {bit.upper():11s} set on {n:2d}/{len(named)} true files")
