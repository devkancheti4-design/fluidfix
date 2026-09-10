#!/usr/bin/env python3
"""Replay the exact candidate order the arm used on Box2D D1 (table.c lines 21, 24, 24, 24, 30)
through fluidfix's own C oracle, restoring the defect between candidates as the loop does,
and dump raw runner output + artifact mtimes when a verdict is red."""
import os, re, subprocess, sys, time
from fluidfix.coracle import COracle
F = "src/table.c"; ANSI = re.compile(r"\x1b\[[0-9;]*m")
orig = open(F).read().split("\n")
def setline(ln, text):
    ls = open(F).read().split("\n"); ls[ln-1] = text; open(F, "w").write("\n".join(ls))
def restore_defect():
    ls = orig[:]; ls[29] = "\t\tset.capacity = 17;"; open(F, "w").write("\n".join(ls))
def raw():
    p = subprocess.run("./build/bin/test", shell=True, capture_output=True, text=True, errors="replace")
    txt = ANSI.sub("", (p.stdout or "") + (p.stderr or "")); lines = [l for l in txt.splitlines() if l.strip()]
    return p.returncode, lines[-2:]
def mt(p):
    try: return f"{os.path.getmtime(p):.2f}"
    except OSError: return "missing"
o = COracle(os.getcwd(), build_cmd="cmake --build build -j4", test_cmd="./build/bin/test", timeout=600)
restore_defect(); red, _ = o.failing_output(); print("defect red:", red, o._fail_tests[:2])
SEQ = [(21, "\tb2HashSet set = { -1 };"), (24, "\tif ( capacity >= 16 )"), (24, "\tif ( capacity > 15 )"),
       (24, "\tif ( capacity < 16 )"), (30, "\t\tset.capacity = 16;"), (33, "\tset.count = -1;")]
for ln, cand in SEQ:
    restore_defect(); setline(ln, cand); t0 = time.time(); ok, why = o.check()
    rc, tail = raw()
    print(f"table.c:{ln} {cand.strip()[:34]:36} -> {'GREEN' if ok else 'red: ' + why[:34]:40} raw rc={rc} {tail} ({time.time()-t0:.0f}s)", flush=True)
    if not ok and "fail" not in why:
        print("   mtimes table.c", mt(F), "table.c.o", mt("build/src/CMakeFiles/box2d.dir/table.c.o"), "libbox2d.a", mt("build/src/libbox2d.a"), "bin/test", mt("build/bin/test"))
open(F, "w").write("\n".join(orig)); o.build(); print("restored; pristine raw:", raw())
