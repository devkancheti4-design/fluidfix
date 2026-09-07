#!/usr/bin/env python
"""Summarize decide_log*.jsonl written by log_decide_plugin.py.
Run:  .venv/bin/python summarize_log.py decide_log_run1.jsonl [more.jsonl ...]
"""
import collections
import json
import sys

sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix.engine import BITS  # noqa: E402

recs = []
for path in sys.argv[1:]:
    recs += [json.loads(l) for l in open(path, encoding="utf-8")]
body = [r for r in recs if r["site"]]            # calls made from src/fluidfix
direct = [r for r in recs if not r["site"]]      # tests calling decide() themselves
print(f"records: {len(recs)}  from the body: {len(body)}  direct from tests: {len(direct)}")

tests = []
for r in body:
    if r["test"] not in tests:
        tests.append(r["test"])
print(f"\ntests during which the BODY consulted the law: {len(tests)}")
for t in tests:
    print("  ", t)


def bits(x):
    return "+".join(b for i, b in enumerate(BITS) if x >> i & 1) or "<empty>"


c = collections.Counter((r["site"], r["x"], r["act"]) for r in body)
print("\nbody consultations: site, x, bits -> act (count)")
for (site, x, act), n in sorted(c.items()):
    print(f"  {site:14} x={x:3d} {bits(x):20} -> {act:22} x{n}")
print(f"\ndistinct situations the body constructed: {sorted({r['x'] for r in body})}")
print(f"distinct sites: {sorted({r['site'] for r in body})}")
