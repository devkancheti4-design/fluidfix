#!/usr/bin/env python3
"""Fill the C tables in RESULT.md from c/summary.txt, c_master/summary.txt and classify_c.py."""
import os, re, subprocess, sys
M = os.path.dirname(os.path.abspath(__file__))
def parse(summary):
    rows = {}
    if not os.path.exists(summary): return rows
    cur = None
    for line in open(summary):
        m = re.match(r"== (D\d) exit=(\d+) wall=(\d+)s", line)
        if m: cur = m[1]; rows[cur] = dict(exit=int(m[2]), wall=int(m[3]), head="", hint="", diff="")
        elif cur and ("repaired" in line or "REFUSED" in line) and not rows[cur]["head"]:
            rows[cur]["head"] = line.strip()[:110]
        elif cur and "hint:" in line and not rows[cur]["hint"]:
            rows[cur]["hint"] = re.sub(r"\s+", " ", line.split("hint:", 1)[1]).strip()[:120]
        elif cur and re.match(r"\d+\t\d+\t", line): rows[cur]["diff"] += line.strip().replace("\t", " ") + " "
    return rows
LAB = {"D1": "vec3.h:284 flipped additive", "D2": "ivec3.h:132 index off-by-one", "D3": "ray.h:140 comparison direction",
       "D4": "ivec2.h:318 augmented assign", "D5": "vec2.h:653 min/max"}
BOX = {"D1": "table.c:30 literal off-by-one", "D2": "math_functions.c:120 comparison direction", "D3": "geometry.c:230 literal off-by-one",
       "D4": "distance.c:47 comparison direction", "D5": "aabb.c:13 comparison direction"}
def table(dirA="c/summary.txt", dirB="c_master/summary.txt", LAB=LAB, hA="0.15.0 (released)", hB="master"):
    a, b = parse(os.path.join(M, dirA)), parse(os.path.join(M, dirB))
    out = [f"| defect | {hA} | {hB} | tree after run (before restore) |", "|---|---|---|---|"]
    for D in sorted(LAB):
        def cell(r):
            if not r: return "not run"
            if r["exit"] == 0 and "repaired" in r["head"]: return f"**repaired byte-exact**, {r['wall']} s"
            if r["exit"] != 2: return f"exit {r['exit']} (wrapper timeout)" if r["exit"] == 124 else f"exit {r['exit']}, {r['wall']} s"
            h = r["hint"]
            why = ("green found, withheld as unproven-unique (BUILT+CAPPED → RAISE_BUDGET)" if "shown unique" in h
                   else "budget, defect line not reached (CAPPED → RAISE_BUDGET)" if "budget exhausted" in h
                   else "every candidate red (REFUTED → HARVEST_COUNTEREXAMPLE)" if "left the suite red" in h
                   else h[:60])
            return f"refused, {r['wall']} s — {why}"
        ra, rb = a.get(D), b.get(D)
        diff = (ra or rb or {}).get("diff", "").strip() or "clean"
        out.append(f"| {D} {LAB[D]} | {cell(ra)} | {cell(rb)} | `{diff}` |")
    return "\n".join(out)
L = "/Users/kanchetidevieswar/neo/fluidfix/research/laws-2026-09-07"
def classify(d, study="37-cglm-lane-log", clone="cglm"):
    p = os.path.join(M, d)
    if not os.path.isdir(p): return "(pending)"
    r = subprocess.run([sys.executable, os.path.join(M, "classify_c.py"), p, os.path.join(L, study), clone], capture_output=True, text=True).stdout.strip()
    return "```\n" + r + "\n```" if r else "(no refusal records)"
def ran(summary):
    return set(parse(os.path.join(M, summary)))
res = os.path.join(M, "RESULT.md"); t = open(res).read()
t = t.replace("<<C_TABLE>>", table())
t = t.replace("<<C_CLASSIFY>>", "Released 0.15.0:\n\n" + classify("c") + "\n\nMaster (after the kind-1 fix):\n\n" + classify("c_master"))
t = t.replace("<<C_FIXED_TABLE>>", table("c_master/summary.txt", "c_fixed/summary.txt", LAB, "master 44346f7 (stale oracle)", "master 7233933 (fixed)"))
t = t.replace("<<C_FIXED_CLASSIFY>>", classify("c_fixed"))
sub = {k: v for k, v in LAB.items() if k in ran("c_fixed_900/summary.txt")}
t = t.replace("<<C900_TABLE>>", table("c_fixed/summary.txt", "c_fixed_900/summary.txt", sub, "fixed, --budget 300", "fixed, --budget 900") if sub else "(no refusal was left to re-run)")
t = t.replace("<<C900_CLASSIFY>>", classify("c_fixed_900") if sub else "")
t = t.replace("<<BOX2D2_TABLE>>", table("box2d_master/summary.txt", "box2d_master2/summary.txt", BOX, "first run (harness fault)", "second run (stale oracle)"))
t = t.replace("<<BOX2D_FIXED_TABLE>>", table("box2d_master2/summary.txt", "box2d_fixed/summary.txt", BOX, "master 44346f7 (stale oracle)", "master 7233933 (fixed)"))
t = t.replace("<<BOX2D_FIXED_CLASSIFY>>", classify("box2d_fixed", "36-box2d-lane-log", "box2d"))
idle = os.path.join(M, "full_suite_master_idle.log")
t = t.replace("<<SUITE_IDLE>>", ("**" + open(idle).read().strip().splitlines()[-1].strip() + "**") if os.path.exists(idle) else "(pending)")
open(res, "w").write(t); print("filled; placeholders left:", t.count("<<"))
