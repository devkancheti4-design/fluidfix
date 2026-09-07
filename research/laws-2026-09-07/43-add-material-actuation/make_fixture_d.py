#!/usr/bin/env python
"""Variant D — CONTROL: identical code, but every test asserts DIRECTLY (no
shared helper).  Used to check the UNREAD observation does not misfire on the
ordinary case, where widening would be pure cost.
Usage: python make_fixture_d.py OUTDIR [--clean]
"""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_fixture as A

F = dict(A.FILES)
for rel in [k for k in F if k.startswith("tests/test_")]:
    src = F[rel]
    src = re.sub(r"^from shop\.support\.expect import .*\n", "", src, flags=re.M)
    src = re.sub(r"expect_equal\((.*), (.*)\)$", r"assert \1 == \2", src, flags=re.M)
    src = re.sub(r"expect_close\((.*), (.*)\)$", r"assert abs(\1 - \2) <= 1e-9", src, flags=re.M)
    F[rel] = src

if __name__ == "__main__":
    A.FILES = F
    out = os.path.abspath(sys.argv[1])
    A.build(out, inject="--clean" not in sys.argv)
    print("built", out, "(clean)" if "--clean" in sys.argv else "(defect injected)")
