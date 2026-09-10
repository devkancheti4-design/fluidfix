#!/usr/bin/env python3
"""Classify every rejected C candidate against the pristine line it edited:
did the edit change a digit glued to an identifier (never a literal), a real
literal, an operator, min/max, or something else?
usage: classify_c.py <results-dir> <study-dir> <clone-subdir>
  study-dir holds defects.py (DEFECTS: id -> (relpath, line, original, defective, kind));
  pristine lines come from `git show HEAD:<relpath>` in the clone."""
import json, os, re, sys, collections, subprocess, importlib.util
CD, STUDY, CLONE = sys.argv[1], sys.argv[2], sys.argv[3]
spec = importlib.util.spec_from_file_location("defects", os.path.join(STUDY, "defects.py"))
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
DEFECTS = mod.DEFECTS
root = os.path.join(STUDY, CLONE)
_cache = {}
def pristine_line(rel, ln):
    if rel not in _cache:
        _cache[rel] = subprocess.run(["git", "-C", root, "show", f"HEAD:{rel}"], capture_output=True, text=True).stdout.split("\n")
    return _cache[rel][ln - 1] if ln - 1 < len(_cache[rel]) else ""
def kind_of_edit(orig, cand):
    i = 0
    while i < min(len(orig), len(cand)) and orig[i] == cand[i]: i += 1
    j = 0
    while j < min(len(orig), len(cand)) - i and orig[-1 - j] == cand[-1 - j]: j += 1
    a, b = orig[i:len(orig) - j], cand[i:len(cand) - j]; before = orig[:i]
    if (a.isdigit() or b.isdigit()) and re.search(r"[A-Za-z_\d]$", before): return "identifier-digit"
    if a.isdigit() or b.isdigit(): return "literal"
    if re.search(r"[-+*/<>=!]", a + b): return "operator"
    if "min" in a + b or "max" in a + b: return "minmax"
    return "other"
for D in sorted(DEFECTS):
    rel, ln = DEFECTS[D][0], DEFECTS[D][1]
    p = os.path.join(CD, f"{D}.refusal.json")
    if not os.path.exists(p):
        log = os.path.join(CD, f"{D}.log")
        if os.path.exists(log) and "repaired" in open(log).read():
            m = re.search(r"repaired line (\d+) in (\d+) suite runs \(([\d.]+)s\)", open(log).read())
            print(f"{D}: REPAIRED {rel}:{m[1]} in {m[2]} suite runs, {m[3]} s" if m else f"{D}: repaired")
        else: print(f"{D}: (no record yet)")
        continue
    j = json.load(open(p)); rej = j.get("rejected_candidates", [])
    cnt = collections.Counter(); reached = False
    for r in rej:
        rr, l = r["at"].rsplit(":", 1); l = int(l)
        if rr == rel and l == ln: reached = True
        cnt[kind_of_edit(pristine_line(rr, l), r["tried"])] += 1
    sites = sorted({int(r["at"].rsplit(":", 1)[1]) for r in rej}); files = sorted({r["at"].rsplit(":", 1)[0].split("/")[-1] for r in rej})
    print(f"{D}: {len(rej):3d} rejected | {dict(cnt)} | files {files} lines {sites[0] if sites else '-'}..{sites[-1] if sites else '-'} | defect {rel.split('/')[-1]}:{ln} reached: {reached} | {j.get('status')}")
