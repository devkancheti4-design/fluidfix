#!/usr/bin/env python3
"""Reproduces every number in REPORT.md from results.json / followup_literal.json.
    ../../../.venv/bin/python analyze.py
"""
import json
import os
import re
import statistics as st

HERE = os.path.dirname(os.path.abspath(__file__))
R = [r for r in json.load(open(os.path.join(HERE, "results.json")))
     if "skipped" not in r]
n = len(R)
P = "/Users/kanchetidevieswar/neo/fluidfix/research/laws-2026-09-07/" \
    "19-sight-vs-coverage/cglm/test/src/test_vec3.h"

print(f"=== F1  rank of the true defect file, {n} injected defects, cglm ===")
for k, lab in (("rank_body", "BODY   (shipped C path)"),
               ("rank_purecov", "PURECOV(gcov tier alone)"),
               ("rank_sight", "SIGHT  (law + cov bits)"),
               ("rank_sight0", "SIGHT0 (law, no cov)")):
    v = [r[k] for r in R]
    print(f"  {lab}  top1={sum(x == 1 for x in v):2d}/{n} "
          f"top3={sum(x <= 3 for x in v):2d}/{n} "
          f"top5={sum(x <= 5 for x in v):2d}/{n} "
          f"median={st.median(v):4.1f} worst={max(v)}")
pre = [(r["prefix"].index(r["file"]) + 1 if r["file"] in r["prefix"] else None)
       for r in R]
print(f"  PREFIX (find_candidate_files_c only, no coverage)  "
      f"top1={sum(x == 1 for x in pre)}/{n} "
      f"top3={sum(x is not None and x <= 3 for x in pre)}/{n}  ranks={pre}")
print(f"  BODY ranks  ={[r['rank_body'] for r in R]}")
print("  -> coverage tier changes the true file's rank in exactly "
      f"{sum(1 for a, b in zip(pre, [r['rank_body'] for r in R]) if a != b)}"
      f"/{n} defects")

print("\n=== F2  the gcov tier is a constant on cglm ===")
print("  files with fail_cov == full_cov (specificity exactly 1.0): "
      f"{sum(r['n_fail_true'] == r['n_full_true'] for r in R)}/{n} true files")
print(f"  spec_hist (files with spec>=0.9 / >=0.5 / >=0.25) per defect: "
      f"{ {tuple(r['spec_hist'].values()) for r in R} } of "
      f"{ {r['n_fail_cov_files'] for r in R} } covered files")
print(f"  spec of the true file: { {r['spec_true'] for r in R} }")

print("\n=== F3  cost ===")
for key, lab in ((lambda r: r["timing"]["probe_coverage_s"]
                  + r["timing"]["full_coverage_s"], "gcov tier"),
                 (lambda r: r["timing"]["find_candidate_files_c_s"],
                  "find_candidate_files_c"),
                 (lambda r: r["sight_meta"]["measure_s"], "SIGHT 8 bits"),
                 (lambda r: r["suite_s"], "suite (oracle)")):
    v = [key(r) for r in R]
    print(f"  {lab:24s} median {st.median(v):7.3f}s  total {sum(v):8.1f}s")

print("\n=== F4  which SIGHT lanes fire on C ===")
print(f"  FRAMED on a production file : "
      f"{sum(any(not f.startswith('test') for f in r['sight_meta']['framed']) for r in R)}/{n}")
print(f"  SCARCE fired at all         : "
      f"{sum(bool(r['sight_meta']['scarce_named']) for r in R)}/{n}")
print(f"  LITERAL fired               : "
      f"{sum(bool(r['sight_meta']['lit_named']) for r in R)}/{n}, always on "
      f"{sorted({tuple(r['sight_meta']['lit_named']) for r in R})}")
print(f"  priority histogram          : {sorted({tuple(sorted(r['priority_hist'].items())) for r in R})}")

print("\n=== F5  LITERAL is harvested from the absolute path ===")
pd = sorted(set(re.findall(r"\d{2,}", P)))
print(f"  digits >=2 in the __FILE__ path cglm's ASSERT prints: {pd}")
print(f"  runs where all of them appear in assert_lits: "
      f"{sum(set(pd) <= set(r['sight_meta']['assert_lits']) for r in R)}/{n}")
print("  `07` matches only the URL comment 2013/07 in vec2.h and ivec2.h:")
os.system("grep -nE '(^|[^A-Za-z0-9_.])07([^A-Za-z0-9_.]|$)' "
          f"{HERE}/cglm/include/cglm/vec2.h {HERE}/cglm/include/cglm/ivec2.h")

fu_path = os.path.join(HERE, "followup_literal.json")
if os.path.exists(fu_path):
    print("\n=== F6  SIGHT with the path excluded from LITERAL ===")
    for r in json.load(open(fu_path)):
        print(f"  {r['id']:16s} rank body={r['rank_body']:2} "
              f"sight={r['rank_sight']:2} sight_FIX={r['rank_sight_fix']:2} "
              f"| discriminating literals left: {r['lit_hits_fix']} "
              f"| priorities {r['prio_hist_sight']} -> {r['prio_hist_fix']}")
