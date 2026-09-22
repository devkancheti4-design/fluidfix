import sys, importlib.util
from pathlib import Path
from collections import Counter
R=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(R/"src")); sys.path.insert(0,str(R/"research/life-fluidfix-2026-09-18"))
from life_fluidfix import shapes_repair, run_test
sys.path.insert(0,str(R/"research/sibling-2026-09-22"))
from novel import instance, DICT
why=Counter(); shown=0
for form in range(1,8):
    for k in range(12):
        buggy, fixed, test = instance(form, form*1000+k)
        if run_test(buggy, test):
            why[("NOT RED before repair", form)] += 1; continue
        got = shapes_repair(buggy, test, DICT)
        if not got: why[("refused", form)] += 1; continue
        if got["code"].strip()==fixed.strip(): why[("exact", form)] += 1; continue
        why[(f"other green: kind {got['kind']} {got['shape']}", form)] += 1
        if shown < 8:
            shown += 1; print(f"form {form}  kind {got['kind']:<2} {got['shape']:26} {got['before'].strip()[:36]:36} -> {got['after'].strip()[:36]}")
print()
for (w,f),n in sorted(why.items(), key=lambda x:(x[0][1],x[0][0])): print(f"  form {f}  {n:>2}  {w}")
