#!/usr/bin/env python3
"""Replay master's cglm D1 candidate sequence through fluidfix's own C oracle
on a second cglm copy. The arm rejected the PRISTINE line at vec3.h:284 with
"9 test(s) failed, first: glm_ray_at"; this asks whether that verdict
reproduces in isolation. Run from inside a configured cglm clone:
  PYTHONPATH=<fluidfix>/src python3 replay_d1.py
"""
import os, re, subprocess, time
from fluidfix.coracle import COracle
ROOT = os.getcwd(); F = "include/cglm/vec3.h"; LN = 284
ANSI = re.compile(r"\x1b\[[0-9;]*m")
def summary():
    out = subprocess.run(["./build/tests"], capture_output=True, text=True, errors="replace")
    m = re.search(r"(\d+) tests ran, (\d+) passed, (\d+) failed", ANSI.sub("", out.stdout + out.stderr))
    return m.group(0) if m else "no summary"
def setline(text):
    ls = open(F).read().split("\n"); ls[LN-1] = text; open(F, "w").write("\n".join(ls))
PRISTINE = "  dest[0] = a[0] + b[0];"; DEFECT = "  dest[0] = a[0] - b[0];"
subprocess.run("cmake --build build -j2", shell=True, capture_output=True)
print("pristine x10:", [summary().split(", ")[-1] for _ in range(10)])
o = COracle(ROOT, build_cmd="cmake --build build -j2", test_cmd="./build/tests", timeout=300)
setline(DEFECT); red, _ = o.failing_output(); print("defect red:", red, "|", summary())
for cand in ("  dest[-1] = a[0] - b[0];", "  dest[0] = a[-1] - b[0];", "  dest[0] = a[0] - b[-1];", PRISTINE, DEFECT, PRISTINE):
    setline(cand); t0 = time.time(); ok, why = o.check()
    print(f"{cand!r:32} -> {'GREEN' if ok else 'red: ' + why[:60]}  | runner: {summary()}  ({time.time()-t0:.0f}s)")
    setline(DEFECT)          # the loop restores the defective line between candidates
setline(PRISTINE)
