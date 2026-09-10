#!/usr/bin/env python3
"""Run the real cguard flow on Box2D D1 (coverage tier and all) with COracle.run
instrumented: every build+test call is logged with its exit code and the tail of
its raw output, so the 'suite red' verdict on the pristine line can be read.
Run from the study dir (36-box2d-lane-log) after `python3 defects.py inject D1 box2d`."""
import os, re, sys, time
sys.path.insert(0, os.getcwd())
from fluidfix import coracle
from fluidfix.observers import MechanicalObserver
ANSI = re.compile(r"\x1b\[[0-9;]*m")
LOG = open("probe_box2d_d1.log", "w")
orig_run = coracle.COracle.run
def run(self, extra=None, timeout=None):
    src = open(os.path.join(self.root, "src/table.c")).read().split("\n")[29].strip()
    t0 = time.time(); rc, out = orig_run(self, extra, timeout)
    clean = ANSI.sub("", out or ""); tail = [l for l in clean.splitlines() if l.strip()][-2:]
    LOG.write(f"{time.strftime('%H:%M:%S')} table.c:30={src!r:28} rc={rc} {time.time()-t0:5.1f}s tail={tail}\n"); LOG.flush()
    return rc, out
coracle.COracle.run = run
o = coracle.COracle("box2d", build_cmd="cmake --build build -j4", test_cmd="./build/bin/test", timeout=300)
rep = coracle.cguard_once(o, MechanicalObserver(), budget=300)
print("STATUS", rep.status); print(rep.summary()[:400])
