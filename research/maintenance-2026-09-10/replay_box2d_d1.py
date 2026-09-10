#!/usr/bin/env python3
"""Replay Box2D D1 (src/table.c:30, capacity 16 -> 17) through fluidfix's own C
oracle: inject the defect, judge the PRISTINE line as a candidate, and print the
raw runner output when the verdict is red. Run from inside the configured Box2D
clone (36-box2d-lane-log/box2d):  PYTHONPATH=<fluidfix>/src python3 replay_box2d_d1.py
"""
import os, re, subprocess, sys, time
from fluidfix.coracle import COracle
F = "src/table.c"; LN = 30
PRISTINE = "\t\tset.capacity = 16;"; DEFECT = "\t\tset.capacity = 17;"
ANSI = re.compile(r"\x1b\[[0-9;]*m")
def setline(text):
    ls = open(F).read().split("\n"); assert ls[LN-1].strip() in (PRISTINE.strip(), DEFECT.strip()), ls[LN-1]
    ls[LN-1] = text; open(F, "w").write("\n".join(ls))
def raw_run():
    p = subprocess.run("./build/bin/test", shell=True, capture_output=True, text=True, errors="replace")
    return p.returncode, ANSI.sub("", (p.stdout or "") + (p.stderr or ""))
o = COracle(os.getcwd(), build_cmd="cmake --build build -j4", test_cmd="./build/bin/test", timeout=600)
setline(DEFECT); red, out = o.failing_output(); print("defect red:", red, "| fails:", o._fail_tests[:3])
N = int(sys.argv[1]) if len(sys.argv) > 1 else 4
for i in range(N):
    setline(DEFECT); o.build()
    setline(PRISTINE); t0 = time.time(); ok, why = o.check()
    rc, txt = raw_run()
    tail = [l for l in txt.splitlines() if l.strip()][-3:]
    print(f"cycle {i+1}: pristine judged {'GREEN' if ok else 'RED: ' + why[:40]} | raw rc={rc} tail={tail} ({time.time()-t0:.0f}s)", flush=True)
setline(PRISTINE); o.build(); print("restored, pristine build rc:", raw_run()[0])
