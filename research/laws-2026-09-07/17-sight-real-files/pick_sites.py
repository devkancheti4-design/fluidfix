#!/usr/bin/env python
"""Pick one single-token defect site per source file, mechanically, from the
pristine whole-suite coverage (full_cov_pristine.json). Preference order:
  A  ' + ' -> ' - '   on an executed assignment/return line (flipped-additive)
  B  ' - ' -> ' + '
  C  ' < ' -> ' > '   (flipped-comparison-direction)
Excluded: lines with B2_ASSERT, comments, printf, for-loops, ++/+=, strings.
Writes defects.json: [{file, line, old, new, text}]  (first pick + alternates)."""
import json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "box2d")
FILES = sys.argv[1:] or """src/aabb.c src/bitset.c src/body.c src/broad_phase.c
src/constraint_graph.c src/contact.c src/contact_solver.c src/distance.c
src/distance_joint.c src/dynamic_tree.c src/geometry.c src/hull.c src/island.c
src/joint.c src/manifold.c src/math_functions.c src/physics_world.c
src/prismatic_joint.c src/revolute_joint.c src/shape.c""".split()
cov = json.load(open(os.path.join(HERE, "full_cov_pristine.json")))
BAD = re.compile(r"B2_ASSERT|//|/\*|\*/|printf|\bfor\s*\(|\+\+|--|\+=|-=|\"|\bsizeof|#|B2_VALIDATE|B2_UNUSED")
RULES = [(" + ", " - "), (" - ", " + "), (" < ", " > ")]
out = []
for rel in FILES:
    lines = open(os.path.join(ROOT, rel), encoding="utf-8").read().split("\n")
    execd = set(cov.get(rel, []))
    picks = []
    for old, new in RULES:
        for ln in sorted(execd):
            t = lines[ln - 1]
            if old in t and not BAD.search(t) and ("=" in t or "return" in t) and t.count(old) == 1:
                picks.append({"file": rel, "line": ln, "old": old, "new": new, "text": t.strip()})
            if len(picks) >= 4:
                break
        if len(picks) >= 4:
            break
    if not picks:
        print(f"NO SITE for {rel} ({len(execd)} executed lines)")
        continue
    out.append(picks)
    p = picks[0]
    print(f"{rel:28s} L{p['line']:<5d} {p['old']!r}->{p['new']!r}  {p['text'][:80]}")
json.dump(out, open(os.path.join(HERE, "defects.json"), "w"), indent=1)
print(len(out), "files with a site")
