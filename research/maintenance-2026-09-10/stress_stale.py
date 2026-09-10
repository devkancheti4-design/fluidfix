"""Fast write/build cycles through fluidfix's C oracle: write the defect, build,
then write the PRISTINE line immediately (same wall-clock second) and judge it.
A correct oracle says GREEN every time."""
import os, sys, time
from fluidfix.coracle import COracle
F = "include/cglm/vec3.h"; LN = 284
PRISTINE = "  dest[0] = a[0] + b[0];"; DEFECT = "  dest[0] = a[0] - b[0];"
def setline(text):
    ls = open(F).read().split("\n"); ls[LN-1] = text; open(F, "w").write("\n".join(ls))
o = COracle(os.getcwd(), build_cmd="cmake --build build -j4", test_cmd="./build/tests", timeout=300)
setline(DEFECT); o.failing_output()
red = 0; N = int(sys.argv[1]) if len(sys.argv) > 1 else 8
for i in range(N):
    setline(DEFECT); rc, _ = o.build()                 # defect compiled
    setline(PRISTINE)                                  # pristine written right after the build ends
    ok, why = o.check()
    print(f"cycle {i+1}: pristine judged {'GREEN' if ok else 'RED  <- stale: ' + why[:50]}", flush=True)
    red += (not ok)
print(f"RED verdicts on pristine: {red}/{N}")
setline(PRISTINE)
