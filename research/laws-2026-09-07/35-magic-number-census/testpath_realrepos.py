#!/usr/bin/env python
"""_is_test_path applied to the ACTUAL oracle sources of the two real repos
fluidfix benchmarks on (read-only: the shared clones are only walked).

coracle.py imports guard._is_test_path and applies it to C paths at lines
441, 714 and 732 -- so this is the live filter, not a hypothetical.
"""
import os
import sys
sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix.guard import _is_test_path                       # noqa: E402

SC = ("/private/tmp/claude-501/-Users-kanchetidevieswar-neo/"
      "a9bf7d26-7aef-4c1e-a919-68bc40ac2e97/scratchpad")
EXT = (".c", ".h", ".cc", ".cpp", ".hpp", ".cxx", ".hh", ".cs")   # coracle:88

for repo in ("box2d", "cglm"):
    root = os.path.join(SC, repo)
    if not os.path.isdir(root):
        print(f"{repo}: MISSING"); continue
    seen = hidden = 0
    escapees = []
    for dp, dn, fns in os.walk(root):
        dn[:] = [d for d in dn if d != ".git"]
        for fn in fns:
            if not fn.endswith(EXT):
                continue
            rel = os.path.relpath(os.path.join(dp, fn), root).replace("\\", "/")
            # ground truth: the file lives under the repo's own test tree
            top = rel.split("/")[0]
            if top not in ("test", "tests", "unit_tests"):
                continue
            seen += 1
            if _is_test_path(rel):
                hidden += 1
            else:
                escapees.append(rel)
    print(f"\n{repo}: oracle source files under its test tree: {seen}")
    print(f"  recognised by _is_test_path: {hidden}")
    print(f"  ESCAPE (fluidfix may edit its own oracle): {len(escapees)}")
    for e in escapees[:12]:
        print(f"    {e}")
    if len(escapees) > 12:
        print(f"    ... and {len(escapees)-12} more")
