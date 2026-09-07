#!/usr/bin/env python
"""Dump whole-suite executed lines per source file on the PRISTINE tree,
using the body's own gcov tier (fluidfix.coracle._Coverage.lines). Output:
full_cov_pristine.json  {rel: [executed line numbers]}.
Run: nice -n 15 bin/timeout 300 ../../../.venv/bin/python cov_dump.py"""
import json, os, sys, time
sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix.coracle import COracle
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "box2d")
o = COracle(ROOT, test_cmd="./build/bin/test", build_dir="build", timeout=280)
cov = o.coverage()
print("gcov available:", cov.available())
t0 = time.time()
full = cov.lines()
print(f"cov.lines() took {time.time()-t0:.1f}s, {len(full)} files")
json.dump({k: sorted(v) for k, v in full.items()},
          open(os.path.join(HERE, "full_cov_pristine.json"), "w"), indent=0)
for rel in sorted(full, key=lambda r: -len(full[r])):
    print(f"{len(full[rel]):6d}  {rel}")
