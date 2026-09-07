#!/usr/bin/env python
"""Build the gcov tier on the Box2D copy and dump executed lines to
coverage.json, using fluidfix's own _Coverage class (coracle.py)."""
import json, os, sys, time
sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix.coracle import COracle, _Coverage
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "box2d_copy")
o = COracle(ROOT, test_cmd="./build/bin/test", timeout=240)
cov = _Coverage(o)
print("gcov available:", cov.available())
t = time.time()
lines = cov.lines(timeout=240)
print(f"full-suite coverage in {time.time()-t:.1f}s; files={len(lines)}")
out = {k: sorted(v) for k, v in lines.items()}
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 "coverage.json"), "w"))
cs = out.get("src/contact_solver.c", [])
print("src/contact_solver.c executed lines:", len(cs))
